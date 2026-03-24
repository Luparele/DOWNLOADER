import sys
import os
import uuid
import threading
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import imageio_ffmpeg
import shutil

import yt_dlp as youtube_dl

if getattr(sys, 'frozen', False):
    # PyInstaller uses _MEIPASS for bundled files
    BASE_DIR = sys._MEIPASS
    # EXEC_DIR is where the executable is physically located
    EXEC_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    EXEC_DIR = BASE_DIR

# Fix ffmpeg location for yt-dlp to recognize its basename
if os.path.exists(os.path.join(EXEC_DIR, "ffmpeg.exe")):
    ffmpeg_link = os.path.join(EXEC_DIR, "ffmpeg.exe")
else:
    import imageio_ffmpeg
    ffmpeg_link = imageio_ffmpeg.get_ffmpeg_exe()

app = FastAPI(title="Futuristic YouTube-DL Web UI")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins, including the Capacitor Android app
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# The static files mount is moved to the end of the file so it doesn't shadow API routes

class VideoRequest(BaseModel):
    url: str
    format_id: str = "best"
    browser: str = "none"



@app.post("/api/info")
def get_video_info(req: VideoRequest):
    ydl_opts = {
        'simulate': True,
        'quiet': True,
        'no_warnings': True,
        # Bypass options for Cloud IPs 
        'extractor_args': {
            'youtube': ['player_client=android,web']
        },
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
            'Sec-Fetch-Mode': 'navigate',
        },
        'nocheckcertificate': True,
        'socket_timeout': 30,
        'ffmpeg_location': ffmpeg_link,
    }
    
    cookies_path = os.path.join(EXEC_DIR, "cookies.txt")
    has_cookies = os.path.exists(cookies_path)
    
    # Filesystem Diagnostic for Render
    try:
        files = os.listdir(EXEC_DIR)
        print(f"DEBUG FS: CurDir: {os.getcwd()} | Root: {EXEC_DIR} | Files: {files}")
    except:
        pass

    print(f"DEBUG INFO: cookies.txt path: {cookies_path} | Exists: {has_cookies}")
    
    if has_cookies:
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

DOWNLOAD_TASKS = {}

@app.post("/api/download")
async def start_download(req: VideoRequest):
    task_id = str(uuid.uuid4())
    DOWNLOAD_TASKS[task_id] = {
        "status": "starting",
        "percent": "0%",
        "speed": "",
        "eta": "",
        "file": None,
        "error": None
    }
    
    # Start thread
    threading.Thread(target=run_download_task, args=(task_id, req)).start()
    return {"status": "started", "task_id": task_id}

def run_download_task(task_id: str, req: VideoRequest):
    # Ensure Base Downloads directory exists
    downloads_dir = os.path.join(EXEC_DIR, "Downloads")
    os.makedirs(downloads_dir, exist_ok=True)
    
    if req.format_id and req.format_id != "best":
        format_param = f"bestvideo[height<={req.format_id}]+bestaudio/best[height<={req.format_id}]/best"
    else:
        format_param = "bestvideo+bestaudio/best"
        
    def progress_hook(d):
        if d['status'] == 'downloading':
            DOWNLOAD_TASKS[task_id].update({
                "status": "downloading",
                "percent": d.get('_percent_str', '').strip(),
                "speed": d.get('_speed_str', '').strip(),
                "eta": d.get('_eta_str', '').strip()
            })
        elif d['status'] == 'finished':
            DOWNLOAD_TASKS[task_id].update({
                "status": "processing",
                "percent": "100%",
                "eta": "00:00"
            })
            
    ydl_opts = {
        'outtmpl': os.path.join(downloads_dir, '%(extractor)s', '%(title)s.%(ext)s'),
        'format': format_param,
        'merge_output_format': 'mp4',
        'ffmpeg_location': ffmpeg_link,
        'noplaylist': True,
        'retries': 10,
        'fragment_retries': 10,
        'extractor_retries': 5,
        'extractor_args': {'youtube': ['player_client=android,web']},
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
            'Sec-Fetch-Mode': 'navigate',
            'Referer': 'https://www.tiktok.com/',
        },
        'socket_timeout': 30,
        'prefer_free_formats': True,
        'nocheckcertificate': True,
        'progress_hooks': [progress_hook]
    }
    
    cookies_path = os.path.join(EXEC_DIR, "cookies.txt")
    if os.path.exists(cookies_path):
        ydl_opts['cookiefile'] = cookies_path
    elif req.browser and req.browser != "none":
        ydl_opts['cookiesfrombrowser'] = [req.browser]

    try:
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(req.url, download=True)
            platform = info.get('extractor', 'unknown')
            generated_path = ydl.prepare_filename(info)
            sanitized_name = os.path.basename(generated_path)
            final_name = f"{os.path.splitext(sanitized_name)[0]}.{info.get('ext', 'mp4')}"
            
            DOWNLOAD_TASKS[task_id].update({
                "status": "success",
                "file": f"Downloads/{platform}/{final_name}"
            })
    except Exception as e:
        DOWNLOAD_TASKS[task_id].update({
            "status": "error",
            "error": str(e)
        })

@app.get("/api/progress/{task_id}")
async def get_progress(task_id: str):
    task = DOWNLOAD_TASKS.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task_id não encontrado.")
    return task

@app.get("/api/serve-file")
async def serve_file(path: str):
    """
    Streams a file from the server's filesystem to the user's device.
    """
    # Security: Ensure we are only serving from the Downloads directory
    base_dir = os.path.join(EXEC_DIR, "Downloads")
    file_path = os.path.abspath(os.path.join(base_dir, "..", path))
    
    if not file_path.startswith(base_dir) or not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Arquivo não encontrado ou acesso negado.")
    
    filename = os.path.basename(file_path)
    return FileResponse(
        path=file_path,
        filename=filename,
        media_type='application/octet-stream'
    )

@app.get("/api/open-folder")
async def open_folder(path: str):
    """
    Opens the directory containing the requested file on the server's local machine.
    """
    base_dir = os.path.join(EXEC_DIR, "Downloads")
    file_path = os.path.abspath(os.path.join(base_dir, "..", path))
    
    if not file_path.startswith(base_dir) or not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Arquivo não encontrado ou acesso negado.")
    
    folder_path = os.path.dirname(file_path)
    try:
        if os.name == 'nt':
            os.startfile(folder_path)
        elif sys.platform == 'darwin':
            import subprocess
            subprocess.Popen(['open', folder_path])
        else:
            import subprocess
            subprocess.Popen(['xdg-open', folder_path])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
        
    return {"status": "success"}

# Mount static files at the root, but do it last so it doesn't override /api routes
static_dir = os.path.join(BASE_DIR, "web_app", "static")
app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
