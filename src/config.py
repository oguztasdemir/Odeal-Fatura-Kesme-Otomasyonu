import os
import json
import time
import pandas as pd

# Global Application State
STATE = {
    "status": "Giriş Bekleniyor...",
    "status_color": "#ff1744",
    "logs": ["Uygulama başlatıldı. Oturum açın."],
    "companies": [],
    "accounts": [],
    "settings": {"serial": 42, "serial_prefix": "YRN"},
    "excel_data": None,
    "excel_table": [], # list of dicts for frontend display
    "excel_queue": [], # queue of Excel files for batch processing
    "kpis": {"kalem": 0, "miktar": 0, "kdvsiz": 0, "iskonto": 0, "toplam": 0},
    "backups": [], # active backup sessions list
    "selected_company": None,
    "driver": None,
    "stop_flag": False,
    "auth_step": "login", # "login", "code", "confirmed"
    "prep_status": "Başlat",
    "prep_btn_color": "#3d5afe",
    "login_message": "",
    "login_message_color": "",
    "session_invoices_count": 0
}

# Paths point to the project root directory
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXCEL_FOLDER = os.path.join(ROOT_DIR, "excel_belgeleri")
BACKUP_FOLDER = os.path.join(ROOT_DIR, "yedekler")
BACKUP_HIST_FOLDER = os.path.join(BACKUP_FOLDER, "backups")

# Active JSON files are stored directly in yedekler/
COMPANIES_FILE = os.path.join(BACKUP_FOLDER, "firmalar.json")
SETTINGS_FILE = os.path.join(BACKUP_FOLDER, "ayarlar.json")
ACCOUNTS_FILE = os.path.join(BACKUP_FOLDER, "hesaplar.json")
DOWNLOADS_FOLDER = os.path.join(ROOT_DIR, "indirilen_faturalar")
COOKIES_FILE = os.path.join(BACKUP_FOLDER, "cookies.json")
HISTORY_FILE = os.path.join(BACKUP_FOLDER, "fatura_gecmisi.json")
SCREENSHOTS_FOLDER = os.path.join(ROOT_DIR, "hata_ekranlari")
BACKUPS_FILE = os.path.join(BACKUP_FOLDER, "yedek_oturumlari.json")

if not os.path.exists(EXCEL_FOLDER):
    try:
        os.makedirs(EXCEL_FOLDER)
    except Exception as e:
        print(f"Excel klasörü oluşturulamadı: {e}")

if not os.path.exists(DOWNLOADS_FOLDER):
    try:
        os.makedirs(DOWNLOADS_FOLDER)
    except Exception as e:
        print(f"İndirme klasörü oluşturulamadı: {e}")

if not os.path.exists(BACKUP_FOLDER):
    try:
        os.makedirs(BACKUP_FOLDER)
    except Exception as e:
        print(f"Yedek klasörü oluşturulamadı: {e}")

if not os.path.exists(BACKUP_HIST_FOLDER):
    try:
        os.makedirs(BACKUP_HIST_FOLDER)
    except Exception as e:
        print(f"Yedekleme alt klasörü oluşturulamadı: {e}")

if not os.path.exists(SCREENSHOTS_FOLDER):
    try:
        os.makedirs(SCREENSHOTS_FOLDER)
    except Exception as e:
        print(f"Hata ekranları klasörü oluşturulamadı: {e}")

def clean_old_backups(prefix):
    try:
        files = [f for f in os.listdir(BACKUP_HIST_FOLDER) if f.startswith(prefix) and "_" in f and not f.endswith("_yedek.json")]
        files.sort()
        while len(files) > 5:
            to_remove = files.pop(0)
            os.remove(os.path.join(BACKUP_HIST_FOLDER, to_remove))
    except Exception as e:
        print(f"Eski yedek temizleme hatası: {e}")

def load_data():
    global STATE
    if os.path.exists(COMPANIES_FILE):
        try:
            with open(COMPANIES_FILE, "r", encoding="utf-8") as f:
                STATE["companies"] = json.load(f)
        except:
            STATE["companies"] = []
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                STATE["settings"] = json.load(f)
                if "serial_prefix" not in STATE["settings"]:
                    STATE["settings"]["serial_prefix"] = "YRN"
        except:
            STATE["settings"] = {"serial": 42, "serial_prefix": "YRN"}
    if os.path.exists(ACCOUNTS_FILE):
        try:
            with open(ACCOUNTS_FILE, "r", encoding="utf-8") as f:
                STATE["accounts"] = json.load(f)
        except:
            STATE["accounts"] = []
            
    if os.path.exists(BACKUPS_FILE):
        try:
            with open(BACKUPS_FILE, "r", encoding="utf-8") as f:
                STATE["backups"] = json.load(f)
        except:
            STATE["backups"] = []
    else:
        STATE["backups"] = []

