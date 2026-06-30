import time
import os
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

from .config import STATE, log_message, save_data, SETTINGS_FILE, ACCOUNTS_FILE, COMPANIES_FILE

def get_or_create_driver():
    if STATE["driver"]:
        try:
            # Test if driver is still open and responsive
            _ = STATE["driver"].current_url
        except Exception:
            log_message("Kapanmış veya yanıt vermeyen tarayıcı tespit edildi. Yeniden başlatılıyor...")
            try:
                STATE["driver"].quit()
            except Exception:
                pass
            STATE["driver"] = None

    if not STATE["driver"]:
        log_message("Chrome tarayıcısı başlatılıyor...")
        try:
            s = Service(ChromeDriverManager().install())
            o = Options()
            o.add_argument("--start-maximized")
            STATE["driver"] = webdriver.Chrome(service=s, options=o)
            STATE["driver"].get("https://fatura.odeal.com/index.php")
            log_message("Chrome tarayıcısı başarıyla başlatıldı ve Ödeal açıldı.")
        except Exception as e:
            log_message(f"Tarayıcı başlatma hatası: {str(e)}")
            raise e
    return STATE["driver"]

def init_chrome_driver():
    try:
        get_or_create_driver()
    except Exception:
        pass

def login_process_thread(email, password):
    try:
        STATE["stop_flag"] = False
        STATE["status"] = "Oturum Açılıyor..."
        STATE["status_color"] = "#ffea00"
        STATE["logged_in_email"] = email
        STATE["logged_in_password"] = password
        STATE["login_message"] = f"E-posta: {email} - Giriş yapılıyor..."
        STATE["login_message_color"] = "#ffea00"
        
        driver = get_or_create_driver()
        # Ensure we are on the login page
        if "fatura.odeal.com" not in driver.current_url:
            driver.get("https://fatura.odeal.com/index.php")
        
        wait = WebDriverWait(driver, 15)
        email_el = wait.until(EC.presence_of_element_located((By.XPATH, "/html/body/div[1]/div/div/form/div[1]/input")))
        email_el.clear()
        email_el.send_keys(email)
        
        if STATE["stop_flag"]:
            log_message("İşlem kullanıcı tarafından durduruldu.")
            return
            
        pass_el = driver.find_element(By.XPATH, "/html/body/div[1]/div/div/form/div[2]/input")
        pass_el.clear()
        pass_el.send_keys(password)
        driver.find_element(By.XPATH, "/html/body/div[1]/div/div/form/div[3]/button").click()
        
        log_message("Giriş bilgileri gönderildi. Sayfa yanıtı bekleniyor...")
        
        # Wait up to 10 seconds to see if code input appears or if error popup appears
        login_failed = False
        for _ in range(10):
            if STATE["stop_flag"]:
                log_message("İşlem kullanıcı tarafından durduruldu.")
                return
            
            # Check if error popup is visible
            try:
                error_el = driver.find_element(By.XPATH, "/html/body/div[3]/div/h2")
                if error_el.is_displayed() and "Giriş Başarısız" in error_el.text:
                    login_failed = True
                    break
            except Exception:
                pass
                
            # Check if verification code input is visible
            try:
                code_el = driver.find_element(By.XPATH, "/html/body/div[3]/div/input[1]")
                if code_el.is_displayed():
                    break
            except Exception:
                pass
                
            time.sleep(1)
            
        if login_failed:
            log_message("Hatalı giriş tespiti: Giriş Başarısız uyarısı alındı.")
            try:
                close_btn = driver.find_element(By.XPATH, "/html/body/div[3]/div/div[6]/button[1]")
                if close_btn.is_displayed():
                    close_btn.click()
            except Exception:
                pass
            raise Exception("Giriş Başarısız: E-posta veya şifre hatalı girildi.")

        log_message("Giriş bilgileri onaylandı. SMS/Google Doğrulama Kodu bekleniyor...")
        STATE["status"] = "Doğrulama Bekleniyor"
        STATE["status_color"] = "#ffea00"
        STATE["auth_step"] = "code"
    except Exception as e:
        log_message(f"Giriş hatası: {str(e)}")
        STATE["login_message"] = "Giriş Başarısız! Bilgileri kontrol edip tekrar deneyin."
        STATE["login_message_color"] = "#ff1744"
        STATE["status"] = "Hata Oluştu"
        STATE["status_color"] = "#ff1744"
        STATE["auth_step"] = "login"
        if STATE["driver"]:
            try:
                log_message("Giriş sayfasına geri dönmek için tarayıcı yenileniyor (F5)...")
                STATE["driver"].refresh()
            except Exception:
                pass

