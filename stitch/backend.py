from fastapi import FastAPI, File, UploadFile, Form, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
import whisper
from fastapi.staticfiles import StaticFiles
import tempfile
import shutil
import os
import sys
import subprocess
import uuid
import json
from dotenv import load_dotenv

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


# Add parent dir so we can import dubber
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)
# Add current dir so we can import live_pipeline
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, CURRENT_DIR)

import live_pipeline
from dotenv import load_dotenv
load_dotenv(os.path.join(ROOT_DIR, ".env"))

app = FastAPI()

# Allow CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files from the current directory (stitch)
app.mount("/static", StaticFiles(directory=os.path.dirname(os.path.abspath(__file__))), name="static")

@app.get("/ui")
async def get_ui():
    return FileResponse(os.path.join(os.path.dirname(os.path.abspath(__file__)), "code.html"))


# Model Cache
models = {}

def get_model(model_size: str):
    if model_size not in models:
        print(f"Loading Whisper model: {model_size}...")
        models[model_size] = whisper.load_model(model_size)
    return models[model_size]

@app.get("/")
def root():
    return {"message": "Whisper backend is running."}

@app.get("/status/{job_id}")
def get_status(job_id: str):
    """Retrieve the current status of a dubbing job."""
    # Look for status files in the root directory (parent of stitch)
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    status_file = os.path.join(root_dir, f"status_{job_id}.txt")
    
    if not os.path.exists(status_file):
        return {"status": "Waiting..."}
    with open(status_file, "r", encoding="utf-8") as f:
        status_text = f.read().strip()
    return {"status": status_text}

