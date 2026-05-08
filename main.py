from fastapi import FastAPI
from yt_dlp import YoutubeDL

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

        return {
            "title": info["title"],
            "channel": info["channel"],
            "duration": info["duration"],
        }