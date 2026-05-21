import sys
import traceback
print(">>> run_app_android module loaded")

def start_server(files_dir, ffmpeg_path):
    print(">>> start_server called with dir:", files_dir, "and ffmpeg:", ffmpeg_path)
    import os
    os.environ["ANDROID_FILES_DIR"] = str(files_dir)
    os.environ["FFMPEG_PATH"] = str(ffmpeg_path)
    try:
        import uvicorn
        from web_app.main import app
        uvicorn.run(app, host="127.0.0.1", port=48921, log_level="info")
    except Exception as e:
        print(">>> start_server error:", e)
        traceback.print_exc()
        sys.stderr.flush()
