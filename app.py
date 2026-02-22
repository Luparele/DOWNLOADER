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
    format_id: str = None

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
async def download(req: VideoReq):
    print(f"Download request: {req.url} - Selected Format ID: {req.format_id}")
    
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
            
        # Refined format selection: 
        # Try to merge with best audio, otherwise just use the ID.
        # This prevents falling back to 'best' (which could be 4K).
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
        }
        if req.browser != "none":
            opts_dl['cookiesfrombrowser'] = [req.browser]
            
        with youtube_dl.YoutubeDL(opts_dl) as ydl:
            ydl.download([req.url])
            return {"status": "ok", "platform": platform}
    except Exception as e:
        print(f"Error during download: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))




