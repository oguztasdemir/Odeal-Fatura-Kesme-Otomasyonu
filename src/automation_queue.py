import time
import os

from .config import STATE, log_message, EXCEL_FOLDER, load_excel_data
from .automation_invoice import prepare_process_thread, process_products_thread

def process_queue_thread():
    try:
        STATE["stop_flag"] = False
        log_message("Çoklu Excel fatura kesme sırası başlatıldı...")
        
        for item in STATE["excel_queue"]:
            if STATE["stop_flag"]:
                log_message("Kuyruk işlemi durduruldu.")
                break
                
            if item["status"] != "Bekliyor":
                continue
                
            item["status"] = "İşleniyor"
            log_message(f"Kuyruktaki dosya işleniyor: {item['name']}")
            
            excel_path = os.path.join(EXCEL_FOLDER, item["name"])
            if not os.path.exists(excel_path):
                item["status"] = "Hata (Dosya Yok)"
                log_message(f"Hata: Dosya bulunamadı: {item['name']}")
                continue
                
            try:
                load_excel_data(excel_path)
            except Exception as load_err:
                item["status"] = f"Hata ({load_err})"
                log_message(f"Dosya okuma hatası: {item['name']} -> {load_err}")
                continue
                
            if not STATE["selected_company"]:
                item["status"] = "Hata (Firma Seçilmedi)"
                log_message(f"Hata: Fatura kesimi için seçili firma yok.")
                break
                
            try:
                log_message(f"Firma hazırlığı başlatılıyor: {STATE['selected_company']['title']}")
                prepare_process_thread()
                time.sleep(2)
                
                if STATE["prep_status"] != "Hazır":
                    item["status"] = "Hata (Hazırlık Başarısız)"
                    log_message(f"Hazırlık başarısız olduğu için işleme geçilemedi.")
                    continue
                    
                process_products_thread()
                time.sleep(3)
                
                if STATE["status"] == "Tamamlandı!":
                    item["status"] = "Tamamlandı"
                    log_message(f"Fatura başarıyla tamamlandı: {item['name']}")
                else:
                    item["status"] = "Hata (Fatura Kesilemedi)"
                    log_message(f"Fatura kesimi sırasında hata oluştu: {item['name']}")
                    
            except Exception as proc_err:
                item["status"] = "Hata"
                log_message(f"Süreç hatası ({item['name']}): {proc_err}")
                
        log_message("Çoklu Excel fatura kesme sırası tamamlandı!")
    except Exception as q_err:
        log_message(f"Kuyruk işleme hatası: {q_err}")
