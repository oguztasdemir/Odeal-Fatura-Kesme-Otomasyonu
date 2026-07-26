import time
import os
import json
from datetime import datetime
import pandas as pd
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC

from .config import STATE, log_message, save_data, COMPANIES_FILE, SETTINGS_FILE, HISTORY_FILE
from .automation_core import get_or_create_driver, find_element_safe, handle_error
from .automation_login import close_announcement_popup

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
        search_input = find_element_safe(
            STATE["driver"],
            "/html/body/div[1]/div[8]/div[1]/div[3]/div[1]/div[3]/div/div[2]/div/div[1]/div/span/span[1]/span/ul/li/input",
            [
                "//span[contains(@class, 'select2-container')]//input",
                "//input[contains(@class, 'select2-search__field')]",
                "//li[contains(@class, 'select2-search')]//input"
            ]
        )
        search_input.clear()
        search_input.send_keys(STATE["selected_company"]["tax_no"])
        time.sleep(3)
        
        try:
            result_item = find_element_safe(
                STATE["driver"],
                "/html/body/span/span/span/ul/li[1]",
                [
                    "//ul[contains(@class, 'select2-results__options')]/li[1]",
                    "//li[contains(@class, 'select2-results__option')]"
                ]
            )
            result_text = result_item.text
            log_message(f"Bulunan firma seçiliyor: {result_text}")
            result_item.click()
            time.sleep(2)
            
            STATE["driver"].execute_script("window.scrollBy(0, 500);")
            log_message("Sayfa 500px aşağı kaydırıldı.")
            
            invoice_settings()
            return True
        except Exception as click_err:
            log_message(f"Hızlı aramada firma bulunamadı veya tıklanamadı: {click_err}")
            return False
    except Exception as search_err:
        log_message(f"Hızlı arama kutusu bulunamadı: {search_err}")
        return False

