import sys
import os
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import imageio_ffmpeg
import shutil

import yt_dlp as youtube_dl

# Fix ffmpeg location for yt-dlp to recognize its basename
# imageio-ffmpeg detects the OS (Win/Linux) automatically
ffmpeg_link = imageio_ffmpeg.get_ffmpeg_exe()

app = FastAPI(title="Futuristic YouTube-DL Web UI")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins, including the Capacitor Android app
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="web_app/static"), name="static")

class VideoRequest(BaseModel):
    url: str
    format_id: str = "best"
    browser: str = "none"

@app.get("/")
async def root():
    return FileResponse("web_app/static/index.html")

@app.post("/api/info")
async def get_video_info(req: VideoRequest):
    ydl_opts = {
        'simulate': True,
        'quiet': True,
        'no_warnings': True,
        # Bypass options for Cloud IPs (YouTube Bot Detection block)
        'extractor_args': {
            'youtube': ['player_client=android,ios,web']
        },
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Linux; Android 13; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Mobile Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
            'Sec-Fetch-Mode': 'navigate',
        },
        'sleep_requests': 1.5,
        'sleep_interval': 2,
        'max_sleep_interval': 5,
        'nocheckcertificate': True,
        'socket_timeout': 30,
        'ffmpeg_location': ffmpeg_link,
    }
    
    cookies_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cookies.txt")
    if os.path.exists(cookies_path):
        ydl_opts['cookiefile'] = cookies_path
    elif req.browser and req.browser != "none":
        ydl_opts['cookiesfrombrowser'] = [req.browser]
    
    try:
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            # Provide an empty dict for context or use extract_info directly
            info = ydl.extract_info(req.url, download=False)
            if 'entries' in info:
                # Can be a playlist or a list of videos
                info = info['entries'][0]
                
            # Extract unique resolutions available
            resolutions = set()
            for f in info.get("formats", []):
                height = f.get("height")
                vcodec = f.get("vcodec")
                if height and height > 0 and vcodec != "none":
                    resolutions.add(height)
            
            valid_formats = []
            for h in sorted(list(resolutions), reverse=True):
                valid_formats.append({
                    "format_id": str(h),
                    "resolution": f"{h}p",
                    "ext": "mp4",
                    "filesize": None
                })
            
            return {
                "title": info.get("title"),
                "thumbnail": info.get("thumbnail"),
                "duration": info.get("duration"),
                "platform": info.get("extractor", "Unknown"),
                "formats": valid_formats
            }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/download")
async def download_video(req: VideoRequest):
    # Ensure Base Downloads directory exists
    downloads_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "Downloads")
    os.makedirs(downloads_dir, exist_ok=True)
    
    # If format_id isn't specified or is empty, fallback to 'best'
    if req.format_id and req.format_id != "best":
        # Using a more resilient format string that gracefully falls back
        format_param = f"bestvideo[height<={req.format_id}][ext=mp4]+bestaudio[ext=m4a]/best[height<={req.format_id}]/best"
    else:
        format_param = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best"
    
    # Use %(extractor)s to dynamically create a subfolder with the platform name!
    ydl_opts = {
        'outtmpl': os.path.join(downloads_dir, '%(extractor)s', '%(title)s.%(ext)s'),
        'format': format_param,
        'merge_output_format': 'mp4',
        'ffmpeg_location': ffmpeg_link,
        'noplaylist': True,
        'retries': 10,
        'fragment_retries': 10,
        'extractor_retries': 5,
        # Anti-Bot Bypass (Using Android App signature API instead of vulnerable Web Browser)
        'extractor_args': {
            'youtube': ['player_client=android,ios,web']
        },
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Linux; Android 13; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Mobile Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
            'Sec-Fetch-Mode': 'navigate',
        },
        'sleep_requests': 1.5,
        'sleep_interval': 2,
        'max_sleep_interval': 5,
        'socket_timeout': 30,
        'prefer_free_formats': True,
    }
    
    cookies_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cookies.txt")
    if os.path.exists(cookies_path):
        ydl_opts['cookiefile'] = cookies_path
    elif req.browser and req.browser != "none":
        ydl_opts['cookiesfrombrowser'] = [req.browser]
    
    try:
        # In a real app we'd want this to be background task or async, but 
        # since youtube-dl is blocking, let's keep it simple for MVP
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(req.url, download=True)
            platform = info.get('extractor', 'unknown')
            file_name = f"{info.get('title')}.{info.get('ext', 'mp4')}"
            return {"status": "success", "file": f"Downloads/{platform}/{file_name}"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/open-folder")
async def open_downloads_folder():
    downloads_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "Downloads")
    os.makedirs(downloads_dir, exist_ok=True)
    
    try:
        # Since the user is on Windows, we can use os.startfile
        if os.name == 'nt':
            os.startfile(downloads_dir)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao abrir pasta: {str(e)}")
