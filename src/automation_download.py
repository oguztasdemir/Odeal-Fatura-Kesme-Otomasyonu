import time
import os
import json
import re
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC

from .config import STATE, log_message, save_data, SETTINGS_FILE, DOWNLOADS_FOLDER, BACKUP_FOLDER, BACKUPS_FILE, COMPANIES_FILE
from .automation_core import get_or_create_driver, find_element_safe, wait_for_download_complete, handle_error

DOWNLOAD_HISTORY_FILE = os.path.join(BACKUP_FOLDER, "indirilen_tarihcesi.json")

def load_download_history():
    if os.path.exists(DOWNLOAD_HISTORY_FILE):
        try:
            with open(DOWNLOAD_HISTORY_FILE, "r", encoding="utf-8") as f:
                return set(json.load(f))
        except:
            pass
    return set()

def save_download_history(history_set):
    try:
        with open(DOWNLOAD_HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(list(history_set), f, ensure_ascii=False, indent=4)
    except Exception as e:
        log_message(f"İndirme tarihçesi kaydedilemedi: {e}")

def wait_for_processing_overlay(driver, timeout=45):
    xpath_overlay = "/html/body/div[1]/div[8]/div[1]/div[2]/div/div[6]/div/div[2]/div/div[2]"
    time.sleep(1.0) # give it a moment to potentially appear
    try:
        elements = driver.find_elements(By.XPATH, xpath_overlay)
        if elements:
            el = elements[0]
            if el.is_displayed() and "İşleniyor" in el.text:
                log_message("İşleniyor ekranı algılandı, kaybolması bekleniyor...")
                # Wait for it to become invisible or not have 'İşleniyor' text
                WebDriverWait(driver, timeout).until(
                    lambda d: not d.find_elements(By.XPATH, xpath_overlay) or 
                              not d.find_element(By.XPATH, xpath_overlay).is_displayed() or 
                              "İşleniyor" not in d.find_element(By.XPATH, xpath_overlay).text
                )
                log_message("İşleniyor ekranı kayboldu.")
                time.sleep(1.0)
    except Exception as e:
        log_message(f"İşleniyor ekranı beklerken hata veya zaman aşımı: {e}")

def download_invoices_thread(start_date_str, end_date_str, download_type, filter_query=None, direction="gelen", sort_order="asc", session_id=None):
    try:
        STATE["stop_flag"] = False
        STATE["status"] = "Faturalar İndiriliyor..."
        STATE["status_color"] = "#ffea00"
        STATE["session_invoices_count"] = 0
        log_message(f"Fatura indirme işlemi başlatıldı: {start_date_str} - {end_date_str} ({download_type}) - Yön: {direction} - Filtre: {filter_query if filter_query else 'Yok'} - Sıralama: {sort_order}")
        
        # Initialize or fetch backup session
        if "backups" not in STATE or STATE["backups"] is None:
            STATE["backups"] = []
            
        active_session = None
        if session_id:
            for b in STATE["backups"]:
                if b["id"] == session_id:
                    active_session = b
                    break
                    
        if not active_session:
            for b in STATE["backups"]:
                if b["start_date"] == start_date_str and b["end_date"] == end_date_str and b["direction"] == direction and b["download_type"] == download_type and b["status"] == "partial":
                    active_session = b
                    break
                
        if not active_session:
            new_session_id = f"backup_{int(time.time())}"
            active_session = {
                "id": new_session_id,
                "start_date": start_date_str,
                "end_date": end_date_str,
                "last_processed_date": start_date_str,
                "direction": direction,
                "download_type": download_type,
                "filter_query": filter_query or "",
                "sort_order": sort_order,
                "status": "partial",
                "progress": 0
            }
            STATE["backups"].append(active_session)
            save_data(BACKUPS_FILE, STATE["backups"])
            
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
        end_date = datetime.strptime(end_date_str, "%Y-%m-%d")
        
        download_history = load_download_history()
        seen_invoices = set()
        log_message(f"Toplam {len(download_history)} adet daha önce indirilmiş fatura kaydı yüklendi.")
        
        driver = get_or_create_driver()
        wait = WebDriverWait(driver, 15)
        
        url = "https://fatura.odeal.com/gidenfatura" if direction == "giden" else "https://fatura.odeal.com/gelenfatura"
        log_message(f"{'Giden' if direction == 'giden' else 'Gelen'} Fatura sayfasına yönlendiriliyor...")
        driver.get(url)
        time.sleep(3)
        
        start_year = start_date.year
        end_year = end_date.year
        
        # Read actually available year links from the portal screen dynamically
        available_years = []
        try:
            year_links = driver.find_elements(By.XPATH, "//a[contains(@class, 'years-filter')]")
            if not year_links:
                year_links = driver.find_elements(By.XPATH, "//div[contains(@class, 'yil_listele')]//a")
            for link in year_links:
                txt = link.text.strip()
                if txt.isdigit():
                    val = int(txt)
                    if start_year <= val <= end_year:
                        available_years.append(val)
        except Exception as year_err:
            log_message(f"Yıl filtre butonları okunamadı: {year_err}")
            
        if not available_years:
            available_years = list(range(max(2024, start_year), end_year + 1))
            
        reverse_years = (sort_order == "desc")
        years_to_process = sorted(list(set(available_years)), reverse=reverse_years)
        
        for current_year in years_to_process:
            if STATE["stop_flag"]:
                log_message("İşlem kullanıcı tarafından durduruldu.")
                return
            
            log_message(f"{current_year} yılı faturaları yükleniyor...")
            
            year_links = driver.find_elements(By.XPATH, "//a[contains(@class, 'years-filter')]")
            if not year_links:
                year_links = driver.find_elements(By.XPATH, "//div[contains(@class, 'yil_listele')]//a")
            year_clicked = False
            for link in year_links:
                if str(current_year) in link.text:
                    log_message(f"{current_year} yılı filtresine tıklanıyor...")
                    driver.execute_script("arguments[0].click();", link)
                    year_clicked = True
                    time.sleep(4)
                    break
            
            if not year_clicked:
                log_message(f"Uyarı: {current_year} yılı için buton bulunamadı. Sayfadaki mevcut filtreyle devam ediliyor.")
            
            try:
                select_el = find_element_safe(
                    driver,
                    "/html/body/div[1]/div[8]/div[1]/div[2]/div/div[6]/div/div[1]/div[1]/div/label/select",
                    [
                        "//select[contains(@name, 'length') or @class='custom-select']",
                        "//label/select"
                    ],
                    wait_time=5
                )
                driver.execute_script("arguments[0].value = '50'; arguments[0].dispatchEvent(new Event('change'));", select_el)
                log_message("Listeleme adeti JS ile 50 olarak seçildi. Sayfa yüklenmesi bekleniyor...")
                 
                wait_for_processing_overlay(driver)
            except Exception as select_err:
                log_message(f"Listeleme adeti 50 seçilemedi: {select_err}")
            
            page_num = 1
            while True:
                if STATE["stop_flag"]:
                    log_message("İşlem kullanıcı tarafından durduruldu.")
                    return
                
                # Wait for any dynamic page transition to finish loading
                wait_for_processing_overlay(driver)
                
                rows = driver.find_elements(By.XPATH, "//table[contains(@id, 'table') or contains(@class, 'table')]/tbody/tr")
                if not rows:
                    rows = driver.find_elements(By.XPATH, "/html/body/div[1]/div[8]/div[1]/div[2]/div/div[6]/div/div[2]/div/div[1]/div[2]/table/tbody/tr")
                
                if not rows:
                    log_message("Bu sayfada fatura bulunamadı.")
                    break
                
                # Step 1: Click "Select All" header checkbox if rows are not selected
                try:
                    driver.execute_script("""
                        window.checked = [];
                        var checkboxes = document.querySelectorAll("#gelen-table tbody input[type='checkbox'], table tbody input[type='checkbox']");
                        checkboxes.forEach(function(chk) {
                            chk.checked = true;
                            var id = chk.id || chk.value;
                            if (id && id !== 'select-all') {
                                window.checked.push(id);
                            }
                        });
                        var selectAll = document.getElementById("select-all");
                        if (selectAll) {
                            selectAll.checked = true;
                        }
                    """)
                    log_message("Sayfadaki tüm fatura kutuları ve global seçim listesi (checked) JS ile işaretlendi.")
                    time.sleep(1.0)
                except Exception as all_err:
                    log_message(f"Seçim listesi hazırlanırken hata oluştu: {all_err}")
                
                checked_count = 0
                actual_download_count = 0
                all_older_than_start = True
                all_newer_than_end = True
                page_selected_nos = []
                last_processed_date_in_page = None
                
                # Step 2: Iterate through rows and uncheck excluded ones
                row_count = len(rows)
                for idx in range(1, row_count + 1):
                    if STATE["stop_flag"]:
                        return
                    
                    try:
                        current_rows = driver.find_elements(By.XPATH, "//table[contains(@id, 'table') or contains(@class, 'table')]/tbody/tr")
                        if not current_rows:
                            current_rows = driver.find_elements(By.XPATH, "/html/body/div[1]/div[8]/div[1]/div[2]/div/div[6]/div/div[2]/div/div[1]/div[2]/table/tbody/tr")
                        if idx - 1 >= len(current_rows):
                            break
                        row = current_rows[idx - 1]
                        
                        cells = row.find_elements(By.TAG_NAME, "td")
                        if len(cells) < 4:
                            continue
                            
                        # Automatically harvest company information from td[6] (index 5)
                        if len(cells) >= 6:
                            try:
                                sender_cell = cells[5]
                                cell_text = sender_cell.text.strip()
                                if cell_text:
                                    vkn_match = re.search(r'\b\d{10,11}\b', cell_text)
                                    if vkn_match:
                                        vkn = vkn_match.group(0)
                                        title = cell_text
                                        title = re.sub(r'\b\d{10,11}\b', '', title)
                                        title = re.sub(r'(?i)vkn|tckn|vergi|no|tc', '', title)
                                        title = re.sub(r'[\(\)\:\-\n\r\t]', ' ', title)
                                        title = re.sub(r'\s+', ' ', title).strip()
                                        
                                        if title and len(vkn) in [10, 11]:
                                            existing = next((c for c in STATE["companies"] if c["tax_no"] == vkn), None)
                                            if not existing:
                                                new_c = {
                                                    "title": title[:35].strip(),
                                                    "tax_no": vkn,
                                                    "city": "İSTANBUL",
                                                    "district": "ŞİŞLİ",
                                                    "tax_office": "ŞİŞLİ",
                                                    "full_name": title
                                                }
                                                STATE["companies"].append(new_c)
                                                save_data(COMPANIES_FILE, STATE["companies"])
                                                log_message(f"Yeni firma tespit edildi ve kaydedildi: {title} ({vkn})")
                            except:
                                pass
                        
                        date_str = ""
                        for cell in cells:
                            txt = cell.text.strip()
                            match = re.search(r'\b\d{2}\.\d{2}\.\d{4}\b', txt)
                            if match:
                                date_str = match.group(0)
                                break
                        
                        if not date_str:
                            continue
                            
                        last_processed_date_in_page = date_str
                        row_date = datetime.strptime(date_str, "%d.%m.%Y")
                        
                        # Update session progress dynamically
                        if active_session:
                            try:
                                formatted_date = row_date.strftime("%Y-%m-%d")
                                active_session["last_processed_date"] = formatted_date
                                
                                start_d = datetime.strptime(active_session["start_date"], "%Y-%m-%d")
                                end_d = datetime.strptime(active_session["end_date"], "%Y-%m-%d")
                                total_days = (end_d - start_d).days
                                if total_days > 0:
                                    proc_days = (row_date - start_d).days
                                    if sort_order == "desc":
                                        proc_days = total_days - proc_days
                                    progress = int((proc_days / total_days) * 100)
                                    active_session["progress"] = max(0, min(99, progress))
                                else:
                                    active_session["progress"] = 0
                            except:
                                pass
                                
                        should_download = True
                        
                        if row_date >= start_date:
                            all_older_than_start = False
                        if row_date <= end_date:
                            all_newer_than_end = False

                        if row_date < start_date or row_date > end_date:
                            should_download = False
                            
                        if should_download and filter_query:
                            found_query = False
                            for cell in cells:
                                if filter_query.lower() in cell.text.lower():
                                    found_query = True
                                    break
                            if not found_query:
                                should_download = False
                                
                        fatura_no = ""
                        for cell in cells:
                            txt = cell.text.strip()
                            match = re.search(r'\b[A-Za-z]{3}\d{13}\b', txt)
                            if match:
                                fatura_no = match.group(0).upper()
                                break
                        
                        if should_download and fatura_no and fatura_no in download_history:
                            should_download = False
                            
                        if not should_download:
                            try:
                                chk = row.find_element(By.XPATH, ".//input[@type='checkbox']")
                                if chk.is_selected():
                                    driver.execute_script("arguments[0].checked = false;", chk)
                            except:
                                pass
                        else:
                            if fatura_no:
                                seen_invoices.add(fatura_no)
                                STATE["session_invoices_count"] = len(seen_invoices)
                                page_selected_nos.append(fatura_no)
                            actual_download_count += 1
                            
                        checked_count += 1
                                
                    except Exception as row_err:
                        log_message(f"Fatura satırı {idx} okunurken hata: {row_err}")
                
                if last_processed_date_in_page:
                    try:
                        dt = datetime.strptime(last_processed_date_in_page, "%d.%m.%Y")
                        formatted_date = dt.strftime("%Y-%m-%d")
                        STATE["settings"]["last_download_date"] = formatted_date
                        save_data(SETTINGS_FILE, STATE["settings"])
                    except:
                        pass

                # No checkboxes were clicked, so we skip long stabilization waits
                time.sleep(0.5)
                        
                if actual_download_count > 0:
                    log_message(f"{actual_download_count} adet uygun yeni fatura seçildi. Toplu indirme işlemi başlatılıyor...")
                    
                    if download_type == "pdf":
                    try:
                        # 1. Wait a bit for the system to settle down
                        log_message("Sayfa stabilizasyonu bekleniyor (3 saniye)...")
                        time.sleep(3.0)
                        
                        # 2. Click the bulk action dropdown button
                        dropdown_xpath = "/html/body/div[1]/div[8]/div[1]/div[2]/div/div[4]/div[2]/div/div/div/div[3]/button"
                        dropdown_btn = WebDriverWait(driver, 15).until(
                            EC.element_to_be_clickable((By.XPATH, dropdown_xpath))
                        )
                        log_message("Toplu İşlem butonuna tıklanıyor...")
                        driver.execute_script("arguments[0].click();", dropdown_btn)
                        
                        # 3. Wait a bit again
                        log_message("Açılır menü için bekleniyor (3 saniye)...")
                        time.sleep(3.0)
                        
                        # 4. Click the bulk PDF download option
                        option_xpath = "/html/body/div[1]/div[8]/div[1]/div[2]/div/div[4]/div[2]/div/div/div/div[3]/div/a[2]"
                        pdf_option = WebDriverWait(driver, 15).until(
                            EC.element_to_be_clickable((By.XPATH, option_xpath))
                        )
                        log_message("Toplu PDF İndir seçeneğine tıklanıyor...")
                        driver.execute_script("arguments[0].click();", pdf_option)
                        
                        log_message("Toplu indirme işlemi başlatıldı. Menü sonrası bekleniyor...")
                        time.sleep(3.0)
                        
                        # Wait for overlay
                        wait_for_processing_overlay(driver)
                        
                        downloaded_file = wait_for_download_complete(DOWNLOADS_FOLDER)
                        if downloaded_file:
                            log_message(f"Fatura dosyası başarıyla indirildi: {os.path.basename(downloaded_file)}")
                            if page_selected_nos:
                                download_history.update(page_selected_nos)
                                save_download_history(download_history)
                        else:
                            log_message("Uyarı: İndirme zaman aşımına uğradı veya dosya bulunamadı.")
                    except Exception as pdf_err:
                        log_message(f"PDF indirme işlem adımları sırasında hata oluştu: {pdf_err}")
                else:
                    js_func = "download_all();"
                    if download_type == "print":
                        js_func = "print_all();"
                    elif download_type == "xml":
                        js_func = "download_all_xml_to_zip();"
                        
                    try:
                        log_message(f"Toplu indirme JS tetikleniyor: {js_func}")
                        driver.execute_script(js_func)
                        log_message("Toplu indirme JS tetiklendi, dosyanın tamamlanması bekleniyor...")
                        
                        if download_type != "print":
                            downloaded_file = wait_for_download_complete(DOWNLOADS_FOLDER)
                            if downloaded_file:
                                log_message(f"Fatura dosyası başarıyla indirildi: {os.path.basename(downloaded_file)}")
                                if page_selected_nos:
                                    download_history.update(page_selected_nos)
                                    save_download_history(download_history)
                            else:
                                log_message("Uyarı: İndirme zaman aşımına uğradı veya dosya bulunamadı.")
                        except Exception as pdf_err:
                            log_message(f"PDF indirme işlem adımları sırasında hata oluştu: {pdf_err}")
                    else:
                        js_func = "download_all();"
                        if download_type == "print":
                            js_func = "print_all();"
                        elif download_type == "xml":
                            js_func = "download_all_xml_to_zip();"
                            
                        try:
                            log_message(f"Toplu indirme JS tetikleniyor: {js_func}")
                            driver.execute_script(js_func)
                            log_message("Toplu indirme JS tetiklendi, dosyanın tamamlanması bekleniyor...")
                            
                            if download_type != "print":
                                downloaded_file = wait_for_download_complete(DOWNLOADS_FOLDER)
                                if downloaded_file:
                                    log_message(f"Fatura dosyası başarıyla indirildi: {os.path.basename(downloaded_file)}")
                                    if page_selected_nos:
                                        download_history.update(page_selected_nos)
                                        save_download_history(download_history)
                                else:
                                    log_message("Uyarı: İndirme zaman aşımına uğradı veya dosya bulunamadı.")
                            else:
                                time.sleep(5)
                                if page_selected_nos:
                                    download_history.update(page_selected_nos)
                                    save_download_history(download_history)
                        except Exception as action_err:
                            log_message(f"Toplu işlem sırasında hata oluştu: {action_err}")
                else:
                    log_message("Bu sayfada indirilecek yeni fatura bulunamadı.")
                
                # Boundary breaks based on sorting direction
                if sort_order == "asc" and all_newer_than_end:
                    log_message("Bu sayfadaki ve sonrasındaki tüm faturalar aranan bitiş tarihinden daha yeni. Tarama sonlandırılıyor.")
                    break
                elif sort_order == "desc" and all_older_than_start:
                    log_message("Bu sayfadaki ve sonrasındaki tüm faturalar aranan başlangıç tarihinden daha eski. Tarama sonlandırılıyor.")
                    break
                
                next_page_val = page_num + 1
                li_idx = page_num + 2
                page_btn_xpath = f"/html/body/div[1]/div[8]/div[1]/div[2]/div/div[6]/div/div[3]/div[2]/div/ul/li[{li_idx}]/a"
                
                next_btn = None
                try:
                    elements = driver.find_elements(By.XPATH, page_btn_xpath)
                    if elements:
                        btn = elements[0]
                        if btn.is_displayed() and btn.text.strip() == str(next_page_val):
                            next_btn = btn
                except Exception as page_err:
                    log_message(f"Sonraki sayfa ({next_page_val}) butonu kontrol edilirken hata: {page_err}")
                
                if next_btn:
                    log_message(f"Sayfa {next_page_val} butonuna tıklanıyor...")
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", next_btn)
                    time.sleep(0.5)
                    try:
                        next_btn.click()
                    except Exception:
                        driver.execute_script("arguments[0].click();", next_btn)
                    page_num += 1
                    # Save backup progress
                    save_data(BACKUPS_FILE, STATE["backups"])
                    
                    # Wait for overlay and new page data to load
                    wait_for_processing_overlay(driver)
                else:
                    log_message(f"Sayfa {next_page_val} butonu bulunamadı veya pasif. Sayfa tarama tamamlandı.")
                    break
        
        STATE["settings"]["last_download_date"] = end_date_str
        save_data(SETTINGS_FILE, STATE["settings"])
        
        # Mark session as completed
        if active_session:
            active_session["status"] = "completed"
            active_session["progress"] = 100
            active_session["last_processed_date"] = end_date_str
            save_data(BACKUPS_FILE, STATE["backups"])
        
        log_message("Fatura indirme işlemi başarıyla tamamlandı!")
        STATE["status"] = "Tamamlandı!"
        STATE["status_color"] = "#00e676"
    except Exception as e:
        handle_error(e)
