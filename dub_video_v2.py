#!/usr/bin/env python3
"""
Kannada → English Video Dubbing Pipeline (Improved Version)
=============================================================
- Better transcription with Whisper large model
- Saves transcript for review
- Adjusts TTS speed to match original timing
- Option to mix original audio (background) with dubbed speech
- Better segment handling

Usage:
    python dub_video_v2.py input_video.mp4 output_video.mp4
"""

import argparse
import asyncio
import json
import os
import shutil
import sys
import time
import math

import whisper
from deep_translator import GoogleTranslator
from pydub import AudioSegment
import edge_tts
import ffmpeg


# ─────────────────────────── helpers ────────────────────────────

def ensure_ffmpeg():
    """Check that ffmpeg is available on PATH."""
    if shutil.which("ffmpeg") is None:
        sys.exit(
            "ERROR: ffmpeg not found on PATH.\n"
            "Install it from https://ffmpeg.org/download.html and ensure it is on your PATH."
        )


def extract_audio(video_path: str, audio_path: str):
    """Extract audio from video as 16 kHz mono WAV (Whisper's expected format)."""
    print(f"[1/8] Extracting audio from '{video_path}' ...")
    (
        ffmpeg
        .input(video_path)
        .output(audio_path, ac=1, ar=16000, format="wav")
        .overwrite_output()
        .run(quiet=True)
    )
    print(f"       Saved to '{audio_path}'")


def extract_audio_stereo(video_path: str, audio_path: str):
    """Extract audio from video as stereo WAV for background mixing."""
    (
        ffmpeg
        .input(video_path)
        .output(audio_path, ac=2, ar=44100, format="wav")
        .overwrite_output()
        .run(quiet=True)
    )


def chunk_audio(audio_path: str, chunk_dir: str, chunk_minutes: int = 5):
    """Split a WAV file into smaller chunks and return the list of chunk paths."""
    print(f"[2/8] Splitting audio into ~{chunk_minutes}-minute chunks ...")
    audio = AudioSegment.from_wav(audio_path)
    chunk_ms = chunk_minutes * 60 * 1000
    total_chunks = math.ceil(len(audio) / chunk_ms)
    paths = []
    for i in range(total_chunks):
        start = i * chunk_ms
        end = min((i + 1) * chunk_ms, len(audio))
        chunk = audio[start:end]
        chunk_path = os.path.join(chunk_dir, f"chunk_{i:04d}.wav")
        chunk.export(chunk_path, format="wav")
        paths.append((chunk_path, start / 1000.0))  # (path, offset_seconds)
    print(f"       Created {len(paths)} chunk(s)")
    return paths


def transcribe_chunks(chunks, model_name: str = "large", temp_dir: str = None):
    """Transcribe each audio chunk with Whisper using translation mode.
    Returns a flat list of segments with absolute timestamps.
    """
    print(f"[3/8] Transcribing with Whisper (model={model_name}, task=translate to English) ...")
    model = whisper.load_model(model_name)
    all_segments = []
    
    for idx, (chunk_path, offset) in enumerate(chunks):
        print(f"       Transcribing chunk {idx + 1}/{len(chunks)} ...")
        # Use task="translate" to directly translate to English!
        result = model.transcribe(
            chunk_path, 
            language="kn",  # Source language: Kannada
            task="translate",  # Whisper will translate to English directly
            verbose=False,
            condition_on_previous_text=True,  # Better context
            compression_ratio_threshold=2.4,
            logprob_threshold=-1.0,
            no_speech_threshold=0.6,
        )
        for seg in result.get("segments", []):
            all_segments.append({
                "start": seg["start"] + offset,
                "end": seg["end"] + offset,
                "text": seg["text"].strip(),
                "duration": seg["end"] - seg["start"],
            })
    
    print(f"       Total segments: {len(all_segments)}")
    
    # Save transcript for review
    if temp_dir:
        transcript_path = os.path.join(temp_dir, "transcript.json")
        with open(transcript_path, "w", encoding="utf-8") as f:
            json.dump(all_segments, f, indent=2, ensure_ascii=False)
        print(f"       Transcript saved to '{transcript_path}'")
        
        # Also save as readable text
        txt_path = os.path.join(temp_dir, "transcript.txt")
        with open(txt_path, "w", encoding="utf-8") as f:
            for seg in all_segments:
                start = seg["start"]
                end = seg["end"]
                f.write(f"[{start:.2f}s - {end:.2f}s]: {seg['text']}\n")
        print(f"       Readable transcript saved to '{txt_path}'")
    
    return all_segments


