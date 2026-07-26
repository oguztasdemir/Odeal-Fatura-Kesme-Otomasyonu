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
                    if (filename.endswith('.py') and "html_template.py" not in filename) or filename.endswith('.html'):
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
                restart_needed = False
                for f in current_files:
                    try:
                        mtime = os.path.getmtime(f)
                        if f not in watched_files or watched_files[f] != mtime:
                            if "config.py" in f or "main_browser.py" in f:
                                restart_needed = True
                                break
                    except:
                        pass
                
                if restart_needed:
                    print("\n[Watcher] Kritik dosya değişikliği algılandı, sunucu yeniden başlatılıyor...\n")
                    args = sys.argv.copy()
                    if "--restarted" not in args:
                        args.append("--restarted")
                    quoted_args = [f'"{arg}"' if ' ' in arg else arg for arg in args]
                    os.execv(sys.executable, [sys.executable] + quoted_args)
                else:
                    print("\n[Hot-Reload] Kod değişikliği algılandı, modüller canlı olarak yenilendi.\n")
                    # Update cache without restart
                    for f in current_files:
                        try:
                            watched_files[f] = os.path.getmtime(f)
                        except:
                            pass

    threading.Thread(target=watch, daemon=True).start()

class DynamicHandler(socketserver.BaseRequestHandler):
    def handle(self):
        import importlib
        import src.config
        import src.automation_core
        import src.automation_login
        import src.automation_download
        import src.automation_invoice
        import src.automation_sync
        import src.automation_queue
        import src.automation
        import src.server
        try:
            importlib.reload(src.automation_core)
            importlib.reload(src.automation_login)
            importlib.reload(src.automation_download)
            importlib.reload(src.automation_invoice)
            importlib.reload(src.automation_sync)
            importlib.reload(src.automation_queue)
            importlib.reload(src.automation)
            importlib.reload(src.server)
        except Exception as e:
            print(f"[Hot-Reload] Yenileme Hatası: {e}")
        
        # Delegate socket connection to the dynamically loaded RequestHandler
        src.server.RequestHandler(self.request, self.client_address, self.server)

if __name__ == "__main__":
    start_watcher()
    
    # Load settings and companies data
    load_data()
    
    socketserver.TCPServer.allow_reuse_address = True
    
    PORT = 8000
    # Find next available port if 8000 is taken
    while True:
        try:
            # Use DynamicHandler as the socket server delegate
            httpd = socketserver.TCPServer(("", PORT), DynamicHandler)
            break
        except OSError:
            PORT += 1
            
    url = f"http://localhost:{PORT}"
    print(f"Uygulama sunucusu başlatıldı: {url}")
    
    if "--restarted" not in sys.argv:
        webbrowser.open(url)
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("Sunucu kapatılıyor.")
        httpd.server_close()
