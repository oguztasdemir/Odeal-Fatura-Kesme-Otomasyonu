# Ödeal Akıllı Fatura Otomasyon Paneli (Web)

Bu proje, Ödeal e-Fatura Portalı üzerinden fatura kesme işlemlerini otomatikleştiren, yerel Excel dosyalarından veri aktarımı yapan akıllı bir otomasyon aracıdır.



## 🚀 Öne Çıkan Özellikler

- **Göz Özelliği ile Şifre Göster/Gizle:** Giriş alanlarında şifrenizi doğru yazdığınızı kontrol edebilmeniz için `👁️` / `🙈` göz özelliği eklendi.
- **Klavye Dostu Arayüz:** Alanlar arasında **Tab** tuşuyla geçiş yapabilir ve **Enter** tuşuna basarak formları hızlıca gönderebilirsiniz.
- **Güvenli Çıkış Yap Butonu:** Sol menüdeki **HESAPTAN ÇIKIŞ YAP** butonuyla tarayıcı oturumunu güvenli bir şekilde kapatabilir ve arka plandaki ChromeDriver sürecini sonlandırabilirsiniz.
- **F5 Durum Koruma (Sayfa Yenileme Desteği):** Sayfaya F5 atsanız dahi o an bulunduğunuz sekme (aktif alan) ve seçmiş olduğunuz firma bilgileri hafızada tutulmaya devam eder.
- **Otomatik Kod Yenileyici (Hot Reloading):** Projedeki dosyalarda değişiklik yaptığınızda, sunucu otomatik olarak güncel haliyle yeniden başlatılır (Klasör yolunda boşluk olması durumu dahi güvenle desteklenir).
- **Özel Arayüz Bildirimleri:** Tarayıcının üstünden çıkan rahatsız edici standart uyarı pencereleri yerine ekran içi özel tasarım bildirimler entegre edilmiştir.
- **Akıllı Hata Yönetimi & Otomatik Kurtarma:** Giriş bilgileri yanlış olduğunda tarayıcı otomatik olarak yenilenir ve temiz bir giriş ekranıyla yeniden başlamanız sağlanır.

---

## ⚙️ Kurulum Adımları

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
* **`yedekler/`**: Şifreleriniz, ayarlarınız ve firma tanımlarınız gibi tüm hassas veriler (.gitignore'a dahil şekilde) burada saklanır:
  - `firmalar.json`: Tanımladığınız firmaların listesini barındırır.
  - `ayarlar.json`: Faturanın kesileceği seri numarasının sırasını takip eder.
  - `hesaplar.json`: Manuel eklediğiniz veya başarılı giriş yaptığınız hesapların listesini barındırır.
* **`main_browser.py`**: Uygulamanın ana çalıştırma dosyası, dosya izleyicisi ve web sunucu motorudur.
* **`src/`**: Sunucu, HTML şablonları ve Selenium otomasyon betiklerinin yer aldığı çekirdek kod dizinidir.

---

## 💡 Nasıl Çalışır?

1. **Oturum Yönetimi:** Ödeal giriş bilgilerinizi girip **Sistemi Başlat** butonuna basın (veya alanlardayken **Enter**'a basın). Telefonunuza SMS kodu geldiğinde kodu girip **Kodu Onayla** (veya **Enter**) deyin.
2. **Firma Seçimi:** Fatura keseceğiniz firmayı listeden seçin ve **Başlat** butonuna tıklayın. Sayfa otomatik olarak aşağı kayacak ve fatura başlığı hazırlanacaktır.
3. **Excel Yükleme:** Fatura kalemlerini içeren Excel dosyasını seçin (klasördeki dosyalardan hızlıca getirebilir veya bilgisayarınızdan manuel yükleyebilirsiniz). Kalemler ve KPI özetleri ekranda belirecektir.
4. **Faturaları İşle:** **Faturaları İşle** butonuna bastığınızda Selenium otomasyonu fatura kalemlerini ve iskonto oranlarını tek tek Ödeal fatura ekranına işleyecektir.