def submit_code_thread(code):
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

        # Girişin doğrulanması
        if "fatura.odeal.com" in STATE["driver"].current_url and "index.php" not in STATE["driver"].current_url:
            log_message("Giriş başarılı!")
            STATE["status"] = "Giriş Başarılı"
            STATE["status_color"] = "#00e676"
            STATE["auth_step"] = "confirmed"
            
            email = STATE.get("logged_in_email", "")
            password = STATE.get("logged_in_password", "")
            if email and password:
                existing = next((acc for acc in STATE["accounts"] if acc["email"] == email), None)
                if existing:
                    existing["password"] = password
                else:
                    STATE["accounts"].append({"email": email, "password": password})
                save_data(ACCOUNTS_FILE, STATE["accounts"])
                log_message(f"Hesap sisteme kaydedildi/güncellendi: {email}")
            
            STATE["logged_in_password"] = None
            
            STATE["login_message"] = f"E-posta: {email} - Oturum Başarılı!"
            STATE["login_message_color"] = "#00e676"
        else:
            raise Exception("Giriş doğrulanamadı. Kod hatalı veya geçersiz olabilir.")
            
    except Exception as e:
        STATE["login_message"] = "Hata Yakalandı veya Kod Hatalı!"
        STATE["login_message_color"] = "#ff1744"
        STATE["auth_step"] = "code"
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
        STATE["driver"].refresh()
        time.sleep(2)
        close_announcement_popup(STATE["driver"])
        
        if try_quick_search(wait):
            return
            
        log_message("Hızlı sorgu başarısız, detaylı kayıt modalı deneniyor...")
        long_registration(wait)
        
        if STATE["stop_flag"]: return
        invoice_settings()
        
    except Exception as e:
        handle_error(e)

def try_quick_search(wait):
    try:
        # Arama kutusuna vergi numarası yazma
        search_input = wait.until(EC.presence_of_element_located((By.XPATH, "/html/body/div[1]/div[8]/div[1]/div[3]/div[1]/div[3]/div/div[2]/div/div[1]/div/span/span[1]/span/ul/li/input")))
        search_input.clear()
        search_input.send_keys(STATE["selected_company"]["tax_no"])
        time.sleep(3)
        
        try:
            # Listelenen ilk sonuca tıklama
            result_item = STATE["driver"].find_element(By.XPATH, "/html/body/span/span/span/ul/li[1]")
            result_text = result_item.text
            log_message(f"Bulunan firma seçiliyor: {result_text}")
            result_item.click()
            time.sleep(2)
            
            # Sayfayı aşağı kaydırarak odağı fatura bilgilerine getirme
            STATE["driver"].execute_script("window.scrollBy(0, 500);")
            log_message("Sayfa 500px aşağı kaydırıldı.")
            
            # Başarılı tıklama sonrası doğrudan fatura ayarlarına geçiş
            invoice_settings()
            return True
        except Exception as click_err:
            log_message(f"Hızlı aramada firma bulunamadı veya tıklanamadı: {click_err}")
            return False
    except Exception as search_err:
        log_message(f"Hızlı arama kutusu bulunamadı: {search_err}")
        return False

def long_registration(wait):
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
                save_data(COMPANIES_FILE, STATE["companies"])
                log_message(f"Firma ticari ünvanı güncellendi: {captured_name}")
                break
                
    STATE["driver"].find_element(By.XPATH, "/html/body/div[1]/div[10]/div/div/div[3]/button[1]").click()
    time.sleep(2)

