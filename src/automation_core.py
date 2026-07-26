import time
import os
import json
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

from .config import STATE, log_message, save_data, SETTINGS_FILE, DOWNLOADS_FOLDER, COOKIES_FILE, SCREENSHOTS_FOLDER, ROOT_DIR

def kill_zombie_automation_chrome():
    try:
        import subprocess
        # Query wmic for chrome processes with our custom profile path
        cmd = 'wmic process where "name=\'chrome.exe\'" get ProcessID,CommandLine'
        output = subprocess.check_output(cmd, shell=True, text=True, errors='ignore')
        killed_any = False
        for line in output.splitlines():
            if "chrome_profile" in line and "ProcessID" not in line:
                parts = line.strip().split()
                if parts:
                    pid = parts[-1]
                    if pid.isdigit():
                        log_message(f"Arka plandaki zombi tarayıcı süreci temizleniyor: PID {pid}")
                        subprocess.run(f"taskkill /F /PID {pid}", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        killed_any = True
        if killed_any:
            time.sleep(2) # Allow OS time to release file locks
    except Exception as ke:
        print(f"Zombi temizleme hatası: {ke}")

def is_port_open(port):
    import socket
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.2) # 200ms timeout is plenty for localhost
            s.connect(("127.0.0.1", port))
            return True
    except Exception:
        return False

def get_or_create_driver():
    if STATE["driver"]:
        try:
            # Check window handles as a safer liveliness test
            _ = STATE["driver"].window_handles
        except Exception as e:
            msg = str(e).lower()
            if any(k in msg for k in ["invalid session id", "no such session", "chrome not reachable", "disconnected"]):
                log_message("Kapanmış veya yanıt vermeyen tarayıcı tespit edildi. Yeniden bağlanılmaya çalışılıyor...")
                try:
                    STATE["driver"].quit()
                except Exception:
                    pass
                STATE["driver"] = None

    if not STATE["driver"]:
        # 1. Try to attach to an already running Chrome instance debugging on port 9222
        attached = False
        if is_port_open(9222):
            try:
                log_message("Açık olan tarayıcı portu tespit edildi, bağlanılıyor...")
                s = Service(ChromeDriverManager().install())
                o = Options()
                o.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
                driver = webdriver.Chrome(service=s, options=o)
                # Fetch URL to test if the connection actually works
                _ = driver.current_url
                STATE["driver"] = driver
                log_message("Açık olan Chrome tarayıcı oturumuna başarıyla bağlanıldı!")
                attached = True
                
                # Since we connected to a running Chrome, check if it's already logged in
                current_url = driver.current_url
                if "fatura.odeal.com" in current_url and "index.php" not in current_url and "login" not in current_url:
                    STATE["auth_step"] = "confirmed"
                    STATE["status"] = "Giriş Başarılı"
                    STATE["status_color"] = "#00e676"
            except Exception as attach_err:
                log_message(f"Açık olan tarayıcıya bağlanılamadı: {attach_err}")
                
        if not attached:
            # 2. If it fails, launch a new Chrome with remote debugging and custom profile enabled
            log_message("Mevcut Chrome oturumu bulunamadı. Kilitli arka plan süreçleri temizleniyor...")
            kill_zombie_automation_chrome()
            log_message("Yeni tarayıcı başlatılıyor (Hata Ayıklama Modu - Port 9222)...")
            try:
                s = Service(ChromeDriverManager().install())
                o = Options()
                o.add_argument("--remote-debugging-port=9222")
                o.add_argument("--start-maximized")
                
                # Set a dedicated custom profile inside the workspace to persist cookies and logins
                profile_dir = os.path.join(ROOT_DIR, "chrome_profile")
                o.add_argument(f"--user-data-dir={profile_dir}")
                
                prefs = {
                    "download.default_directory": DOWNLOADS_FOLDER,
                    "download.prompt_for_download": False,
                    "download.directory_upgrade": True,
                    "safebrowsing.enabled": True
                }
                o.add_experimental_option("prefs", prefs)
                
                driver = webdriver.Chrome(service=s, options=o)
                STATE["driver"] = driver
                driver.get("https://fatura.odeal.com/index.php")
                log_message("Yeni Chrome tarayıcısı başarıyla başlatıldı ve Ödeal açıldı.")
                
                if os.path.exists(COOKIES_FILE):
                    try:
                        log_message("Kayıtlı oturum çerezleri yükleniyor...")
                        with open(COOKIES_FILE, "r", encoding="utf-8") as f:
                            cookies = json.load(f)
                        for cookie in cookies:
                            try:
                                driver.add_cookie(cookie)
                            except Exception:
                                pass
                        
                        driver.get("https://fatura.odeal.com/index.php")
                        time.sleep(3)
                        
                        current_url = driver.current_url
                        if "fatura.odeal.com" in current_url and "index.php" not in current_url and "login" not in current_url:
                            log_message("Önceki oturum başarıyla geri yüklendi! Otomatik giriş yapıldı.")
                            STATE["auth_step"] = "confirmed"
                            STATE["status"] = "Giriş Başarılı"
                            STATE["status_color"] = "#00e676"
                        else:
                            log_message("Kayıtlı oturum süresi dolmuş veya geçersiz. Lütfen tekrar giriş yapın.")
                    except Exception as ce:
                        log_message(f"Çerez yükleme hatası: {ce}")
            except Exception as e:
                log_message(f"Tarayıcı başlatma hatası: {str(e)}")
                raise e
    return STATE["driver"]

