import uvicorn
import webview
import threading
import time
import multiprocessing
from web_app.main import app
import socket

def start_server(port):
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="error")

if __name__ == "__main__":
    multiprocessing.freeze_support()
    
    try:
        port = 8000
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(('127.0.0.1', port))
            except OSError:
                s.bind(('127.0.0.1', 0))
                port = s.getsockname()[1]
                
        # Start uvicorn server in a daemon thread so it dies when the window closes
        t = threading.Thread(target=start_server, args=(port,), daemon=True)
        t.start()
        
        # Open a native desktop window using pywebview
        webview.create_window('Downloader - Extrator de Mídias', f'http://127.0.0.1:{port}', width=1000, height=800)
        webview.start()
        
    except Exception as e:
        import traceback
        with open("crash_log.txt", "w") as f:
            f.write(traceback.format_exc())