def invoice_settings():
    wait = WebDriverWait(STATE["driver"], 10)
    
    # 1. Döviz kuru (TRY)
    try:
        currency_select = STATE["driver"].find_element(By.XPATH, "/html/body/div[1]/div[8]/div[1]/div[3]/div[1]/div[8]/div/div[2]/div[2]/div[4]/div/select")
        STATE["driver"].execute_script("arguments[0].scrollIntoView({block: 'center'});", currency_select)
        time.sleep(1)
        Select(currency_select).select_by_index(0)
        log_message("Para birimi seçildi.")
    except Exception as e:
        log_message(f"Para birimi seçilemedi: {e}")
        
    time.sleep(1)
    if STATE["stop_flag"]: return
    
    # 2. Seri numarası girişi
    try:
        serial_input = STATE["driver"].find_element(By.XPATH, "/html/body/div[1]/div[8]/div[1]/div[3]/div[1]/div[8]/div/div[2]/div[2]/div[6]/div/div/div[1]/div[1]/div/input")
        STATE["driver"].execute_script("arguments[0].scrollIntoView({block: 'center'});", serial_input)
        time.sleep(1)
        serial_val = f"YRN{str(STATE['settings']['serial']).zfill(13)}"
        try:
            serial_input.clear()
            serial_input.send_keys(serial_val)
        except Exception:
            STATE["driver"].execute_script("arguments[0].value = arguments[1]; arguments[0].dispatchEvent(new Event('input')); arguments[0].dispatchEvent(new Event('change'));", serial_input, serial_val)
        log_message("Fatura seri numarası girildi.")
    except Exception as e:
        log_message(f"Seri numarası girilemedi: {e}")
        
    time.sleep(1)
    if STATE["stop_flag"]: return
    
    # 3. Tarih seçimi (Fatura Tarihi ve İade Fatura Tarihi)
    for attempt in range(3):
        try:
            # Hata uyarısı modalı çıkmışsa kapat
            try:
                error_el = STATE["driver"].find_element(By.XPATH, "/html/body/div[7]/div/div[2]")
                if error_el.is_displayed() and "Lütfen iade fatura tarihi giriniz." in error_el.text:
                    kapat_btn = STATE["driver"].find_element(By.XPATH, "/html/body/div[7]/div/div[6]/button[1]")
                    STATE["driver"].execute_script("arguments[0].click();", kapat_btn)
                    log_message("Hata uyarı penceresi (Tarih Eksik) kapatıldı. Tarih yeniden girilmeye çalışılacak...")
                    time.sleep(1.5)
            except Exception:
                pass
                
            # Normal fatura tarihi
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
                
            # İade Fatura Tarihi
            try:
                return_date_inputs = STATE["driver"].find_elements(By.XPATH, "//input[@placeholder='gg.aa.yyyy']")
                if return_date_inputs:
                    for inp in return_date_inputs:
                        if inp.is_displayed():
                            STATE["driver"].execute_script("arguments[0].scrollIntoView({block: 'center'});", inp)
                            time.sleep(1)
                            try:
                                inp.click()
                            except Exception:
                                STATE["driver"].execute_script("arguments[0].click();", inp)
                            time.sleep(1.5)
                            
                            clicked_today = False
                            try:
                                today_btn_calendar = STATE["driver"].find_element(By.XPATH, "//button[contains(text(), 'Bugün')] | //a[contains(text(), 'Bugün')] | //span[contains(text(), 'Bugün')]")
                                if today_btn_calendar.is_displayed():
                                    try:
                                        today_btn_calendar.click()
                                    except Exception:
                                        STATE["driver"].execute_script("arguments[0].click();", today_btn_calendar)
                                    clicked_today = True
                                    log_message("Takvimden 'Bugün' seçildi.")
                            except Exception as calendar_today_err:
                                log_message(f"Takvim Bugün butonu bulunamadı: {calendar_today_err}")
                            
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
            STATE["driver"].execute_script("arguments[0].click();", save_btn)
        log_message("Fatura ayarları kaydedildi.")
        on_prep_finished()
    except Exception as e:
        log_message(f"Fatura ayarları kaydedilemedi: {e}")

def on_prep_finished():
    STATE["prep_status"] = "Hazır"
    STATE["prep_btn_color"] = "#00e676"
    STATE["status"] = "Firma Hazır"
    STATE["status_color"] = "#00e676"
    log_message("Fatura başlığı ve ayarları başarıyla hazırlandı.")

def process_products_thread():
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
    log_message(f"Hata Oluştu: {str(e)}")
    STATE["status"] = "Hata Oluştu!"
    STATE["status_color"] = "#ff1744"
