#!/usr/bin/env python3
"""
Kannada → English Video Dubbing Pipeline
==========================================
Extracts audio from a video, transcribes Kannada speech with Whisper,
translates to English, synthesizes English speech with Edge TTS,
and merges the new audio back into the original video.

Usage:
    python dub_video.py input_video.mp4 output_video.mp4
"""

import argparse
import asyncio
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
import torch
import torch_directml  # AMD GPU support via DirectML


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
    print(f"[1/7] Extracting audio from '{video_path}' ...")
    (
        ffmpeg
        .input(video_path)
        .output(audio_path, ac=1, ar=16000, format="wav")
        .overwrite_output()
        .run(quiet=True)
    )
    print(f"       Saved to '{audio_path}'")


def chunk_audio(audio_path: str, chunk_dir: str, chunk_minutes: int = 5):
    """Split a WAV file into smaller chunks and return the list of chunk paths."""
    print(f"[2/7] Splitting audio into ~{chunk_minutes}-minute chunks ...")
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


def transcribe_chunks(chunks, model_name: str = "medium", use_gpu: bool = True):
    """Transcribe each audio chunk with Whisper. Returns a flat list of segments
    with absolute timestamps (offset-adjusted).
    Each segment: {"start": float, "end": float, "text": str}
    """
    # Setup device - use DirectML for AMD GPU on Windows
    if use_gpu:
        try:
            dml_device = torch_directml.device()
            print(f"[3/7] Transcribing with Whisper (model={model_name}, language=kn, device=AMD GPU via DirectML) ...")
            model = whisper.load_model(model_name, device=dml_device)
        except Exception as e:
            print(f"       WARNING: DirectML failed ({e}), falling back to CPU...")
            print(f"[3/7] Transcribing with Whisper (model={model_name}, language=kn, device=CPU) ...")
            model = whisper.load_model(model_name)
    else:
        print(f"[3/7] Transcribing with Whisper (model={model_name}, language=kn, device=CPU) ...")
        model = whisper.load_model(model_name)
    all_segments = []
    for idx, (chunk_path, offset) in enumerate(chunks):
        print(f"       Transcribing chunk {idx + 1}/{len(chunks)} ...")
        result = model.transcribe(chunk_path, language="kn", verbose=False)
        for seg in result.get("segments", []):
            all_segments.append({
                "start": seg["start"] + offset,
                "end":   seg["end"]   + offset,
                "text":  seg["text"].strip(),
            })
    print(f"       Total segments: {len(all_segments)}")
    return all_segments


def translate_segments(segments):
    """Translate each segment's text from Kannada to English."""
    print(f"[4/7] Translating {len(segments)} segment(s) to English ...")
    translator = GoogleTranslator(source="kn", target="en")
    for i, seg in enumerate(segments):
        if not seg["text"]:
            seg["translated"] = ""
            continue
        try:
            seg["translated"] = translator.translate(seg["text"])
        except Exception as e:
            print(f"       WARNING: Translation failed for segment {i}: {e}")
            seg["translated"] = seg["text"]  # fallback: keep original
        # Be polite to upstream API
        if (i + 1) % 50 == 0:
            time.sleep(1)
    print("       Translation complete")
    return segments


async def _synthesize_segment(text: str, wav_path: str, voice: str):
    """Synthesize a single text segment to an MP3, then convert to WAV."""
    mp3_path = wav_path.replace(".wav", ".mp3")
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(mp3_path)
    # Convert MP3 to WAV for consistent processing
    audio = AudioSegment.from_mp3(mp3_path)
    audio.export(wav_path, format="wav")
    os.remove(mp3_path)


