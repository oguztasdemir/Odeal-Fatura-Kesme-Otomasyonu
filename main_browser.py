import http.server
import socketserver
import json
import os
import threading
import time
import webbrowser
import pandas as pd
import urllib.parse
import io
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# Global Application State
STATE = {
    "status": "Sistem Hazır",
    "status_color": "#00e676", # COLOR_SUCCESS
    "logs": ["Uygulama başlatıldı. Oturum açın."],
    "companies": [],
    "accounts": [],
    "settings": {"serial": 42},
    "excel_data": None,
    "excel_table": [], # list of dicts for frontend display
    "kpis": {"kalem": 0, "miktar": 0, "kdvsiz": 0, "iskonto": 0, "toplam": 0},
    "selected_company": None,
    "driver": None,
    "stop_flag": False,
    "auth_step": "login", # "login", "code", "confirmed"
    "prep_status": "Başlat",
    "prep_btn_color": "#3d5afe",
    "login_message": "",
    "login_message_color": ""
}

COMPANIES_FILE = "firmalar.json"
SETTINGS_FILE = "ayarlar.json"
ACCOUNTS_FILE = "hesaplar.json"
EXCEL_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "excel_belgeleri")

if not os.path.exists(EXCEL_FOLDER):
    try:
        os.makedirs(EXCEL_FOLDER)
    except Exception as e:
        print(f"Klasör oluşturulamadı: {e}")

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
        except:
            STATE["settings"] = {"serial": 42}
    if os.path.exists(ACCOUNTS_FILE):
        try:
            with open(ACCOUNTS_FILE, "r", encoding="utf-8") as f:
                STATE["accounts"] = json.load(f)
        except:
            STATE["accounts"] = []

