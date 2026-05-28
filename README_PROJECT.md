# Dubber: AI-Powered Video Dubbing & Live Stream Solution

## Project Overview

**Dubber** is a sophisticated video dubbing pipeline designed to automatically dub videos and live streams with AI-generated voices in different languages. It combines cutting-edge speech recognition, translation, voice cloning, and LipSync technologies to create seamless dubbed video content.

### Main Intention

The primary goal of this project is to enable **live stream dubbing and video translation** without manual voice work. Key use cases include:

- 🎬 **Live Stream Dubbing**: Real-time dubbing of live streaming content across multiple languages
- 🌍 **Video Localization**: Automatically translate and dub content for international audiences
- 🎙️ **Voice Cloning**: Preserve the original speaker's voice characteristics while dubbing
- 💬 **Multi-language Support**: Translate speech content while maintaining synchronized audio/video
- 🎥 **Content Repurposing**: Convert single-language content to multiple languages efficiently

### Architecture Decision

This repository demonstrates a **cloud-assisted video processing architecture** because:
- **Challenge**: Original video dubbing process is computationally expensive (GPU/CPU intensive)
- **Solution**: Offload heavy ML workloads (LipSync, voice synthesis) to cloud APIs (Replicate, OpenVoice)
- **Benefit**: Run on standard hardware; achieve production-quality results
- **Cost-Effective**: Pay per inference rather than maintaining expensive hardware

---

## How It Works

### Dubbing Pipeline Flow

```
INPUT VIDEO
    ↓
[1] Audio Extraction (ffmpeg)
    ↓
[2] Vocal Separation (Demucs)
    ↓
[3] Speech Recognition (Whisper)
    ↓
[4] Translation (Optional)
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

### Components

#### 1. **Audio Extraction**
- Extracts audio track from input video using `ffmpeg`
- Converts to WAV format for processing

#### 2. **Vocal Separation** 
- Uses Meta's Demucs model to isolate vocals from background music
- Preserves instrumentals for mixing back into final output

#### 3. **Speech Recognition**
- OpenAI's **Whisper** transcribes audio to text
- Automatically detects language
- Provides timestamps for accurate synchronization

#### 4. **Translation** (Optional)
- Translates transcribed text to target language
- Preserves context and meaning

#### 5. **Text-to-Speech**
- Converts translated text back to speech
- Multiple TTS engine options:
  - ElevenLabs (natural, expressive voices)
  - Local models (privacy-focused)

#### 6. **Voice Cloning**
- **OpenVoice** (MyShell AI) clones original speaker's voice characteristics
- Applies voice style to TTS output
- Creates natural-sounding dubbed audio

#### 7. **Audio Mixing**
- Combines dubbed speech with background music/effects
- Normalizes audio levels
- Creates final audio mix

#### 8. **LipSync** (Optional)
- **Replicate HeadGen** (`heygen/lipsync-speed`) synchronizes lip movements
- Video character's mouth moves naturally to match new audio
- Premium quality with fast processing

---

## Technology Stack

### Core Technologies

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Speech Recognition** | OpenAI Whisper | Transcribe audio to text |
| **Voice Cloning** | OpenVoice (MyShell) | Clone speaker voice characteristics |
| **Vocal Separation** | Meta Demucs | Separate vocals from music |
| **Audio Processing** | ffmpeg | Video/audio mixing and conversion |
| **LipSync** | Replicate HeadGen | Synchronize lip movements to audio |
| **Backend** | FastAPI + Uvicorn | REST API for processing |
| **Web UI** | Gradio / HTML5 | User interface for uploads/processing |

### API integrations

- **Replicate**: Cloud ML inference for LipSync
- **ElevenLabs** (optional): High-quality TTS
- **OpenVoice**: Local voice cloning engine

---

## Installation & Setup

### Prerequisites

- Python 3.8+
- Git
- ffmpeg (for audio/video processing)
- 4GB+ RAM (more for batch processing)
- Stable internet (for API calls)

### Step 1: Clone & Setup Environment

```bash
git clone <repository-url>
cd whisper-main
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS/Linux
source .venv/bin/activate
```

### Step 2: Install Dependencies

```bash
pip install -r requirements.txt
pip install replicate gradio_client elevenlabs openvoice
```

### Step 3: Configure API Keys

Create a `.env` file in the project root:

```env
# Replicate LipSync API (required for video sync)
REPLICATE_API_TOKEN=your_replicate_api_key_here

