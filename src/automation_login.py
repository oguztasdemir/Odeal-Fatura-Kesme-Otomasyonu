import time
import json
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from .config import STATE, log_message, save_data, COOKIES_FILE, ACCOUNTS_FILE
from .automation_core import get_or_create_driver, find_element_safe, handle_error

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
        if "fatura.odeal.com" not in driver.current_url:
            driver.get("https://fatura.odeal.com/index.php")
        
        wait = WebDriverWait(driver, 15)
        email_el = find_element_safe(
            driver,
            "/html/body/div[1]/div/div/form/div[1]/input",
            [
                "//input[@type='email']",
                "//input[contains(@placeholder, 'posta') or contains(@placeholder, 'Posta') or contains(@placeholder, 'Email')]",
                "//form//input[1]"
            ],
            wait_time=15
        )
        email_el.clear()
        email_el.send_keys(email)
        
        if STATE["stop_flag"]:
            log_message("İşlem kullanıcı tarafından durduruldu.")
            return
            
        pass_el = find_element_safe(
            driver,
            "/html/body/div[1]/div/div/form/div[2]/input",
            [
                "//input[@type='password']",
                "//input[contains(@placeholder, 'ifre') or contains(@placeholder, 'Şifre') or contains(@placeholder, 'Password')]",
                "//form//input[2]"
            ],
            wait_time=5
        )
        pass_el.clear()
        pass_el.send_keys(password)
        
        submit_btn = find_element_safe(
            driver,
            "/html/body/div[1]/div/div/form/div[3]/button",
            [
                "//button[@type='submit']",
                "//form//button",
                "//button[contains(text(), 'Giriş') or contains(., 'Giriş')]"
            ],
            wait_time=5
        )
        submit_btn.click()
        
        log_message("Giriş bilgileri gönderildi. Sayfa yanıtı bekleniyor...")
        
        login_failed = False
        code_detected = False
        
        # Set implicit wait to 0 to prevent blockages during checking
        driver.implicitly_wait(0)
        
        for i in range(75): # 75 * 0.2s = 15s total timeout
            if STATE["stop_flag"]:
                log_message("İşlem kullanıcı tarafından durduruldu.")
                return
            
            # 1. Check for OTP input element (using multiple selectors) - PRIORITY
            try:
                driver.find_element(By.XPATH, "/html/body/div[3]/div/input[1]")
                code_detected = True
                break
            except:
                try:
                    driver.find_element(By.CLASS_NAME, "swal-content__input")
                    code_detected = True
                    break
                except:
                    try:
                        driver.find_element(By.XPATH, "//input[contains(@placeholder, 'Doğrulama') or contains(@placeholder, 'doğrulama')]")
                        code_detected = True
                        break
                    except:
                        pass
            
            # 2. Check for error popup
            try:
                error_el = driver.find_element(By.XPATH, "//h2[contains(text(), 'Giriş Başarısız') or contains(text(), 'Hata')]")
                login_failed = True
                break
            except:
                try:
                    error_el = driver.find_element(By.XPATH, "/html/body/div[3]/div/h2")
                    if "Giriş Başarısız" in error_el.text:
                        login_failed = True
                        break
                except:
                    pass
                        
            time.sleep(0.2)
            
        if login_failed:
            log_message("Hatalı giriş tespiti: Giriş Başarısız uyarısı alındı.")
            try:
                close_btn = driver.find_element(By.XPATH, "//button[contains(text(), 'Kapat') or contains(text(), 'Tamam')]")
                close_btn.click()
            except:
                try:
                    close_btn = driver.find_element(By.XPATH, "/html/body/div[3]/div/div[6]/button[1]")
                    close_btn.click()
                except:
                    pass
            raise Exception("Giriş Başarısız: E-posta veya şifre hatalı girildi.")
            
        if not code_detected:
            raise Exception("Doğrulama kodu ekranı zaman aşımına uğradı veya tespit edilemedi.")

        log_message("Giriş bilgileri onaylandı. SMS/Google Doğrulama Kodu bekleniyor...")
        
        # Check if we have 2FA secret key saved for this account
        account_data = next((acc for acc in STATE.get("accounts", []) if acc.get("email") == email), None)
        two_factor_secret = account_data.get("two_factor_secret", "") if account_data else ""
        
        if two_factor_secret and two_factor_secret.strip():
            log_message("Kayıtlı 2FA gizli anahtarı tespit edildi. Otomatik kod üretiliyor...")
            try:
                import pyotp
                totp = pyotp.TOTP(two_factor_secret.replace(" ", ""))
                code = totp.now()
                log_message(f"2FA kodu otomatik üretildi: {code}. Giriş doğrulanıyor...")
                submit_code_thread(code)
                return
            except Exception as totp_err:
                log_message(f"Otomatik 2FA kodu üretilemedi veya onaylanamadı: {totp_err}. Manuel koda yönlendiriliyor...")
        
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