def save_data(file, data):
    with open(file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

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

# --- AUTOMATION THREADS ---

def init_chrome_driver():
    global STATE
    if not STATE["driver"]:
        try:
            log_message("Chrome tarayıcısı otomatik olarak başlatılıyor...")
            s = Service(ChromeDriverManager().install())
            o = Options()
            o.add_argument("--start-maximized")
            STATE["driver"] = webdriver.Chrome(service=s, options=o)
            STATE["driver"].get("https://fatura.odeal.com/index.php")
            log_message("Chrome tarayıcısı başarıyla başlatıldı ve Ödeal açıldı.")
        except Exception as e:
            log_message(f"Tarayıcı başlatma hatası: {str(e)}")

def login_process_thread(email, password):
    global STATE
    try:
        STATE["stop_flag"] = False
        STATE["status"] = "Oturum Açılıyor..."
        STATE["status_color"] = "#ffea00"
        STATE["logged_in_email"] = email
        STATE["logged_in_password"] = password
        STATE["login_message"] = f"E-posta: {email} - Giriş yapılıyor..."
        STATE["login_message_color"] = "#ffea00"
        
        if not STATE["driver"]:
            log_message("Chrome tarayıcısı başlatılıyor...")
            s = Service(ChromeDriverManager().install())
            o = Options()
            o.add_argument("--start-maximized")
            STATE["driver"] = webdriver.Chrome(service=s, options=o)
            STATE["driver"].get("https://fatura.odeal.com/index.php")
        else:
            log_message("Mevcut Chrome tarayıcısı kullanılıyor...")
            if "fatura.odeal.com" not in STATE["driver"].current_url:
                STATE["driver"].get("https://fatura.odeal.com/index.php")
        
        wait = WebDriverWait(STATE["driver"], 15)
        email_el = wait.until(EC.presence_of_element_located((By.XPATH, "/html/body/div[1]/div/div/form/div[1]/input")))
        email_el.send_keys(email)
        
        if STATE["stop_flag"]:
            log_message("İşlem kullanıcı tarafından durduruldu.")
            return
            
        STATE["driver"].find_element(By.XPATH, "/html/body/div[1]/div/div/form/div[2]/input").send_keys(password)
        STATE["driver"].find_element(By.XPATH, "/html/body/div[1]/div/div/form/div[3]/button").click()
        
        log_message("Giriş bilgileri gönderildi. SMS/Google Doğrulama Kodu bekleniyor...")
        STATE["status"] = "Doğrulama Bekleniyor"
        STATE["status_color"] = "#ffea00"
        STATE["auth_step"] = "code"
    except Exception as e:
        STATE["login_message"] = "Hata Yakalandı"
        STATE["login_message_color"] = "#ff1744"
        handle_error(e)

def submit_code_thread(code):
    global STATE
    try:
        wait = WebDriverWait(STATE["driver"], 15)
        code_input = wait.until(EC.presence_of_element_located((By.XPATH, "/html/body/div[3]/div/input[1]")))
        code_input.clear()
        code_input.send_keys(code)
        STATE["driver"].find_element(By.XPATH, "/html/body/div[3]/div/div[6]/button[1]").click()
        
        time.sleep(3)
        
        # Hatalı kod pop-up uyarısı var mı kontrol et ve kapat
        try:
            error_popup_btn = STATE["driver"].find_element(By.XPATH, "//button[contains(text(), 'Kapat') or contains(text(), 'Tamam')]")
            if error_popup_btn.is_displayed():
                STATE["driver"].execute_script("arguments[0].click();", error_popup_btn)
                log_message("Hatalı kod uyarısı algılandı ve kapatıldı. Lütfen kodu tekrar girin.")
                STATE["login_message"] = "Hatalı Kod! Lütfen tekrar giriniz."
                STATE["login_message_color"] = "#ff1744"
                STATE["auth_step"] = "code"
                return
        except:
            pass

        # Girişin doğrulanması (URL kontrolü veya yönlendirme kontrolü)
        if "fatura.odeal.com" in STATE["driver"].current_url and "index.php" not in STATE["driver"].current_url:
            log_message("Giriş başarılı!")
            STATE["status"] = "Giriş Başarılı"
            STATE["status_color"] = "#00e676"
            STATE["auth_step"] = "confirmed"
            
            email = STATE.get("logged_in_email", "")
            password = STATE.get("logged_in_password", "")
            if email and password:
                # E-posta daha önce eklenmiş mi kontrol et
                existing = next((acc for acc in STATE["accounts"] if acc["email"] == email), None)
                if existing:
                    existing["password"] = password
                else:
                    STATE["accounts"].append({"email": email, "password": password})
                save_data(ACCOUNTS_FILE, STATE["accounts"])
                log_message(f"Hesap sisteme kaydedildi/güncellendi: {email}")
            
            # Bellek temizliği
            STATE["logged_in_password"] = None
            
            STATE["login_message"] = f"E-posta: {email} - Oturum Başarılı!"
            STATE["login_message_color"] = "#00e676"
        else:
            raise Exception("Giriş doğrulanamadı. Kod hatalı veya geçersiz olabilir.")
            
    except Exception as e:
        STATE["login_message"] = "Hata Yakalandı veya Kod Hatalı!"
        STATE["login_message_color"] = "#ff1744"
        STATE["auth_step"] = "code" # Kodu tekrar girmesi için giriş kutularını açık tut
        handle_error(e)

def close_announcement_popup(driver):
    try:
        popup_wait = WebDriverWait(driver, 3)
        btn = popup_wait.until(EC.element_to_be_clickable((By.XPATH, "/html/body/div[6]/div/div[6]/button[1]")))
        btn.click()
        log_message("Duyuru penceresi kapatıldı.")
    except Exception:
        pass

def prepare_process_thread():
    global STATE
    try:
        STATE["stop_flag"] = False
        STATE["prep_status"] = "Hazırlanıyor..."
        STATE["prep_btn_color"] = "#455a64"
        
        wait = WebDriverWait(STATE["driver"], 20)
        log_message("Hızlı Fatura sayfasına yönlendiriliyor...")
        STATE["driver"].get("https://fatura.odeal.com/hizlifatura")
        
        if STATE["stop_flag"]: return
        close_announcement_popup(STATE["driver"])
        
        log_message("Hızlı sorgulama deneniyor...")
        if try_quick_search(wait):
            return
            
        if STATE["stop_flag"]: return
        log_message("Hızlı sorgu sonuç vermedi, sayfa yenilenip tekrar denenecek...")
        STATE["status"] = "Yeniden Deneniyor..."
        STATE["status_color"] = "#ffea00"
        STATE["driver"].refresh()
        time.sleep(2)
        
        close_announcement_popup(STATE["driver"])
        if try_quick_search(wait):
            return
            
        if STATE["stop_flag"]: return
        log_message("Detaylı firma kaydı yapılıyor...")
        long_registration(wait)
        
        if STATE["stop_flag"]: return
        on_prep_finished()
    except Exception as e:
        handle_error(e)

def try_quick_search(wait):
    global STATE
    try:
        search_input = wait.until(EC.presence_of_element_located((By.XPATH, "/html/body/div[1]/div[8]/div[1]/div[3]/div[1]/div[3]/div/div[2]/div/div[1]/div[1]/input")))
        search_input.clear()
        search_input.send_keys(STATE["selected_company"]["tax_no"])
        time.sleep(5)
        if STATE["stop_flag"]: return False
        
        res_xpath = "/html/body/div[1]/div[8]/div[1]/div[3]/div[1]/div[3]/div/div[2]/div/div[1]/div[1]/div/div/a/div/div[1]"
        try:
            result_el = STATE["driver"].find_element(By.XPATH, res_xpath)
            STATE["driver"].execute_script("arguments[0].click();", result_el)
            time.sleep(3)
            if STATE["stop_flag"]: return False
            
            # Scroll down the page so the user can see what happens next
            try:
                STATE["driver"].execute_script("window.scrollBy(0, 500);")
                log_message("Sayfa aşağı kaydırıldı.")
            except Exception as scroll_err:
                log_message(f"Kaydırma hatası: {scroll_err}")
            
            captured_full_name = STATE["selected_company"].get("title", "")
            captured_tax_office = STATE["selected_company"].get("tax_office", "")
            try:
                captured_full_name = STATE["driver"].find_element(By.XPATH, "/html/body/div[1]/div[8]/div[1]/div[3]/div[1]/div[4]/div/div[2]/div[1]/div/div[1]/span[1]").text
                captured_tax_office = STATE["driver"].find_element(By.XPATH, "/html/body/div[1]/div[8]/div[1]/div[3]/div[1]/div[4]/div/div[2]/div[1]/div/div[3]/div/div[2]/span[2]").text
            except Exception as details_err:
                log_message(f"Firma detayları tam okunamadı, devam ediliyor: {details_err}")
            
            # Update company data in memory & save
            for comp in STATE["companies"]:
                if comp["tax_no"] == STATE["selected_company"]["tax_no"]:
                    comp["full_name"] = captured_full_name
                    comp["tax_office"] = captured_tax_office
                    STATE["selected_company"]["full_name"] = captured_full_name
                    STATE["selected_company"]["tax_office"] = captured_tax_office
                    break
            save_data(COMPANIES_FILE, STATE["companies"])
            log_message(f"Firma Seçildi: {captured_full_name}")
            
            invoice_settings(wait)
            on_prep_finished()
            return True
        except Exception as click_err:
            log_message(f"Hızlı aramada firma bulunamadı veya tıklanamadı: {click_err}")
            return False
    except Exception as search_err:
        log_message(f"Hızlı arama kutusu bulunamadı: {search_err}")
        return False

def long_registration(wait):
    global STATE
    STATE["driver"].find_element(By.XPATH, "/html/body/div[1]/div[8]/div[1]/div[3]/div[1]/div[3]/div/div[2]/div/div[2]/a").click()
    time.sleep(2)
    STATE["driver"].find_element(By.XPATH, "/html/body/div[1]/div[10]/div/div/div[2]/div[1]/div[1]/input").send_keys(STATE["selected_company"]["tax_no"])
    time.sleep(1)
    Select(STATE["driver"].find_element(By.XPATH, "/html/body/div[1]/div[10]/div/div/div[2]/div[3]/div[1]/select")).select_by_index(1)
    time.sleep(1)
    Select(STATE["driver"].find_element(By.XPATH, "/html/body/div[1]/div[10]/div/div/div[2]/div[3]/div[2]/select")).select_by_visible_text(STATE["selected_company"]["city"])
    time.sleep(1.5)
    Select(STATE["driver"].find_element(By.XPATH, "/html/body/div[1]/div[10]/div/div/div[2]/div[4]/div[1]/select")).select_by_visible_text(STATE["selected_company"]["district"])
    
    tax_office_input = STATE["driver"].find_element(By.XPATH, "/html/body/div[1]/div[10]/div/div/div[2]/div[7]/div[2]/span/span[1]/span/span[1]")
    tax_office_input.click()
    time.sleep(1.5)
    STATE["driver"].switch_to.active_element.send_keys(STATE["selected_company"]["tax_office"])
    time.sleep(2.5)
    wait.until(EC.element_to_be_clickable((By.XPATH, "/html/body/span/span/span[2]/ul/li"))).click()
    time.sleep(1)
    
    captured_name = STATE["driver"].find_element(By.XPATH, "/html/body/div[1]/div[10]/div/div/div[2]/div[1]/div[2]/input").get_attribute("value")
    if captured_name:
        for comp in STATE["companies"]:
            if comp["tax_no"] == STATE["selected_company"]["tax_no"]:
                comp["full_name"] = captured_name
                STATE["selected_company"]["full_name"] = captured_name
                break
        save_data(COMPANIES_FILE, STATE["companies"])
        log_message(f"Firma Kaydedildi: {captured_name}")
        
    STATE["driver"].find_element(By.XPATH, "/html/body/div[1]/div[10]/div/div/div[3]/button").click()
    time.sleep(3)
    invoice_settings(wait)

def invoice_settings(wait):
    global STATE
    time.sleep(2)
    if STATE["stop_flag"]: return
    
    # 1. Fatura tipi seçimi (Dropdown)
    try:
        select_el = wait.until(EC.presence_of_element_located((By.XPATH, "/html/body/div[1]/div[8]/div[1]/div[3]/div[1]/div[8]/div/div[2]/div[2]/div[1]/div[2]/div/select")))
        STATE["driver"].execute_script("arguments[0].scrollIntoView({block: 'center'});", select_el)
        time.sleep(1)
        try:
            Select(select_el).select_by_index(1)
        except Exception:
            log_message("Fatura tipi normal yolla seçilemedi, yedek yöntem (JS) deneniyor...")
            STATE["driver"].execute_script("arguments[0].selectedIndex = 1; arguments[0].dispatchEvent(new Event('change'));", select_el)
        log_message("Fatura tipi seçildi.")
    except Exception as e:
        log_message(f"Fatura tipi seçilemedi: {e}")
        
    time.sleep(1)
    if STATE["stop_flag"]: return
    
    # 2. Seri numarası girişi (Input)
    try:
        serial_input = STATE["driver"].find_element(By.XPATH, "/html/body/div[1]/div[8]/div[1]/div[3]/div[1]/div[8]/div/div[2]/div[2]/div[6]/div/div/div[1]/div[1]/div/input")
        STATE["driver"].execute_script("arguments[0].scrollIntoView({block: 'center'});", serial_input)
        time.sleep(1)
        serial_val = f"YRN{str(STATE['settings']['serial']).zfill(13)}"
        try:
            serial_input.clear()
            serial_input.send_keys(serial_val)
        except Exception:
            log_message("Seri numarası yazılamadı, yedek yöntem (JS) deneniyor...")
            STATE["driver"].execute_script("arguments[0].value = arguments[1]; arguments[0].dispatchEvent(new Event('input')); arguments[0].dispatchEvent(new Event('change'));", serial_input, serial_val)
        log_message("Fatura seri numarası girildi.")
    except Exception as e:
        log_message(f"Seri numarası girilemedi: {e}")
        
    time.sleep(1)
    if STATE["stop_flag"]: return
    
    # 3. Tarih seçimi (Fatura Tarihi ve İade Fatura Tarihi)
    for attempt in range(3):
        try:
            # 1. Hata uyarısı modalı (/html/body/div[7]/div/div[2]) çıkmışsa kapat
            try:
                error_el = STATE["driver"].find_element(By.XPATH, "/html/body/div[7]/div/div[2]")
                if error_el.is_displayed() and "Lütfen iade fatura tarihi giriniz." in error_el.text:
                    kapat_btn = STATE["driver"].find_element(By.XPATH, "/html/body/div[7]/div/div[6]/button[1]")
                    STATE["driver"].execute_script("arguments[0].click();", kapat_btn)
                    log_message("Hata uyarı penceresi (Tarih Eksik) kapatıldı. Tarih yeniden girilmeye çalışılacak...")
                    time.sleep(1.5)
            except Exception as modal_check_err:
                pass
                
            # Normal fatura tarihi (Düzenleme Tarihi)
            try:
                date_input = STATE["driver"].find_element(By.XPATH, "/html/body/div[1]/div[8]/div[1]/div[3]/div[1]/div[8]/div/div[2]/div[2]/div[6]/div/div/div[1]/div[2]/div/input")
                STATE["driver"].execute_script("arguments[0].scrollIntoView({block: 'center'});", date_input)
                time.sleep(1)
                try:
                    date_input.click()
                except Exception:
                    STATE["driver"].execute_script("arguments[0].click();", date_input)
                time.sleep(1)
                
                today_btn = STATE["driver"].find_element(By.LINK_TEXT, "Bugün")
                STATE["driver"].execute_script("arguments[0].scrollIntoView({block: 'center'});", today_btn)
                time.sleep(1)
                try:
                    today_btn.click()
                except Exception:
                    STATE["driver"].execute_script("arguments[0].click();", today_btn)
                log_message("Normal fatura tarihi 'Bugün' olarak seçildi.")
            except Exception as e:
                log_message(f"Normal tarih seçilemedi: {e}")
                
            # İade Fatura Tarihi (Eğer iade seçildiyse)
            try:
                return_date_inputs = STATE["driver"].find_elements(By.XPATH, "//input[@placeholder='gg.aa.yyyy']")
                if return_date_inputs:
                    for inp in return_date_inputs:
                        if inp.is_displayed():
                            STATE["driver"].execute_script("arguments[0].scrollIntoView({block: 'center'});", inp)
                            time.sleep(1)
                            # Inputu tıklayıp takvim açıyoruz
                            try:
                                inp.click()
                            except Exception:
                                STATE["driver"].execute_script("arguments[0].click();", inp)
                            time.sleep(1.5)
                            
                            # Takvim içerisindeki Bugün butonuna basıyoruz (Sağ alttaki Bugün butonu)
                            clicked_today = False
                            try:
                                # Öncelikle genel bir buton/link olarak 'Bugün' arıyoruz
                                today_btn_calendar = STATE["driver"].find_element(By.XPATH, "//button[contains(text(), 'Bugün')] | //a[contains(text(), 'Bugün')] | //span[contains(text(), 'Bugün')]")
                                if today_btn_calendar.is_displayed():
                                    try:
                                        today_btn_calendar.click()
                                    except Exception:
                                        STATE["driver"].execute_script("arguments[0].click();", today_btn_calendar)
                                    clicked_today = True
                                    log_message("Takvimden 'Bugün' seçildi.")
                            except Exception as calendar_today_err:
                                log_message(f"Takvim Bugün butonu bulunamadı, elle yazma deneniyor: {calendar_today_err}")
                            
                            # Eğer takvimden Bugün'e tıklanamadıysa yedek olarak elle giriyoruz
                            if not clicked_today:
                                today_str = time.strftime("%d/%m/%Y")
                                inp.clear()
                                inp.send_keys(today_str)
                                log_message(f"İade fatura tarihi elle girildi: {today_str}")
                                time.sleep(1)
                            
                            ekle_btn = STATE["driver"].find_element(By.XPATH, "//button[contains(text(), 'Ekle')]")
                            if ekle_btn.is_displayed():
                                STATE["driver"].execute_script("arguments[0].click();", ekle_btn)
                                log_message("İade fatura tarihi 'Ekle' butonuna tıklandı.")
                                time.sleep(1.5)
            except Exception as return_date_err:
                log_message(f"İade fatura tarihi doldurulamadı: {return_date_err}")
                
            break
        except Exception as e:
            log_message(f"Fatura günü girilirken hata oluştu, deneme {attempt+1} başarısız: {e}")
            time.sleep(2)
        
    time.sleep(1)
    if STATE["stop_flag"]: return
    
    # 4. Kaydet butonu
    try:
        save_btn = STATE["driver"].find_element(By.XPATH, "/html/body/div[1]/div[8]/div[1]/div[3]/div[1]/div[8]/div/div[2]/div[2]/div[6]/div/div/div[1]/div[3]")
        STATE["driver"].execute_script("arguments[0].scrollIntoView({block: 'center'});", save_btn)
        time.sleep(1)
        try:
            save_btn.click()
        except Exception:
            log_message("Kaydet butonu normal tıklanamadı, yedek yöntem (JS) deneniyor...")
            STATE["driver"].execute_script("arguments[0].click();", save_btn)
        log_message("Fatura ayarları kaydedildi.")
    except Exception as e:
        log_message(f"Fatura ayarları kaydedilemedi: {e}")

def on_prep_finished():
    global STATE
    STATE["prep_status"] = "Hazır"
    STATE["prep_btn_color"] = "#00e676"
    STATE["status"] = "Firma Hazır"
    STATE["status_color"] = "#00e676"
    log_message("Fatura başlığı ve ayarları başarıyla hazırlandı.")

def process_products_thread():
    global STATE
    try:
        STATE["stop_flag"] = False
        log_message("Ürünler faturaya işleniyor...")
        wait = WebDriverWait(STATE["driver"], 10)
        df = STATE["excel_data"].copy()
        
        for idx, row in df.iterrows():
            if STATE["stop_flag"]: return
            log_message(f"Ürün ekleniyor ({idx+1}/{len(df)}): {row.iloc[0]}")
            wait.until(EC.presence_of_element_located((By.XPATH, "/html/body/div[1]/div[8]/div[1]/div[3]/div[1]/div[9]/div[1]/div[3]/div/div/div[1]/input[1]"))).send_keys(str(row.iloc[0]))
            STATE["driver"].find_element(By.XPATH, "/html/body/div[1]/div[8]/div[1]/div[3]/div[1]/div[9]/div[1]/div[3]/div/div/div[2]/input").send_keys(str(row.iloc[1]))
            Select(STATE["driver"].find_element(By.XPATH, "/html/body/div[1]/div[8]/div[1]/div[3]/div[1]/div[9]/div[1]/div[3]/div/div/div[3]/select")).select_by_visible_text(str(row.iloc[2]))
            STATE["driver"].find_element(By.XPATH, "/html/body/div[1]/div[8]/div[1]/div[3]/div[1]/div[9]/div[1]/div[3]/div/div/div[4]/div/input").send_keys(str(row.iloc[3]))
            mapping = {"0": 1, "1": 2, "10": 3, "20": 4}
            Select(STATE["driver"].find_element(By.XPATH, "/html/body/div[1]/div[8]/div[1]/div[3]/div[1]/div[9]/div[1]/div[3]/div/div/div[6]/select")).select_by_index(mapping.get(str(row.iloc[4]), 4))
            STATE["driver"].find_element(By.XPATH, "/html/body/div[1]/div[8]/div[1]/div[3]/div[1]/div[9]/div[1]/div[3]/div/div/div[8]/button").click()
            time.sleep(2)
            
        # Iskonto Tutarları
        for idx, row in df.iterrows():
            if STATE["stop_flag"]: return
            isk = row.iloc[5]
            if pd.notna(isk) and float(isk) > 0:
                log_message(f"İskonto uygulanıyor: {row.iloc[0]} -> {isk}")
                found = -1
                for n in range(1, len(df) + 2):
                    try:
                        if str(row.iloc[0]) in STATE["driver"].find_element(By.XPATH, f"/html/body/div[1]/div[8]/div[1]/div[3]/div[1]/div[9]/div[1]/div[4]/div/table/tbody/tr[{n}]/td[1]").text:
                            found = n
                            break
                    except:
                        break
                if found != -1:
                    STATE["driver"].find_element(By.XPATH, f"/html/body/div[1]/div[8]/div[1]/div[3]/div[1]/div[9]/div[1]/div[4]/div/table/tbody/tr[{found}]/td[8]/button[1]").click()
                    time.sleep(2)
                    STATE["driver"].find_element(By.XPATH, "/html/body/div[1]/div[8]/div[1]/div[3]/div[1]/div[1]/div/div/div[2]/div[1]/div[2]/div/div[4]/div[3]/div[2]/input").send_keys(str(isk).replace("%",""))
                    STATE["driver"].find_element(By.XPATH, "/html/body/div[1]/div[8]/div[1]/div[3]/div[1]/div[1]/div/div/div[2]/div[1]/div[2]/div/div[4]/div[5]/button").click()
                    time.sleep(1)
                    STATE["driver"].find_element(By.XPATH, "/html/body/div[1]/div[8]/div[1]/div[3]/div[1]/div[1]/div/div/div[3]/button[1]").click()
                    time.sleep(1)
                    STATE["driver"].find_element(By.XPATH, "/html/body/div[7]/div/div[6]/button[1]").click()
                    time.sleep(2)
                    
        STATE["settings"]["serial"] += 1
        save_data(SETTINGS_FILE, STATE["settings"])
        log_message("Tüm işlemler başarıyla tamamlandı!")
        STATE["status"] = "Tamamlandı!"
        STATE["status_color"] = "#00e676"
    except Exception as e:
        handle_error(e)

def handle_error(e):
    global STATE
    log_message(f"Hata Oluştu: {str(e)}")
    STATE["status"] = "Hata Oluştu!"
    STATE["status_color"] = "#ff1744"

# --- WEB FRONTEND CONTENT ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <title>Ödeal | Akıllı Fatura Paneli (Web)</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-color: #0f111a;
            --sidebar-color: #1a1d2b;
            --card-color: #1e2235;
            --accent-color: #3d5afe;
            --text-color: #e1e1e1;
            --success-color: #00e676;
            --warning-color: #ffea00;
            --danger-color: #ff1744;
            --border-color: #2e344e;
        }
        body.light-theme {
            --bg-color: #f4f6f9;
            --sidebar-color: #ffffff;
            --card-color: #ffffff;
            --text-color: #2c3e50;
            --border-color: #d1d8e0;
            --accent-color: #3d5afe;
        }
        body.light-theme input, body.light-theme select {
            background-color: #f1f2f6;
            color: #2c3e50;
            border-color: #ced6e0;
        }
        body.light-theme .log-card {
            background-color: #f1f2f6;
            color: #1b1b1b;
            border-color: #ced6e0;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Inter', sans-serif; }
        body { background-color: var(--bg-color); color: var(--text-color); display: flex; height: 100vh; overflow: hidden; transition: background-color 0.3s, color 0.3s; }
        
        /* Sidebar */
        .sidebar { width: 250px; background-color: var(--sidebar-color); padding: 30px 20px; display: flex; flex-direction: column; border-right: 1px solid var(--border-color); }
        .logo { font-size: 28px; font-weight: 700; color: var(--accent-color); margin-bottom: 30px; text-align: center; }
        .status-badge { padding: 15px; border-radius: 8px; background: rgba(255,255,255,0.05); border-left: 4px solid var(--success-color); font-weight: bold; margin-bottom: 20px; transition: all 0.3s; }
        
        /* Main Panel */
        .main-panel { flex: 1; padding: 30px; overflow-y: auto; height: 100%; }
        
        /* Cards */
        .card { background-color: var(--card-color); border: 1px solid var(--border-color); border-radius: 12px; padding: 25px; margin-bottom: 25px; box-shadow: 0 4px 20px rgba(0,0,0,0.2); }
        .card-header { font-size: 18px; font-weight: 600; color: var(--accent-color); margin-bottom: 20px; display: flex; align-items: center; gap: 10px; }
        
        /* Controls & Form inputs */
        .input-group { display: flex; gap: 10px; margin-bottom: 15px; flex-wrap: wrap; }
        input, select { background-color: #121420; border: 1px solid var(--border-color); color: white; padding: 10px 15px; border-radius: 6px; font-size: 14px; outline: none; }
        input:focus, select:focus { border-color: var(--accent-color); }
        button { cursor: pointer; border: none; padding: 10px 20px; border-radius: 6px; font-weight: 600; font-size: 14px; transition: background-color 0.2s, transform 0.1s; }
        button:active { transform: scale(0.98); }
        
        /* Button colors */
        .btn-primary { background-color: var(--accent-color); color: white; }
        .btn-success { background-color: var(--success-color); color: black; }
        .btn-danger { background-color: var(--danger-color); color: white; }
        .btn-secondary { background-color: #455a64; color: white; }
        button:disabled { background-color: #2b3044 !important; color: #6b7280 !important; cursor: not-allowed; }
        
        /* Company Details Grid */
        .details-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 15px; background-color: rgba(0,0,0,0.2); padding: 15px; border-radius: 8px; margin-top: 15px; }
        .detail-item { display: flex; flex-direction: column; }
        .detail-label { font-size: 11px; color: gray; margin-bottom: 3px; }
        .detail-val { font-size: 14px; font-weight: 600; }
        .fullname-lbl { grid-column: span 2; color: var(--success-color); margin-top: 5px; }
        
        /* Table styles */
        .table-container { margin-top: 15px; background: rgba(0,0,0,0.2); border-radius: 8px; overflow: hidden; }
        table { width: 100%; border-collapse: collapse; text-align: left; font-size: 13px; }
        th { background-color: var(--border-color); color: #9aa0a6; padding: 12px; font-weight: 600; }
        td { padding: 12px; border-bottom: 1px solid rgba(255,255,255,0.05); }
        tr:hover { background-color: rgba(255,255,255,0.02); }
        
        /* KPIs */
        .kpi-container { display: flex; gap: 10px; margin-top: 15px; flex-wrap: wrap; }
        .kpi-card { flex: 1; min-width: 120px; background-color: #151926; padding: 10px; border-radius: 8px; text-align: center; border: 1px solid rgba(255,255,255,0.05); }
        .kpi-title { font-size: 11px; color: gray; margin-bottom: 5px; }
        .kpi-value { font-size: 16px; font-weight: 700; }

        /* Console Logs */
        .log-card { background-color: #05070f; border: 1px solid var(--border-color); border-radius: 8px; padding: 15px; font-family: monospace; font-size: 12px; height: 180px; overflow-y: auto; color: #00ff66; margin-top: 20px; }
        .log-line { margin-bottom: 5px; }

        /* Sidebar Navigation */
        .nav-btn {
            background: transparent;
            color: #9aa0a6;
            text-align: left;
            padding: 12px 15px;
            width: 100%;
            border-radius: 8px;
            margin-bottom: 8px;
            display: flex;
            align-items: center;
            gap: 10px;
            font-weight: 600;
            border: none;
            cursor: pointer;
            transition: all 0.2s;
        }
        .nav-btn:hover { background: rgba(255, 255, 255, 0.05); color: white; }
        .nav-btn.active { background: var(--accent-color) !important; color: white !important; }
    </style>
</head>
<body>
    <div class="sidebar">
        <div class="logo">ÖDEAL</div>
        <div class="status-badge" id="system-status">● Sistem Hazır</div>
        
        <button class="nav-btn active" id="nav-panel" onclick="switchSection('panel')">💻 Fatura Paneli</button>
        <button class="nav-btn" id="nav-accounts" onclick="switchSection('accounts')">🔑 Hesap Yönetimi</button>
        <button class="nav-btn" id="nav-settings" onclick="switchSection('settings')">⚙️ Ayarlar</button>
        
        <button class="btn-secondary" style="width: 100%; margin-top: 15px;" onclick="openHelpModal()">❓ Yardım & Hakkında</button>
        <button class="btn-danger" style="width: 100%; margin-top: auto;" onclick="stopProcess()">🛑 TÜMÜNÜ DURDUR</button>
    </div>
    
    <div class="main-panel">
        <div id="section-panel">
            <!-- 1. Oturum Yönetimi -->
            <div class="card">
                <div class="card-header">🔒 1. Oturum Yönetimi</div>
                <div class="input-group" id="login-fields">
                    <select id="saved-accounts-select" onchange="autoFillAccount(this.value)" style="width: 250px; margin-right: 10px;">
                        <option value="">Kayıtlı Hesap Seç...</option>
                    </select>
                    <input type="text" id="email" placeholder="E-mail" style="width: 250px;" onkeydown="if(event.key === 'Enter') startLogin()">
                    <input type="password" id="password" placeholder="Şifre" style="width: 200px;" onkeydown="if(event.key === 'Enter') startLogin()">
                    <button class="btn-primary" onclick="startLogin()" id="login-btn">Sistemi Başlat</button>
                </div>
                <div class="input-group" id="code-fields" style="display: none;">
                    <input type="text" id="auth-code" placeholder="6 Haneli Doğrulama Kodu" style="width: 250px;" onkeydown="if(event.key === 'Enter') confirmCode()">
                    <button class="btn-success" onclick="confirmCode()" id="confirm-code-btn">Kodu Onayla</button>
                </div>
                <div id="login-status-message" style="margin-top: 10px; font-weight: 600; font-size: 14px; display: none;"></div>
            </div>

        <!-- 2. Firma Seçimi -->
        <div class="card">
            <div class="card-header">🏢 2. Firma Seçimi</div>
            <div class="input-group">
                <select id="company-select" style="width: 300px;" onchange="selectCompany(this.value)">
                    <option value="">Firma seçin...</option>
                </select>
                <button class="btn-success" onclick="openNewCompanyModal()">+ Yeni</button>
                <button class="btn-primary" id="prep-btn" onclick="startPrepare()" disabled>Başlat</button>
            </div>
            
            <div class="details-grid">
                <div class="detail-item">
                    <span class="detail-label">Vergi No</span>
                    <span class="detail-val" id="lbl-tax-no">-</span>
                </div>
                <div class="detail-item">
                    <span class="detail-label">Şehir</span>
                    <span class="detail-val" id="lbl-city">-</span>
                </div>
                <div class="detail-item">
                    <span class="detail-label">İlçe</span>
                    <span class="detail-val" id="lbl-district">-</span>
                </div>
                <div class="detail-item">
                    <span class="detail-label">Vergi Dairesi</span>
                    <span class="detail-val" id="lbl-tax-office">-</span>
                </div>
                <span class="detail-val fullname-lbl" id="lbl-fullname">-</span>
            </div>
        </div>

        <!-- 3. Veri ve Hesaplama -->
        <div class="card">
            <div class="card-header">📊 3. Veri ve Hesaplama</div>
            <div class="input-group">
                <button class="btn-secondary" onclick="downloadTemplate()">📥 Şablon</button>
                <input type="file" id="excel-file" style="display: none;" onchange="uploadExcel()" accept=".xlsx">
                <button class="btn-primary" onclick="document.getElementById('excel-file').click()">📤 Excel Yükle</button>
                <select id="local-excel-select" style="width: 220px;" onchange="selectLocalExcel(this.value)">
                    <option value="">Hızlı Excel Getir...</option>
                </select>
                <button class="btn-secondary" onclick="loadLocalExcelFiles()" title="Klasörü Yenile">🔄</button>
                <button class="btn-success" id="process-btn" onclick="startProcessing()" disabled>🚀 Faturaları İşle</button>
            </div>

            <div class="table-container">
                <table>
                    <thead>
                        <tr>
                            <th>Ürün Adı</th>
                            <th>Miktar</th>
                            <th>Birim</th>
                            <th>Fiyat</th>
                            <th>KDV %</th>
                            <th>İskonto</th>
                        </tr>
                    </thead>
                    <tbody id="excel-tbody">
                        <tr><td colspan="6" style="text-align: center; color: gray;">Henüz veri yüklenmedi</td></tr>
                    </tbody>
                </table>
            </div>

            <div class="kpi-container">
                <div class="kpi-card">
                    <div class="kpi-title">📦 Kalem</div>
                    <div class="kpi-value" id="kpi-kalem">0</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-title">🔢 Miktar</div>
                    <div class="kpi-value" id="kpi-miktar">0</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-title">💰 KDV'siz</div>
                    <div class="kpi-value" id="kpi-kdvsiz">0</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-title">🏷️ İskonto</div>
                    <div class="kpi-value" id="kpi-iskonto">0</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-title">✅ Toplam</div>
                    <div class="kpi-value" id="kpi-toplam">0</div>
                </div>
            </div>
        </div>

        <!-- Canlı Loglar -->
        <div class="log-card" id="logs-container">
            <div class="log-line">Sistem dinleniyor...</div>
        </div>
        </div> <!-- section-panel end -->

        <!-- 4. Hesap Yönetimi Section -->
        <div id="section-accounts" style="display: none;">
            <div class="card">
                <div class="card-header">🔑 Kayıtlı Hesaplar Listesi</div>
                <div style="font-size: 13px; color: #9aa0a6; margin-bottom: 15px;">Aşağıda sistemde kayıtlı olan hesaplarınızı görebilir, şifre değişikliği durumunda güncelleyebilir veya silebilirsiniz.</div>
                <div id="saved-accounts-list" style="display: flex; flex-direction: column; gap: 15px;">
                    <!-- JS accounts load here -->
                </div>
            </div>
            
            <div class="card">
                <div class="card-header">➕ Yeni Hesap Ekle / Güncelle</div>
                <div style="display: flex; flex-direction: column; gap: 15px; max-width: 400px; margin-bottom: 15px;">
                    <input type="text" id="acc-email" placeholder="E-posta Adresi">
                    <input type="password" id="acc-password" placeholder="Şifre">
                </div>
                <button class="btn-success" onclick="saveAccountManually()">Kaydet / Güncelle</button>
            </div>
        </div>

        <!-- 5. Ayarlar Section -->
        <div id="section-settings" style="display: none;">
            <div class="card">
                <div class="card-header">🎨 Arayüz Teması</div>
                <div class="input-group">
                    <button class="btn-primary" onclick="setTheme('dark')">Siyah Tema (Varsayılan)</button>
                    <button class="btn-secondary" style="background-color: #eceff1; color: #37474f;" onclick="setTheme('light')">Beyaz Tema</button>
                </div>
            </div>
            
            <div class="card" style="border: 1px solid var(--danger-color);">
                <div class="card-header" style="color: var(--danger-color);">⚠️ Veri Sıfırlama</div>
                <p style="font-size: 13px; color: #9aa0a6; margin-bottom: 15px;">Bu işlem sadece kayıtlı olan <strong>E-posta ve Şifre (Hesap)</strong> verilerini sıfırlayacaktır. <strong>Müşteri (Firma) verileriniz korunacak ve silinmeyecektir.</strong></p>
                <button class="btn-danger" onclick="resetAccountsData()">KAYITLI HESAPLARI SIFIRLA</button>
            </div>
        </div>
    </div>

    <!-- Yeni Firma Modal -->
    <div id="new-company-modal" style="display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.7); align-items: center; justify-content: center; z-index: 1000;">
        <div class="card" style="width: 400px; background-color: var(--card-color); border: 1px solid var(--border-color);">
            <div class="card-header">🏢 Yeni Firma Ekle</div>
            <div style="display: flex; flex-direction: column; gap: 15px; margin-bottom: 20px;">
                <input type="text" id="new-title" placeholder="Firma Başlığı (Not)">
                <input type="text" id="new-tax" placeholder="Vergi No">
                <input type="text" id="new-city" placeholder="Şehir">
                <input type="text" id="new-district" placeholder="İlçe">
                <input type="text" id="new-office" placeholder="Vergi Dairesi">
            </div>
            <div class="input-group" style="justify-content: flex-end;">
                <button class="btn-secondary" onclick="closeNewCompanyModal()">İptal</button>
                <button class="btn-success" onclick="saveNewCompany()">Kaydet</button>
            </div>
        </div>
    </div>

    <!-- Yardım & Hakkında Modal -->
    <div id="help-modal" style="display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.8); align-items: center; justify-content: center; z-index: 1000; padding: 20px;">
        <div class="card" style="max-width: 550px; width: 100%; background-color: var(--card-color); border: 1px solid var(--border-color); max-height: 90vh; overflow-y: auto;">
            <div class="card-header" style="font-size: 16px; font-weight: bold; color: var(--accent-color);">❓ Ödeal Fatura Otomasyonu - Yardım & Hakkında</div>
            <div style="font-size: 13px; line-height: 1.6; display: flex; flex-direction: column; gap: 12px; margin-bottom: 20px; color: #cfd8dc; text-align: left;">
                <p><strong>Bu Sistem Ne İşe Yarar?</strong><br>
                Bu otomasyon paneli, yerel Excel fatura verilerinizi (`ornek.xlsx` şablonuna göre hazırlanmış) okuyarak Selenium altyapısı ile Ödeal fatura portalına otomatik olarak kaydeder ve işler.</p>
                
                <p><strong>Nasıl Kullanılır? (Adım Adım)</strong></p>
                <ol style="padding-left: 18px; display: flex; flex-direction: column; gap: 6px;">
                    <li><strong>Oturum Açma:</strong> E-posta ve şifrenizi girin. <em>(Giriş kutularındayken Enter'a basabilirsiniz.)</em> SMS onay kodu geldiğinde kodu girip <strong>Kodu Onayla</strong>'ya (veya Enter'a) tıklayın. Oturum başarılı olduğunda mail adresiniz yeşil renkle yazacaktır.</li>
                    <li><strong>Firma Seçimi:</strong> Listeden fatura keseceğiniz müşteriyi seçin. <strong>Başlat</strong> butonuna tıklayın. Sistem sayfayı otomatik olarak aşağı kaydıracaktır.</li>
                    <li><strong>Excel Yükleme:</strong> Fatura kalemlerini barındıran excel dosyanızı <strong>excel_belgeleri</strong> klasörüne atın. Arayüzden bu dosyayı seçip veya yenileyip (🔄) yükleyin. Sistem kalemleri ve toplamları anında hesaplayacaktır.</li>
                    <li><strong>İade Faturaları Uyarısı:</strong> Eğer iade faturası kesiyorsanız ve fatura tarihi girilmemişse, sistem hata uyarısını otomatik kapatarak bugünün tarihini takvimden seçmeyi yeniden deneyecektir.</li>
                    <li><strong>Faturaları İşle:</strong> Her şey hazır olduğunda <strong>Faturaları İşle</strong> butonuna basarak tüm ürün girişlerini ve iskontoları otomatik olarak Ödeal sistemine kaydettirin.</li>
                </ol>
                
                <p style="color: var(--warning-color); font-weight: bold;">⚠️ Güvenlik Uyarısı: Projeyi GitHub'a yüklerken kesinlikle Private (Özel) depo seçin. Müşteri listeniz ve ayarlarınız gizli kalmalıdır.</p>
            </div>
            <div class="input-group" style="justify-content: flex-end;">
                <button class="btn-primary" onclick="closeHelpModal()">Anladım</button>
            </div>
        </div>
    </div>

    <script>
        window.onerror = function(message, source, lineno, colno, error) {
            const errDiv = document.createElement('div');
            errDiv.style.position = 'fixed';
            errDiv.style.bottom = '20px';
            errDiv.style.right = '20px';
            errDiv.style.background = '#ff1744';
            errDiv.style.color = 'white';
            errDiv.style.padding = '15px';
            errDiv.style.borderRadius = '8px';
            errDiv.style.zIndex = '99999';
            errDiv.style.boxShadow = '0 4px 15px rgba(0,0,0,0.5)';
            errDiv.innerText = 'JS Hatası: ' + message + ' (Satır: ' + lineno + ')';
            document.body.appendChild(errDiv);
            return false;
        };

        function updateStatus() {
            fetch('/api/status')
                .then(r => r.json())
                .then(data => {
                    const statusBadge = document.getElementById('system-status');
                    statusBadge.innerText = '● ' + data.status;
                    statusBadge.style.borderLeftColor = data.status_color;

                    // Update login message status
                    const statusMsgDiv = document.getElementById('login-status-message');
                    if (data.login_message) {
                        statusMsgDiv.innerText = data.login_message;
                        statusMsgDiv.style.color = data.login_message_color;
                        statusMsgDiv.style.display = 'block';
                    } else {
                        statusMsgDiv.style.display = 'none';
                    }

                    // Update logs
                    const logsContainer = document.getElementById('logs-container');
                    logsContainer.innerHTML = data.logs.map(log => `<div class="log-line">${log}</div>`).join('');
                    logsContainer.scrollTop = logsContainer.scrollHeight;

                    // Update auth UI steps
                    if (data.auth_step === 'login') {
                        document.getElementById('login-fields').style.display = 'flex';
                        document.getElementById('code-fields').style.display = 'none';
                    } else if (data.auth_step === 'code') {
                        document.getElementById('login-fields').style.display = 'none';
                        document.getElementById('code-fields').style.display = 'flex';
                    } else if (data.auth_step === 'confirmed') {
                        document.getElementById('login-fields').style.display = 'none';
                        document.getElementById('code-fields').style.display = 'none';
                    }

                    // Update prep button state
                    const prepBtn = document.getElementById('prep-btn');
                    prepBtn.innerText = data.prep_status;
                    prepBtn.style.backgroundColor = data.prep_btn_color;
                    
                    if (data.auth_step === 'confirmed' && data.selected_company && data.prep_status !== 'Hazırlanıyor...') {
                        prepBtn.disabled = false;
                    } else {
                        prepBtn.disabled = true;
                    }

                    // Update process button state
                    const processBtn = document.getElementById('process-btn');
                    if (data.prep_status === 'Hazır' && data.excel_table.length > 0) {
                        processBtn.disabled = false;
                    } else {
                        processBtn.disabled = true;
                    }

                    // Update Excel UI Table & KPIs
                    if (data.excel_table.length > 0) {
                        document.getElementById('excel-tbody').innerHTML = data.excel_table.map(row => `
                            <tr>
                                <td>${row['urun']}</td>
                                <td>${row['miktar']}</td>
                                <td>${row['birim']}</td>
                                <td>${row['fiyat']}</td>
                                <td>${row['kdv']}</td>
                                <td>${row['iskonto']}</td>
                            </tr>
                        `).join('');
                    } else {
                        document.getElementById('excel-tbody').innerHTML = `<tr><td colspan="6" style="text-align: center; color: gray;">Henüz veri yüklenmedi</td></tr>`;
                    }

                    document.getElementById('kpi-kalem').innerText = data.kpis.kalem;
                    document.getElementById('kpi-miktar').innerText = data.kpis.miktar;
                    document.getElementById('kpi-kdvsiz').innerText = data.kpis.kdvsiz;
                    document.getElementById('kpi-iskonto').innerText = data.kpis.iskonto;
                    document.getElementById('kpi-toplam').innerText = data.kpis.toplam;
                });
        }

        function startLogin() {
            const email = document.getElementById('email').value;
            const password = document.getElementById('password').value;
            fetch('/api/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email, password })
            });
        }

        // Auto-refresh loops
        setInterval(updateStatus, 1000);
        
        function confirmCode() {
            const code = document.getElementById('auth-code').value;
            fetch('/api/confirm_code', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ code })
            });
        }

        function loadCompanies() {
            fetch('/api/companies')
                .then(r => r.json())
                .then(companies => {
                    const select = document.getElementById('company-select');
                    select.innerHTML = '<option value="">Firma seçin...</option>' + 
                        companies.map(c => `<option value="${c.title}">${c.title}</option>`).join('');
                });
        }

        function selectCompany(title) {
            fetch('/api/select_company', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ title })
            }).then(r => r.json())
              .then(data => {
                  if (data.company) {
                      document.getElementById('lbl-tax-no').innerText = data.company.tax_no || '-';
                      document.getElementById('lbl-city').innerText = data.company.city || '-';
                      document.getElementById('lbl-district').innerText = data.company.district || '-';
                      document.getElementById('lbl-tax-office').innerText = data.company.tax_office || '-';
                      document.getElementById('lbl-fullname').innerText = data.company.full_name || '-';
                  } else {
                      document.getElementById('lbl-tax-no').innerText = '-';
                      document.getElementById('lbl-city').innerText = '-';
                      document.getElementById('lbl-district').innerText = '-';
                      document.getElementById('lbl-tax-office').innerText = '-';
                      document.getElementById('lbl-fullname').innerText = '-';
                  }
              });
        }

        function startPrepare() {
            fetch('/api/prepare', { method: 'POST' });
        }

        function stopProcess() {
            fetch('/api/stop', { method: 'POST' });
        }

        function startProcessing() {
            fetch('/api/process', { method: 'POST' });
        }

        function openNewCompanyModal() {
            document.getElementById('new-company-modal').style.display = 'flex';
        }

        function closeNewCompanyModal() {
            document.getElementById('new-company-modal').style.display = 'none';
        }

        function openHelpModal() {
            document.getElementById('help-modal').style.display = 'flex';
        }

        function closeHelpModal() {
            document.getElementById('help-modal').style.display = 'none';
        }

        function saveNewCompany() {
            const title = document.getElementById('new-title').value;
            const tax_no = document.getElementById('new-tax').value;
            const city = document.getElementById('new-city').value;
            const district = document.getElementById('new-district').value;
            const tax_office = document.getElementById('new-office').value;

            fetch('/api/company', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ title, tax_no, city, district, tax_office })
            }).then(() => {
                closeNewCompanyModal();
                loadCompanies();
            });
        }

        function downloadTemplate() {
            window.location.href = '/api/download_template';
        }

        function uploadExcel() {
            const fileInput = document.getElementById('excel-file');
            if (fileInput.files.length === 0) return;
            
            const formData = new FormData();
            formData.append('file', fileInput.files[0]);

            fetch('/api/upload_excel', {
                method: 'POST',
                body: formData
            }).then(() => {
                updateStatus();
            });
        }

        function loadLocalExcelFiles() {
            fetch('/api/excel_files')
                .then(r => r.json())
                .then(files => {
                    const select = document.getElementById('local-excel-select');
                    select.innerHTML = '<option value="">Hızlı Excel Getir...</option>' + 
                        files.map(f => `<option value="${f}">${f}</option>`).join('');
                });
        }

        function selectLocalExcel(filename) {
            if (!filename) return;
            fetch('/api/load_local_excel', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ filename })
            }).then(() => {
                updateStatus();
            });
        }

        let globalAccounts = [];

        function switchSection(sectionId) {
            // Hide all sections
            document.getElementById('section-panel').style.display = 'none';
            document.getElementById('section-accounts').style.display = 'none';
            document.getElementById('section-settings').style.display = 'none';

            // Show current section
            document.getElementById('section-' + sectionId).style.display = 'block';

            // Update active class on nav buttons
            document.querySelectorAll('.nav-btn').forEach(btn => btn.classList.remove('active'));
            document.getElementById('nav-' + sectionId).classList.add('active');
        }

        function loadAccounts() {
            fetch('/api/accounts')
                .then(r => r.json())
                .then(accounts => {
                    globalAccounts = accounts;
                    
                    // Update login card select
                    const savedSelect = document.getElementById('saved-accounts-select');
                    savedSelect.innerHTML = '<option value="">Kayıtlı Hesap Seç...</option>' + 
                        accounts.map(acc => `<option value="${acc.email}">${acc.email}</option>`).join('');

                    // Update accounts manager list
                    const accountsList = document.getElementById('saved-accounts-list');
                    if (accounts.length === 0) {
                        accountsList.innerHTML = '<div style="color: gray; font-style: italic;">Henüz kayıtlı hesap yok. Başarılı giriş yaptığınızda otomatik olarak kaydedilir.</div>';
                    } else {
                        accountsList.innerHTML = accounts.map(acc => `
                            <div style="background: rgba(255,255,255,0.03); border: 1px solid var(--border-color); padding: 15px; border-radius: 8px; display: flex; align-items: center; justify-content: space-between;">
                                <div style="display: flex; flex-direction: column; gap: 5px;">
                                    <span style="font-weight: 600; font-size: 14px; color: var(--accent-color);">${acc.email}</span>
                                    <span style="font-size: 11px; color: gray;">Şifre: ••••••••</span>
                                </div>
                                <div style="display: flex; gap: 10px;">
                                    <button class="btn-primary" style="padding: 6px 12px; font-size: 12px;" onclick="fillAndGo('${acc.email}')">Doldur</button>
                                    <button class="btn-danger" style="padding: 6px 12px; font-size: 12px;" onclick="deleteAccount('${acc.email}')">Sil</button>
                                </div>
                            </div>
                        `).join('');
                    }
                });
        }

        function autoFillAccount(email) {
            if (!email) {
                document.getElementById('email').value = '';
                document.getElementById('password').value = '';
                return;
            }
            const account = globalAccounts.find(acc => acc.email === email);
            if (account) {
                document.getElementById('email').value = account.email;
                document.getElementById('password').value = account.password;
            }
        }

        function fillAndGo(email) {
            autoFillAccount(email);
            switchSection('panel');
        }

        function saveAccountManually() {
            const email = document.getElementById('acc-email').value;
            const password = document.getElementById('acc-password').value;
            if (!email || !password) {
                alert('Lütfen e-posta ve şifre girin.');
                return;
            }
            fetch('/api/save_account', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email, password })
            }).then(() => {
                document.getElementById('acc-email').value = '';
                document.getElementById('acc-password').value = '';
                loadAccounts();
            });
        }

        function deleteAccount(email) {
            if (!confirm(email + ' hesabını silmek istediğinize emin misiniz?')) return;
            fetch('/api/delete_account', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email })
            }).then(() => {
                loadAccounts();
            });
        }

        function resetAccountsData() {
            if (!confirm('KAYITLI TÜM HESAPLARI SİLMEK istediğinize emin misiniz?\nFirma verileriniz silinmeyecektir.')) return;
            fetch('/api/reset_accounts', { method: 'POST' })
                .then(() => {
                    loadAccounts();
                });
        }

        function setTheme(theme) {
            try {
                if (theme === 'light') {
                    document.body.classList.add('light-theme');
                    localStorage.setItem('theme', 'light');
                } else {
                    document.body.classList.remove('light-theme');
                    localStorage.setItem('theme', 'dark');
                }
            } catch (e) {
                if (theme === 'light') {
                    document.body.classList.add('light-theme');
                } else {
                    document.body.classList.remove('light-theme');
                }
            }
        }

        // Init Theme
        let activeTheme = 'dark';
        try {
            activeTheme = localStorage.getItem('theme') || 'dark';
        } catch (e) {}
        setTheme(activeTheme);

        loadCompanies();
        loadLocalExcelFiles();
        loadAccounts();
    </script>
</body>
</html>
"""

class RequestHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Override to suppress standard HTTP logging outputs in console
        pass

    def do_GET(self):
        global STATE
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
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
                "selected_company": STATE["selected_company"] is not None,
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
            # Find Content-Type if present
            while True:
                line = self.rfile.readline()
                remainbytes -= len(line)
                if not line.strip():
                    break
            
            file_data = io.BytesIO()
            # Read file payload
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

if __name__ == "__main__":
    load_data()
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