# ElevenLabs TTS (optional, for high-quality voices)
ELEVENLABS_API_KEY=your_elevenlabs_key_here

# OpenAI (optional, if not using local Whisper)
OPENAI_API_KEY=your_openai_key_here
```

**Get API Keys:**
- Replicate: https://replicate.com/account/api-tokens
- ElevenLabs: https://elevenlabs.io/app/billing
- OpenAI: https://platform.openai.com/account/api-keys

### Step 4: Download Models

The first run will automatically download required models:
- Whisper model (use `large` for best accuracy or `base` for speed)
- OpenVoice checkpoints
- Demucs model

This may take 5-10 minutes depending on internet speed.

---

## Usage

### Via Web Interface (Recommended)

```bash
# Start backend server
python stitch/backend.py

# Open in browser
http://127.0.0.1:8001/ui
```

**Steps:**
1. Upload video file
2. Select target language
3. Choose voice settings (voice cloning strength)
4. Enable LipSync (optional but recommended)
5. Click "Process"
6. Download dubbed video

### Via Command Line

```bash
# Basic dubbing
python dubber.py --input video.mp4 --output dubbed_video.mp4 --language es

# With LipSync
python dubber.py --input video.mp4 --output dubbed_video.mp4 --language fr --lipsync

# With custom voice cloning
python dubber.py --input video.mp4 --output dubbed_video.mp4 \
  --language de --voice_strength 0.8 --lipsync
```

**Common Parameters:**
- `--input` - Input video file path
- `--output` - Output video file path
- `--language` - Target language (es, fr, de, ja, zh, etc.)
- `--lipsync` - Enable video LipSync
- `--voice_strength` - Voice cloning intensity (0.0-1.0)
- `--tts_engine` - TTS provider (elevenlabs, local)

---

## Performance Considerations

### Processing Times (Approximate)

| Operation | Duration | Hardware | Notes |
|-----------|----------|----------|-------|
| **Audio Extraction** | < 1 min | Any | Fast, I/O bound |
| **Vocal Separation** | 2-5 min | GPU recommended | 1-2 min on GPU |
| **Whisper Transcription** | 2-10 min | GPU recommended | Depends on video length |
| **Voice Cloning (OpenVoice)** | 3-8 min | CPU/GPU | Local processing |
| **LipSync (Replicate)** | 2-10 min | Cloud | Charged per second |
| **Total End-to-End** | **15-45 min** | Mixed | For 10-minute video |

### Cost Estimate (Replicate LipSync)

- **HeadGen LipSync**: $0.0333/second of video
- **10-minute video**: ~$20 USD
- **Batch processing**: Consider longer sessions for volume discounts

### Resource Requirements

| Component | CPU | RAM | GPU | Disk |
|-----------|-----|-----|-----|------|
| **Minimum** | 4-core | 8GB | Optional | 50GB |
| **Recommended** | 8-core | 16GB | 4GB VRAM | 100GB |
| **Ideal** | 16-core | 32GB | 8GB+ VRAM | 200GB |

---

## Project Structure

```
whisper-main/
├── dubber.py                  # Main dubbing pipeline
├── requirements.txt           # Python dependencies
├── .env                       # API keys & configuration
├── stitch/                    # Backend server
│   ├── backend.py            # FastAPI application
│   ├── dub_logic.js          # Frontend dubbing logic
│   ├── final_ui.html         # Web interface
│   └── DESIGN.md             # Architecture documentation
├── OpenVoice/                # Voice cloning engine
│   ├── openvoice/            # Core implementation
│   ├── checkpoints_v2/       # Pre-trained models
│   └── demo_part*.ipynb      # Tutorial notebooks
├── separated/                # Output folder (vocals/music)
└── [job_folders]/            # Temporary processing cache
```

---

## Features

### ✅ Implemented

- [x] Video audio extraction & processing
- [x] Whisper-based speech recognition
- [x] Multi-language support (40+ languages)
- [x] OpenVoice voice cloning
- [x] FFmpeg audio mixing
- [x] Replicate LipSync integration
- [x] Web UI for easy processing
- [x] Batch job tracking
- [x] Error recovery & fallback paths
- [x] Gradio Space backup for LipSync

### 🚀 Future Enhancements

- [ ] Real-time live stream processing
- [ ] Batch video processing API
- [ ] GPU acceleration for local processing
- [ ] Advanced multi-speaker handling
- [ ] Emotion preservation in voice cloning
- [ ] Custom voice profile training
- [ ] Support for sign language translation
- [ ] Mobile-optimized output formats

---

## Troubleshooting

### Issue: "REPLICATE_API_TOKEN not found"

**Solution:** Add token to `.env` file:
```env
REPLICATE_API_TOKEN=r8_xxxxx...
```

### Issue: LipSync fails, falls back to Gradio

**Reason:** Replicate API rate limiting or invalid token
**Solution:** 
- Verify token is valid on https://replicate.com/account/api-tokens
- Check Replicate dashboard for rate limits
- Use fallback Gradio Space (slower but free)

### Issue: Out of memory during processing

**Solution:**
- Reduce video resolution before processing
- Process shorter video segments
- Close other applications
- Upgrade to GPU instance

### Issue: Audio/video sync is off

**Reason:** Incomplete LipSync processing
**Solution:**
- Enable `--lipsync` flag
- Wait for Replicate processing to complete
- Check backend logs for errors

---

## Configuration Examples

### Example 1: Spanish Dubbing with LipSync

```bash
python dubber.py \
  --input film.mp4 \
  --output film_es.mp4 \
  --language es \
  --lipsync \
  --voice_strength 0.9
