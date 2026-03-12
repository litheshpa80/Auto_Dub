"""
Any Language to English Video Dubbing with Voice Cloning (Improved Sync)
- Supports 100+ source languages (auto-detect or specify)
- Clones the original speaker voice using XTTS v2
- Perfect timing sync - English matches original speech duration
- Uses audio ducking to avoid overlap
"""

import argparse
import math
import os
import shutil
import sys

import whisper
from pydub import AudioSegment
import ffmpeg
from TTS.api import TTS
import torch


def ensure_ffmpeg():
    if shutil.which("ffmpeg") is None:
        raise RuntimeError("ffmpeg not found on PATH.")


def extract_audio(video_path, audio_path, sample_rate=16000):
    (
        ffmpeg.input(video_path)
        .output(audio_path, ac=1, ar=sample_rate, format="wav")
        .overwrite_output()
        .run(quiet=True)
    )


def extract_speaker_sample(full_audio_path, output_path, start_sec=5, duration_sec=15):
    audio = AudioSegment.from_wav(full_audio_path)
    start_ms = int(start_sec * 1000)
    end_ms = int((start_sec + duration_sec) * 1000)
    if end_ms > len(audio):
        end_ms = len(audio)
        start_ms = max(0, end_ms - int(duration_sec * 1000))
    sample = audio[start_ms:end_ms]
    sample.export(output_path, format="wav")


def chunk_audio(audio_path, chunk_dir, chunk_minutes=10):
    audio = AudioSegment.from_wav(audio_path)
    chunk_ms = chunk_minutes * 60 * 1000
    total_chunks = math.ceil(len(audio) / chunk_ms)
    paths = []
    for i in range(total_chunks):
        start = i * chunk_ms
        end = min((i + 1) * chunk_ms, len(audio))
        chunk = audio[start:end]
        chunk_path = os.path.join(chunk_dir, "chunk_%04d.wav" % i)
        chunk.export(chunk_path, format="wav")
        paths.append((chunk_path, start / 1000.0))
    return paths


def transcribe_and_translate(chunks, model_name="large", source_language=None):
    model = whisper.load_model(model_name)
    all_segments = []
    for idx, (chunk_path, offset) in enumerate(chunks):
        transcribe_kwargs = {
            "task": "translate",
            "verbose": False,
            "condition_on_previous_text": True,
            "word_timestamps": True,
        }
        if source_language and source_language != "auto":
            transcribe_kwargs["language"] = source_language
        result = model.transcribe(chunk_path, **transcribe_kwargs)
        for seg in result.get("segments", []):
            all_segments.append({
                "start": seg["start"] + offset,
                "end": seg["end"] + offset,
                "text": seg["text"].strip(),
                "duration": seg["end"] - seg["start"],
            })
    return all_segments


def adjust_audio_speed(audio, target_duration_ms):
    current_duration = len(audio)
    if current_duration <= 0 or target_duration_ms <= 0:
        return audio
    speed_ratio = current_duration / target_duration_ms
    speed_ratio = max(0.5, min(2.0, speed_ratio))
    if abs(speed_ratio - 1.0) < 0.05:
        return audio
    new_frame_rate = int(audio.frame_rate * speed_ratio)
    adjusted = audio._spawn(audio.raw_data, overrides={
        "frame_rate": new_frame_rate
    }).set_frame_rate(audio.frame_rate)
    return adjusted


def synthesize_with_voice_clone(segments, speaker_wav, tts_dir, progress_callback=None):
    device = "cuda" if torch.cuda.is_available() else "cpu"
    tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to(device)
    wav_entries = []
    total = len(segments)
    for i, seg in enumerate(segments):
        text = seg.get("text", "").strip()
        if not text or len(text) < 2:
            continue
        wav_path = os.path.join(tts_dir, "seg_%06d.wav" % i)
        target_duration_ms = int(seg["duration"] * 1000)
        try:
            tts.tts_to_file(
                text=text,
                speaker_wav=speaker_wav,
                language="en",
                file_path=wav_path,
            )
            tts_audio = AudioSegment.from_wav(wav_path)
            if target_duration_ms > 0:
                adjusted_audio = adjust_audio_speed(tts_audio, target_duration_ms)
                adjusted_audio.export(wav_path, format="wav")
                final_duration = len(adjusted_audio)
            else:
                final_duration = len(tts_audio)
            wav_entries.append({
                "path": wav_path,
                "start": seg["start"],
                "end": seg["end"],
                "target_duration_ms": target_duration_ms,
                "actual_duration_ms": final_duration,
                "text": text,
            })
        except Exception as e:
            print("WARNING: TTS failed for segment %d: %s" % (i, e))
        if progress_callback:
            progress_callback(i + 1, total)
    return wav_entries


def create_ducked_background(original_audio, segments, duck_level_db=-25):
    background = original_audio
    for seg in segments:
        start_ms = max(0, int(seg["start"] * 1000) - 50)
        end_ms = min(len(background), int(seg["end"] * 1000) + 50)
        if start_ms < end_ms:
            before = background[:start_ms]
            during = background[start_ms:end_ms]
            after = background[end_ms:]
            background = before + (during + duck_level_db) + after
    return background


