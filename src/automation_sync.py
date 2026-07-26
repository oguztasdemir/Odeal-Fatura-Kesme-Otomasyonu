import time
import re
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC

from .config import STATE, log_message, save_data, COMPANIES_FILE
from .automation_core import get_or_create_driver, handle_error, find_element_safe

def sync_customers_thread():
    try:
        STATE["stop_flag"] = False
        STATE["status"] = "Müşteriler Eşitleniyor..."
        STATE["status_color"] = "#ffea00"
        STATE["session_invoices_count"] = 0
        log_message("Ödeal faturalarından hızlı cari tarama senkronizasyonu başlatıldı...")
        
        driver = get_or_create_driver()
        
        new_companies_count = 0
        seen_invoices = set()
        
        urls_to_scan = [
            "https://fatura.odeal.com/gelenfatura",
            "https://fatura.odeal.com/gonderilenfatura"
        ]
        
        for url in urls_to_scan:
            if STATE["stop_flag"]:
                break
                
            log_message(f"Sayfa taranıyor: {url}")
            driver.get(url)
            time.sleep(4)
            
            # Select 100 entries per page
            try:
                limit_select = find_element_safe(
                    driver,
                    "/html/body/div[1]/div[8]/div[1]/div[2]/div/div[6]/div/div[1]/div[1]/div/label/select",
                    [
                        "//select[contains(@name, 'table_length') or contains(@name, 'dataTable_length')]",
                        "//select[contains(@class, 'form-control')]",
                        "//select"
                    ],
                    wait_time=5
                )
                if limit_select:
                    driver.execute_script("arguments[0].value = '50'; arguments[0].dispatchEvent(new Event('change'));", limit_select)
                    log_message("Listeleme adeti JS ile 50 olarak seçildi.")
                    
                # Wait for overlay to disappear
                try:
                    WebDriverWait(driver, 15).until(
                        EC.invisibility_of_element_located((By.XPATH, "//*[contains(text(), 'İşleniyor') or contains(@class, 'processing') or contains(@id, 'processing')]"))
                    )
                except:
                    pass
                time.sleep(1.5)
            except Exception as e_limit:
                log_message(f"Listeleme adeti seçilemedi: {e_limit}")
                
            # Scan up to 5 pages
            for page in range(1, 6):
                if STATE["stop_flag"]:
                    break
                    
                log_message(f"Sayfa {page} taranıyor...")
                rows = driver.find_elements(By.XPATH, "//table[contains(@id, 'table') or contains(@class, 'table')]/tbody/tr")
                if not rows:
                    log_message("Fatura satırı bulunamadı.")
                    break
                    
                page_added = 0
                row_count = len(rows)
                for idx in range(1, row_count + 1):
                    try:
                        current_rows = driver.find_elements(By.XPATH, "//table[contains(@id, 'table') or contains(@class, 'table')]/tbody/tr")
                        if idx - 1 >= len(current_rows):
                            break
                        row = current_rows[idx - 1]
                        cells = row.find_elements(By.TAG_NAME, "td")
                        fatura_no = ""
                        for cell in cells:
                            txt = cell.text.strip()
                            match = re.search(r'\b[A-Za-z]{3}\d{13}\b', txt)
                            if match:
                                fatura_no = match.group(0).upper()
                                break
                        if fatura_no:
                            seen_invoices.add(fatura_no)
                            STATE["session_invoices_count"] = len(seen_invoices)
                            
                        if len(cells) >= 6:
                            sender_cell = cells[5]
                            cell_text = sender_cell.text.strip()
                            if cell_text:
                                vkn_match = re.search(r'\b\d{10,11}\b', cell_text)
                                if vkn_match:
                                    vkn = vkn_match.group(0)
                                    
                                    # Fast bypass: skip if company already exists in local DB
                                    existing = next((c for c in STATE["companies"] if c["tax_no"] == vkn), None)
                                    if existing:
                                        continue
                                        
                                    title = cell_text
                                    title = re.sub(r'\b\d{10,11}\b', '', title)
                                    title = re.sub(r'(?i)vkn|tckn|vergi|no|tc', '', title)
                                    title = re.sub(r'[\(\)\:\-\n\r\t]', ' ', title)
                                    title = re.sub(r'\s+', ' ', title).strip()
                                    
                                    if title and len(vkn) in [10, 11]:
                                        new_c = {
                                            "title": title[:35].strip(),
                                            "tax_no": vkn,
                                            "city": "İSTANBUL",
                                            "district": "ŞİŞLİ",
                                            "tax_office": "ŞİŞLİ",
                                            "full_name": title
                                        }
                                        STATE["companies"].append(new_c)
                                        new_companies_count += 1
                                        page_added += 1
                    except:
                        pass
                        
                if page_added > 0:
                    save_data(COMPANIES_FILE, STATE["companies"])
                    log_message(f"Bu sayfadan {page_added} yeni firma kaydedildi.")
                
                # Check for next page button
                try:
                    next_btn = find_element_safe(
                        driver,
                        "//li[contains(@class, 'next') or contains(@class, 'forward')]",
                        [
                            "//a[contains(text(), 'Sonraki') or contains(., '>')]",
                            "/html/body/div[1]/div[8]/div[1]/div[2]/div/div[6]/div/div[3]/div[2]/div/ul/li[8]"
                        ],
                        wait_time=3
                    )
                    if next_btn and "disabled" not in next_btn.get_attribute("class") and next_btn.is_displayed():
                        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", next_btn)
                        time.sleep(0.5)
                        driver.execute_script("arguments[0].click();", next_btn)
                        time.sleep(4.0)
                    else:
                        break
                except:
                    break
                    
        log_message(f"Cari tarama senkronizasyonu tamamlandı. Toplam {new_companies_count} yeni firma veritabanına eklendi!")
        STATE["status"] = "Tamamlandı!"
        STATE["status_color"] = "#00e676"
    except Exception as e:
        handle_error(e)
        STATE["status"] = "Hata Oluştu!"
        STATE["status_color"] = "#ff1744"
