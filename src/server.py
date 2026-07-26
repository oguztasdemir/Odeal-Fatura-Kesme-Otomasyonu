import http.server
import socketserver
import urllib.parse
import json
import os
import io
import threading
import time
import pandas as pd

from selenium.webdriver.common.by import By
from .config import STATE, COMPANIES_FILE, ACCOUNTS_FILE, EXCEL_FOLDER, load_excel_data, load_mapped_excel_data, save_data, log_message, DOWNLOADS_FOLDER, COOKIES_FILE, HISTORY_FILE, SETTINGS_FILE, SCREENSHOTS_FOLDER, ROOT_DIR, BACKUPS_FILE
from .automation import login_process_thread, submit_code_thread, prepare_process_thread, process_products_thread, download_invoices_thread, process_queue_thread, sync_customers_thread
from .automation_core import kill_zombie_automation_chrome
from .html_template import HTML_TEMPLATE

class RequestHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Override to suppress standard HTTP logging outputs in console
        pass

    def do_GET(self):
        global STATE
        if self.path == '/':
            import importlib
            import src.html_template
            importlib.reload(src.html_template)
            dynamic_template = src.html_template.HTML_TEMPLATE
            
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
            self.send_header('Pragma', 'no-cache')
            self.send_header('Expires', '0')
            self.end_headers()
            self.wfile.write(dynamic_template.encode('utf-8'))
            
        elif self.path == '/static/style.css':
            self.send_response(200)
            self.send_header('Content-type', 'text/css; charset=utf-8')
            self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
            self.end_headers()
            css_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates", "style.css")
            with open(css_path, "r", encoding="utf-8") as f:
                self.wfile.write(f.read().encode('utf-8'))
                
        elif self.path == '/static/script.js':
            self.send_response(200)
            self.send_header('Content-type', 'application/javascript; charset=utf-8')
            self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
            self.end_headers()
            js_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates", "script.js")
            with open(js_path, "r", encoding="utf-8") as f:
                self.wfile.write(f.read().encode('utf-8'))
                
        elif self.path == '/api/status':
            # Dynamically check if there is an active logged-in browser session on port 9222
            if STATE["auth_step"] != "confirmed":
                from .automation_core import is_port_open, get_or_create_driver
                if is_port_open(9222):
                    try:
                        # Attempt to attach and detect active login status
                        get_or_create_driver()
                    except:
                        pass

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
                "login_message_color": STATE.get("login_message_color", ""),
                "settings": STATE["settings"],
                "backups": STATE.get("backups", []),
                "companies": STATE["companies"],
                "session_invoices_count": STATE.get("session_invoices_count", 0)
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
            
        elif self.path == '/api/downloads/list':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            files_list = []
            if os.path.exists(DOWNLOADS_FOLDER):
                for f in os.listdir(DOWNLOADS_FOLDER):
                    f_path = os.path.join(DOWNLOADS_FOLDER, f)
                    if os.path.isfile(f_path):
                        mtime = os.path.getmtime(f_path)
                        size = os.path.getsize(f_path)
                        files_list.append({
                            "name": f,
                            "size": f"{size / 1024:.1f} KB" if size < 1024*1024 else f"{size / (1024*1024):.2f} MB",
                            "date": time.strftime('%d/%m/%Y %H:%M:%S', time.localtime(mtime))
                        })
            self.wfile.write(json.dumps(files_list).encode('utf-8'))
            
        elif self.path.startswith('/api/downloads/download'):
            query = urllib.parse.urlparse(self.path).query
            params = urllib.parse.parse_qs(query)
            filename = params.get('file', [None])[0]
            if filename:
                safe_path = os.path.abspath(os.path.join(DOWNLOADS_FOLDER, filename))
                if safe_path.startswith(os.path.abspath(DOWNLOADS_FOLDER)) and os.path.exists(safe_path):
                    self.send_response(200)
                    self.send_header('Content-type', 'application/octet-stream')
                    self.send_header('Content-Disposition', f'attachment; filename="{filename}"')
                    self.end_headers()
                    with open(safe_path, 'rb') as f:
                        self.wfile.write(f.read())
                    return
            self.send_response(404)
            self.end_headers()
            
        elif self.path.startswith('/api/screenshots/view'):
            query = urllib.parse.urlparse(self.path).query
            params = urllib.parse.parse_qs(query)
            filename = params.get('file', [None])[0]
            if filename:
                safe_path = os.path.abspath(os.path.join(SCREENSHOTS_FOLDER, filename))
                if safe_path.startswith(os.path.abspath(SCREENSHOTS_FOLDER)) and os.path.exists(safe_path):
                    self.send_response(200)
                    self.send_header('Content-type', 'image/png')
                    self.end_headers()
                    with open(safe_path, 'rb') as f:
                        self.wfile.write(f.read())
                    return
            self.send_response(404)
            self.end_headers()
            
        elif self.path == '/api/accounts':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(STATE["accounts"]).encode('utf-8'))
            
        elif self.path == '/api/history':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            history_list = []
            if os.path.exists(HISTORY_FILE):
                try:
                    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                        history_list = json.load(f)
                except:
                    pass
            self.wfile.write(json.dumps(history_list).encode('utf-8'))
            
        elif self.path == '/api/inspect_menu':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            menu_items = []
            if STATE["driver"]:
                try:
                    elements = STATE["driver"].find_elements(By.TAG_NAME, "a")
                    for el in elements:
                        try:
                            text = el.text.strip()
                            href = el.get_attribute("href")
                            if text and href and "odeal.com" in href:
                                menu_items.append({"text": text, "href": href})
                        except:
                            pass
                except Exception as e:
                    menu_items = [{"error": str(e)}]
            self.wfile.write(json.dumps(menu_items).encode('utf-8'))
            
        elif self.path == '/api/history/export':
            history_list = []
            if os.path.exists(HISTORY_FILE):
                try:
                    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                        history_list = json.load(f)
                except:
                    pass
            
            df = pd.DataFrame(history_list)
            if df.empty:
                df = pd.DataFrame(columns=["date", "serial_no", "company_title", "items_count", "total"])
            
            df.columns = ["İşlem Tarihi", "Fatura Seri No", "Firma Ünvanı", "Kalem Sayısı", "Toplam Tutar (TL)"]
            
            output = io.BytesIO()
            df.to_excel(output, index=False)
            xlsx_data = output.getvalue()
            
            self.send_response(200)
            self.send_header('Content-type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            self.send_header('Content-Disposition', 'attachment; filename=fatura_gecmisi.xlsx')
            self.end_headers()
            self.wfile.write(xlsx_data)
            return
        elif self.path == '/api/history/metrics':
            history_list = []
            if os.path.exists(HISTORY_FILE):
                try:
                    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                        history_list = json.load(f)
                except:
                    pass
            
            total_sales = 0.0
            avg_invoice = 0.0
            total_items = 0
            invoice_count = len(history_list)
            
            client_sales = {}
            monthly_sales = {}
            
            for item in history_list:
                try:
                    tot = float(str(item.get("total", 0)).replace(",",""))
                    total_sales += tot
                    total_items += int(item.get("items_count", 0))
                    
                    client = item.get("company_title", "Diğer")
                    client_sales[client] = client_sales.get(client, 0.0) + tot
                    
                    dt_str = item.get("date", "")
                    if "/" in dt_str:
                        parts = dt_str.split("/")
                        if len(parts) >= 3:
                            year_part = parts[2].split(" ")[0]
                            month_part = parts[1]
                            month_key = f"{year_part}-{month_part}"
                            monthly_sales[month_key] = monthly_sales.get(month_key, 0.0) + tot
                except:
                    pass
                    
            if invoice_count > 0:
                avg_invoice = total_sales / invoice_count
                
            sorted_clients = sorted(client_sales.items(), key=lambda x: x[1], reverse=True)[:5]
            top_clients_labels = [c[0] for c in sorted_clients]
            top_clients_data = [round(c[1], 2) for c in sorted_clients]
            
            sorted_months = sorted(monthly_sales.items(), key=lambda x: x[0])
            monthly_labels = [m[0] for m in sorted_months]
            monthly_data = [round(m[1], 2) for m in sorted_months]
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            response = {
                "total_sales": round(total_sales, 2),
                "avg_invoice": round(avg_invoice, 2),
                "total_items": total_items,
                "invoice_count": invoice_count,
                "top_clients_labels": top_clients_labels,
                "top_clients_data": top_clients_data,
                "monthly_labels": monthly_labels,
                "monthly_data": monthly_data
            }
            self.wfile.write(json.dumps(response).encode('utf-8'))
            return
            
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
            
        elif self.path == '/api/company/delete':
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            tax_nos = data.get('tax_nos', [])
            if not isinstance(tax_nos, list):
                tax_nos = [tax_nos]
            
            initial_len = len(STATE["companies"])
            STATE["companies"] = [c for c in STATE["companies"] if c["tax_no"] not in tax_nos]
            if len(STATE["companies"]) < initial_len:
                save_data(COMPANIES_FILE, STATE["companies"])
                log_message(f"{initial_len - len(STATE['companies'])} firma silindi.")
                self.send_response(200)
            else:
                self.send_response(404)
            self.end_headers()
            
        elif self.path == '/api/company/update':
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            old_tax_no = data.get('old_tax_no')
            
            success = False
            for c in STATE["companies"]:
                if c["tax_no"] == old_tax_no:
                    c["title"] = data.get('title')
                    c["tax_no"] = data.get('tax_no')
                    c["city"] = data.get('city')
                    c["district"] = data.get('district')
                    c["tax_office"] = data.get('tax_office')
                    c["full_name"] = data.get('full_name') or data.get('title')
                    success = True
                    break
            if success:
                save_data(COMPANIES_FILE, STATE["companies"])
                log_message(f"Firma güncellendi: {data.get('title')}")
                self.send_response(200)
            else:
                self.send_response(404)
            self.end_headers()
            
        elif self.path == '/api/companies/export':
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            tax_nos = data.get('tax_nos', [])
            
            filtered = [c for c in STATE["companies"] if c["tax_no"] in tax_nos]
            if not filtered:
                filtered = STATE["companies"]
                
            df = pd.DataFrame(filtered)
            if not df.empty:
                df = df[["title", "tax_no", "city", "district", "tax_office", "full_name"]]
                df.columns = ["Firma Başlığı", "Vergi / TCKN No", "Şehir", "İlçe", "Vergi Dairesi", "Tam Ünvan"]
            else:
                df = pd.DataFrame(columns=["Firma Başlığı", "Vergi / TCKN No", "Şehir", "İlçe", "Vergi Dairesi", "Tam Ünvan"])
                
            output = io.BytesIO()
            df.to_excel(output, index=False)
            xlsx_data = output.getvalue()
            
            self.send_response(200)
            self.send_header('Content-type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            self.send_header('Content-Disposition', 'attachment; filename=firmalar.xlsx')
            self.end_headers()
            self.wfile.write(xlsx_data)
            return
            
        elif self.path == '/api/logs/clear':
            STATE["logs"] = ["Loglar temizlendi."]
            self.send_response(200)
            self.end_headers()
            
        elif self.path == '/api/prepare':
            threading.Thread(target=prepare_process_thread, daemon=True).start()
            self.send_response(200)
            self.end_headers()
            
        elif self.path == '/api/process':
            if any(item["status"] == "Bekliyor" for item in STATE["excel_queue"]):
                threading.Thread(target=process_queue_thread, daemon=True).start()
            else:
                threading.Thread(target=process_products_thread, daemon=True).start()
            self.send_response(200)
            self.end_headers()
            
        elif self.path == '/api/download_invoices':
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            start_date = data.get('start_date')
            end_date = data.get('end_date')
            download_type = data.get('download_type')
            filter_query = data.get('filter_query')
            direction = data.get('direction', 'gelen')
            sort_order = data.get('sort_order', 'asc')
            session_id = data.get('session_id')
            
            threading.Thread(target=download_invoices_thread, args=(start_date, end_date, download_type, filter_query, direction, sort_order, session_id), daemon=True).start()
            self.send_response(200)
            self.end_headers()
            
        elif self.path == '/api/sync_customers':
            threading.Thread(target=sync_customers_thread, daemon=True).start()
            self.send_response(200)
            self.end_headers()
            
        elif self.path == '/api/downloads/delete':
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            filename = data.get('file')
            if filename:
                safe_path = os.path.abspath(os.path.join(DOWNLOADS_FOLDER, filename))
                if safe_path.startswith(os.path.abspath(DOWNLOADS_FOLDER)) and os.path.exists(safe_path):
                    try:
                        os.remove(safe_path)
                        log_message(f"Dosya başarıyla silindi: {filename}")
                    except Exception as e:
                        log_message(f"Dosya silme hatası: {e}")
            self.send_response(200)
            self.end_headers()
            
        elif self.path == '/api/backups/rename':
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            session_id = data.get('id')
            new_name = data.get('name')
            
            success = False
            for b in STATE["backups"]:
                if b["id"] == session_id:
                    b["name"] = new_name
                    success = True
                    break
            if success:
                save_data(BACKUPS_FILE, STATE["backups"])
                log_message(f"Yedek oturumu ismi güncellendi: {new_name}")
                self.send_response(200)
            else:
                self.send_response(404)
            self.end_headers()
            
        elif self.path == '/api/backups/delete':
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            session_id = data.get('id')
            
            initial_len = len(STATE["backups"])
            STATE["backups"] = [b for b in STATE["backups"] if b["id"] != session_id]
            if len(STATE["backups"]) < initial_len:
                save_data(BACKUPS_FILE, STATE["backups"])
                log_message("Yedek oturumu silindi.")
                self.send_response(200)
            else:
                self.send_response(404)
            self.end_headers()
            
        elif self.path == '/api/update_excel_cell':
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            row_idx = int(data.get('row'))
            field = data.get('field')
            value = data.get('value')
            
            mapping = {
                "urun": 0,
                "miktar": 1,
                "birim": 2,
                "fiyat": 3,
                "kdv": 4,
                "iskonto": 5
            }
            if field in mapping and 0 <= row_idx < len(STATE["excel_table"]):
                STATE["excel_table"][row_idx][field] = value
                
                # Update underlying dataframe values
                if STATE["excel_data"] is not None:
                    col_idx = mapping[field]
                    STATE["excel_data"].iloc[row_idx, col_idx] = value
                
                # Recalculate KPIs
                try:
                    df = STATE["excel_data"].copy()
                    df.columns = [c.lower() for c in df.columns]
                    m = pd.to_numeric(df.iloc[:, 1], errors='coerce').sum()
                    f = pd.to_numeric(df.iloc[:, 3], errors='coerce')
                    k = pd.to_numeric(df.iloc[:, 4], errors='coerce')
                    i = pd.to_numeric(df.iloc[:, 5], errors='coerce').sum()
                    ks = (pd.to_numeric(df.iloc[:, 1], errors='coerce') * f).sum()
                    kl = (pd.to_numeric(df.iloc[:, 1], errors='coerce') * f * (1 + k/100)).sum() - i
                    
                    STATE["kpis"] = {
                        "kalem": len(df),
                        "miktar": f"{m:.0f}",
                        "kdvsiz": f"{ks:.2f}",
                        "iskonto": f"{i:.2f}",
                        "toplam": f"{kl:.2f}"
                    }
                except Exception as kpi_err:
                    log_message(f"KPI yeniden hesaplanamadı: {kpi_err}")
                    
                log_message(f"Hücre güncellendi: Satır {row_idx+1}, Kolon {field} -> {value}")
            self.send_response(200)
            self.end_headers()
            
        elif self.path == '/api/logout':
            if STATE["driver"]:
                try:
                    STATE["driver"].quit()
                except:
                    pass
                STATE["driver"] = None
            STATE["auth_step"] = "login"
            STATE["status"] = "Giriş Bekleniyor..."
            STATE["status_color"] = "#ff1744"
            STATE["logged_in_email"] = None
            STATE["logged_in_password"] = None
            STATE["login_message"] = "Oturum sonlandırıldı."
            STATE["login_message_color"] = "#ffea00"
            if os.path.exists(COOKIES_FILE):
                try:
                    os.remove(COOKIES_FILE)
                except:
                    pass
            log_message("Çıkış yapıldı ve çerezler temizlendi.")
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
            
        elif self.path == '/api/reload_code':
            try:
                import importlib
                import src.automation_core
                import src.automation_login
                import src.automation_download
                import src.automation_invoice
                import src.automation_sync
                import src.automation_queue
                import src.automation
                
                importlib.reload(src.automation_core)
                importlib.reload(src.automation_login)
                importlib.reload(src.automation_download)
                importlib.reload(src.automation_invoice)
                importlib.reload(src.automation_sync)
                importlib.reload(src.automation_queue)
                importlib.reload(src.automation)
                
                log_message("Sistem kodları canlı olarak güncellendi (Tarayıcı oturumu aktif)!")
                self.send_response(200)
                self.end_headers()
            except Exception as e:
                log_message(f"Kod güncelleme hatası: {str(e)}")
                self.send_response(500)
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
            
            import re
            filename = "uploaded_file.xlsx"
            match = re.search(r'filename="([^"]+)"', line.decode('utf-8', errors='ignore'))
            if match:
                filename = match.group(1)
                
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
            
            file_path = os.path.join(EXCEL_FOLDER, filename)
            try:
                with open(file_path, "wb") as f:
                    f.write(file_data.getvalue())
            except Exception as write_err:
                log_message(f"Excel diske yazılamadı: {write_err}")
                
            try:
                df = pd.read_excel(file_path, nrows=1)
                headers = [str(col) for col in df.columns]
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                response = {
                    "filename": filename,
                    "headers": headers,
                    "default_mapping": STATE.get("last_excel_mapping", {
                        "urun": "", "miktar": "", "birim": "", "fiyat": "", "kdv": "", "iskonto": ""
                    })
                }
                self.wfile.write(json.dumps(response).encode('utf-8'))
            except Exception as e:
                log_message(f"Excel başlık okuma hatası: {str(e)}")
                self.send_response(500)
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))
            
        elif self.path == '/api/load_mapped_excel':
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            filename = data.get('filename')
            mapping = data.get('mapping')
            
            STATE["last_excel_mapping"] = mapping
            
            file_path = os.path.join(EXCEL_FOLDER, filename)
            if os.path.exists(file_path):
                try:
                    df = pd.read_excel(file_path)
                    mapped_df = pd.DataFrame()
                    mapped_df[0] = df[mapping["urun"]] if mapping.get("urun") in df.columns else "Ürün"
                    mapped_df[1] = df[mapping["miktar"]] if mapping.get("miktar") in df.columns else 1
                    mapped_df[2] = df[mapping["birim"]] if mapping.get("birim") in df.columns else "adet"
                    mapped_df[3] = df[mapping["fiyat"]] if mapping.get("fiyat") in df.columns else 0
                    mapped_df[4] = df[mapping["kdv"]] if mapping.get("kdv") in df.columns else "20"
                    mapped_df[5] = df[mapping["iskonto"]] if mapping.get("iskonto") in df.columns else 0
                    mapped_df[6] = df[mapping["iliskili_no"]] if mapping.get("iliskili_no") in df.columns else ""
                    mapped_df[7] = df[mapping["iliskili_tarih"]] if mapping.get("iliskili_tarih") in df.columns else ""
                    
                    mapped_df[0] = mapped_df[0].fillna("Ürün/Hizmet")
                    mapped_df[1] = mapped_df[1].fillna(1)
                    mapped_df[2] = mapped_df[2].fillna("adet")
                    mapped_df[3] = mapped_df[3].fillna(0)
                    mapped_df[4] = mapped_df[4].fillna("20")
                    mapped_df[5] = mapped_df[5].fillna(0)
                    mapped_df[6] = mapped_df[6].fillna("")
                    mapped_df[7] = mapped_df[7].fillna("")
                    
                    load_mapped_excel_data(mapped_df)
                    
                    if not any(item["name"] == filename for item in STATE["excel_queue"]):
                        STATE["excel_queue"].append({"name": filename, "status": "Bekliyor"})
                        
                    log_message(f"Excel sıraya eklendi ({filename}): {len(STATE['excel_table'])} kalem okundu.")
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({"success": True}).encode('utf-8'))
                except Exception as e:
                    log_message(f"Kolon eşleme hatası: {str(e)}")
                    self.send_response(500)
                    self.end_headers()
                    self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))
            else:
                self.send_response(404)
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
                        if not any(item["name"] == filename for item in STATE["excel_queue"]):
                            STATE["excel_queue"].append({"name": filename, "status": "Bekliyor"})
                        log_message(f"Yerel Excel sıraya eklendi ({filename}): {len(STATE['excel_table'])} kalem okundu.")
                    except Exception as e:
                        log_message(f"Yerel Excel okuma hatası: {str(e)}")
            self.send_response(200)
            self.end_headers()
            
        elif self.path == '/api/queue/clear':
            STATE["excel_queue"] = []
            STATE["excel_table"] = []
            STATE["excel_data"] = None
            STATE["kpis"] = {"kalem": 0, "miktar": 0, "kdvsiz": 0, "iskonto": 0, "toplam": 0}
            log_message("Excel sırası temizlendi.")
            self.send_response(200)
            self.end_headers()
            
        elif self.path == '/api/settings/update':
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            serial = int(data.get('serial', 42))
            serial_prefix = data.get('serial_prefix', 'YRN')
            finalization_mode = data.get('finalization_mode', 'manual')
            invoice_scenario = data.get('invoice_scenario', 'TEMEL')
            invoice_type = data.get('invoice_type', 'SATIS')
            
            STATE["settings"]["serial"] = serial
            STATE["settings"]["serial_prefix"] = serial_prefix
            STATE["settings"]["finalization_mode"] = finalization_mode
            STATE["settings"]["invoice_scenario"] = invoice_scenario
            STATE["settings"]["invoice_type"] = invoice_type
            save_data(SETTINGS_FILE, STATE["settings"])
            log_message(f"Ayarlar güncellendi: Ön ek: {serial_prefix}, Sıradaki No: {serial}, Sonlandırma: {finalization_mode}, Senaryo: {invoice_scenario}, Tür: {invoice_type}")
            self.send_response(200)
            self.end_headers()
            
        elif self.path == '/api/settings/clear_download_date':
            STATE["settings"]["last_download_date"] = ""
            save_data(SETTINGS_FILE, STATE["settings"])
            log_message("Son fatura indirme tarihi sıfırlandı.")
            self.send_response(200)
            self.end_headers()
            
        elif self.path == '/api/save_account':
            try:
                post_data = self.rfile.read(content_length)
                data = json.loads(post_data.decode('utf-8'))
                email = data.get('email')
                password = data.get('password')
                two_factor_secret = data.get('two_factor_secret', '')
                if email and password:
                    existing = next((acc for acc in STATE["accounts"] if acc["email"] == email), None)
                    if existing:
                        existing["password"] = password
                        existing["two_factor_secret"] = two_factor_secret
                    else:
                        STATE["accounts"].append({"email": email, "password": password, "two_factor_secret": two_factor_secret})
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
                
                # Delete chrome_profile directory to clear persistent session of the logged out user
                profile_dir = os.path.join(ROOT_DIR, "chrome_profile")
                if os.path.exists(profile_dir):
                    time.sleep(1) # wait briefly for locks to release
                    import shutil
                    try:
                        shutil.rmtree(profile_dir)
                        log_message("Kalıcı oturum profili (chrome_profile) temizlendi.")
                    except Exception:
                        kill_zombie_automation_chrome()
                        try:
                            shutil.rmtree(profile_dir)
                            log_message("Kalıcı oturum profili zombi temizliği sonrası silindi.")
                        except Exception as delete_err:
                            log_message(f"Uyarı: Oturum profili temizlenemedi: {delete_err}")
                
                if os.path.exists(COOKIES_FILE):
                    try:
                        os.remove(COOKIES_FILE)
                    except:
                        pass
                
                STATE["auth_step"] = "login"
                STATE["status"] = "Giriş Bekleniyor..."
                STATE["status_color"] = "#ff1744"
                STATE["logged_in_email"] = None
                STATE["logged_in_password"] = None
                STATE["login_message"] = "Oturum sonlandırıldı ve çerezler temizlendi."
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

