import os
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import imageio_ffmpeg
import asyncio
import yt_dlp as youtube_dl
import urllib.parse

app = FastAPI()

# Configuração CORS para permitir que o frontend na Vercel chame este backend no Render
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Em produção, você pode colocar ["https://seu-front.vercel.app"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Garantir que a pasta Downloads exista antes de montar
base_downloads_dir = os.path.join(os.getcwd(), "Downloads")
if not os.path.exists(base_downloads_dir):
    os.makedirs(base_downloads_dir)

app.mount("/downloads", StaticFiles(directory="Downloads"), name="downloads")

@app.get("/")
def home():
    return FileResponse("index.html")

ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()


# Global dictionary to store download progress per URL
active_downloads = {}

class VideoReq(BaseModel):
    url: str
    browser: str = "none"
    format_id: str = None

@app.get("/")
def root():
    return FileResponse("static/index.html")

@app.get("/api/progress")
def get_progress(url: str):
    return {"progress": active_downloads.get(url, "0%")}

@app.post("/api/info")
def get_info(req: VideoReq):
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
            
            formats = []
            for f in info.get('formats', []):
                # Resolution
                res = f.get('resolution') or f"{f.get('width')}x{f.get('height')}"
                if res == "None" or not res: res = "Audio Only"
                
                # Check for video and audio
                has_v = f.get('vcodec') != 'none'
                has_a = f.get('acodec') != 'none'
                
                type_tag = ""
                if has_v and has_a: type_tag = "[V+A]"
                elif has_v: type_tag = "[Video]"
                elif has_a: type_tag = "[Audio]"

                formats.append({
                    "id": f.get('format_id'),
                    "ext": f.get('ext'),
                    "res": res,
                    "type": type_tag,
                    "note": f.get('format_note') or ""
                })

            return {
                "title": info.get('title'),
                "thumbnail": info.get('thumbnail'),
                "id": info.get('id'),
                "formats": formats[::-1]
            }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/download")
def download(req: VideoReq):
    print(f"Download request: {req.url} - Selected Format ID: {req.format_id}")
    ACTIVE_URL = req.url
    active_downloads[ACTIVE_URL] = "0%"

    def my_hook(d):
        if d['status'] == 'downloading':
            # `_percent_str` typically looks like " 45.3%" or "100.0%"
            active_downloads[ACTIVE_URL] = d.get('_percent_str', '0%').strip()
        elif d['status'] == 'finished':
            active_downloads[ACTIVE_URL] = "100%"

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
            
        base_dir = os.path.join(os.getcwd(), "Downloads")
        platform_dir = os.path.join(base_dir, platform)
        if not os.path.exists(platform_dir): os.makedirs(platform_dir)
            
        if req.format_id and req.format_id != 'best':
            target_format = f"{req.format_id}+bestaudio/{req.format_id}"
        else:
            target_format = 'best'

        print(f"Effective target format for yt-dlp: {target_format}")

        opts_dl = {
            'format': target_format,
            'outtmpl': os.path.join(platform_dir, '%(title)s.%(ext)s'),
            'ffmpeg_location': ffmpeg_exe,
            'nocheckcertificate': True,
            'merge_output_format': 'mp4',
            'progress_hooks': [my_hook]
        }
        if req.browser != "none":
            opts_dl['cookiesfrombrowser'] = [req.browser]
            
        with youtube_dl.YoutubeDL(opts_dl) as ydl:
            res = ydl.extract_info(req.url, download=True)
            original_filepath = ydl.prepare_filename(res)
            base_name = os.path.splitext(os.path.basename(original_filepath))[0]
            final_filename = f"{base_name}.mp4"
            
            # URL encode paths for safe web transit
            encoded_name = urllib.parse.quote(final_filename)
            file_url = f"/downloads/{platform}/{encoded_name}"
            
            # Keep it at 100% until frontend resets it or a new active DL starts
            active_downloads[ACTIVE_URL] = "Concluído!" 
            return {"status": "ok", "platform": platform, "url": file_url, "filename": final_filename}
    except Exception as e:
        print(f"Error during download: {str(e)}")
        active_downloads[ACTIVE_URL] = "Erro!"
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/download_mp3")
def download_mp3(req: VideoReq):
    print(f"MP3 Download request: {req.url}")
    ACTIVE_URL = req.url
    active_downloads[ACTIVE_URL] = "0%"

    def my_hook(d):
        if d['status'] == 'downloading':
            active_downloads[ACTIVE_URL] = d.get('_percent_str', '0%').strip()
        elif d['status'] == 'finished':
            active_downloads[ACTIVE_URL] = "Convertendo (MP3)..."

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
            
        base_dir = os.path.join(os.getcwd(), "Downloads")
        platform_dir = os.path.join(base_dir, platform)
        if not os.path.exists(platform_dir): os.makedirs(platform_dir)

        opts_dl = {
            'format': 'bestaudio/best',
            'outtmpl': os.path.join(platform_dir, '%(title)s.%(ext)s'),
            'ffmpeg_location': ffmpeg_exe,
            'nocheckcertificate': True,
            'progress_hooks': [my_hook],
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        }
        if req.browser != "none":
            opts_dl['cookiesfrombrowser'] = [req.browser]
            
        with youtube_dl.YoutubeDL(opts_dl) as ydl:
            res = ydl.extract_info(req.url, download=True)
            original_filepath = ydl.prepare_filename(res)
            base_name = os.path.splitext(os.path.basename(original_filepath))[0]
            final_filename = f"{base_name}.mp3"
            
            encoded_name = urllib.parse.quote(final_filename)
            file_url = f"/downloads/{platform}/{encoded_name}"

            active_downloads[ACTIVE_URL] = "Concluído (MP3)!" 
            return {"status": "ok", "platform": platform, "url": file_url, "filename": final_filename}
    except Exception as e:
        print(f"Error during MP3 download: {str(e)}")
        active_downloads[ACTIVE_URL] = "Erro!"
        raise HTTPException(status_code=400, detail=str(e))