```

### Example 2: Batch Processing Multiple Videos

```python
import subprocess
import os

videos = ['video1.mp4', 'video2.mp4', 'video3.mp4']
language = 'fr'

for video in videos:
    output = video.replace('.mp4', f'_{language}.mp4')
    cmd = f"python dubber.py --input {video} --output {output} --language {language} --lipsync"
    subprocess.run(cmd, shell=True)
    print(f"✓ Processed {video}")
```

---

## API Reference

### Backend Endpoints

- **POST** `/dub` - Submit dubbing job
- **GET** `/status/<job_id>` - Check processing status
- **GET** `/download/<job_id>` - Download finished video
- **GET** `/cancel/<job_id>` - Cancel active job

---

## Limitations

1. **Long Videos**: Processing 1+ hour videos may require multiple jobs
2. **Real-time Streaming**: Current architecture designed for VOD (video-on-demand)
3. **Audio Quality**: Depends on original audio clarity
4. **Language Pairs**: Some language combinations may have lower quality
5. **Cost**: LipSync via Replicate incurs API charges

---

## Contributing

Contributions welcome! Areas for improvement:

- [ ] Performance optimization (local LipSync model)
- [ ] Additional language support
- [ ] Better error messages
- [ ] Documentation improvements
- [ ] Test coverage

---

## License

This project uses multiple open-source components:
- **Whisper**: MIT License (OpenAI)
- **OpenVoice**: MIT License (MyShell)
- **Demucs**: CC0 License (Meta)
- **FFmpeg**: GPL 2.0

See individual component licenses for details.

---

## Support & Resources

- **Whisper Docs**: https://github.com/openai/whisper
- **OpenVoice Repo**: https://github.com/myshell-ai/OpenVoice
- **Replicate API**: https://replicate.com/docs
- **FFmpeg Guide**: https://ffmpeg.org/documentation.html

---

## Contact

For issues, questions, or feature requests:
- Open an GitHub issue
- Check existing documentation
- Review backend logs: `stitch/uvicorn_log.txt`

---

## Acknowledgments

- **Whisper Team** (OpenAI) - Speech recognition
- **MyShell AI** - OpenVoice voice cloning
- **Meta AI** - Demucs vocal separation
- **Replicate** - LipSync infrastructure
- **Gradio Team** - Web UI framework

---

**Last Updated**: May 2026  
**Status**: Production Ready with Cloud Assistant Architecture  
**Version**: 1.0
