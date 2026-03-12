"""
Flask Web App for Video Dubbing with Voice Cloning
===================================================
Upload a video in any language → get back an English dubbed video with cloned voice.
"""

import os
import uuid
import threading
import time
from flask import (
    Flask, render_template, request, jsonify, send_file, url_for
)
from werkzeug.utils import secure_filename

# Import the dubbing pipeline
from dub_video_clone import dub_video

# ─────────────────── configuration ──────────────────────────────

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "web_uploads")
OUTPUT_FOLDER = os.path.join(BASE_DIR, "web_outputs")
ALLOWED_EXTENSIONS = {"mp4", "mkv", "avi", "mov", "webm", "flv"}
MAX_CONTENT_LENGTH = 2 * 1024 * 1024 * 1024  # 2 GB

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

app = Flask(__name__, template_folder="templates", static_folder="static")
app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH
app.secret_key = "video-dubbing-secret-key"

# ─────────────── job tracking (in-memory) ───────────────────────

jobs = {}  # job_id -> { status, progress, message, output_path, error, filename }


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# ─────────────── background dubbing worker ──────────────────────

def run_dubbing_job(job_id: str, input_path: str, output_path: str, settings: dict):
    """Run the dubbing pipeline in a background thread."""
    try:
        jobs[job_id]["status"] = "processing"
        jobs[job_id]["message"] = "Starting dubbing pipeline..."

        def progress_callback(step, total, message):
            jobs[job_id]["progress"] = int((step / total) * 100)
            jobs[job_id]["message"] = message

        dub_video(
            input_video=input_path,
            output_video=output_path,
            whisper_model=settings.get("whisper_model", "large"),
            source_language=settings.get("source_language", "auto"),
            speaker_sample_start=settings.get("speaker_sample_start", 10),
            speaker_sample_duration=settings.get("speaker_sample_duration", 15),
            keep_background=settings.get("keep_background", True),
            duck_level=settings.get("duck_level", -35),
            progress_callback=progress_callback,
        )

        jobs[job_id]["status"] = "completed"
        jobs[job_id]["progress"] = 100
        jobs[job_id]["message"] = "Dubbing complete! Your video is ready."
        jobs[job_id]["output_path"] = output_path

    except Exception as e:
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["message"] = f"Error: {str(e)}"
        jobs[job_id]["error"] = str(e)
        import traceback
        traceback.print_exc()

    finally:
        # Clean up uploaded file after processing
        try:
            if os.path.exists(input_path):
                os.remove(input_path)
        except Exception:
            pass


# ─────────────────────── routes ─────────────────────────────────

@app.route("/")
def index():
    """Main page with upload form."""
    return render_template("index.html")


@app.route("/upload", methods=["POST"])
def upload():
    """Handle video upload and start dubbing job."""
    if "video" not in request.files:
        return jsonify({"error": "No video file uploaded"}), 400

    file = request.files["video"]
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    if not allowed_file(file.filename):
        return jsonify({"error": f"Invalid file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"}), 400

    # Generate unique job ID
    job_id = str(uuid.uuid4())[:8]
    original_name = secure_filename(file.filename)
    name_base = os.path.splitext(original_name)[0]

    # Save uploaded file
    input_filename = f"{job_id}_{original_name}"
    input_path = os.path.join(UPLOAD_FOLDER, input_filename)
    file.save(input_path)

    # Output file path
    output_filename = f"{name_base}_dubbed_{job_id}.mp4"
    output_path = os.path.join(OUTPUT_FOLDER, output_filename)

    # Parse settings from form
    settings = {
        "whisper_model": request.form.get("whisper_model", "large"),
        "source_language": request.form.get("source_language", "auto"),
        "duck_level": float(request.form.get("duck_level", -35)),
        "keep_background": request.form.get("keep_background", "true").lower() == "true",
        "speaker_sample_start": float(request.form.get("speaker_sample_start", 10)),
        "speaker_sample_duration": float(request.form.get("speaker_sample_duration", 15)),
    }

    # Register job
    jobs[job_id] = {
        "status": "queued",
        "progress": 0,
        "message": "Upload complete. Starting dubbing...",
        "output_path": None,
        "error": None,
        "filename": output_filename,
        "created": time.time(),
    }

    # Start background thread
    thread = threading.Thread(
        target=run_dubbing_job,
        args=(job_id, input_path, output_path, settings),
        daemon=True,
    )
    thread.start()

    return jsonify({"job_id": job_id, "message": "Dubbing started!"})


@app.route("/status/<job_id>")
def job_status(job_id: str):
    """Return the current status of a dubbing job."""
    if job_id not in jobs:
        return jsonify({"error": "Job not found"}), 404
    job = jobs[job_id]
    return jsonify({
        "status": job["status"],
        "progress": job["progress"],
        "message": job["message"],
        "filename": job.get("filename"),
        "error": job.get("error"),
    })


@app.route("/download/<job_id>")
def download(job_id: str):
    """Download the dubbed video."""
    if job_id not in jobs:
        return jsonify({"error": "Job not found"}), 404

    job = jobs[job_id]
    if job["status"] != "completed" or not job.get("output_path"):
        return jsonify({"error": "Video is not ready yet"}), 400

    output_path = job["output_path"]
    if not os.path.exists(output_path):
        return jsonify({"error": "Output file not found"}), 404

    return send_file(
        output_path,
        as_attachment=True,
        download_name=job["filename"],
        mimetype="video/mp4",
    )


# ─────────── cleanup old files (optional) ──────────────────────

def cleanup_old_files(max_age_hours: int = 24):
    """Remove output files older than max_age_hours."""
    now = time.time()
    for folder in [UPLOAD_FOLDER, OUTPUT_FOLDER]:
        for f in os.listdir(folder):
            fpath = os.path.join(folder, f)
            if os.path.isfile(fpath):
                age_hours = (now - os.path.getmtime(fpath)) / 3600
                if age_hours > max_age_hours:
                    os.remove(fpath)


# ─────────────────────── entry point ────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("  Video Dubbing Web App")
    print("  Open http://localhost:5000 in your browser")
    print("=" * 60)
    app.run(host="0.0.0.0", port=5000, debug=False)