@app.post("/transcribe/")
async def transcribe(
    file: UploadFile = File(...), 
    language: str = Form(None), 
    task: str = Form("transcribe"),
    model_size: str = Form("base")
):
    suffix = os.path.splitext(file.filename)[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name
    try:
        current_model = get_model(model_size)
        options = {"task": task}
        if language and language.lower() not in ["auto-detect language", "auto-detect", ""]:
            options["language"] = language
        result = current_model.transcribe(tmp_path, **options)
        return JSONResponse({"text": result["text"]})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
    finally:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception as e:
                print(f"Failed to remove temp transcribe file: {e}")

@app.post("/dub/")
async def dub(
    file: UploadFile = File(...), 
    language: str = Form(None), 
    model_size: str = Form("small"),
    job_id: str = Form(None),
    lipsync: bool = Form(False)  # LipSync is optional and disabled by default
):
    # Use job_id for temp filename to enable resumability
    if not job_id:
        job_id = str(uuid.uuid4())
    suffix = os.path.splitext(file.filename)[1] or ".mp4"
    # Use absolute path for temporary file to ensure dubber can find it
    safe_job_id = job_id.replace("-", "_")
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    tmp_path = os.path.abspath(os.path.join(root_dir, f"tmp_{safe_job_id}{suffix}"))
    
    with open(tmp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        dubber_script = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dubber.py")
        python_exe = sys.executable
        
        # Build command with job_id for status tracking
        cmd = [python_exe, dubber_script, tmp_path, "--model", model_size, "--job-id", job_id]
        if language and language.lower() not in ["auto-detect language", "auto-detect", ""]:
            cmd.extend(["--target_language", language])
        
        if lipsync:
            cmd.append("--lipsync")
            
        print(f"[{job_id}] Running: {' '.join(cmd)}")
        
        # Start dubbing
        result = subprocess.run(
            cmd,
            capture_output=True, text=True, cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        
        # Log output for debugging
        log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dubber_out.log")
        with open(log_path, "w", encoding="utf-8") as f:
            f.write("STDOUT:\n")
            f.write(result.stdout)
            f.write("\nSTDERR:\n")
            f.write(result.stderr)

        if result.returncode != 0:
            print(f"[{job_id}] Error: {result.stderr}")
            return JSONResponse({"error": f"Dubbing failed. See stitch/dubber_out.log for details. Last 200 chars: {result.stderr[-200:]}"}, status_code=500)
        
        base_name = os.path.splitext(os.path.basename(tmp_path))[0]
        dubbed_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            f"{base_name}_dubbed.mp4"
        )
        
        if not os.path.exists(dubbed_path):
            return JSONResponse({"error": "Dubbed file not found."}, status_code=500)
        
        # Succeeded! Cleanup input file
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

        return FileResponse(
            dubbed_path,
            media_type="video/mp4",
            filename=f"{os.path.splitext(file.filename)[0]}_dubbed.mp4",
            headers={"X-Job-ID": job_id}
        )
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
    finally:
        # Leave status files in place if Windows still has a transient lock.
        # A cleanup failure should never turn a finished dubbing request into a 500.
        root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        status_file = os.path.join(root_dir, f"status_{job_id}.txt")
        if os.path.exists(status_file):
            try:
                os.remove(status_file)
            except PermissionError:
                pass

@app.websocket("/live-dub")
async def websocket_live_dub(websocket: WebSocket):
    await websocket.accept()
    print("WebSocket connected for live dubbing")
    
    # Send an initial config request or wait for first message
    try:
        # The first message should be JSON config
        config_data = await websocket.receive_text()
        config = json.loads(config_data)
        target_lang = config.get("language", "spanish")
        model_size = config.get("model_size", "base")
        print(f"Live dub config: lang={target_lang}, model={model_size}")
        
        try:
            current_model = get_model(model_size)
        except Exception as model_err:
            print(f"Error loading Whisper model '{model_size}': {model_err}")
            await websocket.send_text(json.dumps({
                "type": "error", 
                "message": f"Failed to load Whisper model '{model_size}'. If using 'large-v3', the system might be out of memory. Error: {model_err}"
            }))
            await websocket.close()
            return
        
        while True:
            # Receive message
            message = await websocket.receive()
            
            if message["type"] == "websocket.receive":
                if "text" in message and message["text"]:
                    try:
                        data = json.loads(message["text"])
                        if "language" in data:
                            target_lang = data["language"]
                            print(f"Updated live dub config: lang={target_lang}")
                    except json.JSONDecodeError:
                        pass
                    continue
                elif "bytes" in message and message["bytes"]:
                    audio_bytes = message["bytes"]
                else:
                    continue
            elif message["type"] == "websocket.disconnect":
                break
            else:
                continue
                
            # Write to temp file
            print(f"Received audio chunk of size {len(audio_bytes)} bytes")
            with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as tmp:
                tmp.write(audio_bytes)
                tmp_path = tmp.name
                
            try:
                wav_path = tmp_path + ".wav"
                # Explicitly convert to WAV to fix any MediaRecorder WebM header issues
                subprocess.run(["ffmpeg", "-y", "-i", tmp_path, "-ar", "16000", "-ac", "1", wav_path], capture_output=True, check=True)
                # 1. First, check volume to avoid hallucinating on background noise
                is_silent = False
                import wave
                import numpy as np
                try:
                    if os.path.exists(wav_path):
                        with wave.open(wav_path, 'rb') as wf:
                            frames = wf.readframes(wf.getnframes())
                            audio_data = np.frombuffer(frames, dtype=np.int16)
                            if len(audio_data) > 0:
                                rms = np.sqrt(np.mean(audio_data.astype(np.float32)**2))
                                if rms < 100:  # Threshold for background noise
                                    is_silent = True
                                    print(f"Volume too low ({rms:.2f}), skipping transcription.")
                except Exception as e:
                    print(f"Error checking volume: {e}")

                if is_silent:
                    transcribed_text = ""
                else:
                    # Transcribe (use aggressive thresholds for short chunks)
                    result = current_model.transcribe(
                        wav_path if os.path.exists(wav_path) else tmp_path, 
                        fp16=False, 
                        condition_on_previous_text=False,
                        no_speech_threshold=0.6,
                        logprob_threshold=-1.0,
                        compression_ratio_threshold=2.4
                    )
                    transcribed_text = result["text"].strip()
                    
                    # Filter out common Whisper hallucinations for silence
                    hallucinations = ["thank you.", "thanks for watching.", "thank you for watching.", "thanks.", "thank you", "thanks", "you"]
                    if transcribed_text.lower() in hallucinations:
                        print(f"Filtered hallucination: {transcribed_text}")
                        transcribed_text = ""
                try:
                    print(f"Transcribed: {transcribed_text}")
                except UnicodeEncodeError:
                    print(f"Transcribed: {transcribed_text.encode('ascii', 'replace').decode('ascii')}")
                
                if transcribed_text:
                    # 2. Translate
                    translated_text = await live_pipeline.translate_text(transcribed_text, target_lang)
                    try:
                        print(f"Translated: {translated_text}")
                    except UnicodeEncodeError:
                        print(f"Translated: {translated_text.encode('ascii', 'replace').decode('ascii')}")
                    
                    # Send text info back immediately so the user doesn't wait for TTS
                    await websocket.send_text(json.dumps({
                        "type": "transcript",
                        "original": transcribed_text,
                        "translated": translated_text
                    }))
                    
                    # 3. TTS
                    tts_audio_path = await live_pipeline.text_to_speech(translated_text, target_lang)
                    
                    if tts_audio_path and os.path.exists(tts_audio_path):
                        # Convert to WAV for maximum compatibility and instant decoding on client
                        tts_wav_path = tts_audio_path + ".wav"
                        try:
                            # Run ffmpeg to convert MP3 to WAV (24000Hz, mono, PCM 16-bit)
                            subprocess.run(
                                ["ffmpeg", "-y", "-i", tts_audio_path, "-acodec", "pcm_s16le", "-ar", "24000", "-ac", "1", tts_wav_path],
                                capture_output=True,
                                check=True
                            )
                            if os.path.exists(tts_wav_path):
                                with open(tts_wav_path, "rb") as f:
                                    dubbed_bytes = f.read()
                                await websocket.send_bytes(dubbed_bytes)
                            else:
                                raise FileNotFoundError("WAV conversion file not found")
                        except Exception as conv_err:
                            print(f"Error converting TTS to WAV: {conv_err}")
                            # Fallback: send the raw MP3 bytes
                            with open(tts_audio_path, "rb") as f:
                                dubbed_bytes = f.read()
                            await websocket.send_bytes(dubbed_bytes)
                        finally:
                            # Clean up files
                            try:
                                if os.path.exists(tts_audio_path):
                                    os.remove(tts_audio_path)
                            except Exception as e:
                                print(f"Failed to remove tts mp3 file: {e}")
                            try:
                                if os.path.exists(tts_wav_path):
                                    os.remove(tts_wav_path)
                            except Exception as e:
                                print(f"Failed to remove tts wav file: {e}")
                else:
                    # No speech detected, let the user know we are processing
                    await websocket.send_text(json.dumps({
                        "type": "info",
                        "message": "Listening... (no speech detected in last chunk)"
                    }))
            except Exception as e:
                print(f"Error processing chunk: {e}")
                await websocket.send_text(json.dumps({"type": "error", "message": str(e)}))
            finally:
                if os.path.exists(tmp_path):
                    try:
                        os.remove(tmp_path)
                    except Exception as e:
                        print(f"Failed to remove live tmp file: {e}")
                if 'wav_path' in locals() and os.path.exists(wav_path):
                    try:
                        os.remove(wav_path)
                    except Exception as e:
                        print(f"Failed to remove live wav file: {e}")
                    
    except WebSocketDisconnect:
        print("WebSocket disconnected")
    except Exception as e:
        print(f"WebSocket error: {e}")
        try:
            await websocket.close()
        except:
            pass

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend:app", host="127.0.0.1", port=8001, reload=True)