def find_element_safe(driver, absolute_xpath, fallback_selectors=None, wait_time=10):
    if fallback_selectors is None:
        fallback_selectors = []
    try:
        element = WebDriverWait(driver, 3).until(EC.presence_of_element_located((By.XPATH, absolute_xpath)))
        return element
    except:
        pass
        
    for selector in fallback_selectors:
        try:
            element = WebDriverWait(driver, 2).until(EC.presence_of_element_located((By.XPATH, selector)))
            return element
        except:
            pass
            
    return WebDriverWait(driver, wait_time).until(EC.presence_of_element_located((By.XPATH, absolute_xpath)))

def init_chrome_driver():
    try:
        get_or_create_driver()
    except Exception:
        pass

def wait_for_download_complete(directory, timeout=120):
    start_wait_time = time.time()
    start_time = time.time()
    # Wait up to 10 seconds for the download to start and show a .crdownload or .tmp file
    # or for a new zip/xml file to appear directly
    while time.time() - start_time < timeout:
        crdownload_files = [f for f in os.listdir(directory) if f.endswith('.crdownload') or f.endswith('.tmp')]
        
        new_files = []
        for f in os.listdir(directory):
            if f.endswith('.zip') or f.endswith('.xml') or f.endswith('.pdf'):
                f_path = os.path.join(directory, f)
                try:
                    if os.path.getmtime(f_path) >= start_wait_time - 3:
                        new_files.append(f_path)
                except:
                    pass
        
        # If there are active downloads in progress, keep waiting
        if crdownload_files:
            time.sleep(2)
            continue
            
        # If a new completed file is found and no active downloads are in progress, return it
        if new_files:
            latest_file = max(new_files, key=os.path.getmtime)
            # Small extra sleep to ensure OS filesystem handles the file release
            time.sleep(2)
            return latest_file
            
        time.sleep(2)
    return None

def handle_error(e):
    import traceback
    tb = traceback.format_exc()
    print(f"--- PYTHON TRACEBACK ---\n{tb}------------------------")
    log_message(f"Hata Oluştu: {str(e)}")
    STATE["status"] = "Hata Oluştu!"
    STATE["status_color"] = "#ff1744"
    
    screenshot_name = f"error_{int(time.time())}.png"
    screenshot_path = os.path.join(SCREENSHOTS_FOLDER, screenshot_name)
    try:
        responsive = False
        if STATE["driver"]:
            try:
                _ = STATE["driver"].window_handles
                responsive = True
            except Exception:
                pass
                
        if responsive and STATE["driver"]:
            STATE["driver"].save_screenshot(screenshot_path)
            log_message(f"Hata ekran görüntüsü kaydedildi: {screenshot_name}")
        else:
            log_message("Tarayıcı bağlantısı kapalı veya yanıt vermiyor. Ekran görüntüsü alınamadı.")
            screenshot_name = None
    except Exception as s_err:
        log_message(f"Ekran görüntüsü kaydedilemedi: {s_err}")
        screenshot_name = None
        
    for item in STATE["excel_queue"]:
        if item["status"] in ["Bekliyor", "İşleniyor"]:
            item["status"] = f"Hata: {str(e)[:50]}"
            if screenshot_name:
                item["error_screenshot"] = screenshot_name
            break
