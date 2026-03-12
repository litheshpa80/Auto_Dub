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

## 📚 Libraries & Technologies Explained (Beginner-Friendly)

If you're new to programming or AI, here's what every piece of this project does and **why we need it**:

### 🐍 Python
- **What it is:** A programming language — the most popular language for AI/ML projects.
- **Why we use it:** Almost every AI library (Whisper, XTTS, PyTorch) is built for Python. It's easy to read and write.
- **Version:** 3.10 or newer.

---

### 🎤 OpenAI Whisper (`openai-whisper`)
- **What it is:** An AI model made by **OpenAI** (the company behind ChatGPT) that can **listen to audio and convert it to text** (speech-to-text).
- **What it does in this project:**
  - Listens to the original video's audio (e.g., Kannada, Hindi, Japanese)
  - **Translates** it directly to English text
  - Gives **timestamps** for each sentence (e.g., "this sentence starts at 5.2s and ends at 8.1s")
- **Why it's special:** It understands **100+ languages** and can translate them all to English in one step.
- **Size:** The `large` model is ~3 GB (most accurate). Smaller models like `tiny` or `base` are faster but less accurate.
- **Think of it as:** A translator who listens to any language and writes down the English translation with exact timing.

---

### 🗣️ Coqui TTS / XTTS v2 (`TTS`)
- **What it is:** An AI model that can **generate human speech from text** (text-to-speech). XTTS v2 is a special version that can **clone someone's voice**.
- **What it does in this project:**
  - Takes the English text from Whisper
  - Takes a **15-second sample** of the original speaker's voice
  - Generates English speech that **sounds like the original speaker** — same tone, pitch, and style
- **Why it's special:** Unlike basic TTS (which sounds robotic), XTTS v2 produces natural-sounding speech that mimics the original person.
- **Size:** ~2 GB model download.
- **Think of it as:** An impersonator who can read any English text in someone else's voice.

---

### 🔥 PyTorch (`torch`)
- **What it is:** A **machine learning framework** made by Meta (Facebook). It's the engine that powers AI models.
- **What it does in this project:**
  - Whisper and XTTS v2 are both built on PyTorch
  - It handles all the complex math (matrix operations, neural networks) that makes AI work
  - If you have an **NVIDIA GPU**, PyTorch can use it to process things much faster
- **Why we need it:** Without PyTorch, Whisper and XTTS cannot run. It's like the engine inside a car — you don't see it, but nothing works without it.
- **Size:** ~1.5 GB.
- **Think of it as:** The engine that powers all the AI brains in this project.

---

### 🎵 PyDub (`pydub`)
- **What it is:** A simple Python library for **editing audio files** — cutting, merging, speeding up, adjusting volume.
- **What it does in this project:**
  - **Speed adjustment:** If the English TTS is 4 seconds but the original speech was 3 seconds, PyDub speeds it up to fit perfectly
  - **Audio ducking:** Lowers the volume of the original voice by -35dB during speech so you don't hear both languages
  - **Mixing:** Combines the background audio with the new English voice
  - **Normalization:** Makes the final audio volume consistent
- **Think of it as:** An audio editing tool (like Audacity) but controlled by code.

---

### 🎬 FFmpeg (`ffmpeg-python`)
- **What it is:** A powerful **command-line tool** for processing video and audio files. `ffmpeg-python` is a Python wrapper that lets us control FFmpeg from Python code.
- **What it does in this project:**
  - **Extracts audio** from the input video (separates the sound from the video)
  - **Merges** the new dubbed audio back into the video (replaces the old sound)
  - Handles format conversion (WAV, AAC, MP4)
- **Why we need it:** Python alone can't easily read/write video files. FFmpeg is the industry standard for video processing (used by YouTube, Netflix, VLC, etc.).
- **Think of it as:** A Swiss Army knife for video/audio files.

---

### 🌐 Flask (`flask`)
- **What it is:** A lightweight Python **web framework** — it lets you build websites and web apps with Python.
- **What it does in this project:**
  - Serves the **web page** where you upload videos
  - Handles **file uploads** from your browser
  - Runs the dubbing process in the **background** while showing progress
  - Provides a **download link** when the dubbed video is ready
- **Why Flask and not Django/React/etc.:** Flask is the simplest web framework in Python — perfect for a single-page app like this. No unnecessary complexity.
- **Think of it as:** The waiter at a restaurant — it takes your order (upload), sends it to the kitchen (dubbing pipeline), and brings back your food (download).

---

### 🔤 Jinja2 (comes with Flask)
- **What it is:** A **template engine** — it lets Python generate HTML pages dynamically.
- **What it does:** Powers the `index.html` template that shows the web UI.
- **Think of it as:** A mail merge tool — it fills in blanks in the HTML template with real data.

---

### 🔒 Werkzeug (comes with Flask)
- **What it is:** A **web utility library** that Flask is built on top of.
- **What it does:** Handles secure file uploads, URL routing, and HTTP requests.
- **Think of it as:** The plumbing behind the web server — you don't interact with it directly.

---

### 🧵 Threading (built into Python)
- **What it is:** Python's built-in way to run tasks **in the background**.
- **What it does in this project:**
  - When you click "Start Dubbing" on the website, the dubbing runs in a **background thread**
  - This means the website stays responsive — you can see the progress bar updating while it works
  - Without threading, the website would freeze until dubbing is complete
- **Think of it as:** Having a helper work in the back room while the receptionist keeps talking to you.

---

### 📦 Other Small Libraries

| Library | What it does |
|---------|-------------|
| `math` | Basic math operations (splitting audio into chunks) |
| `os` | File/folder operations (creating temp directories, checking if files exist) |
| `shutil` | Copying/deleting folders, checking if FFmpeg is installed |
| `uuid` | Generates unique IDs for each dubbing job |
| `argparse` | Parses command-line arguments (when running from terminal) |
| `time` | Tracking how long jobs take |
| `tempfile` | Creates temporary folders that auto-delete |

---

### 🖥️ Frontend (Web UI) Technologies

| Technology | What it does |
|-----------|-------------|
| **HTML5** | The structure of the web page (buttons, text, layout) |
| **CSS3** | The styling — dark theme, gradients, animations, responsive design |
| **JavaScript** | Makes the page interactive — drag & drop, progress polling, form submission |
| **Fetch API** | Sends the video to the server and checks job status (AJAX requests) |

> No React, Vue, or npm needed — it's a single `index.html` file with everything included. Simple!

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