import os
import sys
import subprocess
from pathlib import Path

# Ensure ffmpeg path is added to PATH environment variable on Windows
if os.name == 'nt':
    extra_paths = [
        r"C:\Program Files (x86)\iMobie\AnyMiro\FFmpeg",
        r"C:\ffmpeg\bin",
        r"C:\Program Files\ffmpeg\bin",
    ]
    for path in extra_paths:
        if os.path.exists(path):
            # Prepend to front of PATH so it overrides any broken symlinks (like Microsoft WinGet's links)
            paths = os.environ["PATH"].split(os.pathsep)
            if path in paths:
                paths.remove(path)
            os.environ["PATH"] = os.pathsep.join([path] + paths)

import whisper
import asyncio
import edge_tts
import requests
import torch
import argparse
import shutil
from deep_translator import GoogleTranslator

import traceback
import replicate
from audio_separator.separator import Separator
try:
    from gradio_client import Client, handle_file
except ImportError:
    from gradio_client import Client
    def handle_file(path):
        return path
from dotenv import load_dotenv

# Add OpenVoice to path
OPENVOICE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "OpenVoice")
sys.path.insert(0, OPENVOICE_DIR)

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY", "")

def update_status(job_id, status_text):
    """Write current status to a temp file for the backend to read."""
    if job_id:
        # Use absolute path for status files to avoid working directory issues
        root_dir = os.path.dirname(os.path.abspath(__file__))
        status_file = os.path.join(root_dir, f"status_{job_id}.txt")
        try:
            with open(status_file, "w", encoding="utf-8") as f:
                f.write(status_text)
            print(f"STATUS: {status_text}")
        except Exception as e:
            print(f"FAILED TO UPDATE STATUS: {e}")

# ──────────────────────────────────────────────────────────────
# Step 1: Extract audio from video
# ──────────────────────────────────────────────────────────────
def extract_audio(video_path, audio_path, job_id=None):
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Input video file not found: {video_path}")
        
    update_status(job_id, "Step 1/7: Extracting original audio...")
    # Keep stderr for debugging if needed, or at least don't swallow it entirely if it fails
    command = ["ffmpeg", "-y", "-i", video_path, "-q:a", "0", "-map", "a", audio_path]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"FFMPEG ERROR: {result.stderr}")
        raise RuntimeError(f"FFmpeg audio extraction failed: {result.stderr}")

# ──────────────────────────────────────────────────────────────
# Step 2: Separate vocals from background using audio-separator
# ──────────────────────────────────────────────────────────────
def separate_audio(audio_path, output_dir, job_id=None):
    separator = Separator(output_dir=output_dir)
    
    # Check for existing stems first
    vocals_path = None
    instrumental_path = None
    if os.path.exists(output_dir):
        files = os.listdir(output_dir)
        for f in files:
            f_lower = f.lower()
            if "vocal" in f_lower:
                vocals_path = os.path.join(output_dir, f)
            elif "instrument" in f_lower or "no_vocal" in f_lower or "accomp" in f_lower:
                instrumental_path = os.path.join(output_dir, f)
    
    if vocals_path and instrumental_path:
        update_status(job_id, "Reusing existing separated audio stems...")
        return vocals_path, instrumental_path

    update_status(job_id, "Step 2/7: Separating vocals from background (AI Isolation)...")
    separator.load_model()
    output_files = separator.separate(audio_path)
    
    vocals_path = None
    instrumental_path = None
    for f in output_files:
        f_lower = f.lower()
        if "vocal" in f_lower:
            vocals_path = os.path.join(output_dir, f) if not os.path.isabs(f) else f
        elif "instrument" in f_lower or "no_vocal" in f_lower or "accomp" in f_lower:
            instrumental_path = os.path.join(output_dir, f) if not os.path.isabs(f) else f

    if not vocals_path and len(output_files) >= 2:
        instrumental_path = output_files[0]
        vocals_path = output_files[1]
    elif not vocals_path and len(output_files) == 1:
        vocals_path = output_files[0]

    return vocals_path, instrumental_path