def long_registration(wait):
    trigger_btn = find_element_safe(
        STATE["driver"],
        "/html/body/div[1]/div[8]/div[1]/div[3]/div[1]/div[3]/div/div[2]/div/div[2]/a",
        [
            "//a[@data-target='#cariEkle']",
            "//button[@data-target='#cariEkle']",
            "//a[contains(text(), 'Yeni Alıcı') or contains(text(), 'Alıcı Ekle') or contains(text(), 'Yeni Müşteri')]",
            "//a[contains(@class, 'btn') and contains(text(), 'Yeni')]"
        ]
    )
    trigger_btn.click()
    time.sleep(2)
    
    vkn_input = find_element_safe(
        STATE["driver"],
        "//input[@id='edit-vkn']",
        ["//input[@placeholder='VKN/TCKN (*)']", "/html/body/div[1]/div[10]/div/div/div[2]/div[2]/div[1]/input"]
    )
    vkn_input.clear()
    vkn_input.send_keys(STATE["selected_company"]["tax_no"])
    time.sleep(1)
    
    ulke_select = find_element_safe(
        STATE["driver"],
        "//select[@id='edit-ulke']",
        ["/html/body/div[1]/div[10]/div/div/div[2]/div[4]/div[1]/select"]
    )
    Select(ulke_select).select_by_index(1)
    time.sleep(1)
    
    sehir_select = find_element_safe(
        STATE["driver"],
        "//select[@id='edit-sehir']",
        ["/html/body/div[1]/div[10]/div/div/div[2]/div[4]/div[2]/select"]
    )
    
    autofilled_city = ""
    try:
        autofilled_city = Select(sehir_select).first_selected_option.text.strip()
    except:
        pass
        
    if autofilled_city and "Seçin" not in autofilled_city:
        for c in STATE["companies"]:
            if c["tax_no"] == STATE["selected_company"]["tax_no"]:
                c["city"] = autofilled_city
                save_data(COMPANIES_FILE, STATE["companies"])
                break
    else:
        try:
            Select(sehir_select).select_by_visible_text(STATE["selected_company"]["city"])
        except:
            pass
    time.sleep(1.5)
    
    ilce_select = find_element_safe(
        STATE["driver"],
        "//select[@id='edit-ilce']",
        ["/html/body/div[1]/div[10]/div/div/div[2]/div[5]/div[1]/select"]
    )
    
    autofilled_district = ""
    try:
        autofilled_district = Select(ilce_select).first_selected_option.text.strip()
    except:
        pass
        
    if autofilled_district and "Seçin" not in autofilled_district:
        for c in STATE["companies"]:
            if c["tax_no"] == STATE["selected_company"]["tax_no"]:
                c["district"] = autofilled_district
                save_data(COMPANIES_FILE, STATE["companies"])
                break
    else:
        try:
            Select(ilce_select).select_by_visible_text(STATE["selected_company"]["district"])
        except:
            pass
    time.sleep(1.5)
    
    try:
        tax_office_select = find_element_safe(
            STATE["driver"],
            "//select[@id='edit-vergidairesi']",
            ["/html/body/div[1]/div[10]/div/div/div[2]/div[8]/div[2]/select"]
        )
        autofilled_tax_office = Select(tax_office_select).first_selected_option.text.strip()
        if autofilled_tax_office and "Seçin" not in autofilled_tax_office:
            for c in STATE["companies"]:
                if c["tax_no"] == STATE["selected_company"]["tax_no"]:
                    c["tax_office"] = autofilled_tax_office
                    save_data(COMPANIES_FILE, STATE["companies"])
                    break
    except:
        pass
        
    try:
        tax_office_span = find_element_safe(
            STATE["driver"],
            "//select[@id='edit-vergidairesi']/following-sibling::span",
            [
                "/html/body/div[1]/div[10]/div/div/div[2]/div[8]/div[2]/span/span[1]/span/span[1]",
                "//span[contains(@class, 'select2-container')]"
            ]
        )
        tax_office_span.click()
        time.sleep(1.5)
        STATE["driver"].switch_to.active_element.send_keys(STATE["selected_company"]["tax_office"])
        time.sleep(2.5)
        wait.until(EC.element_to_be_clickable((By.XPATH, "//ul[contains(@class, 'select2-results__options')]/li"))).click()
        time.sleep(1)
    except Exception as tax_err:
        pass
    
    unvan_input = find_element_safe(
        STATE["driver"],
        "//input[@id='edit-unvan']",
        ["/html/body/div[1]/div[10]/div/div/div[2]/div[2]/div[2]/input"]
    )
    captured_name = unvan_input.get_attribute("value")
    if captured_name:
        for comp in STATE["companies"]:
            if comp["tax_no"] == STATE["selected_company"]["tax_no"]:
                comp["full_name"] = captured_name
                save_data(COMPANIES_FILE, STATE["companies"])
                log_message(f"Firma ticari ünvanı güncellendi: {captured_name}")
                break
                
    save_btn = find_element_safe(
        STATE["driver"],
        "//a[@id='edit-kaydet']",
        ["//a[contains(text(), 'Kaydet')]", "/html/body/div[1]/div[10]/div/div/div[2]/div[12]/a"]
    )
    save_btn.click()
    time.sleep(2)