def assemble_audio_perfect_sync(wav_entries, segments, total_duration_ms,
                                 output_path, original_audio_path=None,
                                 keep_background=True, duck_level=-30):
    if keep_background and original_audio_path:
        original = AudioSegment.from_wav(original_audio_path)
        if len(original) < total_duration_ms:
            original = original + AudioSegment.silent(duration=total_duration_ms - len(original))
        else:
            original = original[:total_duration_ms]
        combined = create_ducked_background(original, segments, duck_level)
    else:
        combined = AudioSegment.silent(duration=total_duration_ms)
    for entry in wav_entries:
        seg_audio = AudioSegment.from_wav(entry["path"])
        pos_ms = int(entry["start"] * 1000)
        target_dur = entry.get("target_duration_ms", 0)
        if target_dur > 0 and len(seg_audio) > target_dur + 200:
            seg_audio = seg_audio[:target_dur + 100]
        combined = combined.overlay(seg_audio, position=pos_ms)
    combined = combined.normalize()
    combined.export(output_path, format="wav")


def merge_audio_video(video_path, audio_path, output_path):
    video_in = ffmpeg.input(video_path)
    audio_in = ffmpeg.input(audio_path)
    (
        ffmpeg.output(
            video_in.video,
            audio_in.audio,
            output_path,
            vcodec="copy",
            acodec="aac",
            audio_bitrate="192k",
        )
        .overwrite_output()
        .run(quiet=True)
    )


def get_audio_duration_ms(audio_path):
    return len(AudioSegment.from_wav(audio_path))


def dub_video(input_video, output_video, whisper_model="large",
              source_language="auto",
              speaker_sample_start=10, speaker_sample_duration=15,
              keep_background=True, duck_level=-35, progress_callback=None):
    ensure_ffmpeg()
    if not os.path.isfile(input_video):
        raise FileNotFoundError("Input video not found: " + input_video)

    def _report(step, total, msg):
        print("[%d/%d] %s" % (step, total, msg))
        if progress_callback:
            progress_callback(step, total, msg)

    temp_dir = os.path.join(os.path.dirname(os.path.abspath(output_video)), "temp_clone")
    os.makedirs(temp_dir, exist_ok=True)
    chunk_dir = os.path.join(temp_dir, "chunks")
    os.makedirs(chunk_dir, exist_ok=True)
    tts_dir = os.path.join(temp_dir, "tts")
    os.makedirs(tts_dir, exist_ok=True)

    full_audio = os.path.join(temp_dir, "full_audio.wav")
    full_audio_22k = os.path.join(temp_dir, "full_audio_22k.wav")
    speaker_sample = os.path.join(temp_dir, "speaker_sample.wav")
    assembled_audio = os.path.join(temp_dir, "english_audio.wav")

    try:
        _report(1, 7, "Extracting audio from video...")
        extract_audio(input_video, full_audio, 16000)
        extract_audio(input_video, full_audio_22k, 22050)

        _report(2, 7, "Extracting speaker voice sample for cloning...")
        extract_speaker_sample(full_audio_22k, speaker_sample,
                               speaker_sample_start, speaker_sample_duration)

        _report(3, 7, "Splitting audio into chunks...")
        chunks = chunk_audio(full_audio, chunk_dir)

        _report(4, 7, "Transcribing and translating with Whisper...")
        segments = transcribe_and_translate(chunks, whisper_model, source_language)
        if not segments:
            raise RuntimeError("No speech detected in the video!")

        _report(5, 7, "Synthesizing %d segments with voice cloning..." % len(segments))
        wav_entries = synthesize_with_voice_clone(segments, speaker_sample, tts_dir)
        if not wav_entries:
            raise RuntimeError("No TTS segments generated!")

        _report(6, 7, "Assembling audio with perfect sync...")
        total_duration = get_audio_duration_ms(full_audio)
        assemble_audio_perfect_sync(
            wav_entries, segments, total_duration, assembled_audio,
            original_audio_path=full_audio_22k if keep_background else None,
            keep_background=keep_background,
            duck_level=duck_level,
        )

        _report(7, 7, "Merging dubbed audio with video...")
        merge_audio_video(input_video, assembled_audio, output_video)

        return output_video
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def main():
    parser = argparse.ArgumentParser(
        description="Dub Kannada video to English with VOICE CLONING"
    )
    parser.add_argument("input_video", help="Path to input video (Kannada)")
    parser.add_argument("output_video", help="Path for dubbed output video")
    parser.add_argument("--whisper-model", default="large",
                        choices=["tiny", "base", "small", "medium", "large"])
    parser.add_argument("--source-language", default="auto",
                        help="Source language code: auto, kn, hi, ta, te, ml, fr, es, de, ja, ko, zh, ar, ru, etc.")
    parser.add_argument("--speaker-sample-start", type=float, default=10)
    parser.add_argument("--speaker-sample-duration", type=float, default=15)
    parser.add_argument("--no-background", action="store_true")
    parser.add_argument("--duck-level", type=float, default=-35)
    args = parser.parse_args()

    dub_video(
        input_video=args.input_video,
        output_video=args.output_video,
        whisper_model=args.whisper_model,
        source_language=args.source_language,
        speaker_sample_start=args.speaker_sample_start,
        speaker_sample_duration=args.speaker_sample_duration,
        keep_background=not args.no_background,
        duck_level=args.duck_level,
    )
    print("Done! Voice-cloned dubbed video saved to: " + args.output_video)


if __name__ == "__main__":
    main()
