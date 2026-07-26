# Ödeal Akıllı Fatura Otomasyon Paneli (Web)

Bu proje, Ödeal e-Fatura Portalı üzerinden fatura kesme, yedekleme ve indirme işlemlerini otomatikleştiren, yerel Excel dosyalarından veri aktarımı yapan ve gelişmiş finansal analizler sunan akıllı bir otomasyon yazılımıdır.

---

## 🚀 Öne Çıkan Özellikler

### 1. 🤖 Kurumsal Düzeyde Fatura Otomasyonu
- **Fatura Senaryoları & Türleri:** Temel/Ticari fatura senaryosu ile Satış/İade fatura türü seçeneklerini tam otomatik doldurma.
- **İade Referans Yönetimi:** Excel'den gelen orijinal fatura numarası (`iliskili_no`) ve tarihini (`iliskili_tarih`) iade faturalarına otomatik işleme.
- **Çoklu Excel Kuyruğu:** Birden fazla Excel dosyasını sıraya ekleyerek arka arkaya toplu fatura kesebilme.

### 2. 🛡️ Akıllı Hata Önleme ve Kurtarma Motorları
- **🔢 Akıllı Seri Numarası Çakışma Önleyici (Collision Prevention):** Fatura numarası çakışması veya "mükerrer numara" hatası aldığında SweetAlert uyarısını otomatik kapatır, seri numarasını ayarlarda **+1 artırır**, kaydeder ve yeni numarayla işleme devam eder.
- **📸 Hata Anında Ekran Görüntüsü (Smart Screenshots):** Fatura kesilirken hata oluştuğunda tarayıcının o anki görüntüsünü kaydeder. Kuyruk listesinde hata satırının yanındaki **"Ekranı Gör 📸"** butonu ile hatayı doğrudan panel üzerinden izleyebilirsiniz.
- **🗺️ Kendi Kendini Onaran Xpath Seçicileri (Self-Healing Xpaths):** Ödeal portalındaki butonların Xpath adresleri değişse dahi, bot metin aramalarıyla elementlerin yerini bulur ve çalışmaya devam eder.

### 3. 📊 Finansal Dashboard & Raporlama
- **KPI Kartları:** Toplam Ciro, Fatura Sayısı, Ortalama Fatura Tutarı ve Toplam Satılan Kalem sayılarını anlık gösteren KPI kartları.
- **Chart.js Grafikleri:** "Aylık Ciro Gelişimi" ve "En Çok Çalışılan Firmalar (Top 5)" interaktif çizelgeleri.
- **Excel Muhasebe Raporu:** Kesilen tüm geçmiş faturaları tek tıkla detaylı Excel dosyası olarak dışa aktarabilme.

### 4. 🗺️ Kolon Eşleştirme Sihirbazı (Dynamic Mapping)
- Excel sütun yapısına olan bağımlılığı kaldırır. Yüklediğiniz Excel'deki sütunları (Ürün, Miktar, Birim, Fiyat, KDV, İskonto) sürükle-bırak/seçim yöntemiyle eşleştirin, sistem bir sonraki yükleme için tercihlerinizi otomatik kaydeder.

### 5. 📥 Toplu Fatura Yedekleme & Cari Senkronizasyon
- **Toplu İndirme:** Tarih aralığı belirterek veya "kaldığı yerden devam et" seçeneğiyle gelen/giden faturaları toplu olarak PDF veya XML formatında ZIP arşivi halinde indirme.
- **Cari Rehber Senkronizasyonu:** Ödeal portalında kayıtlı tüm müşterilerinizi yerel veritabanınızla (`firmalar.json`) tek tıkla eşitleyin.

---

## 📂 Klasör Yapısı

* **`excel_belgeleri/`**: Sırayla işlenecek fatura Excel dosyaları.
* **`hata_ekranlari/`**: Hata anında çekilen portal ekran görüntüleri.
* **`indirilen_faturalar/`**: Toplu indirilen ZIP paketleri.
* **`yedekler/`**: Oturum ve veri dosyaları (`firmalar.json`, `ayarlar.json`, `hesaplar.json`, `cookies.json`).
* **`src/`**: Çekirdek kod yapısı:
  - `templates/`: Arayüze ait `main.html`, `style.css` ve `script.js` statik dosyaları.
  - `automation_core.py`: Chrome sürücü yöneticisi ve hata kaydedici.
  - `automation_login.py`: Oturum açma ve SMS doğrulama.
  - `automation_invoice.py`: Ürün girme ve çakışma önleyici.
  - `automation_download.py`: Fatura indirme döngüsü.
  - `automation_sync.py`: Cari kart senkronizasyonu.
  - `automation_queue.py`: Excel kuyruğu kontrolü.
  - `server.py`: API ve Web Sunucusu.
  - `html_template.py`: Şablon dosyası birleştirici.

---

## ⚙️ Kurulum Adımları

1. **Gereksinimleri Yükleyin:**
   ```bash
   pip install pandas selenium webdriver-manager openpyxl xlsxwriter
   ```
2. **Uygulamayı Başlatın:**
   ```bash
   python main_browser.py
   ```
3. **Panele Giriş Yapın:**
   Tarayıcınızdan `http://localhost:8000` adresine gidin.