def invoice_settings():
    wait = WebDriverWait(STATE["driver"], 10)
    
    try:
        currency_select = STATE["driver"].find_element(By.XPATH, "/html/body/div[1]/div[8]/div[1]/div[3]/div[1]/div[8]/div/div[2]/div[2]/div[4]/div/select")
        STATE["driver"].execute_script("arguments[0].scrollIntoView({block: 'center'});", currency_select)
        time.sleep(1)
        Select(currency_select).select_by_index(0)
        log_message("Para birimi seçildi.")
    except Exception as e:
        log_message(f"Para birimi seçilemedi: {e}")
        
    try:
        scenario_val = STATE["settings"].get("invoice_scenario", "TEMEL")
        type_val = STATE["settings"].get("invoice_type", "SATIS")
        
        selects = STATE["driver"].find_elements(By.TAG_NAME, "select")
        for sel in selects:
            try:
                options = [opt.text.lower() for opt in sel.find_elements(By.TAG_NAME, "option")]
                if any("temel" in opt or "ticari" in opt for opt in options):
                    for opt in sel.find_elements(By.TAG_NAME, "option"):
                        if ("temel" in opt.text.lower() and scenario_val == "TEMEL") or \
                           ("ticari" in opt.text.lower() and scenario_val == "TİCARİ"):
                            Select(sel).select_by_visible_text(opt.text)
                            log_message(f"Fatura Senaryosu seçildi: {opt.text}")
                            break
                elif any("satış" in opt or "iade" in opt for opt in options):
                    for opt in sel.find_elements(By.TAG_NAME, "option"):
                        if ("satış" in opt.text.lower() and type_val == "SATIS") or \
                           ("iade" in opt.text.lower() and type_val == "IADE"):
                            Select(sel).select_by_visible_text(opt.text)
                            log_message(f"Fatura Türü seçildi: {opt.text}")
                            break
            except:
                pass
    except Exception as sel_err:
        log_message(f"Senaryo/Tür seçimi başarısız: {sel_err}")
        
    time.sleep(1)
    if STATE["stop_flag"]: return
    
    try:
        serial_input = STATE["driver"].find_element(By.XPATH, "/html/body/div[1]/div[8]/div[1]/div[3]/div[1]/div[8]/div/div[2]/div[2]/div[6]/div/div/div[1]/div[1]/div/input")
        STATE["driver"].execute_script("arguments[0].scrollIntoView({block: 'center'});", serial_input)
        time.sleep(1)
        prefix = STATE['settings'].get('serial_prefix', 'YRN')
        serial_val = f"{prefix}{str(STATE['settings']['serial']).zfill(16 - len(prefix))}"
        try:
            serial_input.clear()
            serial_input.send_keys(serial_val)
        except Exception:
            STATE["driver"].execute_script("arguments[0].value = arguments[1]; arguments[0].dispatchEvent(new Event('input')); arguments[0].dispatchEvent(new Event('change'));", serial_input, serial_val)
        log_message(f"Fatura seri numarası girildi: {serial_val}")
    except Exception as e:
        log_message(f"Seri numarası girilemedi: {e}")
        
    time.sleep(1)
    if STATE["stop_flag"]: return
    
    for attempt in range(3):
        try:
            try:
                error_el = STATE["driver"].find_element(By.XPATH, "/html/body/div[7]/div/div[2]")
                if error_el.is_displayed() and "Lütfen iade fatura tarihi giriniz." in error_el.text:
                    kapat_btn = STATE["driver"].find_element(By.XPATH, "/html/body/div[7]/div/div[6]/button[1]")
                    STATE["driver"].execute_script("arguments[0].click();", kapat_btn)
                    log_message("Hata uyarı penceresi (Tarih Eksik) kapatıldı. Tarih yeniden girilmeye çalışılacak...")
                    time.sleep(1.5)
            except Exception:
                pass
                
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
                
            try:
                ref_no = STATE.get("selected_invoice_no", "")
                ref_date = STATE.get("selected_invoice_date", "")
                
                if ref_no:
                    try:
                        no_input = find_element_safe(
                            STATE["driver"],
                            "",
                            [
                                "//input[contains(@placeholder, 'Fatura No')]",
                                "//input[contains(@placeholder, 'Fatura Numarası')]",
                                "//input[contains(@placeholder, 'Belge No')]",
                                "//input[contains(@placeholder, 'FaturaNo')]"
                            ],
                            wait_time=3
                        )
                        if no_input:
                            STATE["driver"].execute_script("arguments[0].scrollIntoView({block: 'center'});", no_input)
                            time.sleep(1)
                            no_input.clear()
                            no_input.send_keys(ref_no)
                            log_message(f"İlişkili fatura no girildi: {ref_no}")
                    except Exception as no_err:
                        log_message(f"İlişkili fatura no doldurulamadı: {no_err}")
                
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
                            if ref_date:
                                inp.clear()
                                inp.send_keys(ref_date)
                                log_message(f"İlişkili fatura tarihi girildi: {ref_date}")
                                clicked_today = True
                                time.sleep(1)
                            
                            if not clicked_today:
                                try:
                                    today_btn_calendar = STATE["driver"].find_element(By.XPATH, "//button[contains(text(), 'Bugün')] | //a[contains(text(), 'Bugün')] | //span[contains(text(), 'Bugün')]")
                                    if today_btn_calendar.is_displayed():
                                        try:
                                            today_btn_calendar.click()
                                        except Exception:
                                            STATE["driver"].execute_script("arguments[0].click();", today_btn_calendar)
                                        clicked_today = True
                                        log_message("Takvimden 'Bugün' seçildi.")
                                except Exception:
                                    pass
                                    
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
                log_message(f"İade fatura bilgileri doldurulamadı: {return_date_err}")
                
            break
        except Exception as e:
            log_message(f"Fatura günü girilirken hata oluştu, deneme {attempt+1} başarısız: {e}")
            time.sleep(2)
        
    time.sleep(1)
    if STATE["stop_flag"]: return
    
    max_collision_retries = 5
    for attempt in range(max_collision_retries):
        try:
            save_btn = STATE["driver"].find_element(By.XPATH, "/html/body/div[1]/div[8]/div[1]/div[3]/div[1]/div[8]/div/div[2]/div[2]/div[6]/div/div/div[1]/div[3]")
            STATE["driver"].execute_script("arguments[0].scrollIntoView({block: 'center'});", save_btn)
            time.sleep(1)
            try:
                save_btn.click()
            except Exception:
                STATE["driver"].execute_script("arguments[0].click();", save_btn)
            time.sleep(2)
            
            collision_detected = False
            try:
                popup_el = STATE["driver"].find_element(By.XPATH, "//div[contains(@class, 'swal') or contains(@class, 'modal')]")
                if popup_el.is_displayed():
                    text = popup_el.text.lower()
                    if "kullanılmış" in text or "mükerrer" in text or "fatura numarası" in text or "geçersiz" in text or "seri" in text:
                        log_message(f"Seri numarası çakışması algılandı! Popup içeriği: {popup_el.text}")
                        collision_detected = True
                        
                        close_btn = popup_el.find_element(By.XPATH, ".//button[contains(text(), 'Tamam') or contains(text(), 'Kapat') or contains(text(), 'OK')]")
                        STATE["driver"].execute_script("arguments[0].click();", close_btn)
                        time.sleep(1.5)
            except:
                pass
                
            if collision_detected:
                STATE["settings"]["serial"] = STATE["settings"].get("serial", 42) + 1
                save_data(SETTINGS_FILE, STATE["settings"])
                
                serial_input = STATE["driver"].find_element(By.XPATH, "/html/body/div[1]/div[8]/div[1]/div[3]/div[1]/div[8]/div/div[2]/div[2]/div[6]/div/div/div[1]/div[1]/div/input")
                prefix = STATE['settings'].get('serial_prefix', 'YRN')
                serial_val = f"{prefix}{str(STATE['settings']['serial']).zfill(16 - len(prefix))}"
                
                try:
                    serial_input.clear()
                    serial_input.send_keys(serial_val)
                except Exception:
                    STATE["driver"].execute_script("arguments[0].value = arguments[1]; arguments[0].dispatchEvent(new Event('input')); arguments[0].dispatchEvent(new Event('change'));", serial_input, serial_val)
                log_message(f"Yeni seri numarası girildi ve yeniden deneniyor: {serial_val} (Deneme {attempt+1}/{max_collision_retries})")
                continue
            else:
                log_message("Fatura ayarları başarıyla kaydedildi.")
                on_prep_finished()
                break
        except Exception as e:
            log_message(f"Kaydetme denemesi sırasında hata: {e}")
            if attempt == max_collision_retries - 1:
                raise e
            time.sleep(2)

