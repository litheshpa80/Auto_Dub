# Auto_Dub: AI-Powered Video Dubbing & LipSync Pipeline

Auto_Dub is a video translation and dubbing pipeline designed to automatically translate and dub videos or live streams with AI-generated cloned voices. By integrating speech recognition, machine translation, voice cloning, and LipSync technologies, Auto_Dub provides high-quality localized video content.

Developed by **[Lithesh P A](https://github.com/litheshpa80)**.

---

## 🚀 Key Features

- 🎬 **Video Localization**: Automatically translate speech into target languages while maintaining audio/video alignment.
- 🎙️ **Voice Cloning**: Preserves the original speaker's vocal characteristics (pitch, tone, style) in the dubbed voice using **OpenVoice**.
- 💬 **Multi-language Support**: Support for transcribing and translating between 40+ languages.
- 🎵 **Vocal & Background Separation**: Uses Meta's **Demucs** model to isolate and preserve background music and sound effects while dubbing vocals.
- 👄 **LipSync Synchronization**: Employs **Replicate HeadGen** (`heygen/lipsync-speed`) to naturally align mouth movements with the newly generated audio.
- 💻 **Interactive Web UI**: A clean, responsive FastAPI-based web interface to upload, process, and track your dubbing runs.

---

## 🛠️ Architecture & How It Works

Auto_Dub leverages a **cloud-assisted hybrid architecture** to perform intensive AI processing efficiently:

```
INPUT VIDEO
    ↓
[1] Audio Extraction (ffmpeg)
    ↓
[2] Vocal Separation (Meta Demucs)
    ↓
[3] Speech Recognition (OpenAI Whisper)
    ↓
[4] Translation (Target Language)
    ↓
[5] Text-to-Speech (ElevenLabs / Local TTS)
    ↓
[6] Voice Cloning (OpenVoice)
    ↓
[7] Audio Mixing (ffmpeg)
    ↓
[8] LipSync (Replicate HeadGen)
    ↓
OUTPUT VIDEO (Dubbed + Synchronized)
```

---

## 📦 Technology Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Speech Recognition** | OpenAI Whisper | Transcribe speech to text with timestamps |
| **Voice Cloning** | OpenVoice (MyShell AI) | Clones source speaker's voice qualities |
| **Vocal Separation** | Meta Demucs | Splits vocals from background audio/music |
| **Audio Processing** | FFmpeg | Audio/video manipulation and mixing |
| **LipSync** | Replicate HeadGen | Synchronizes mouth/lips to dubbed audio |
| **Backend API** | FastAPI + Uvicorn | High-performance backend routing |
| **Web UI** | Gradio / Vanilla HTML5 | Interactive UI for uploading and processing |

---

## ⚙️ Installation & Setup

### Prerequisites
- Python 3.8 - 3.11
- Git
- FFmpeg (added to your system PATH)
- 8GB+ RAM recommended
- A stable internet connection (for cloud model execution)

### Step 1: Clone the Repository
```bash
git clone https://github.com/litheshpa80/Auto_Dub.git
cd Auto_Dub
```

### Step 2: Initialize Virtual Environment
```bash
python -m venv .venv

# Activate on Windows
.venv\Scripts\activate

# Activate on macOS/Linux
source .venv/bin/activate
```

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
pip install replicate gradio_client elevenlabs openvoice
```

### Step 4: Configure Environment Variables
Create a `.env` file in the root directory:
```env
# Replicate Token (required for LipSync)
REPLICATE_API_TOKEN=your_replicate_token_here

# ElevenLabs Key (optional, for high-quality TTS)
ELEVENLABS_API_KEY=your_elevenlabs_key_here

# OpenAI Key (optional, if using cloud Whisper)
OPENAI_API_KEY=your_openai_key_here
```

---

## 🖥️ Usage

### Running the Web UI (FastAPI)
To run the full web application locally:
```bash
python stitch/backend.py
```
Open your browser and navigate to:
```
http://127.0.0.1:8001/ui
```

### Running via CLI (Command Line)
You can run the dubbing pipeline programmatically through `dubber.py`:

```bash
# Basic Spanish translation and dubbing
python dubber.py --input sample.mp4 --output dubbed_es.mp4 --language es

# Spanish dubbing with Voice Cloning & LipSync enabled
python dubber.py --input sample.mp4 --output dubbed_es.mp4 --language es --lipsync --voice_strength 0.8
```

---

## 📂 Project Structure

```
Auto_Dub/
├── dubber.py                  # Core pipeline script
├── requirements.txt           # Python dependencies
├── README.md                  # Project documentation
├── .env                       # API credentials (ignored by git)
├── stitch/                    # Web UI and Backend Server
│   ├── backend.py            # FastAPI Application
│   ├── dub_logic.js          # Client-side processing logic
│   ├── final_ui.html         # User Interface Layout
│   └── DESIGN.md             # UI architecture decisions
├── OpenVoice/                # Local voice cloning engine
│   ├── openvoice/            # OpenVoice implementation files
│   └── checkpoints_v2/       # Model weights (ignored by git)
└── whisper-main/             # OpenAI Whisper local module
```

---

## 📝 License & Acknowledgments

This project combines several excellent open-source models:
- **Whisper**: MIT License (OpenAI)
- **OpenVoice**: MIT License (MyShell AI)
- **Demucs**: CC0 License (Meta)

Special thanks to **Replicate** for providing serverless hosting for LipSync processing.