def calculate_speech_rate(text: str, duration: float) -> str:
    """Calculate appropriate speech rate adjustment for TTS."""
    # Estimate: average English speech is ~150 words per minute
    words = len(text.split())
    if duration <= 0 or words == 0:
        return "+0%"
    
    target_wpm = (words / duration) * 60
    
    # Adjust rate to fit the original timing
    if target_wpm > 200:
        return "+50%"  # Speak faster
    elif target_wpm > 170:
        return "+25%"
    elif target_wpm > 150:
        return "+10%"
    elif target_wpm < 100:
        return "-20%"
    elif target_wpm < 120:
        return "-10%"
    else:
        return "+0%"


async def _synthesize_segment(text: str, wav_path: str, voice: str, rate: str = "+0%"):
    """Synthesize a single text segment with rate adjustment."""
    mp3_path = wav_path.replace(".wav", ".mp3")
    communicate = edge_tts.Communicate(text, voice, rate=rate)
    await communicate.save(mp3_path)
    # Convert MP3 to WAV for consistent processing
    audio = AudioSegment.from_mp3(mp3_path)
    audio.export(wav_path, format="wav")
    os.remove(mp3_path)
    return len(audio)  # Return duration in ms


def synthesize_speech(segments, tts_dir: str, voice: str = "en-US-GuyNeural", adjust_rate: bool = True):
    """Generate a WAV file for each segment using Edge TTS.
    Returns the list of (wav_path, start_sec, duration_ms) tuples.
    """
    print(f"[4/8] Synthesizing English speech with Edge TTS (voice={voice}) ...")
    wav_entries = []
    
    for i, seg in enumerate(segments):
        text = seg.get("text", "").strip()
        if not text:
            continue
        
        wav_path = os.path.join(tts_dir, f"seg_{i:06d}.wav")
        
        # Calculate rate adjustment to match original timing
        rate = "+0%"
        if adjust_rate:
            rate = calculate_speech_rate(text, seg.get("duration", 3.0))
        
        try:
            duration_ms = asyncio.run(_synthesize_segment(text, wav_path, voice, rate))
            wav_entries.append({
                "path": wav_path,
                "start": seg["start"],
                "end": seg["end"],
                "original_duration": seg.get("duration", 0) * 1000,
                "tts_duration": duration_ms,
                "text": text,
            })
        except Exception as e:
            print(f"       WARNING: TTS failed for segment {i}: {e}")
        
        if (i + 1) % 20 == 0:
            print(f"       Synthesized {i + 1}/{len(segments)} segments ...")
    
    print(f"       Synthesized {len(wav_entries)} segment(s)")
    return wav_entries


def assemble_audio(wav_entries, total_duration_ms: int, output_path: str, 
                   original_audio_path: str = None, mix_background: float = 0.0):
    """
    Place each TTS segment at its original timestamp offset.
    Optionally mix with reduced volume original audio for background sounds/music.
    """
    print(f"[5/8] Assembling full English audio track ...")
    
    # Start with silence or original audio as background
    if mix_background > 0 and original_audio_path:
        print(f"       Mixing original audio at {int(mix_background * 100)}% volume as background...")
        original = AudioSegment.from_wav(original_audio_path)
        # Reduce volume of original
        original = original - (20 * (1 - mix_background))  # dB reduction
        combined = original[:total_duration_ms]
        # Pad if necessary
        if len(combined) < total_duration_ms:
            combined = combined + AudioSegment.silent(duration=total_duration_ms - len(combined))
    else:
        combined = AudioSegment.silent(duration=total_duration_ms)
    
    for entry in wav_entries:
        seg_audio = AudioSegment.from_wav(entry["path"])
        pos_ms = int(entry["start"] * 1000)
        
        # If TTS is longer than original segment, trim it
        original_dur = entry.get("original_duration", 0)
        if original_dur > 0 and len(seg_audio) > original_dur * 1.5:
            # Speed up the audio to fit (within limits)
            seg_audio = seg_audio[:int(original_dur * 1.3)]
        
        # Overlay the segment at its timestamp position
        combined = combined.overlay(seg_audio, position=pos_ms)
    
    combined.export(output_path, format="wav")
    print(f"       Saved assembled audio to '{output_path}'")


def merge_audio_video(video_path: str, audio_path: str, output_path: str):
    """Replace the original audio in the video with the new English audio."""
    print(f"[6/8] Merging English audio into video → '{output_path}' ...")
    video_in = ffmpeg.input(video_path)
    audio_in = ffmpeg.input(audio_path)
    (
        ffmpeg
        .output(
            video_in.video,
            audio_in.audio,
            output_path,
            vcodec="copy",
            acodec="aac",
            audio_bitrate="192k",
            strict="experimental",
        )
        .overwrite_output()
        .run(quiet=True)
    )
    print("       Done!")


