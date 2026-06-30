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
        .sidebar { width: 250px; background-color: var(--sidebar-color); padding: 30px 20px; display: flex; flex-direction: column; border-right: 1px solid var(--border-color); position: relative; z-index: 10; }
        .logo { font-size: 28px; font-weight: 700; color: var(--accent-color); margin-bottom: 30px; text-align: center; }
        .status-badge { padding: 15px; border-radius: 8px; background: rgba(255,255,255,0.05); border-left: 4px solid var(--success-color); font-weight: bold; margin-bottom: 20px; transition: all 0.3s; }
        
        /* Main Panel */
        .main-panel { flex: 1; padding: 30px; overflow-y: auto; height: 100%; position: relative; z-index: 5; }
        
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
        button.nav-btn {
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
            user-select: none;
        }
        button.nav-btn:hover { background: rgba(255, 255, 255, 0.05); color: white; }
        button.nav-btn.active { background: var(--accent-color) !important; color: white !important; }
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
        <button class="btn-secondary" style="width: 100%; margin-top: 10px; background-color: #d32f2f; color: white;" onclick="logout()">🚪 HESAPTAN ÇIKIŞ YAP</button>
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
                    <div style="position: relative; display: inline-block;">
                        <input type="password" id="password" placeholder="Şifre" style="width: 200px; padding-right: 35px;" onkeydown="if(event.key === 'Enter') startLogin()">
                        <span id="toggle-login-pass" onclick="togglePasswordVisibility('password', 'toggle-login-pass')" style="position: absolute; right: 10px; top: 50%; transform: translateY(-50%); cursor: pointer; user-select: none; font-size: 16px;">👁️</span>
                    </div>
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
                    <input type="text" id="acc-email" placeholder="E-posta Adresi" onkeydown="if(event.key === 'Enter') saveAccountManually()">
                    <div style="position: relative; width: 100%;">
                        <input type="password" id="acc-password" placeholder="Şifre" style="width: 100%; padding-right: 35px;" onkeydown="if(event.key === 'Enter') saveAccountManually()">
                        <span id="toggle-acc-pass" onclick="togglePasswordVisibility('acc-password', 'toggle-acc-pass')" style="position: absolute; right: 10px; top: 50%; transform: translateY(-50%); cursor: pointer; user-select: none; font-size: 16px;">👁️</span>
                    </div>
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

    <!-- Özel Bildirim Modalı -->
    <div id="custom-alert-modal" style="display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.6); align-items: center; justify-content: center; z-index: 1100;">
        <div class="card" style="width: 380px; text-align: center; background-color: var(--card-color); border: 2px solid var(--accent-color); padding: 30px; margin-bottom: 0;">
            <div id="custom-alert-icon" style="font-size: 40px; margin-bottom: 15px;">ℹ️</div>
            <div id="custom-alert-message" style="font-size: 15px; font-weight: 600; margin-bottom: 20px; line-height: 1.5; color: var(--text-color);"></div>
            <button class="btn-primary" style="width: 120px;" onclick="closeCustomAlert()">Tamam</button>
        </div>
    </div>

    <!-- Özel Onay Modalı -->
    <div id="custom-confirm-modal" style="display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.6); align-items: center; justify-content: center; z-index: 1100;">
        <div class="card" style="width: 400px; text-align: center; background-color: var(--card-color); border: 2px solid var(--warning-color); padding: 30px; margin-bottom: 0;">
            <div style="font-size: 40px; margin-bottom: 15px;">⚠️</div>
            <div id="custom-confirm-message" style="font-size: 15px; font-weight: 600; margin-bottom: 20px; line-height: 1.5; color: var(--text-color);"></div>
            <div class="input-group" style="justify-content: center; gap: 15px; margin-bottom: 0;">
                <button class="btn-secondary" id="custom-confirm-cancel-btn">İptal</button>
                <button class="btn-danger" id="custom-confirm-ok-btn">Evet, Onayla</button>
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

        function showCustomAlert(message, icon = 'ℹ️') {
            document.getElementById('custom-alert-message').innerText = message;
            document.getElementById('custom-alert-icon').innerText = icon;
            document.getElementById('custom-alert-modal').style.display = 'flex';
        }

        function closeCustomAlert() {
            document.getElementById('custom-alert-modal').style.display = 'none';
        }

        function showCustomConfirm(message) {
            return new Promise((resolve) => {
                document.getElementById('custom-confirm-message').innerText = message;
                document.getElementById('custom-confirm-modal').style.display = 'flex';
                
                const okBtn = document.getElementById('custom-confirm-ok-btn');
                const cancelBtn = document.getElementById('custom-confirm-cancel-btn');
                
                const newOkBtn = okBtn.cloneNode(true);
                const newCancelBtn = cancelBtn.cloneNode(true);
                okBtn.parentNode.replaceChild(newOkBtn, okBtn);
                cancelBtn.parentNode.replaceChild(newCancelBtn, cancelBtn);
                
                newOkBtn.addEventListener('click', () => {
                    document.getElementById('custom-confirm-modal').style.display = 'none';
                    resolve(true);
                });
                
                newCancelBtn.addEventListener('click', () => {
                    document.getElementById('custom-confirm-modal').style.display = 'none';
                    resolve(false);
                });
            });
        }

        function togglePasswordVisibility(inputId, toggleId) {
            const input = document.getElementById(inputId);
            const toggle = document.getElementById(toggleId);
            if (input && toggle) {
                if (input.type === 'password') {
                    input.type = 'text';
                    toggle.innerText = '🙈';
                } else {
                    input.type = 'password';
                    toggle.innerText = '👁️';
                }
            }
        }

        function updateStatus() {
            fetch('/api/status')
                .then(r => {
                    if (!r.ok) throw new Error("HTTP error " + r.status);
                    return r.json();
                })
                .then(data => {
                    try {
                        const statusBadge = document.getElementById('system-status');
                        if (statusBadge) {
                            statusBadge.innerText = '● ' + (data.status || '');
                            statusBadge.style.borderLeftColor = data.status_color || '';
                        }

                        // Update login message status
                        const statusMsgDiv = document.getElementById('login-status-message');
                        if (statusMsgDiv) {
                            if (data.login_message) {
                                statusMsgDiv.innerText = data.login_message;
                                statusMsgDiv.style.color = data.login_message_color || '';
                                statusMsgDiv.style.display = 'block';
                            } else {
                                statusMsgDiv.style.display = 'none';
                            }
                        }

                        // Update logs
                        const logsContainer = document.getElementById('logs-container');
                        if (logsContainer && data.logs) {
                            logsContainer.innerHTML = data.logs.map(log => `<div class="log-line">${log}</div>`).join('');
                            logsContainer.scrollTop = logsContainer.scrollHeight;
                        }

                        // Update auth UI steps
                        const loginFields = document.getElementById('login-fields');
                        const codeFields = document.getElementById('code-fields');
                        if (data.auth_step === 'login') {
                            if (loginFields) loginFields.style.display = 'flex';
                            if (codeFields) codeFields.style.display = 'none';
                        } else if (data.auth_step === 'code') {
                            if (loginFields) loginFields.style.display = 'none';
                            if (codeFields) codeFields.style.display = 'flex';
                        } else if (data.auth_step === 'confirmed') {
                            if (loginFields) loginFields.style.display = 'none';
                            if (codeFields) codeFields.style.display = 'none';
                        }

                        // Update prep button state
                        const prepBtn = document.getElementById('prep-btn');
                        if (prepBtn) {
                            prepBtn.innerText = data.prep_status || '';
                            prepBtn.style.backgroundColor = data.prep_btn_color || '';
                            
                            if (data.auth_step === 'confirmed' && data.selected_company && data.prep_status !== 'Hazırlanıyor...') {
                                prepBtn.disabled = false;
                            } else {
                                prepBtn.disabled = true;
                            }
                        }

                        // Update process button state
                        const processBtn = document.getElementById('process-btn');
                        if (processBtn) {
                            if (data.prep_status === 'Hazır' && data.excel_table && data.excel_table.length > 0) {
                                processBtn.disabled = false;
                            } else {
                                processBtn.disabled = true;
                            }
                        }

                        // Update Excel UI Table & KPIs
                        const tbody = document.getElementById('excel-tbody');
                        if (tbody) {
                            if (data.excel_table && data.excel_table.length > 0) {
                                tbody.innerHTML = data.excel_table.map(row => `
                                    <tr>
                                        <td>${row['urun'] || ''}</td>
                                        <td>${row['miktar'] || ''}</td>
                                        <td>${row['birim'] || ''}</td>
                                        <td>${row['fiyat'] || ''}</td>
                                        <td>${row['kdv'] || ''}</td>
                                        <td>${row['iskonto'] || ''}</td>
                                    </tr>
                                `).join('');
                            } else {
                                tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; color: gray;">Henüz veri yüklenmedi</td></tr>`;
                            }
                        }

                        if (data.kpis) {
                            const kalem = document.getElementById('kpi-kalem');
                            const miktar = document.getElementById('kpi-miktar');
                            const kdvsiz = document.getElementById('kpi-kdvsiz');
                            const iskonto = document.getElementById('kpi-iskonto');
                            const toplam = document.getElementById('kpi-toplam');
                            if (kalem) kalem.innerText = data.kpis.kalem ?? 0;
                            if (miktar) miktar.innerText = data.kpis.miktar ?? 0;
                            if (kdvsiz) kdvsiz.innerText = data.kpis.kdvsiz ?? 0;
                            if (iskonto) iskonto.innerText = data.kpis.iskonto ?? 0;
                            if (toplam) toplam.innerText = data.kpis.toplam ?? 0;
                        }

                        // Restore selected company details on screen refresh
                        const compSelect = document.getElementById('company-select');
                        if (compSelect && data.selected_company) {
                            compSelect.value = data.selected_company.title;
                            const taxNo = document.getElementById('lbl-tax-no');
                            const city = document.getElementById('lbl-city');
                            const dist = document.getElementById('lbl-district');
                            const office = document.getElementById('lbl-tax-office');
                            const fullname = document.getElementById('lbl-fullname');
                            
                            if (taxNo) taxNo.innerText = data.selected_company.tax_no || '-';
                            if (city) city.innerText = data.selected_company.city || '-';
                            if (dist) dist.innerText = data.selected_company.district || '-';
                            if (office) office.innerText = data.selected_company.tax_office || '-';
                            if (fullname) fullname.innerText = data.selected_company.full_name || '-';
                        }
                    } catch (innerErr) {
                        console.error("Error processing status data:", innerErr);
                    }
                })
                .catch(err => {
                    console.warn("Status fetch failed:", err);
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
            try {
                localStorage.setItem('activeSection', sectionId);
                // Hide all sections
                const panel = document.getElementById('section-panel');
                const accounts = document.getElementById('section-accounts');
                const settings = document.getElementById('section-settings');
                
                if (panel) panel.style.display = 'none';
                if (accounts) accounts.style.display = 'none';
                if (settings) settings.style.display = 'none';

                // Show current section
                const target = document.getElementById('section-' + sectionId);
                if (target) {
                    target.style.display = 'block';
                }

                // Update active class on nav buttons
                document.querySelectorAll('.nav-btn').forEach(btn => btn.classList.remove('active'));
                const navBtn = document.getElementById('nav-' + sectionId);
                if (navBtn) {
                    navBtn.classList.add('active');
                }
            } catch (e) {
                console.error("switchSection error:", e);
            }
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
                showCustomAlert('Lütfen e-posta ve şifre girin.', '⚠️');
                return;
            }
            fetch('/api/save_account', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email, password })
            })
            .then(res => {
                if (!res.ok) throw new Error("HTTP error " + res.status);
                document.getElementById('acc-email').value = '';
                document.getElementById('acc-password').value = '';
                loadAccounts();
                showCustomAlert('Hesap başarıyla kaydedildi/güncellendi.', '✅');
            })
            .catch(err => {
                console.error("Save account error:", err);
                showCustomAlert("Hesap kaydedilemedi: " + err.message, '❌');
            });
        }

        async function deleteAccount(email) {
            const confirmed = await showCustomConfirm(email + ' hesabını silmek istediğinize emin misiniz?');
            if (!confirmed) return;
            fetch('/api/delete_account', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email })
            }).then(() => {
                loadAccounts();
            });
        }

        async function resetAccountsData() {
            const confirmed = await showCustomConfirm('KAYITLI TÜM HESAPLARI SİLMEK istediğinize emin misiniz?\\nFirma verileriniz silinmeyecektir.');
            if (!confirmed) return;
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

        function logout() {
            showCustomConfirm('Hesaptan çıkış yapmak ve tarayıcıyı kapatmak istediğinize emin misiniz?').then(confirmed => {
                if (confirmed) {
                    fetch('/api/logout', { method: 'POST' }).then(res => {
                        if (res.ok) {
                            showCustomAlert('Hesaptan başarıyla çıkış yapıldı ve tarayıcı kapatıldı.', '🚪');
                        } else {
                            showCustomAlert('Çıkış yapılırken bir hata oluştu.', '❌');
                        }
                    });
                }
            });
        }

        // Init Theme
        let activeTheme = 'dark';
        try {
            activeTheme = localStorage.getItem('theme') || 'dark';
        } catch (e) {}
        setTheme(activeTheme);

        // Init Section
        try {
            let activeSec = localStorage.getItem('activeSection') || 'panel';
            switchSection(activeSec);
        } catch (e) {}

        loadCompanies();
        loadLocalExcelFiles();
        loadAccounts();
    </script>
</body>
</html>
"""
