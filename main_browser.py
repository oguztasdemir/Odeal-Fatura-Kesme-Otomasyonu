import socketserver
import threading
import webbrowser
import http.server
import os
import sys
import time

from src.config import load_data
from src.server import RequestHandler

def start_watcher():
    def watch():
        # Get all python and html files and their initial modification times
        watched_files = {}
        def get_files():
            files = []
            current_dir = os.path.dirname(os.path.abspath(__file__))
            for root, _, filenames in os.walk(current_dir):
                if any(ignored in root for ignored in [".git", "venv", ".venv", "__pycache__"]):
                    continue
                for filename in filenames:
                    if filename.endswith('.py') or filename.endswith('.html'):
                        files.append(os.path.join(root, filename))
            return files

        for f in get_files():
            try:
                watched_files[f] = os.path.getmtime(f)
            except OSError:
                pass

        while True:
            time.sleep(1.0)
            current_files = get_files()
            changed = False
            for f in current_files:
                try:
                    mtime = os.path.getmtime(f)
                    if f not in watched_files or watched_files[f] != mtime:
                        changed = True
                        break
                except OSError:
                    pass
            
            if not changed and len(current_files) != len(watched_files):
                changed = True

            if changed:
                print("\n[Watcher] Dosya değişikliği algılandı, sunucu otomatik olarak yeniden başlatılıyor...\n")
                quoted_args = [f'"{arg}"' if ' ' in arg else arg for arg in sys.argv]
                os.execv(sys.executable, [sys.executable] + quoted_args)

    threading.Thread(target=watch, daemon=True).start()

if __name__ == "__main__":
    start_watcher()
    
    # Load settings and companies data
    load_data()
    
    socketserver.TCPServer.allow_reuse_address = True
    
    PORT = 8000
    # Find next available port if 8000 is taken
    while True:
        try:
            handler = RequestHandler
            httpd = socketserver.TCPServer(("", PORT), handler)
            break
        except OSError:
            PORT += 1
            
    url = f"http://localhost:{PORT}"
    print(f"Uygulama sunucusu başlatıldı: {url}")
    webbrowser.open(url)
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("Sunucu kapatılıyor.")
        httpd.server_close()