def on_prep_finished():
    STATE["prep_status"] = "Hazır"
    STATE["prep_btn_color"] = "#00e676"
    STATE["status"] = "Firma Hazır"
    STATE["status_color"] = "#00e676"
    log_message("Fatura başlığı ve ayarları başarıyla hazırlandı.")

def map_unit(unit_str):
    if not unit_str:
        return "adet"
    val = str(unit_str).strip().lower()
    mappings = {
        "adet": "adet", "ad.": "adet", "ad": "adet", "pcs": "adet", "porsiyon": "adet", "paket": "adet",
        "kg": "kg", "kilogram": "kg", "kilo": "kg", "gr": "gram", "gram": "gram",
        "litre": "litre", "lt": "litre", "l": "litre",
        "metre": "metre", "mt": "metre", "m": "metre"
    }
    return mappings.get(val, unit_str)

def process_products_thread():
    try:
        STATE["stop_flag"] = False
        log_message("Ürünler faturaya işleniyor...")
        wait = WebDriverWait(STATE["driver"], 10)
        df = STATE["excel_data"].copy()
        
        for idx, row in df.iterrows():
            if STATE["stop_flag"]: return
            log_message(f"Ürün ekleniyor ({idx+1}/{len(df)}): {row.iloc[0]}")
            prod_input = find_element_safe(
                STATE["driver"],
                "/html/body/div[1]/div[8]/div[1]/div[3]/div[1]/div[9]/div[1]/div[3]/div/div/div[1]/input[1]",
                [
                    "//div[contains(@class, 'product') or contains(@class, 'item')]//input",
                    "//input[contains(@placeholder, 'Ürün') or contains(@placeholder, 'Hizmet')]",
                    "//input[contains(@id, 'urun')]"
                ]
            )
            prod_input.send_keys(str(row.iloc[0]))
            
            qty_input = find_element_safe(
                STATE["driver"],
                "/html/body/div[1]/div[8]/div[1]/div[3]/div[1]/div[9]/div[1]/div[3]/div/div/div[2]/input",
                [
                    "//input[@type='number' or contains(@placeholder, 'Miktar') or contains(@placeholder, 'Adet')]",
                    "//input[contains(@id, 'miktar')]"
                ]
            )
            qty_input.send_keys(str(row.iloc[1]))
            
            unit_select = find_element_safe(
                STATE["driver"],
                "/html/body/div[1]/div[8]/div[1]/div[3]/div[1]/div[9]/div[1]/div[3]/div/div/div[3]/select",
                [
                    "//select[contains(@class, 'birim') or contains(@id, 'birim') or contains(@name, 'unit')]",
                    "//select[1]"
                ]
            )
            unit_val = map_unit(row.iloc[2])
            try:
                Select(unit_select).select_by_visible_text(str(unit_val))
            except Exception:
                try:
                    Select(unit_select).select_by_visible_text(str(row.iloc[2]))
                except Exception:
                    Select(unit_select).select_by_index(0)
            
            price_input = find_element_safe(
                STATE["driver"],
                "/html/body/div[1]/div[8]/div[1]/div[3]/div[1]/div[9]/div[1]/div[3]/div/div/div[4]/div/input",
                [
                    "//input[contains(@placeholder, 'Fiyat') or contains(@placeholder, 'Birim Fiyat')]",
                    "//input[contains(@id, 'fiyat')]"
                ]
            )
            price_input.send_keys(str(row.iloc[3]))
            
            kdv_select = find_element_safe(
                STATE["driver"],
                "/html/body/div[1]/div[8]/div[1]/div[3]/div[1]/div[9]/div[1]/div[3]/div/div/div[6]/select",
                [
                    "//select[contains(@class, 'kdv') or contains(@id, 'kdv')]",
                    "//select[2]"
                ]
            )
            mapping = {"0": 1, "1": 2, "10": 3, "20": 4}
            Select(kdv_select).select_by_index(mapping.get(str(row.iloc[4]), 4))
            
            add_btn = find_element_safe(
                STATE["driver"],
                "/html/body/div[1]/div[8]/div[1]/div[3]/div[1]/div[9]/div[1]/div[3]/div/div/div[8]/button",
                [
                    "//button[contains(., 'Ekle') or contains(., '+')]",
                    "//button[contains(@class, 'btn-primary')]"
                ]
            )
            add_btn.click()
            time.sleep(2)
            
        for idx, row in df.iterrows():
            if STATE["stop_flag"]: return
            isk = row.iloc[5]
            if pd.notna(isk) and float(isk) > 0:
                log_message(f"İskonto uygulanıyor: {row.iloc[0]} -> {isk}")
                try:
                    driver = STATE["driver"]
                    product_row = driver.find_element(By.XPATH, f"//table//tbody//tr[td[1][contains(., '{row.iloc[0]}')]]")
                    discount_btn = product_row.find_element(By.XPATH, ".//td[8]/button[1]")
                    driver.execute_script("arguments[0].click();", discount_btn)
                    time.sleep(2)
                    
                    discount_input = find_element_safe(
                        driver,
                        "/html/body/div[1]/div[8]/div[1]/div[3]/div[1]/div[1]/div/div/div[2]/div[1]/div[2]/div/div[4]/div[3]/div[2]/input",
                        ["//div[contains(@class, 'modal')]//input", "//input[contains(@placeholder, 'oran') or contains(@placeholder, 'tutar')]"]
                    )
                    discount_input.send_keys(str(isk).replace("%",""))
                    
                    modal_save_btn = find_element_safe(
                        driver,
                        "/html/body/div[1]/div[8]/div[1]/div[3]/div[1]/div[1]/div/div/div[2]/div[1]/div[2]/div/div[4]/div[5]/button",
                        ["//div[contains(@class, 'modal')]//button[contains(., 'Uygula') or contains(., 'Kaydet')]"]
                    )
                    driver.execute_script("arguments[0].click();", modal_save_btn)
                    time.sleep(1)
                    
                    modal_close_btn = find_element_safe(
                        driver,
                        "/html/body/div[1]/div[8]/div[1]/div[3]/div[1]/div[1]/div/div/div[3]/button[1]",
                        ["//div[contains(@class, 'modal')]//div[contains(@class, 'footer')]//button[1]"]
                    )
                    driver.execute_script("arguments[0].click();", modal_close_btn)
                    time.sleep(1)
                    
                    alert_ok_btn = find_element_safe(
                        driver,
                        "/html/body/div[7]/div/div[6]/button[1]",
                        ["//div[contains(@class, 'sweet') or contains(@class, 'alert')]//button[contains(., 'Tamam') or contains(., 'Evet') or contains(@class, 'confirm')]"]
                    )
                    driver.execute_script("arguments[0].click();", alert_ok_btn)
                    time.sleep(2)
                except Exception as isk_err:
                    log_message(f"İskonto uygulama hatası ({row.iloc[0]}): {isk_err}")
                    
        prefix = STATE['settings'].get('serial_prefix', 'YRN')
        serial_val = f"{prefix}{str(STATE['settings']['serial']).zfill(16 - len(prefix))}"
        
        STATE["settings"]["serial"] += 1
        save_data(SETTINGS_FILE, STATE["settings"])
        
        history_entry = {
            "date": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
            "company_title": STATE["selected_company"]["title"] if STATE["selected_company"] else "-",
            "total": STATE["kpis"]["toplam"],
            "items_count": STATE["kpis"]["kalem"],
            "serial_no": serial_val
        }
        
        history_data = []
        if os.path.exists(HISTORY_FILE):
            try:
                with open(HISTORY_FILE, "r", encoding="utf-8") as hf:
                    history_data = json.load(hf)
            except:
                history_data = []
        history_data.insert(0, history_entry)
        
        try:
            with open(HISTORY_FILE, "w", encoding="utf-8") as hf:
                json.dump(history_data, hf, ensure_ascii=False, indent=4)
        except Exception as he:
            log_message(f"İşlem geçmişi kaydedilemedi: {he}")

        mode = STATE["settings"].get("finalization_mode", "manual")
        if mode != "manual":
            log_message(f"Fatura sonlandırılıyor: Mod: {mode}")
            try:
                driver = STATE["driver"]
                if mode == "draft":
                    draft_btn = None
                    for btn in driver.find_elements(By.TAG_NAME, "button"):
                        txt = btn.text.lower()
                        if "taslak" in txt or ("kaydet" in txt and "fatura" in txt):
                            draft_btn = btn
                            break
                    if draft_btn:
                        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", draft_btn)
                        time.sleep(1)
                        driver.execute_script("arguments[0].click();", draft_btn)
                        log_message("Fatura taslak olarak kaydedildi.")
                        time.sleep(3)
                        try:
                            ok_btn = driver.find_element(By.XPATH, "//button[contains(text(), 'Tamam') or contains(text(), 'Kapat') or contains(text(), 'ok')]")
                            driver.execute_script("arguments[0].click();", ok_btn)
                        except:
                            pass
                    else:
                        log_message("Taslak Kaydet butonu bulunamadı, manuel devam edin.")
                elif mode == "send":
                    send_btn = None
                    for btn in driver.find_elements(By.TAG_NAME, "button"):
                        txt = btn.text.lower()
                        if "gönder" in txt or "oluştur" in txt or "onayla" in txt:
                            send_btn = btn
                            break
                    if send_btn:
                        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", send_btn)
                        time.sleep(1)
                        driver.execute_script("arguments[0].click();", send_btn)
                        log_message("Fatura gönderildi.")
                        time.sleep(3)
                        try:
                            ok_btn = driver.find_element(By.XPATH, "//button[contains(text(), 'Tamam') or contains(text(), 'Kapat') or contains(text(), 'Evet')]")
                            driver.execute_script("arguments[0].click();", ok_btn)
                        except:
                            pass
                    else:
                        log_message("Gönder butonu bulunamadı, manuel devam edin.")
            except Exception as final_err:
                log_message(f"Fatura sonlandırma hatası: {final_err}")

        log_message("Tüm işlemler başarıyla tamamlandı!")
        STATE["status"] = "Tamamlandı!"
        STATE["status_color"] = "#00e676"
    except Exception as e:
        handle_error(e)