# Startup Auto-Login Session Check Thread
def run_startup_login_check():
    time.sleep(3.0)
    while True:
        try:
            from .automation_core import get_or_create_driver, is_port_open
            is_logged_in = False
            
            if is_port_open(9222):
                try:
                    driver = get_or_create_driver()
                    menu_els = driver.find_elements(By.XPATH, "//*[contains(text(), 'ANASAYFA') or contains(text(), 'E-DÖNÜŞÜM')]")
                    logout_els = driver.find_elements(By.XPATH, "//a[contains(@href, 'logout') or contains(@href, 'cikis')]")
                    if menu_els or logout_els:
                        is_logged_in = True
                except:
                    pass
            
            if STATE.get("auth_step") == "confirmed" and not is_logged_in:
                STATE["auth_step"] = "login"
                STATE["status"] = "Oturum sonlandırıldı."
                STATE["status_color"] = "#ff1744"
                STATE["login_message"] = "Oturum sonlandırıldı."
                STATE["login_message_color"] = "#ffea00"
                log_message("UYARI: Arka plandaki e-Fatura oturumu sonlandırıldı veya çıkış yapıldı!")
                
            elif STATE.get("auth_step") != "confirmed" and is_logged_in:
                STATE["auth_step"] = "confirmed"
                if STATE.get("status") in ["Sistem Hazır", "Giriş Bekleniyor...", "Oturum Açılıyor...", "Oturum sonlandırıldı.", "Giriş yapılması bekleniyor...", None]:
                    STATE["status"] = "Sistem Hazır"
                    STATE["status_color"] = "#00e676"
                log_message("Bağlı ve aktif e-Fatura oturumu algılandı, kontrol paneli otomatik açıldı!")
        except Exception as e:
            pass
        time.sleep(10.0)

if not STATE.get("startup_check_launched"):
    STATE["startup_check_launched"] = True
    threading.Thread(target=run_startup_login_check, daemon=True).start()