def get_audio_duration_ms(audio_path: str) -> int:
    """Return duration of a WAV file in milliseconds."""
    audio = AudioSegment.from_wav(audio_path)
    return len(audio)


# ─────────────────────────── main ───────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Dub a Kannada video into English automatically (Improved Version)."
    )
    parser.add_argument("input_video", help="Path to the input video file (Kannada audio)")
    parser.add_argument("output_video", help="Path for the dubbed output video file")
    parser.add_argument(
        "--whisper-model", default="large",
        choices=["tiny", "base", "small", "medium", "large"],
        help="Whisper model size (default: large for best quality)",
    )
    parser.add_argument(
        "--chunk-minutes", type=int, default=10,
        help="Split audio into chunks of this many minutes (default: 10)",
    )
    parser.add_argument(
        "--voice", default="en-US-GuyNeural",
        help="Edge TTS voice name (default: en-US-GuyNeural). "
             "Other options: en-US-AriaNeural (female), en-GB-RyanNeural (British male), "
             "en-IN-PrabhatNeural (Indian male). Run 'edge-tts --list-voices' for all.",
    )
    parser.add_argument(
        "--mix-background", type=float, default=0.15,
        help="Mix original audio as background (0.0-1.0, default: 0.15 for 15%% volume). "
             "This preserves background music and sound effects.",
    )
    parser.add_argument(
        "--no-rate-adjust", action="store_true",
        help="Disable automatic speech rate adjustment to match original timing",
    )
    parser.add_argument(
        "--keep-temp", action="store_true",
        help="Do not delete intermediate files on completion",
    )
    args = parser.parse_args()

    # --- Preflight checks ---
    ensure_ffmpeg()
    if not os.path.isfile(args.input_video):
        sys.exit(f"ERROR: Input video not found: {args.input_video}")

    # --- Create temp workspace ---
    temp_dir = os.path.join(os.path.dirname(os.path.abspath(args.output_video)), "temp_dub")
    os.makedirs(temp_dir, exist_ok=True)
    chunk_dir = os.path.join(temp_dir, "chunks")
    os.makedirs(chunk_dir, exist_ok=True)
    tts_dir = os.path.join(temp_dir, "tts")
    os.makedirs(tts_dir, exist_ok=True)

    full_audio = os.path.join(temp_dir, "full_audio.wav")
    full_audio_stereo = os.path.join(temp_dir, "full_audio_stereo.wav")
    assembled_audio = os.path.join(temp_dir, "english_audio.wav")

    try:
        # Step 1: Extract audio
        extract_audio(args.input_video, full_audio)
        
        # Extract stereo version for background mixing
        if args.mix_background > 0:
            print("       Extracting stereo audio for background mixing...")
            extract_audio_stereo(args.input_video, full_audio_stereo)

        # Step 2: Chunk audio
        chunks = chunk_audio(full_audio, chunk_dir, args.chunk_minutes)

        # Step 3: Transcribe AND translate with Whisper
        # Using task="translate" gets both transcription and translation in one step!
        segments = transcribe_chunks(chunks, args.whisper_model, temp_dir)
        if not segments:
            sys.exit("ERROR: No speech segments detected. Is the video in Kannada?")

        # Step 4: Synthesize (segments already in English from Whisper translation)
        wav_entries = synthesize_speech(
            segments, 
            tts_dir, 
            args.voice, 
            adjust_rate=not args.no_rate_adjust
        )
        if not wav_entries:
            sys.exit("ERROR: No TTS segments were generated.")

        # Step 5: Assemble with optional background mixing
        total_duration = get_audio_duration_ms(full_audio)
        background_audio = full_audio_stereo if args.mix_background > 0 else None
        assemble_audio(
            wav_entries, 
            total_duration, 
            assembled_audio,
            original_audio_path=background_audio,
            mix_background=args.mix_background
        )

        # Step 6: Merge
        merge_audio_video(args.input_video, assembled_audio, args.output_video)

        print(f"\n✅ Dubbed video saved to: {args.output_video}")
        print(f"\n📝 Tips for better results:")
        print(f"   - Check transcript at: {os.path.join(temp_dir, 'transcript.txt')}")
        print(f"   - Try different voices: en-US-AriaNeural, en-IN-PrabhatNeural")
        print(f"   - Adjust --mix-background (0.0-0.3) to keep more/less original audio")

    finally:
        if not args.keep_temp:
            print("Cleaning up temporary files ...")
            shutil.rmtree(temp_dir, ignore_errors=True)
        else:
            print(f"Temporary files kept in: {temp_dir}")


if __name__ == "__main__":
    main()