# ──────────────────────────────────────────────────────────────
# Step 3: Transcribe and translate using Whisper
# ──────────────────────────────────────────────────────────────
def transcribe_and_translate(audio_path, model_size="small", target_language=None, job_id=None):
    update_status(job_id, f"Step 3/7: Transcribing speech using Whisper ({model_size})...")
    model = whisper.load_model(model_size)
    
    options = {"task": "transcribe"} # We transcribe first to auto-detect the original language
        
    result = model.transcribe(audio_path, **options)
    segments = result["segments"]

    if target_language and target_language.lower() not in ["auto-detect", "auto-detect language", "none", ""]:
        update_status(job_id, f"Step 3.5/7: Translating text to {target_language}...")
        lang_map = {
            "spanish": "es", "french": "fr", "german": "de", "italian": "it",
            "portuguese": "pt", "hindi": "hi", "english": "en", "japanese": "ja",
            "korean": "ko", "chinese": "zh-CN", "russian": "ru", "kannada": "kn",
            "malayalam": "ml", "tamil": "ta", "telugu": "te", "marathi": "mr",
            "bengali": "bn", "punjabi": "pa", "arabic": "ar", "turkish": "tr",
            "vietnamese": "vi", "thai": "th"
        }
        target_code = lang_map.get(target_language.lower(), "en")
        
        for segment in segments:
            original_text = segment["text"]
            if original_text.strip():
                try:
                    translated = GoogleTranslator(source='auto', target=target_code).translate(original_text)
                    segment["text"] = translated
                except Exception as e:
                    print(f"Translation error: {e}")
                    
    return segments

