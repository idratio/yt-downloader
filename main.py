import os
from fastapi import FastAPI, HTTPException
from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

app = FastAPI()

@app.get("/")
def home():
    return {"message": "API running"}

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
        # If it fails, raise the error and stop
        raise HTTPException(status_code=400, detail=str(e))

    # If it succeeds, the code continues here (notice it is aligned with the try block)
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

@app.get("/download")
def download_video(url: str, quality: int = 720):
    if quality not in [360, 480, 720, 1080]:
        return {"error": "Invalid quality. Use 360, 480, 720, or 1080"}

    format_selector = f"bestvideo[height<={quality}]+bestaudio/best[height<={quality}]"

    options = {
        "outtmpl": f"{DOWNLOAD_DIR}/%(title)s.%(ext)s",
        "format": format_selector,
        "merge_output_format": "mp4"
    }

    try:
        with YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
    except DownloadError as e:
        raise HTTPException(status_code=400, detail=f"Download failed: {str(e)}")

    return {
        "status": "download complete",
        "quality": quality,
        "file": filename
    }