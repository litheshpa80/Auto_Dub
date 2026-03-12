# Kannada → English Video Dubbing

Automatically dub a Kannada-language video into English using:

- **OpenAI Whisper** — speech-to-text (Kannada)
- **Google Translate** — Kannada → English translation
- **Coqui TTS** — English speech synthesis
- **FFmpeg** — audio extraction and video muxing

---

## 1. Install FFmpeg

FFmpeg must be installed **separately** and available on your `PATH`.

### Windows
```bash
# Option A – winget (Windows 10+)
winget install Gyan.FFmpeg

# Option B – Chocolatey
choco install ffmpeg

# Option C – Manual
# Download from https://www.gyan.dev/ffmpeg/builds/
# Extract and add the bin/ folder to your system PATH.
```

### Linux (Debian / Ubuntu)
```bash
sudo apt update && sudo apt install ffmpeg -y
```

### macOS
```bash
brew install ffmpeg
```

**Verify**: `ffmpeg -version` should print version info.

---

## 2. Python Environment Setup

Python **3.8 – 3.11** is recommended.

```bash
# Create a virtual environment (recommended)
python -m venv venv

# Activate it
# Windows:
venv\Scripts\activate
# Linux / macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

> **Note**: Whisper and Coqui TTS will download model files on first run
> (~1–3 GB depending on model size). Ensure you have enough disk space and a
> stable internet connection for the first run.

---

## 3. Run the Script

```bash
python dub_video.py input_video.mp4 output_video.mp4
```

### Optional Arguments

| Flag | Default | Description |
|------|---------|-------------|
| `--whisper-model` | `medium` | Whisper model size: `tiny`, `base`, `small`, `medium`, `large` |
| `--chunk-minutes` | `5` | Audio chunk length in minutes (lower = less RAM) |
| `--tts-model` | `tts_models/en/ljspeech/tacotron2-DDC` | Coqui TTS model identifier |
| `--keep-temp` | *(off)* | Keep intermediate files for debugging |

**Example with options**:
```bash
python dub_video.py movie.mp4 movie_en.mp4 --whisper-model large --chunk-minutes 10
```

---

## 4. Tips & Troubleshooting

| Issue | Solution |
|-------|----------|
| **Out of memory** | Use a smaller Whisper model (`small` or `base`) or reduce `--chunk-minutes` |
| **CUDA not detected** | Install the CUDA-enabled PyTorch build: `pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121` |
| **Slow on CPU** | A GPU is strongly recommended for Whisper and TTS. On CPU, a 2-hour video may take several hours |
| **Translation errors** | Google Translate is used via `deep-translator`; ensure internet connectivity |
| **ffmpeg not found** | Make sure FFmpeg is installed and on your system `PATH` |

---

## 5. Project Structure

```
├── dub_video.py        # Main pipeline script
├── requirements.txt    # Python dependencies
└── README.md           # This file
```