# ──────────────────────────────────────────────────────────────
# Step 4: Generate base English TTS
# ──────────────────────────────────────────────────────────────
async def generate_tts_segment(text, output_path, target_language="english", duration=1.0):
    # Check if there is any readable text (contains alphanumeric characters)
    if not text or not any(c.isalnum() for c in text):
        # Generate silence of the specified duration using ffmpeg
        subprocess.run([
            "ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono",
            "-t", str(max(0.1, duration)), output_path
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return

    if not target_language or target_language.lower() in ["auto-detect", "auto-detect language", "none", ""]:
        target_language = "english"
        
    is_english = target_language.lower() == "english"

    if is_english and ELEVENLABS_API_KEY:
        url = f"https://api.elevenlabs.io/v1/text-to-speech/21m00Tcm4TlvDq8ikWAM"
        headers = {"Accept": "audio/mpeg", "Content-Type": "application/json", "xi-api-key": ELEVENLABS_API_KEY}
        data = {"text": text, "model_id": "eleven_monolingual_v1", "voice_settings": {"stability": 0.5, "similarity_boost": 0.5}}
        response = requests.post(url, json=data, headers=headers)
        if response.status_code == 200:
            with open(output_path, 'wb') as f:
                f.write(response.content)
            return

    voice_map = {
        "spanish": "es-ES-AlvaroNeural",
        "french": "fr-FR-HenriNeural",
        "german": "de-DE-KillianNeural",
        "italian": "it-IT-DiegoNeural",
        "portuguese": "pt-PT-DuarteNeural",
        "hindi": "hi-IN-MadhurNeural",
        "english": "en-US-ChristopherNeural",
        "japanese": "ja-JP-KeitaNeural",
        "korean": "ko-KR-InJoonNeural",
        "chinese": "zh-CN-YunxiNeural",
        "russian": "ru-RU-DmitryNeural",
        "kannada": "kn-IN-GaganNeural",
        "malayalam": "ml-IN-MidhunNeural",
        "tamil": "ta-IN-ValluvarNeural",
        "telugu": "te-IN-MohanNeural",
        "marathi": "mr-IN-AarohiNeural",
        "bengali": "bn-IN-BashkarNeural",
        "arabic": "ar-SA-HamedNeural",
        "turkish": "tr-TR-AhmetNeural",
        "vietnamese": "vi-VN-HoaiMyNeural",
        "thai": "th-TH-NiwatNeural"
    }
    voice = voice_map.get(target_language.lower(), "en-US-ChristopherNeural")
    
    try:
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(output_path)
    except Exception as e:
        print(f"TTS synthesis failed for text={repr(text)}, voice={voice}: {e}. Generating fallback silence.")
        # Generate silence of the specified duration using ffmpeg
        subprocess.run([
            "ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono",
            "-t", str(max(0.1, duration)), output_path
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

# ──────────────────────────────────────────────────────────────
# Step 5: Clone voice using OpenVoice
# ──────────────────────────────────────────────────────────────
def setup_openvoice(job_id=None):
    update_status(job_id, "Step 4/7: Initializing AI Voice Cloning...")
    from openvoice.api import ToneColorConverter
    from huggingface_hub import snapshot_download

    ckpt_dir = os.path.join(OPENVOICE_DIR, "checkpoints_v2")
    if not os.path.exists(ckpt_dir):
        snapshot_download(repo_id="myshell-ai/OpenVoiceV2", local_dir=ckpt_dir)

    converter_ckpt = os.path.join(ckpt_dir, "converter")
    device = "cuda:0" if torch.cuda.is_available() else "cpu"
    tone_color_converter = ToneColorConverter(os.path.join(converter_ckpt, "config.json"), device=device)
    tone_color_converter.load_ckpt(os.path.join(converter_ckpt, "checkpoint.pth"))
    return tone_color_converter, device

def clone_voice(tone_color_converter, source_audio_path, reference_audio_path, output_path, device):
    target_se = tone_color_converter.extract_se(reference_audio_path)
    source_se = tone_color_converter.extract_se(source_audio_path)
    tone_color_converter.convert(
        audio_src_path=source_audio_path, src_se=source_se, tgt_se=target_se, 
        output_path=output_path, tau=0.3
    )

# ──────────────────────────────────────────────────────────────
# Step 6: Build dubbed audio track
# ──────────────────────────────────────────────────────────────
def build_dubbed_audio(segments, output_audio_path, target_language="english", vocals_path=None, tone_color_converter=None, device=None, job_id=None):
    update_status(job_id, f"Step 5-6/7: Generating cloned {target_language} voice segments...")
    inputs = []
    filter_complex = []
    use_voice_cloning = tone_color_converter is not None and vocals_path is not None

    for i, segment in enumerate(segments):
        text = segment["text"].strip()
        start_ms = int(segment["start"] * 1000)
        duration = max(0.1, segment["end"] - segment["start"])
        
        temp_tts_path = f"temp_tts_{i}.mp3"
        if i % 5 == 0:
            update_status(job_id, f"Processing voice segment {i+1}/{len(segments)}...")
            
        asyncio.run(generate_tts_segment(text, temp_tts_path, target_language, duration))

        if use_voice_cloning:
            cloned_path = f"temp_cloned_{i}.wav"
            try:
                clone_voice(tone_color_converter, temp_tts_path, vocals_path, cloned_path, device)
                if os.path.exists(temp_tts_path): os.remove(temp_tts_path)
                temp_tts_path = cloned_path
            except Exception as e:
                print(f"Skipping cloning for segment {i}: {e}")
        
        inputs.extend(["-i", temp_tts_path])
        filter_complex.append(f"[{i}]adelay={start_ms}|{start_ms}[a{i}];")
        
    if not inputs: return

    amix_inputs = "".join([f"[a{i}]" for i in range(len(segments))])
    filter_complex.append(f"{amix_inputs}amix=inputs={len(segments)}:dropout_transition=0:normalize=0[aout]")
    
    update_status(job_id, "Stitching audio segments...")
    command = ["ffmpeg", "-y"] + inputs + ["-filter_complex", "".join(filter_complex), "-map", "[aout]", output_audio_path]
    subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    # Cleanup
    for i in range(len(segments)):
        for prefix in ["temp_tts_", "temp_cloned_"]:
            path = f"{prefix}{i}.mp3" if "tts" in prefix else f"{prefix}{i}.wav"
            if os.path.exists(path): os.remove(path)

# ──────────────────────────────────────────────────────────────
# Step 7: Mux audio back into video
# ──────────────────────────────────────────────────────────────
def mux_audio_video(video_path, background_audio_path, dubbed_audio_path, output_video_path, job_id=None):
    update_status(job_id, "Step 7/7: Mixing final audio and rendering video...")
    
    if background_audio_path and os.path.exists(background_audio_path):
        command = [
            "ffmpeg", "-y", "-i", video_path, "-i", background_audio_path, "-i", dubbed_audio_path,
            "-filter_complex", "[1:a]volume=0.8[bg];[2:a]volume=1.0[tts];[bg][tts]amix=inputs=2:duration=first:dropout_transition=0:normalize=0[aout]",
            "-map", "0:v:0", "-map", "[aout]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", output_video_path
        ]
    else:
        command = [
            "ffmpeg", "-y", "-i", video_path, "-i", dubbed_audio_path,
            "-filter_complex", "[0:a]volume=0.08[orig];[1:a]volume=1.0[tts];[orig][tts]amix=inputs=2:duration=first:dropout_transition=0:normalize=0[aout]",
            "-map", "0:v:0", "-map", "[aout]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", output_video_path
        ]
    subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def _write_output_file(output_value, output_path):
    if isinstance(output_value, str):
        response = requests.get(output_value, timeout=120)
        response.raise_for_status()
        with open(output_path, "wb") as file:
            file.write(response.content)
        return

    if hasattr(output_value, "read"):
        with open(output_path, "wb") as file:
            file.write(output_value.read())
        return

    if isinstance(output_value, list) and output_value:
        _write_output_file(output_value[0], output_path)
        return

    raise RuntimeError(f"Unsupported LipSync output type: {type(output_value)!r}")

def _apply_replicate_lipsync(video_path, audio_path, output_path, job_id=None):
    token = os.environ.get("REPLICATE_API_TOKEN", "").strip()
    if not token:
        raise RuntimeError("REPLICATE_API_TOKEN is not set")

    update_status(job_id, "Step 8/8: Applying AI LipSync (Replicate)...")

    client = replicate.Client(api_token=token)
    uploaded_video = client.files.create(Path(video_path))
    uploaded_audio = client.files.create(Path(audio_path))

    result = client.run(
        "heygen/lipsync-speed",
        input={
            "video": uploaded_video.urls["get"],
            "audio": uploaded_audio.urls["get"],
            "enable_dynamic_duration": True,
            "disable_music_track": True,
            "enable_speech_enhancement": True,
        },
    )

    _write_output_file(result, output_path)
    return True

# ──────────────────────────────────────────────────────────────
# Step 8: LipSync (Optional) using Hugging Face
# ──────────────────────────────────────────────────────────────
def apply_lipsync(video_path, audio_path, output_path, job_id=None):
    replicate_token = os.environ.get("REPLICATE_API_TOKEN", "").strip()
    try:
        if replicate_token:
            return _apply_replicate_lipsync(video_path, audio_path, output_path, job_id)

        update_status(job_id, "Step 8/8: Applying AI LipSync (Hugging Face)...")
        SPACE_ID = "manavisrani07/gradio-lipsync-wav2lip"
        client = Client(SPACE_ID)
        result = client.predict(
            video=handle_file(video_path),
            audio=handle_file(audio_path),
            checkpoint="wav2lip_gan",
            no_smooth=0,
            resize_factor=1,
            pad_top=0,
            pad_bottom=0,
            pad_left=0,
            api_name="/generate"
        )

        final_video_path = result if isinstance(result, str) else result.get("video")

        if final_video_path and os.path.exists(final_video_path):
            shutil.copy(final_video_path, output_path)
            return True
        raise RuntimeError("LipSync result file not found.")

    except Exception as e:
        print(f"LipSync failed (this is optional, core dubbing still works): {e}")
        update_status(job_id, f"LipSync skipped (optional feature unavailable)")
        # Fallback: copy original dubbed video to output
        if video_path != output_path:
            shutil.copy(video_path, output_path)
        return False

# ──────────────────────────────────────────────────────────────
# Main pipeline
# ──────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Professional Video Dubbing Pipeline")
    parser.add_argument("video_file", help="Path to the source video file")
    parser.add_argument("--target_language", help="Target language to dub into", default=None)
    parser.add_argument("--model", help="Whisper model size", default="small")
    parser.add_argument("--job-id", help="Unique identifier for status tracking", default=None)
    parser.add_argument("--lipsync", action="store_true", help="[OPTIONAL] Enable LipSync using Hugging Face (free public Space, may be unreliable). Default: disabled. Core dubbing works without it.")
    
    args = parser.parse_args()
    video_file = args.video_file
    job_id = args.job_id

    base_name = os.path.splitext(os.path.basename(video_file))[0]
    safe_name = base_name.replace(" ", "_")
    temp_audio = f"{safe_name}_temp_audio.wav"
    dubbed_audio = f"{safe_name}_dubbed_audio.wav"
    output_video = f"{base_name}_dubbed.mp4"
    sep_dir = f"{safe_name}_separated"
    os.makedirs(sep_dir, exist_ok=True)

    try:
        extract_audio(video_file, temp_audio, job_id)
        vocals_path, instrumental_path = separate_audio(temp_audio, sep_dir, job_id)
        segments = transcribe_and_translate(vocals_path or temp_audio, model_size=args.model, target_language=args.target_language, job_id=job_id)
        
        try:
            tone_color_converter, device = setup_openvoice(job_id)
        except Exception as e:
            tone_color_converter, device = None, None
        
        build_dubbed_audio(segments, dubbed_audio, args.target_language, vocals_path, tone_color_converter, device, job_id)
        
        temp_muxed_video = f"{safe_name}_temp_muxed.mp4"
        mux_audio_video(video_file, instrumental_path, dubbed_audio, temp_muxed_video, job_id)
        
        if args.lipsync:
            success = apply_lipsync(temp_muxed_video, dubbed_audio, output_video, job_id)
            if not success:
                # Fallback to muxed video if lipsync fails
                shutil.copy(temp_muxed_video, output_video)
        else:
            shutil.copy(temp_muxed_video, output_video)
            
        if os.path.exists(temp_muxed_video):
            os.remove(temp_muxed_video)
            
        update_status(job_id, "DONE")
        print(f"\nSUCCESS! Dubbed video saved as: {output_video}")
    except Exception:
        error_msg = traceback.format_exc()
        update_status(job_id, f"ERROR: See dubber_out.log")
        sys.stderr.write(f"\nFATAL ERROR in dubber.py:\n{error_msg}\n")
        sys.exit(1)
    finally:
        if os.path.exists(temp_audio): os.remove(temp_audio)
        if os.path.exists(dubbed_audio): os.remove(dubbed_audio)

if __name__ == "__main__":
    main()
