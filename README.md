# 🎬 Auto_Dub — AI Video Dubbing with Voice Cloning

**Automatically dub any video from 100+ languages to English with the original speaker's cloned voice.**

Built with OpenAI Whisper (transcription/translation) + Coqui XTTS v2 (voice cloning) + Flask (web UI).

![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python)
![Whisper](https://img.shields.io/badge/OpenAI-Whisper-green)
![XTTS](https://img.shields.io/badge/Coqui-XTTS_v2-orange)
![Flask](https://img.shields.io/badge/Flask-Web_App-lightgrey?logo=flask)

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🌍 **100+ Languages** | Auto-detect or manually select source language (Hindi, Kannada, Tamil, Telugu, Japanese, French, Spanish, Arabic, etc.) |
| 🎙️ **Voice Cloning** | Clones the original speaker's voice using Coqui XTTS v2 — output sounds like the same person speaking English |
| ⏱️ **Perfect Sync** | TTS audio is speed-adjusted to match the original speech timing exactly |
| 🔇 **Audio Ducking** | Original voice is suppressed (-35dB) during speech — no overlap between languages |
| 🎵 **Background Preserved** | Music, ambient sounds, and effects are kept — only the voice is replaced |
| 🌐 **Web Interface** | Beautiful drag-and-drop web UI — upload video, configure settings, download result |
| 💻 **CLI Support** | Also works from the command line for scripting/automation |

---

## 🖥️ Demo

### Web Interface
1. Open `http://localhost:5000` in your browser
2. Drag & drop your video
3. Select source language
4. Click **Start Dubbing**
5. Download the dubbed video when ready

### How It Works (Pipeline)

```
Input Video (any language)
    │
    ├─ 1. Extract audio (FFmpeg)
    ├─ 2. Extract speaker voice sample (15s clip for cloning)
    ├─ 3. Split audio into chunks
    ├─ 4. Transcribe & translate to English (Whisper)
    ├─ 5. Generate English speech with cloned voice (XTTS v2)
    ├─ 6. Speed-adjust TTS + duck original audio + assemble
    └─ 7. Merge dubbed audio with original video
    │
Output Video (English dubbed, speaker's voice)
```

---

## 🚀 Quick Start

### Prerequisites
- **Python 3.10+**
- **FFmpeg** — [Download](https://ffmpeg.org/download.html) and add to PATH
- **~8 GB RAM** minimum (models are large)
- **GPU (optional)** — NVIDIA CUDA speeds up processing significantly

### Installation

```bash
# Clone the repository
git clone https://github.com/litheshpa80/Auto_Dub.git
cd Auto_Dub

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install openai-whisper pydub ffmpeg-python flask
pip install TTS            # Coqui TTS (includes XTTS v2)
pip install torch           # PyTorch (CPU version, or install CUDA version for GPU)
```

> **Note:** First run will download Whisper (~3 GB) and XTTS v2 (~2 GB) models automatically.

### Run — Web App

```bash
python app.py
```
Open **http://localhost:5000** in your browser.

### Run — Command Line

```bash
# Basic usage (auto-detect language)
python dub_video_clone.py input.mp4 output.mp4

# Specify source language
python dub_video_clone.py input.mp4 output.mp4 --source-language kn

# Use smaller Whisper model (faster, less accurate)
python dub_video_clone.py input.mp4 output.mp4 --whisper-model medium

# Full options
python dub_video_clone.py input.mp4 output.mp4 \
    --source-language hi \
    --whisper-model large \
    --duck-level -50 \
    --speaker-sample-start 10 \
    --speaker-sample-duration 15
```

---

## ⚙️ Configuration

### CLI Arguments

| Argument | Default | Description |
|----------|---------|-------------|
| `input_video` | (required) | Path to input video file |
| `output_video` | (required) | Path for output dubbed video |
| `--source-language` | `auto` | Source language code (`auto`, `kn`, `hi`, `ta`, `te`, `ml`, `fr`, `es`, `de`, `ja`, `ko`, `zh`, `ar`, `ru`, etc.) |
| `--whisper-model` | `large` | Whisper model size: `tiny`, `base`, `small`, `medium`, `large` |
| `--duck-level` | `-35` | How much to reduce original voice in dB (-50 = nearly silent) |
| `--speaker-sample-start` | `10` | Start time (seconds) to extract voice sample for cloning |
| `--speaker-sample-duration` | `15` | Duration (seconds) of voice sample |
| `--no-background` | `false` | Remove ALL original audio (no background sounds) |

### Web UI Settings
All CLI options are available in the web UI under **⚙️ Advanced Settings**.

---

## 🌍 Supported Languages

Auto_Dub supports **100+ source languages** via OpenAI Whisper. Common ones:

| Region | Languages |
|--------|-----------|
| **Indian** | Kannada, Hindi, Tamil, Telugu, Malayalam, Marathi, Bengali, Gujarati, Punjabi, Urdu, Nepali, Sinhala |
| **East Asian** | Japanese, Korean, Chinese (Mandarin), Thai, Vietnamese, Indonesian, Malay, Filipino |
| **European** | French, German, Spanish, Portuguese, Italian, Dutch, Polish, Russian, Ukrainian, Czech, Greek, Swedish, Danish, Finnish, Norwegian, Hungarian, Turkish, Romanian |
| **Middle East** | Arabic, Persian (Farsi), Hebrew |
| **African** | Swahili, Afrikaans |

> Set to **Auto-Detect** and Whisper will figure out the language automatically.

---

## 📁 Project Structure

```
Auto_Dub/
├── app.py                  # Flask web server
├── dub_video_clone.py      # Core dubbing pipeline (CLI + importable)
├── dub_video.py            # Earlier version (Edge TTS, no voice cloning)
├── dub_video_v2.py         # Earlier version (Whisper translate mode)
├── templates/
│   └── index.html          # Web UI (drag & drop, progress bar, download)
├── static/                 # Static assets (CSS/JS if needed)
├── web_uploads/            # Temporary uploaded videos
├── web_outputs/            # Dubbed output videos (downloadable)
├── requirements.txt        # Python dependencies
├── run_dub.bat             # Windows batch file to run CLI
└── README.md               # This file
```

---

## 🧠 Tech Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Transcription & Translation | [OpenAI Whisper](https://github.com/openai/whisper) (large) | Converts speech to English text with timestamps |
| Voice Cloning | [Coqui XTTS v2](https://github.com/coqui-ai/TTS) | Generates English speech that sounds like the original speaker |
| Audio Processing | [PyDub](https://github.com/jiaaro/pydub) | Speed adjustment, ducking, mixing, normalization |
| Video Processing | [FFmpeg](https://ffmpeg.org/) | Audio extraction, video/audio merging |
| Web Framework | [Flask](https://flask.palletsprojects.com/) | Upload, progress tracking, download |
| ML Framework | [PyTorch](https://pytorch.org/) | Backend for Whisper and XTTS |

---

## 💡 How Voice Cloning Works

1. A **15-second sample** of the original speaker's voice is extracted from the video
2. XTTS v2 analyzes the voice characteristics (tone, pitch, accent, pace)
3. When generating English speech, XTTS v2 produces audio that **mimics the original speaker**
4. The result sounds like the same person speaking English — not a generic TTS robot voice

---

## ⚡ Performance

| Whisper Model | Accuracy | Speed (4-min video, CPU) | VRAM |
|--------------|----------|-------------------------|------|
| `tiny` | ★★☆☆☆ | ~2 min | ~1 GB |
| `base` | ★★★☆☆ | ~3 min | ~1 GB |
| `small` | ★★★☆☆ | ~5 min | ~2 GB |
| `medium` | ★★★★☆ | ~10 min | ~5 GB |
| `large` | ★★★★★ | ~20 min | ~10 GB |

> Voice cloning (XTTS v2) adds ~1-3 seconds per segment on CPU, much faster on GPU.

---

## 🚀 Deployment Options

| Option | Cost | Always Online? | Speed |
|--------|------|---------------|-------|
| **Local PC** | Free | Only when PC is on | Fast (your hardware) |
| **Local + ngrok** | Free | Only when PC is on | Fast + public URL |
| **Hugging Face Spaces** | Free | ✅ Yes | Slow (CPU only) |
| **RunPod** | ~$0.20/hr | When running | Very fast (GPU) |
| **AWS EC2 / GCP VM** | ~$10-30/mo | ✅ Yes | Fast |

---

## 📝 License

This project is for educational and personal use. The AI models used have their own licenses:
- Whisper: [MIT License](https://github.com/openai/whisper/blob/main/LICENSE)
- Coqui TTS / XTTS v2: [MPL 2.0](https://github.com/coqui-ai/TTS/blob/dev/LICENSE.txt)

---

## 🙏 Credits

- [OpenAI Whisper](https://github.com/openai/whisper) — Speech recognition & translation
- [Coqui AI TTS](https://github.com/coqui-ai/TTS) — Voice cloning with XTTS v2
- [FFmpeg](https://ffmpeg.org/) — Audio/video processing
- [Flask](https://flask.palletsprojects.com/) — Web framework

---

**Made by [@litheshpa80](https://github.com/litheshpa80)**