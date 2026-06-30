import http.server
import socketserver
import urllib.parse
import json
import os
import io
import threading
import pandas as pd

from .config import STATE, COMPANIES_FILE, ACCOUNTS_FILE, EXCEL_FOLDER, load_excel_data, save_data, log_message
from .automation import login_process_thread, submit_code_thread, prepare_process_thread, process_products_thread
from .html_template import HTML_TEMPLATE

class RequestHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Override to suppress standard HTTP logging outputs in console
        pass

    def do_GET(self):
        global STATE
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
            self.send_header('Pragma', 'no-cache')
            self.send_header('Expires', '0')
            self.end_headers()
            self.wfile.write(HTML_TEMPLATE.encode('utf-8'))
            
        elif self.path == '/api/status':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({
                "status": STATE["status"],
                "status_color": STATE["status_color"],
                "logs": STATE["logs"],
                "auth_step": STATE["auth_step"],
                "prep_status": STATE["prep_status"],
                "prep_btn_color": STATE["prep_btn_color"],
                "selected_company": STATE["selected_company"],
                "excel_table": STATE["excel_table"],
                "kpis": STATE["kpis"],
                "login_message": STATE.get("login_message", ""),
                "login_message_color": STATE.get("login_message_color", "")
            }).encode('utf-8'))
            
        elif self.path == '/api/companies':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(STATE["companies"]).encode('utf-8'))
            
        elif self.path == '/api/download_template':
            # Create a simple Excel template
            df = pd.DataFrame(columns=["Ürün Adı", "Miktar", "Birim", "Birim Fiyat", "KDV Oranı", "İskonto Tutarı"])
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False)
            excel_data = output.getvalue()
            
            self.send_response(200)
            self.send_header('Content-type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            self.send_header('Content-Disposition', 'attachment; filename=sablon.xlsx')
            self.end_headers()
            self.wfile.write(excel_data)
            
        elif self.path == '/api/excel_files':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            files = []
            if os.path.exists(EXCEL_FOLDER):
                files = [f for f in os.listdir(EXCEL_FOLDER) if f.endswith('.xlsx')]
            self.wfile.write(json.dumps(files).encode('utf-8'))
            
        elif self.path == '/api/accounts':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(STATE["accounts"]).encode('utf-8'))
            
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        global STATE
        content_length = int(self.headers.get('Content-Length', 0))
        
        if self.path == '/api/login':
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            email = data.get('email')
            password = data.get('password')
            
            threading.Thread(target=login_process_thread, args=(email, password), daemon=True).start()
            self.send_response(200)
            self.end_headers()
            
        elif self.path == '/api/confirm_code':
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            code = data.get('code')
            
            threading.Thread(target=submit_code_thread, args=(code,), daemon=True).start()
            self.send_response(200)
            self.end_headers()
            
        elif self.path == '/api/select_company':
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            title = data.get('title')
            
            STATE["selected_company"] = next((c for c in STATE["companies"] if c["title"] == title), None)
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"company": STATE["selected_company"]}).encode('utf-8'))
            
        elif self.path == '/api/company':
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            new_comp = {
                "title": data.get('title'),
                "tax_no": data.get('tax_no'),
                "city": data.get('city'),
                "district": data.get('district'),
                "tax_office": data.get('tax_office'),
                "full_name": ""
            }
            STATE["companies"].append(new_comp)
            save_data(COMPANIES_FILE, STATE["companies"])
            log_message(f"Yeni firma kaydedildi: {new_comp['title']}")
            self.send_response(200)
            self.end_headers()
            
        elif self.path == '/api/prepare':
            threading.Thread(target=prepare_process_thread, daemon=True).start()
            self.send_response(200)
            self.end_headers()
            
        elif self.path == '/api/process':
            threading.Thread(target=process_products_thread, daemon=True).start()
            self.send_response(200)
            self.end_headers()
            
        elif self.path == '/api/stop':
            STATE["stop_flag"] = True
            STATE["prep_status"] = "Durduruldu"
            STATE["prep_btn_color"] = "#ff1744"
            STATE["status"] = "İşlem Durduruldu"
            STATE["status_color"] = "#ff1744"
            log_message("İşlemler durduruldu.")
            self.send_response(200)
            self.end_headers()
            
        elif self.path == '/api/upload_excel':
            boundary = self.headers.get_boundary().encode()
            remainbytes = content_length
            line = self.rfile.readline()
            remainbytes -= len(line)
            if not boundary in line:
                self.send_response(400)
                self.end_headers()
                return
            
            line = self.rfile.readline()
            remainbytes -= len(line)
            while True:
                line = self.rfile.readline()
                remainbytes -= len(line)
                if not line.strip():
                    break
            
            file_data = io.BytesIO()
            preline = self.rfile.readline()
            remainbytes -= len(preline)
            while remainbytes > 0:
                line = self.rfile.readline()
                remainbytes -= len(line)
                if boundary in line:
                    preline = preline[0:-1]
                    if preline.endswith(b'\r'):
                        preline = preline[0:-1]
                    file_data.write(preline)
                    break
                else:
                    file_data.write(preline)
                    preline = line
                    
            file_data.seek(0)
            try:
                load_excel_data(file_data)
                log_message(f"Excel başarıyla yüklendi: {len(STATE['excel_table'])} kalem ürün okundu.")
            except Exception as e:
                log_message(f"Excel okuma hatası: {str(e)}")
                
            self.send_response(200)
            self.end_headers()
            
        elif self.path == '/api/load_local_excel':
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            filename = data.get('filename')
            
            if filename:
                full_path = os.path.join(EXCEL_FOLDER, filename)
                if os.path.exists(full_path):
                    try:
                        load_excel_data(full_path)
                        log_message(f"Yerel Excel başarıyla yüklendi ({filename}): {len(STATE['excel_table'])} kalem ürün okundu.")
                    except Exception as e:
                        log_message(f"Yerel Excel okuma hatası: {str(e)}")
            self.send_response(200)
            self.end_headers()
            
        elif self.path == '/api/save_account':
            try:
                post_data = self.rfile.read(content_length)
                data = json.loads(post_data.decode('utf-8'))
                email = data.get('email')
                password = data.get('password')
                if email and password:
                    existing = next((acc for acc in STATE["accounts"] if acc["email"] == email), None)
                    if existing:
                        existing["password"] = password
                    else:
                        STATE["accounts"].append({"email": email, "password": password})
                    save_data(ACCOUNTS_FILE, STATE["accounts"])
                    log_message(f"Hesap manuel olarak kaydedildi/güncellendi: {email}")
                self.send_response(200)
                self.end_headers()
            except Exception as e:
                log_message(f"Hesap kaydetme hatası: {str(e)}")
                self.send_response(500)
                self.end_headers()
            
        elif self.path == '/api/delete_account':
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            email = data.get('email')
            if email:
                STATE["accounts"] = [acc for acc in STATE["accounts"] if acc["email"] != email]
                save_data(ACCOUNTS_FILE, STATE["accounts"])
                log_message(f"Hesap silindi: {email}")
            self.send_response(200)
            self.end_headers()
            
        elif self.path == '/api/logout':
            try:
                if STATE["driver"]:
                    try:
                        STATE["driver"].quit()
                    except Exception:
                        pass
                    STATE["driver"] = None
                
                STATE["auth_step"] = "login"
                STATE["status"] = "Sistem Hazır"
                STATE["status_color"] = "#00e676"
                STATE["logged_in_email"] = None
                STATE["logged_in_password"] = None
                STATE["login_message"] = "Oturum sonlandırıldı."
                STATE["login_message_color"] = "#ffea00"
                STATE["prep_status"] = "Başlat"
                STATE["prep_btn_color"] = "#3d5afe"
                STATE["selected_company"] = None
                
                log_message("Kullanıcı çıkış yaptı ve tarayıcı kapatıldı.")
                self.send_response(200)
                self.end_headers()
            except Exception as e:
                log_message(f"Çıkış yapma hatası: {str(e)}")
                self.send_response(500)
                self.end_headers()
                
        elif self.path == '/api/reset_accounts':
            STATE["accounts"] = []
            if os.path.exists(ACCOUNTS_FILE):
                try:
                    os.remove(ACCOUNTS_FILE)
                except:
                    pass
            log_message("Kayıtlı tüm hesap verileri sıfırlandı.")
            self.send_response(200)
            self.end_headers()
            
        else:
            self.send_response(404)
            self.end_headers()
