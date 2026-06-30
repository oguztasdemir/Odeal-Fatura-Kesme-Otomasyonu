# Ödeal Akıllı Fatura Otomasyon Paneli (Web)

Bu proje, Ödeal e-Fatura Portalı üzerinden fatura kesme işlemlerini otomatikleştiren, yerel Excel dosyalarından veri aktarımı yapan akıllı bir otomasyon aracıdır.

> ⚠️ **ÖNEMLİ GÜVENLİK UYARISI:** Bu projeyi GitHub'a yüklerken **kesinlikle PRIVATE (ÖZEL)** depo seçeneğini kullanın. Müşteri bilgileriniz (`firmalar.json`), fatura serisi ayarlarınız (`ayarlar.json`) ve `excel_belgeleri/` altındaki fatura verileriniz `.gitignore` dosyası ile engellenmiştir ve internette herkese açık olarak paylaşılmamalıdır.

---

## 🚀 Kurulum Adımları

1. **Python Yükleme:** Bilgisayarınızda Python 3.8 veya üzeri bir sürümün yüklü olduğundan emin olun.
2. **Bağımlılıkları Yükleme:** Terminal veya Komut İstemi (CMD) üzerinden proje klasörüne gidip aşağıdaki kütüphaneleri yükleyin:
   ```bash
   pip install pandas selenium webdriver-manager openpyxl xlsxwriter
   ```
3. **Uygulamayı Başlatma:** Aşağıdaki komutla sunucuyu başlatın:
   ```bash
   python main_browser.py
   ```
4. **Tarayıcı Girişi:** Konsolda belirtilen adrese (genellikle `http://localhost:8000`) tarayıcınızdan gidin.

---

## 📂 Klasör Yapısı

* **`excel_belgeleri/`**: Fatura kesilecek Excel dosyalarını buraya yerleştirebilirsiniz. Arayüzden bu dosyaları tek tıkla ("Hızlı Excel Getir") seçip yükleyebilirsiniz.
* **`main_browser.py`**: Uygulamanın ana kaynak kodu ve web sunucu motorudur.
* **`firmalar.json`**: Tanımladığınız firmaların listesini barındırır.
* **`ayarlar.json`**: Faturanın kesileceği seri numarasının sırasını takip eder.

---

## 💡 Nasıl Çalışır?

1. **Oturum Yönetimi:** Ödeal giriş bilgilerinizi girip **Sistemi Başlat** butonuna basın (veya alanlardayken **Enter**'a basın). Telefonunuza SMS kodu geldiğinde kodu girip **Kodu Onayla** (veya **Enter**) deyin.
2. **Firma Seçimi:** Fatura keseceğiniz firmayı listeden seçin ve **Başlat** butonuna tıklayın. Sayfa otomatik olarak aşağı kayacak ve fatura başlığı hazırlanacaktır.
3. **Excel Yükleme:** Fatura kalemlerini içeren Excel dosyasını seçin (klasördeki dosyalardan hızlıca getirebilir veya bilgisayarınızdan manuel yükleyebilirsiniz). Kalemler ve KPI özetleri ekranda belirecektir.
4. **Faturaları İşle:** **Faturaları İşle** butonuna bastığınızda Selenium otomasyonu fatura kalemlerini ve iskonto oranlarını tek tek Ödeal fatura ekranına işleyecektir.
