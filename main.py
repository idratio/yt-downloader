import os
import uuid
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError


DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

app = FastAPI()

# A temporary in-memory database to store download progress
progress_db = {}


app.mount("/static", StaticFiles(directory="static"), name="static")
@app.get("/")
def home():
    return FileResponse("static/index.html")


@app.get("/info")
def get_info(url: str):
    options = {
        "quiet": True,
        "skip_download": True
    }

    try:
        with YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=False)
    except DownloadError as e:
        raise HTTPException(status_code=400, detail=str(e))

    formats = []
    for f in info.get("formats", []):
        formats.append({
            "format_id": f.get("format_id"),
            "ext": f.get("ext"),
            "resolution": f.get("resolution")
        })

    return {
        "title": info.get("title"),
        "channel": info.get("uploader"),
        "formats": formats[:10]
    }


# The background worker function
def process_download(url: str, quality: int, task_id: str):
    # This hook updates our dictionary every time yt-dlp downloads a chunk
    def progress_hook(d):
        if d['status'] == 'downloading':
            progress_db[task_id] = {
                "status": "downloading",
                "percent": d.get('_percent_str', '0%').strip(),
                "speed": d.get('_speed_str', 'N/A').strip(),
                "eta": d.get('_eta_str', 'N/A').strip()
            }
        elif d['status'] == 'finished':
            progress_db[task_id] = {
                "status": "processing",
                "percent": "100%",
                "message": "Download finished, merging video and audio..."
            }

    format_selector = f"bestvideo[height<={quality}]+bestaudio/best[height<={quality}]"

    options = {
        "outtmpl": f"{DOWNLOAD_DIR}/%(title)s.%(ext)s",
        "format": format_selector,
        "merge_output_format": "mp4",
        "progress_hooks": [progress_hook],
        "quiet": True  # Keeps Uvicorn logs clean
    }

    try:
        with YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            progress_db[task_id] = {
                "status": "complete",
                "file": filename
            }
    except Exception as e:
        progress_db[task_id] = {
            "status": "error",
            "detail": str(e)
        }


@app.get("/download")
def download_video(url: str, background_tasks: BackgroundTasks, quality: int = 720):
    if quality not in [360, 480, 720, 1080, 1440, 2160]:
        return {"error": "Invalid quality. Use 360, 480, 720, 1080, 1440 or 2160"}

    # Generate a unique ID and initialize the tracker
    task_id = str(uuid.uuid4())
    progress_db[task_id] = {"status": "starting", "percent": "0%"}

    # Hand the heavy lifting off to FastAPI's background thread
    background_tasks.add_task(process_download, url, quality, task_id)

    # Return immediately!
    return {
        "message": "Download started in the background",
        "task_id": task_id,
        "progress_url": f"/progress/{task_id}"
    }


@app.get("/progress/{task_id}")
def get_progress(task_id: str):
    if task_id not in progress_db:
        raise HTTPException(status_code=404, detail="Task not found")
    return progress_db[task_id]


@app.get("/download/audio")
def download_audio(url: str):
    options = {
        "outtmpl": f"{DOWNLOAD_DIR}/%(title)s.%(ext)s",
        "format": "bestaudio/best",
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }],
    }

    try:
        with YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info).rsplit('.', 1)[0] + '.mp3'
    except DownloadError as e:
        raise HTTPException(status_code=400, detail=f"Audio download failed: {str(e)}")

    return {
        "status": "audio download complete",
        "file": filename
    }