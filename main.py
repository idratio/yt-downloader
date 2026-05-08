import os

from fastapi import FastAPI
from yt_dlp import YoutubeDL
import os
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

    with YoutubeDL(options) as ydl:
        info = ydl.extract_info(url, download=False)

    formats = []

    for f in info.get("formats", []):

        formats.append({
            "format_id": f["format_id"],
            "ext": f.get("get"),
            "resolution": f.get("resolution")
        })

    return {
        "title": info.get("title"),
        "channel": info.get("uploader"),
        "formats": formats[:10]
    }

@app.get("/download")
def download(url: str):

    options = {
        "outtmpl": f"{DOWNLOAD_DIR}/%(title)s.%(ext)s",
        "format": "best"
    }

    with YoutubeDL(options) as ydl:

        info = ydl.extract_info(url, download=True)

        filename = ydl.prepare_filename(info)

    return {
        "status": "downlaod complete",
        "file": filename
    }