def on_login_success():
    log_message("Giriş başarılı!")
    STATE["status"] = "Giriş Başarılı"
    STATE["status_color"] = "#00e676"
    STATE["auth_step"] = "confirmed"
    
    try:
        cookies = STATE["driver"].get_cookies()
        with open(COOKIES_FILE, "w", encoding="utf-8") as f:
            json.dump(cookies, f, ensure_ascii=False, indent=4)
        log_message("Giriş çerezleri başarıyla kaydedildi.")
    except Exception as cookie_err:
        log_message(f"Çerezler kaydedilemedi: {cookie_err}")
    
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

def submit_code_thread(code):
    try:
        STATE["status"] = "Doğrulama Yapılıyor..."
        driver = STATE["driver"]
        # 1. Check if already redirected/logged in
        if "fatura.odeal.com" in driver.current_url and "index.php" not in driver.current_url and "login" not in driver.current_url:
            log_message("Giriş zaten yapılmış olarak algılandı.")
            on_login_success()
            return

        # 2. Try to enter the code
        try:
            wait = WebDriverWait(driver, 8)
            code_input = wait.until(EC.element_to_be_clickable((By.XPATH, "/html/body/div[3]/div/input[1]")))
            code_input.click()
            code_input.clear()
            code_input.send_keys(code)
            submit_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "/html/body/div[3]/div/div[6]/button[1]")))
            submit_btn.click()
            log_message("Doğrulama kodu girildi ve gönderildi.")
        except Exception as input_err:
            # Check if redirect happened during our input attempt (e.g. user entered it manually)
            time.sleep(2)
            if "fatura.odeal.com" in driver.current_url and "index.php" not in driver.current_url and "login" not in driver.current_url:
                log_message("Giriş başarılı algılandı (kod giriş aşaması atlandı).")
                on_login_success()
                return
            else:
                log_message(f"Doğrulama kodu girilemedi: {input_err}")
                STATE["login_message"] = "Doğrulama ekranına ulaşılamadı veya zaman aşımı!"
                STATE["login_message_color"] = "#ff1744"
                STATE["auth_step"] = "code"
                STATE["status"] = "Doğrulama Bekleniyor"
                STATE["status_color"] = "#ffea00"
                return

        # 3. Wait for redirect or error popup
        redirected = False
        for i in range(15):
            time.sleep(1)
            if "fatura.odeal.com" in driver.current_url and "index.php" not in driver.current_url and "login" not in driver.current_url:
                redirected = True
                break
            
            # Check for error popup
            try:
                error_popup_btn = driver.find_element(By.XPATH, "//button[contains(text(), 'Kapat') or contains(text(), 'Tamam')]")
                if error_popup_btn.is_displayed():
                    driver.execute_script("arguments[0].click();", error_popup_btn)
                    log_message("Hatalı kod uyarısı algılandı ve kapatıldı. Lütfen kodu tekrar girin.")
                    STATE["login_message"] = "Hatalı Kod! Lütfen tekrar giriniz."
                    STATE["login_message_color"] = "#ff1744"
                    STATE["auth_step"] = "code"
                    STATE["status"] = "Doğrulama Bekleniyor"
                    STATE["status_color"] = "#ffea00"
                    return
            except:
                pass

        if redirected:
            on_login_success()
        else:
            log_message("Hatalı veya zaman aşımına uğramış doğrulama kodu.")
            STATE["login_message"] = "Hatalı Kod! Lütfen tekrar giriniz."
            STATE["login_message_color"] = "#ff1744"
            STATE["auth_step"] = "code"
            STATE["status"] = "Doğrulama Bekleniyor"
            STATE["status_color"] = "#ffea00"
            
    except Exception as e:
        log_message(f"Doğrulama iş parçacığı hatası: {e}")
        STATE["login_message"] = "Bir hata oluştu. Kodu tekrar girin."
        STATE["login_message_color"] = "#ff1744"
        STATE["auth_step"] = "code"
        STATE["status"] = "Doğrulama Bekleniyor"
        STATE["status_color"] = "#ffea00"

def close_announcement_popup(driver):
    try:
        popup_wait = WebDriverWait(driver, 3)
        btn = popup_wait.until(EC.element_to_be_clickable((By.XPATH, "/html/body/div[6]/div/div[6]/button[1]")))
        btn.click()
        log_message("Duyuru penceresi kapatıldı.")
    except Exception:
        pass