def synthesize_speech(segments, tts_dir: str, voice: str = "en-US-AriaNeural"):
    """Generate a WAV file for each translated segment using Edge TTS.
    Returns the list of (wav_path, start_sec) tuples.
    """
    print(f"[5/7] Synthesizing English speech with Edge TTS (voice={voice}) ...")
    wav_entries = []
    for i, seg in enumerate(segments):
        text = seg.get("translated", "").strip()
        if not text:
            continue
        wav_path = os.path.join(tts_dir, f"seg_{i:06d}.wav")
        try:
            asyncio.run(_synthesize_segment(text, wav_path, voice))
            wav_entries.append((wav_path, seg["start"]))
        except Exception as e:
            print(f"       WARNING: TTS failed for segment {i}: {e}")
        if (i + 1) % 100 == 0:
            print(f"       Synthesized {i + 1}/{len(segments)} segments ...")
    print(f"       Synthesized {len(wav_entries)} segment(s)")
    return wav_entries


def assemble_audio(wav_entries, total_duration_ms: int, output_path: str):
    """Place each TTS segment at its original timestamp offset to build one
    continuous audio track. Gaps are filled with silence.
    """
    print(f"[6/7] Assembling full English audio track ...")
    # Start with silence of the full video duration
    combined = AudioSegment.silent(duration=total_duration_ms)
    for wav_path, start_sec in wav_entries:
        seg_audio = AudioSegment.from_wav(wav_path)
        pos_ms = int(start_sec * 1000)
        # Overlay the segment at its timestamp position
        combined = combined.overlay(seg_audio, position=pos_ms)
    combined.export(output_path, format="wav")
    print(f"       Saved assembled audio to '{output_path}'")


def merge_audio_video(video_path: str, audio_path: str, output_path: str):
    """Replace the original audio in the video with the new English audio."""
    print(f"[7/7] Merging English audio into video → '{output_path}' ...")
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
        description="Dub a Kannada video into English automatically."
    )
    parser.add_argument("input_video", help="Path to the input video file (Kannada audio)")
    parser.add_argument("output_video", help="Path for the dubbed output video file")
    parser.add_argument(
        "--whisper-model", default="medium",
        choices=["tiny", "base", "small", "medium", "large"],
        help="Whisper model size (default: medium)",
    )
    parser.add_argument(
        "--chunk-minutes", type=int, default=5,
        help="Split audio into chunks of this many minutes (default: 5)",
    )
    parser.add_argument(
        "--voice", default="en-US-AriaNeural",
        help="Edge TTS voice name (default: en-US-AriaNeural). "
             "Run 'edge-tts --list-voices' to see all available voices.",
    )
    parser.add_argument(
        "--keep-temp", action="store_true",
        help="Do not delete intermediate files on completion",
    )
    parser.add_argument(
        "--no-gpu", action="store_true",
        help="Disable GPU acceleration (use CPU only)",
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
    assembled_audio = os.path.join(temp_dir, "english_audio.wav")

    try:
        # Step 1: Extract audio
        extract_audio(args.input_video, full_audio)

        # Step 2: Chunk audio
        chunks = chunk_audio(full_audio, chunk_dir, args.chunk_minutes)

        # Step 3: Transcribe (use AMD GPU via DirectML by default)
        segments = transcribe_chunks(chunks, args.whisper_model, use_gpu=not args.no_gpu)
        if not segments:
            sys.exit("ERROR: No speech segments detected. Is the video in Kannada?")

        # Step 4: Translate
        segments = translate_segments(segments)

        # Step 5: Synthesize
        wav_entries = synthesize_speech(segments, tts_dir, args.voice)
        if not wav_entries:
            sys.exit("ERROR: No TTS segments were generated.")

        # Step 6: Assemble
        total_duration = get_audio_duration_ms(full_audio)
        assemble_audio(wav_entries, total_duration, assembled_audio)

        # Step 7: Merge
        merge_audio_video(args.input_video, assembled_audio, args.output_video)

        print(f"\n✅ Dubbed video saved to: {args.output_video}")

    finally:
        if not args.keep_temp:
            print("Cleaning up temporary files ...")
            shutil.rmtree(temp_dir, ignore_errors=True)
        else:
            print(f"Temporary files kept in: {temp_dir}")


if __name__ == "__main__":
    main()