def save_data(file, data):
    # Save main file
    with open(file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
        
    # Save backup copies inside backups/ subdirectory
    try:
        base_name = os.path.basename(file)
        name, ext = os.path.splitext(base_name)
        
        # 1. Latest backup
        latest_backup_path = os.path.join(BACKUP_HIST_FOLDER, f"{name}_yedek{ext}")
        with open(latest_backup_path, "w", encoding="utf-8") as bf:
            json.dump(data, bf, ensure_ascii=False, indent=4)
            
        # 2. Timestamped historical backup
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        history_path = os.path.join(BACKUP_HIST_FOLDER, f"{name}_{timestamp}{ext}")
        with open(history_path, "w", encoding="utf-8") as hf:
            json.dump(data, hf, ensure_ascii=False, indent=4)
            
        clean_old_backups(name)
    except Exception as e:
        print(f"Yedek oluşturma hatası: {e}")

def log_message(msg):
    STATE["logs"].append(f"[{time.strftime('%H:%M:%S')}] {msg}")
    print(f"LOG: {msg}")

def load_excel_data(file_path_or_io):
    global STATE
    STATE["excel_data"] = pd.read_excel(file_path_or_io)
    STATE["excel_table"] = []
    for _, r in STATE["excel_data"].iterrows():
        STATE["excel_table"].append({
            "urun": str(r.iloc[0]),
            "miktar": str(r.iloc[1]),
            "birim": str(r.iloc[2]),
            "fiyat": str(r.iloc[3]),
            "kdv": str(r.iloc[4]),
            "iskonto": str(r.iloc[5])
        })
    
    # Calculate KPIs
    df = STATE["excel_data"].copy()
    df.columns = [c.lower() for c in df.columns]
    m = pd.to_numeric(df.iloc[:, 1]).sum()
    f = pd.to_numeric(df.iloc[:, 3])
    k = pd.to_numeric(df.iloc[:, 4])
    i = pd.to_numeric(df.iloc[:, 5]).sum()
    ks = (pd.to_numeric(df.iloc[:, 1]) * f).sum()
    kl = (pd.to_numeric(df.iloc[:, 1]) * f * (1 + k/100)).sum() - i
    
    STATE["kpis"] = {
        "kalem": len(df),
        "miktar": f"{m:.0f}",
        "kdvsiz": f"{ks:.2f}",
        "iskonto": f"{i:.2f}",
        "toplam": f"{kl:.2f}"
    }

def load_mapped_excel_data(df):
    global STATE
    STATE["excel_data"] = df
    STATE["excel_table"] = []
    for _, r in STATE["excel_data"].iterrows():
        STATE["excel_table"].append({
            "urun": str(r.iloc[0]),
            "miktar": str(r.iloc[1]),
            "birim": str(r.iloc[2]),
            "fiyat": str(r.iloc[3]),
            "kdv": str(r.iloc[4]),
            "iskonto": str(r.iloc[5])
        })
    
    # Extract iade original invoice references if present
    STATE["selected_invoice_no"] = str(df.iloc[0, 6]) if len(df.columns) > 6 and pd.notna(df.iloc[0, 6]) else ""
    STATE["selected_invoice_date"] = str(df.iloc[0, 7]) if len(df.columns) > 7 and pd.notna(df.iloc[0, 7]) else ""
    
    m = pd.to_numeric(df.iloc[:, 1], errors='coerce').fillna(0).sum()
    f = pd.to_numeric(df.iloc[:, 3], errors='coerce').fillna(0)
    k = pd.to_numeric(df.iloc[:, 4], errors='coerce').fillna(0)
    i = pd.to_numeric(df.iloc[:, 5], errors='coerce').fillna(0).sum()
    ks = (pd.to_numeric(df.iloc[:, 1], errors='coerce').fillna(0) * f).sum()
    kl = (pd.to_numeric(df.iloc[:, 1], errors='coerce').fillna(0) * f * (1 + k/100)).sum() - i
    
    STATE["kpis"] = {
        "kalem": len(df),
        "miktar": f"{m:.0f}",
        "kdvsiz": f"{ks:.2f}",
        "iskonto": f"{i:.2f}",
        "toplam": f"{kl:.2f}"
    }
