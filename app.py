import os
import yt_dlp as youtube_dl
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import imageio_ffmpeg

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()

class VideoReq(BaseModel):
    url: str
    browser: str = "none"

@app.get("/")
async def root():
    return FileResponse("static/index.html")

@app.post("/api/info")
async def get_info(req: VideoReq):
    opts = {
        'simulate': True,
        'nocheckcertificate': True,
        'ffmpeg_location': ffmpeg_exe,
    }
    if req.browser != "none":
        opts['cookiesfrombrowser'] = [req.browser]
        
    try:
        with youtube_dl.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(req.url, download=False)
            return {
                "title": info.get('title'),
                "thumbnail": info.get('thumbnail'),
                "id": info.get('id')
            }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/download")
async def download(req: VideoReq):
    # Setup for initial info extraction to get the platform
    opts_info = {
        'simulate': True,
        'nocheckcertificate': True,
        'ffmpeg_location': ffmpeg_exe,
    }
    if req.browser != "none":
        opts_info['cookiesfrombrowser'] = [req.browser]
    
    try:
        with youtube_dl.YoutubeDL(opts_info) as ydl:
            info = ydl.extract_info(req.url, download=False)
            platform = info.get('extractor_key', 'Generic').capitalize()
            
        # Define and create output directory hierarchy
        base_dir = os.path.join(os.getcwd(), "Downloads")
        platform_dir = os.path.join(base_dir, platform)
        if not os.path.exists(platform_dir):
            os.makedirs(platform_dir)
            
        opts_dl = {
            'format': 'best',
            'outtmpl': os.path.join(platform_dir, '%(title)s.%(ext)s'),
            'ffmpeg_location': ffmpeg_exe,
            'nocheckcertificate': True,
        }
        if req.browser != "none":
            opts_dl['cookiesfrombrowser'] = [req.browser]
            
        with youtube_dl.YoutubeDL(opts_dl) as ydl:
            ydl.download([req.url])
            return {"status": "ok", "platform": platform}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

