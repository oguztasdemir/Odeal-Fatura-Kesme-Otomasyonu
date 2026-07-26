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

let isConfirmed = false;
let session_terminated_alerted = false;
let lastExcelTableStr = "";
let currentBackups = [];
let selectedBackupSessionId = null;

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

                // Update live counters
                const counterInvoices = document.getElementById('counter-invoices');
                if (counterInvoices) {
                    counterInvoices.innerText = `Fatura: ${data.session_invoices_count || 0}`;
                }
                const counterCompanies = document.getElementById('counter-companies');
                if (counterCompanies) {
                    counterCompanies.innerText = `Firma: ${data.companies ? data.companies.length : 0}`;
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
                
                const loginLogsContainer = document.getElementById('login-logs-container');
                if (loginLogsContainer && data.logs) {
                    loginLogsContainer.innerHTML = data.logs.map(log => `<div class="log-line">${log}</div>`).join('');
                    loginLogsContainer.scrollTop = loginLogsContainer.scrollHeight;
                }

                // Update auth UI steps
                const loginFields = document.getElementById('login-fields');
                const codeFields = document.getElementById('code-fields');
                if (data.auth_step === 'login' || data.auth_step === 'code') {
                    document.body.classList.add('not-logged-in');
                    const loginSection = document.getElementById('section-login');
                    if (loginSection) loginSection.style.display = 'block';
                    
                    // Hide all other sections in main-panel
                    document.querySelectorAll('.main-panel > div').forEach(div => {
                        if (div.id && div.id !== 'section-login') {
                            div.style.display = 'none';
                        }
                    });
                    
                    if (data.auth_step === 'login') {
                        if (loginFields) loginFields.style.display = 'flex';
                        if (codeFields) codeFields.style.display = 'none';
                        const loginBtn = document.getElementById('login-btn');
                        if (loginBtn && loginBtn.innerText === 'Sistem Başlatılıyor...' && data.status === 'Hata Oluştu') {
                            loginBtn.disabled = false;
                            loginBtn.innerText = 'Sistemi Başlat / Giriş Yap';
                        } else if (loginBtn && loginBtn.innerText !== 'Sistem Başlatılıyor...') {
                            loginBtn.disabled = false;
                            loginBtn.innerText = 'Sistemi Başlat / Giriş Yap';
                        }
                    } else {
                        if (loginFields) loginFields.style.display = 'none';
                        if (codeFields) codeFields.style.display = 'flex';
                        const loginBtn = document.getElementById('login-btn');
                        if (loginBtn) {
                            loginBtn.disabled = false;
                            loginBtn.innerText = 'Sistemi Başlat / Giriş Yap';
                        }
                        const confirmBtn = document.getElementById('confirm-code-btn');
                        if (confirmBtn) {
                            if (data.status === 'Doğrulama Bekleniyor') {
                                confirmBtn.disabled = false;
                                confirmBtn.innerText = 'Kodu Onayla';
                            } else if (data.status === 'Doğrulama Yapılıyor...') {
                                confirmBtn.disabled = true;
                                confirmBtn.innerText = 'onaylama kodu deneniyor...';
                            }
                        }
                    }
                } else if (data.auth_step === 'confirmed') {
                    document.body.classList.remove('not-logged-in');
                    const loginSection = document.getElementById('section-login');
                    if (loginSection) loginSection.style.display = 'none';
                    if (loginFields) loginFields.style.display = 'none';
                    if (codeFields) codeFields.style.display = 'none';
                    
                    // Restore active section
                    const activeSec = localStorage.getItem('activeSection') || 'panel';
                    const targetSec = document.getElementById('section-' + activeSec);
                    if (targetSec && targetSec.style.display === 'none') {
                        switchSection(activeSec);
                    }
                }

                // Lock/unlock access
                const newConfirmed = (data.auth_step === 'confirmed');
                if (newConfirmed) {
                    session_terminated_alerted = false;
                }
                if (isConfirmed && !newConfirmed && !session_terminated_alerted) {
                    session_terminated_alerted = true;
                    showCustomAlert('Oturum Sonlandırıldı! Arka plandaki tarayıcı oturumu kapatıldı veya sonlandırıldı. Lütfen sistemi yeniden başlatıp tekrar giriş yapın.', '⚠️');
                    showSection('accounts');
                }
                isConfirmed = newConfirmed;
                
                document.getElementById('nav-panel').disabled = !isConfirmed;
                document.getElementById('nav-download').disabled = !isConfirmed;
                document.getElementById('nav-downloads-list').disabled = !isConfirmed;
                document.getElementById('nav-history').disabled = !isConfirmed;
                document.getElementById('nav-companies-list').disabled = !isConfirmed;
                document.getElementById('nav-accounts').disabled = !isConfirmed;
                document.getElementById('nav-settings').disabled = !isConfirmed;

                // TÜMÜNÜ DURDUR button active state control
                const stopBtn = document.querySelector("button[onclick='stopProcess()']");
                if (stopBtn) {
                    const finishedStates = ["Sistem Hazır", "Tamamlandı!", "Hata Oluştu", "Giriş Bekleniyor...", "Oturum Kapatıldı", "Giriş yapılması bekleniyor..."];
                    const isRunning = !finishedStates.includes(data.status);
                    stopBtn.disabled = !isRunning;
                }

                if (!isConfirmed) {
                    const sections = ['panel', 'download', 'downloads-list', 'history', 'companies-list', 'accounts', 'settings'];
                    sections.forEach(s => {
                        const el = document.getElementById('section-' + s);
                        if (el) el.style.display = 'none';
                        const btn = document.getElementById('nav-' + s);
                        if (btn) btn.classList.remove('active');
                    });
                    const loginSec = document.getElementById('section-login');
                    if (loginSec) loginSec.style.display = 'block';
                } else {
                    const loginSec = document.getElementById('section-login');
                    if (loginSec) loginSec.style.display = 'none';
                    
                    let activeSection = localStorage.getItem('activeSection');
                    if (!activeSection || activeSection === 'login') {
                        activeSection = 'panel';
                        localStorage.setItem('activeSection', 'panel');
                    }
                    const activeEl = document.getElementById('section-' + activeSection);
                    if (activeEl && activeEl.style.display === 'none') {
                        switchSection(activeSection);
                    }
                }

                // Load settings values if user is not typing
                const settingPrefix = document.getElementById('setting-serial-prefix');
                const settingSerial = document.getElementById('setting-serial');
                const settingMode = document.getElementById('setting-finalization-mode');
                const settingScenario = document.getElementById('setting-invoice-scenario');
                const settingType = document.getElementById('setting-invoice-type');
                
                if (data.settings) {
                    if (settingPrefix && document.activeElement !== settingPrefix) {
                        settingPrefix.value = data.settings.serial_prefix || 'YRN';
                    }
                    if (settingSerial && document.activeElement !== settingSerial) {
                        settingSerial.value = data.settings.serial || '';
                    }
                    if (settingMode && document.activeElement !== settingMode) {
                        settingMode.value = data.settings.finalization_mode || 'manual';
                    }
                    if (settingScenario && document.activeElement !== settingScenario) {
                        settingScenario.value = data.settings.invoice_scenario || 'TEMEL';
                    }
                    if (settingType && document.activeElement !== settingType) {
                        settingType.value = data.settings.invoice_type || 'SATIS';
                    }
                }

                // Update queue tbody
                const queueTbody = document.getElementById('queue-tbody');
                const queueContainer = document.getElementById('queue-container');
                if (queueTbody && queueContainer) {
                    if (data.excel_queue && data.excel_queue.length > 0) {
                        queueContainer.style.display = 'block';
                        queueTbody.innerHTML = data.excel_queue.map(item => {
                            let statusColor = 'gray';
                            if (item.status === 'Bekliyor') statusColor = 'orange';
                            else if (item.status === 'İşleniyor') statusColor = 'var(--accent-color)';
                            else if (item.status === 'Tamamlandı') statusColor = 'var(--success-color)';
                            else if (item.status.startsWith('Hata')) statusColor = 'var(--danger-color)';
                            
                             let screenshotBtn = '';
                             if (item.error_screenshot) {
                                 screenshotBtn = `<button class="btn-danger" style="padding: 2px 6px; font-size: 11px; margin-left: 10px; border-radius: 4px; display: inline-flex; align-items: center; gap: 4px;" onclick="viewErrorScreenshot('${item.error_screenshot}')">Ekranı Gör 📸</button>`;
                             }
                             
                             return `
                                 <tr>
                                     <td style="font-weight: 600;">${item.name}</td>
                                     <td style="text-align: center; color: ${statusColor}; font-weight: 600; display: flex; align-items: center; justify-content: center;">
                                         <span>${item.status}</span>
                                         ${screenshotBtn}
                                     </td>
                                 </tr>
                             `;
                        }).join('');
                    } else {
                        queueContainer.style.display = 'none';
                    }
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
                        tbody.innerHTML = data.excel_table.map((row, idx) => {
                            const isMiktarValid = !isNaN(parseFloat(row['miktar'])) && parseFloat(row['miktar']) >= 0;
                            const isFiyatValid = !isNaN(parseFloat(row['fiyat'])) && parseFloat(row['fiyat']) >= 0;
                            const isKdvValid = ['0', '1', '10', '20'].includes(String(row['kdv']).trim());
                            
                            return `
                                <tr>
                                    <td contenteditable="true" onblur="updateExcelCell(${idx}, 'urun', this.innerText)" style="outline: none;">${row['urun'] || ''}</td>
                                    <td contenteditable="true" onblur="updateExcelCell(${idx}, 'miktar', this.innerText)" style="outline: none; ${isMiktarValid ? '' : 'background-color: rgba(255, 23, 68, 0.25); border: 1px solid var(--danger-color) !important;'}">${row['miktar'] || ''}</td>
                                    <td contenteditable="true" onblur="updateExcelCell(${idx}, 'birim', this.innerText)" style="outline: none;">${row['birim'] || ''}</td>
                                    <td contenteditable="true" onblur="updateExcelCell(${idx}, 'fiyat', this.innerText)" style="outline: none; ${isFiyatValid ? '' : 'background-color: rgba(255, 23, 68, 0.25); border: 1px solid var(--danger-color) !important;'}">${row['fiyat'] || ''}</td>
                                    <td contenteditable="true" onblur="updateExcelCell(${idx}, 'kdv', this.innerText)" style="outline: none; ${isKdvValid ? '' : 'background-color: rgba(255, 23, 68, 0.25); border: 1px solid var(--danger-color) !important;'}">${row['kdv'] || ''}</td>
                                    <td contenteditable="true" onblur="updateExcelCell(${idx}, 'iskonto', this.innerText)" style="outline: none;">${row['iskonto'] || ''}</td>
                                </tr>
                            `;
                        }).join('');
                    } else {
                        tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; color: gray;">Henüz veri yüklenmedi</td></tr>`;
                    }
                }

                // Trigger Chart updates
                const currentExcelTableStr = JSON.stringify(data.excel_table || []);
                if (currentExcelTableStr !== lastExcelTableStr) {
                    lastExcelTableStr = currentExcelTableStr;
                    updateCharts(data.excel_table);
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

                // Update download logs
                const dlLogsContainer = document.getElementById('download-logs-container');
                if (dlLogsContainer && data.logs) {
                    dlLogsContainer.innerHTML = data.logs.map(log => `<div class="log-line">${log}</div>`).join('');
                    dlLogsContainer.scrollTop = dlLogsContainer.scrollHeight;
                }

                // Update last download date from settings
                if (data.settings) {
                    const lastDlDate = document.getElementById('lbl-last-dl-date');
                    if (lastDlDate) {
                        lastDlDate.innerText = data.settings.last_download_date || '-';
                    }
                }

                // Update backups list
                const backupsList = document.getElementById('backup-sessions-list');
                if (backupsList && data.backups) {
                    currentBackups = data.backups;
                    if (data.backups.length === 0) {
                        backupsList.innerHTML = `<div style="font-size: 12px; color: gray; text-align: center; padding: 20px;">Henüz aktif yedekleme oturumu yok.</div>`;
                    } else {
                        backupsList.innerHTML = data.backups.map(session => {
                            const isCompleted = session.status === 'completed';
                            const badgeColor = isCompleted ? '#00e676' : 'var(--warning-color)';
                            const badgeTextColor = '#000';
                            const badgeText = isCompleted ? 'Tamamlandı' : `%${session.progress} tamamlandı`;
                            const directionText = session.direction === 'giden' ? 'Giden' : 'Gelen';
                            const typeText = session.download_type.toUpperCase();
                            
                            const displayName = session.name || `${directionText} (${typeText})`;
                            const subtitle = session.name ? `${directionText} (${typeText}) | ` : '';
                            
                            let progressInfo = '';
                            if (!isCompleted) {
                                progressInfo = `<div style="font-size: 10px; color: #00bcd4;">Kaldığı yer: ${session.last_processed_date}</div>`;
                            }
                            
                            const isActive = session.id === selectedBackupSessionId;
                            const activeBorder = isActive ? '; border-color: var(--accent-color) !important; box-shadow: 0 0 10px rgba(67,97,238,0.2)' : '';
                            
                            return `
                                <div class="backup-session-item" style="background: #1e1e24; border: 1px solid #333; border-radius: 6px; padding: 10px; display: flex; flex-direction: column; gap: 4px; position: relative; transition: border-color 0.2s${activeBorder}" onmouseover="this.style.borderColor='var(--accent-color)'" onmouseout="this.style.borderColor='${isActive ? 'var(--accent-color)' : '#333'}'">
                                    <div style="display: flex; justify-content: space-between; align-items: center; font-size: 12px; margin-bottom: 2px;">
                                        <span style="font-weight: 600; color: #fff; cursor: pointer; flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" onclick="loadBackupSession('${session.id}')">${displayName}</span>
                                        <div style="display: flex; gap: 8px; align-items: center; z-index: 10; margin-left: 8px;">
                                            <span style="cursor: pointer; font-size: 12px;" title="Adlandır" onclick="renameBackupSession('${session.id}', event)">✏️</span>
                                            <span style="cursor: pointer; font-size: 12px; color: var(--danger-color);" title="Sil" onclick="deleteBackupSession('${session.id}', event)">🗑️</span>
                                        </div>
                                    </div>
                                    <div onclick="loadBackupSession('${session.id}')" style="cursor: pointer; display: flex; flex-direction: column; gap: 4px;">
                                        <div style="display: flex; justify-content: space-between; align-items: center; font-size: 11px;">
                                            <span style="color: gray;">${subtitle}Tarih: ${session.start_date} - ${session.end_date}</span>
                                            <span class="badge" style="background-color: ${badgeColor}; color: ${badgeTextColor}; font-size: 9px; font-weight: 600; padding: 1px 4px; border-radius: 3px;">${badgeText}</span>
                                        </div>
                                        ${progressInfo}
                                    </div>
                                </div>
                            `;
                        }).reverse().join('');
                    }
                }

                // Update companies filter dropdown
                const companyFilter = document.getElementById('dl-company-filter');
                if (companyFilter && data.companies) {
                    const currentVal = companyFilter.value;
                    let html = '<option value="">Tüm Firmalar</option>';
                    data.companies.forEach(c => {
                        html += `<option value="${c.tax_no}">${c.title}</option>`;
                    });
                    companyFilter.innerHTML = html;
                    companyFilter.value = currentVal;
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
    const loginBtn = document.getElementById('login-btn');
    if (loginBtn) {
        loginBtn.disabled = true;
        loginBtn.innerText = 'Sistem Başlatılıyor...';
    }
    fetch('/api/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password })
    });
}

// Auto-refresh loops
setInterval(updateStatus, 1000);

function confirmCode() {
    const code = document.getElementById('auth-code').value.trim();
    if (code.length !== 6) {
        return;
    }
    const btn = document.getElementById('confirm-code-btn');
    if (btn) {
        btn.disabled = true;
        btn.innerText = 'onaylama kodu deneniyor...';
    }
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

function reloadCode() {
    showCustomAlert('Sistem kodları güncelleniyor...', '🔄');
    fetch('/api/reload_code', { method: 'POST' })
        .then(res => {
            if (res.ok) {
                showCustomAlert('Sistem kodları başarıyla güncellendi!', '✅');
            } else {
                showCustomAlert('Kod güncelleme sırasında hata oluştu.', '❌');
            }
        })
        .catch(err => {
            showCustomAlert('Bağlantı hatası: ' + err, '❌');
        });
}

function loadBackupSession(sessionId) {
    const session = currentBackups.find(b => b.id === sessionId);
    if (!session) return;
    
    selectedBackupSessionId = sessionId;
    updateStatus(); // Refresh borders in UI
    
    const directionSelect = document.getElementById('dl-direction');
    if (directionSelect) directionSelect.value = session.direction;
    
    const filterInput = document.getElementById('dl-filter-query');
    if (filterInput) filterInput.value = session.filter_query || '';
    
    const typeSelect = document.getElementById('dl-type');
    if (typeSelect) typeSelect.value = session.download_type;
    
    const sortSelect = document.getElementById('dl-sort-order');
    if (sortSelect) sortSelect.value = session.sort_order || 'asc';
    
    const allScratchCheck = document.getElementById('dl-all-scratch');
    
    if (session.status === 'completed') {
        if (allScratchCheck) allScratchCheck.checked = false;
        
        const startDateInput = document.getElementById('dl-start-date');
        const endDateInput = document.getElementById('dl-end-date');
        if (startDateInput) startDateInput.value = session.start_date;
        if (endDateInput) endDateInput.value = session.end_date;
    } else {
        if (allScratchCheck) allScratchCheck.checked = false;
        
        const startDateInput = document.getElementById('dl-start-date');
        const endDateInput = document.getElementById('dl-end-date');
        if (startDateInput) startDateInput.value = session.last_processed_date;
        if (endDateInput) endDateInput.value = session.end_date;
    }
    
    showCustomAlert('Yedekleme oturumu parametreleri yüklendi. Kaldığı yerden devam etmek için "Bul ve İndirmeyi Başlat" butonuna basın.', '📥');
}

function renameBackupSession(sessionId, event) {
    if (event) event.stopPropagation();
    const session = currentBackups.find(b => b.id === sessionId);
    if (!session) return;
    
    const oldName = session.name || '';
    const newName = prompt('Yedek oturumu için yeni bir isim girin:', oldName);
    if (newName === null) return;
    
    fetch('/api/backups/rename', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id: sessionId, name: newName.trim() })
    }).then(res => {
        if (res.ok) {
            showCustomAlert('Yedek oturumu başarıyla adlandırıldı!', '✅');
            updateStatus();
        } else {
            showCustomAlert('Yedek adlandırılırken hata oluştu.', '❌');
        }
    }).catch(err => {
        showCustomAlert('Bağlantı hatası: ' + err, '❌');
    });
}

function deleteBackupSession(sessionId, event) {
    if (event) event.stopPropagation();
    
    showCustomConfirm('Bu yedekleme oturumunu silmek istediğinize emin misiniz? (İndirilen dosyalar silinmez)').then(confirmed => {
        if (confirmed) {
            fetch('/api/backups/delete', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ id: sessionId })
            }).then(res => {
                if (res.ok) {
                    showCustomAlert('Yedek oturumu silindi.', '🗑️');
                    updateStatus();
                } else {
                    showCustomAlert('Yedek silinirken hata oluştu.', '❌');
                }
            }).catch(err => {
                showCustomAlert('Bağlantı hatası: ' + err, '❌');
            });
        }
    });
}

// Override startInvoiceDownload to pass filter query and sort order
function startInvoiceDownload() {
    const allScratch = document.getElementById('dl-all-scratch').checked;
    const dlType = document.getElementById('dl-type').value;
    const filterQuery = document.getElementById('dl-filter-query').value;
    const direction = document.getElementById('dl-direction').value;
    const sortOrder = document.getElementById('dl-sort-order').value;
    
    let startDate = '';
    let endDate = '';
    
    if (allScratch) {
        startDate = '2020-01-01'; // Default starting date for full download
        const today = new Date();
        endDate = today.toISOString().split('T')[0];
    } else {
        startDate = document.getElementById('dl-start-date').value;
        endDate = document.getElementById('dl-end-date').value;
    }
    
    if (!startDate || !endDate) {
        showCustomAlert('Lütfen geçerli başlangıç ve bitiş tarihleri seçiniz.', '⚠️');
        return;
    }
    
    showCustomAlert('Fatura indirme işlemi arka planda başlatıldı. İlerleme durumunu aşağıdaki loglardan takip edebilirsiniz.', 'ℹ️');
    
    fetch('/api/download_invoices', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            start_date: startDate,
            end_date: endDate,
            download_type: dlType,
            filter_query: filterQuery,
            direction: direction,
            sort_order: sortOrder,
            session_id: selectedBackupSessionId
        })
    });
}

function clearSelectedBackupSession() {
    selectedBackupSessionId = null;
    document.getElementById('dl-filter-query').value = '';
    document.getElementById('dl-start-date').value = '';
    document.getElementById('dl-end-date').value = '';
    updateStatus(); // Update border colors instantly
    showCustomAlert('Yedekleme oturumu seçimi sıfırlandı. Yeni bir yedekleme başlatabilirsiniz.', 'ℹ️');
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

// Sequential Excel Uploader
function uploadExcel() {
    const fileInput = document.getElementById('excel-file');
    if (fileInput.files.length === 0) return;
    
    showCustomAlert(`${fileInput.files.length} adet Excel sıraya yükleniyor...`, 'ℹ️');
    
    const uploadPromises = [];
    for (let i = 0; i < fileInput.files.length; i++) {
        const formData = new FormData();
        formData.append('file', fileInput.files[i]);
        
        const promise = fetch('/api/upload_excel', {
            method: 'POST',
            body: formData
        });
        uploadPromises.push(promise);
    }
    
    Promise.all(uploadPromises).then(() => {
        fileInput.value = "";
        showCustomAlert('Dosyalar sıraya başarıyla eklendi.', '✅');
        updateStatus();
    });
}

function showMappingModal(filename, headers, defaultMapping) {
    document.getElementById('mapped-filename').value = filename;
    
    const fields = ['urun', 'miktar', 'birim', 'fiyat', 'kdv', 'iskonto', 'iliskili_no', 'iliskili_tarih'];
    const selectIds = {
        'urun': 'map-urun',
        'miktar': 'map-miktar',
        'birim': 'map-birim',
        'fiyat': 'map-fiyat',
        'kdv': 'map-kdv',
        'iskonto': 'map-iskonto',
        'iliskili_no': 'map-iliskili-no',
        'iliskili_tarih': 'map-iliskili-tarih'
    };
    
    fields.forEach(field => {
        const select = document.getElementById(selectIds[field]);
        select.innerHTML = '<option value="">(Varsayılan / Boş)</option>' + 
            headers.map(h => `<option value="${h}">${h}</option>`).join('');
        
        let matched = false;
        const defVal = defaultMapping ? defaultMapping[field] : '';
        if (defVal && headers.includes(defVal)) {
            select.value = defVal;
            matched = true;
        }
        
        if (!matched) {
            const keywords = {
                'urun': ['ürün', 'hizmet', 'name', 'title', 'açıklama', 'aciklama', 'urun'],
                'miktar': ['miktar', 'adet', 'qty', 'quantity', 'mıktar'],
                'birim': ['birim', 'unit', 'ölçü', 'olcu'],
                'fiyat': ['fiyat', 'price', 'tutar', 'birim fiyat', 'rate'],
                'kdv': ['kdv', 'tax', 'kdv oranı', 'kdv orani'],
                'iskonto': ['iskonto', 'indirim', 'discount'],
                'iliskili_no': ['ilişkili fatura', 'iade no', 'orijinal fatura', 'belge no', 'referans no', 'fatura no', 'iliskili'],
                'iliskili_tarih': ['ilişkili tarih', 'iade tarihi', 'belge tarihi', 'referans tarih', 'fatura tarihi', 'iliskili_tarih']
            };
            
            for (let h of headers) {
                const hLower = h.toLowerCase();
                if (keywords[field].some(kw => hLower.includes(kw))) {
                    select.value = h;
                    break;
                }
            }
        }
    });
    
    document.getElementById('excel-mapping-modal').style.display = 'flex';
}

function closeMappingModal() {
    document.getElementById('excel-mapping-modal').style.display = 'none';
}

function submitExcelMapping() {
    const filename = document.getElementById('mapped-filename').value;
    const mapping = {
        'urun': document.getElementById('map-urun').value,
        'miktar': document.getElementById('map-miktar').value,
        'birim': document.getElementById('map-birim').value,
        'fiyat': document.getElementById('map-fiyat').value,
        'kdv': document.getElementById('map-kdv').value,
        'iskonto': document.getElementById('map-iskonto').value,
        'iliskili_no': document.getElementById('map-iliskili-no').value,
        'iliskili_tarih': document.getElementById('map-iliskili-tarih').value
    };
    
    fetch('/api/load_mapped_excel', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ filename, mapping })
    })
    .then(r => r.json())
    .then(res => {
        closeMappingModal();
        updateStatus();
        showCustomAlert("Excel başarıyla kolon eşleştirmesine göre yüklendi!", "✅");
    })
    .catch(err => {
        showCustomAlert("Eşleştirme yüklenirken hata oluştu: " + err, "⚠️");
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

function switchSection(sectionId) {
    if (!isConfirmed && sectionId !== 'login') {
        return;
    }
    try {
        localStorage.setItem('activeSection', sectionId);
        const loginSec = document.getElementById('section-login');
        const panel = document.getElementById('section-panel');
        const download = document.getElementById('section-download');
        const downloadsList = document.getElementById('section-downloads-list');
        const historySec = document.getElementById('section-history');
        const companiesListSec = document.getElementById('section-companies-list');
        const accounts = document.getElementById('section-accounts');
        const settings = document.getElementById('section-settings');
        
        if (loginSec) loginSec.style.display = 'none';
        if (panel) panel.style.display = 'none';
        if (download) download.style.display = 'none';
        if (downloadsList) downloadsList.style.display = 'none';
        if (historySec) historySec.style.display = 'none';
        if (companiesListSec) companiesListSec.style.display = 'none';
        if (accounts) accounts.style.display = 'none';
        if (settings) settings.style.display = 'none';

        const target = document.getElementById('section-' + sectionId);
        if (target) {
            target.style.display = 'block';
        }
        
        if (sectionId === 'downloads-list') {
            loadDownloadsList();
        } else if (sectionId === 'history') {
            loadHistoryList();
        } else if (sectionId === 'companies-list') {
            loadCompaniesTable();
        }

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
            const savedSelect = document.getElementById('saved-accounts-select');
            savedSelect.innerHTML = '<option value="">Kayıtlı Hesap Seç...</option>' + 
                accounts.map(acc => `<option value="${acc.email}">${acc.email}</option>`).join('');

            const accountsList = document.getElementById('saved-accounts-list');
            if (accounts.length === 0) {
                accountsList.innerHTML = '<div style="color: gray; font-style: italic;">Henüz kayıtlı hesap yok. Başarılı giriş yaptığınızda otomatik olarak kaydedilir.</div>';
            } else {
                accountsList.innerHTML = accounts.map(acc => {
                    const has2fa = acc.two_factor_secret && acc.two_factor_secret.trim() ? 
                        '<span style="color: var(--success-color); font-weight: bold;">(2FA Aktif 🔒)</span>' : 
                        '<span style="color: var(--warning-color);">(2FA Pasif 🔓)</span>';
                    return `
                        <div style="background: rgba(255,255,255,0.03); border: 1px solid var(--border-color); padding: 15px; border-radius: 8px; display: flex; align-items: center; justify-content: space-between;">
                            <div style="display: flex; flex-direction: column; gap: 5px;">
                                <span style="font-weight: 600; font-size: 14px; color: var(--accent-color);">${acc.email}</span>
                                <span style="font-size: 11px; color: gray;">Şifre: •••••••• | ${has2fa}</span>
                            </div>
                            <div style="display: flex; gap: 10px;">
                                <button class="btn-primary" style="padding: 6px 12px; font-size: 12px;" onclick="fillAndGo('${acc.email}')">Doldur</button>
                                <button class="btn-secondary" style="padding: 6px 12px; font-size: 12px; border: 1px solid var(--border-color);" onclick="editAccount('${acc.email}')">Düzenle</button>
                                <button class="btn-danger" style="padding: 6px 12px; font-size: 12px;" onclick="deleteAccount('${acc.email}')">Sil</button>
                            </div>
                        </div>
                    `;
                }).join('');
            }
        });
}

function editAccount(email) {
    const account = globalAccounts.find(acc => acc.email === email);
    if (account) {
        document.getElementById('acc-email').value = account.email;
        document.getElementById('acc-password').value = account.password;
        document.getElementById('acc-2fa').value = account.two_factor_secret || '';
    }
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
    const two_factor_secret = document.getElementById('acc-2fa').value;
    if (!email || !password) {
        showCustomAlert('Lütfen e-posta ve şifre girin.', '⚠️');
        return;
    }
    fetch('/api/save_account', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password, two_factor_secret })
    })
    .then(res => {
        if (!res.ok) throw new Error("HTTP error " + res.status);
        document.getElementById('acc-email').value = '';
        document.getElementById('acc-password').value = '';
        document.getElementById('acc-2fa').value = '';
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
        body: JSON.stringify({ file: email })
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
                    setTimeout(() => { window.location.reload(); }, 1500);
                } else {
                    showCustomAlert('Çıkış yapılırken bir hata oluştu.', '❌');
                }
            });
        }
    });
}

let chartProductsInstance = null;
let chartKdvInstance = null;

function updateCharts(excelTable) {
    const reportsCard = document.getElementById('reports-card');
    if (!excelTable || excelTable.length === 0) {
        if (reportsCard) reportsCard.style.display = 'none';
        return;
    }
    if (reportsCard) reportsCard.style.display = 'block';

    const productNames = [];
    const productTotals = [];
    const kdvRates = {};

    excelTable.forEach(row => {
        const name = row.urun || 'Bilinmeyen Ürün';
        const miktar = parseFloat(row.miktar) || 0;
        const fiyat = parseFloat(row.fiyat) || 0;
        const kdv = parseFloat(row.kdv) || 0;
        const iskonto = parseFloat(row.iskonto) || 0;
        
        const totalWithoutKdv = miktar * fiyat;
        const totalWithKdv = totalWithoutKdv * (1 + kdv / 100) - iskonto;
        
        productNames.push(name.length > 15 ? name.substring(0, 15) + '...' : name);
        productTotals.push(totalWithKdv);

        const kdvKey = `%${kdv}`;
        kdvRates[kdvKey] = (kdvRates[kdvKey] || 0) + totalWithoutKdv;
    });

    if (chartProductsInstance) chartProductsInstance.destroy();
    if (chartKdvInstance) chartKdvInstance.destroy();

    const ctxProd = document.getElementById('chart-products').getContext('2d');
    chartProductsInstance = new Chart(ctxProd, {
        type: 'bar',
        data: {
            labels: productNames,
            datasets: [{
                label: 'Toplam Tutar (TL)',
                data: productTotals,
                backgroundColor: '#3d5afe',
                borderColor: '#2e344e',
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false }
            },
            scales: {
                y: { beginAtZero: true, grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#8e9aa6' } },
                x: { grid: { display: false }, ticks: { color: '#8e9aa6' } }
            }
        }
    });

    const ctxKdv = document.getElementById('chart-kdv').getContext('2d');
    chartKdvInstance = new Chart(ctxKdv, {
        type: 'pie',
        data: {
            labels: Object.keys(kdvRates),
            datasets: [{
                data: Object.values(kdvRates),
                backgroundColor: ['#00e676', '#ffea00', '#ff1744', '#3d5afe', '#e040fb']
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { position: 'bottom', labels: { color: '#e1e1e1', font: { family: 'Inter' } } }
            }
        }
    });
}

function updateExcelCell(row, field, value) {
    fetch('/api/update_excel_cell', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ row, field, value })
    });
}

function loadDownloadsList() {
    const tbody = document.getElementById('downloads-tbody');
    if (!tbody) return;
    
    fetch('/api/downloads/list')
        .then(r => r.json())
        .then(files => {
            if (files.length === 0) {
                tbody.innerHTML = `<tr><td colspan="4" style="text-align: center; color: gray; padding: 20px;">Henüz indirilmiş fatura paketi bulunmuyor.</td></tr>`;
            } else {
                tbody.innerHTML = files.map(file => `
                    <tr>
                        <td style="font-weight: 600; color: var(--success-color);">${file.name}</td>
                        <td>${file.size}</td>
                        <td>${file.date}</td>
                        <td style="text-align: center;">
                            <div style="display: flex; gap: 10px; justify-content: center;">
                                <button class="btn-primary" style="padding: 6px 12px; font-size: 12px;" onclick="downloadPackageFile('${file.name}')">İndir</button>
                                <button class="btn-danger" style="padding: 6px 12px; font-size: 12px;" onclick="deletePackageFile('${file.name}')">Sil</button>
                            </div>
                        </td>
                    </tr>
                `).join('');
            }
        }).catch(err => {
            tbody.innerHTML = `<tr><td colspan="4" style="text-align: center; color: var(--danger-color);">Hata: ${err.message}</td></tr>`;
        });
}

function downloadPackageFile(filename) {
    window.location.href = `/api/downloads/download?file=${encodeURIComponent(filename)}`;
}

async function deletePackageFile(filename) {
    const confirmed = await showCustomConfirm(filename + ' dosyasını silmek istediğinize emin misiniz?');
    if (!confirmed) return;
    fetch('/api/downloads/delete', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ file: filename })
    }).then(() => {
        loadDownloadsList();
    });
}

function clearExcelQueue() {
    fetch('/api/queue/clear', { method: 'POST' }).then(() => {
        showCustomAlert('Kuyruk başarıyla temizlendi.', '✅');
        updateStatus();
    });
}

function updateSerialSettings() {
    const prefix = document.getElementById('setting-serial-prefix').value;
    const serial = document.getElementById('setting-serial').value;
    const mode = document.getElementById('setting-finalization-mode').value;
    const scenario = document.getElementById('setting-invoice-scenario').value;
    const type = document.getElementById('setting-invoice-type').value;
    
    if (!prefix || prefix.length !== 3) {
        showCustomAlert('Lütfen tam olarak 3 harfli bir ön ek giriniz (Örn: YRN).', '⚠️');
        return;
    }
    if (!serial || isNaN(parseInt(serial))) {
        showCustomAlert('Lütfen geçerli bir sıra numarası giriniz.', '⚠️');
        return;
    }
    fetch('/api/settings/update', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            serial: parseInt(serial),
            serial_prefix: prefix.toUpperCase(),
            finalization_mode: mode,
            invoice_scenario: scenario,
            invoice_type: type
        })
    }).then(() => {
        showCustomAlert('Fatura seri ayarları başarıyla güncellendi.', '✅');
        updateStatus();
    });
}

let globalCompanies = [];

function loadCompaniesTable() {
    fetch('/api/companies')
        .then(r => r.json())
        .then(companies => {
            globalCompanies = companies;
            filterCompaniesTable();
        })
        .catch(err => console.error("Firma yükleme hatası:", err));
}

function filterCompaniesTable() {
    const query = document.getElementById('company-search-input').value.toLowerCase();
    const tbody = document.getElementById('companies-table-tbody');
    if (!tbody) return;
    
    // Update total count badge
    const countBadge = document.getElementById('companies-count-badge');
    if (countBadge) {
        countBadge.innerText = `${globalCompanies.length} Firma`;
    }
    
    // Uncheck select all on redraw
    const selectAllCheck = document.getElementById('company-select-all');
    if (selectAllCheck) selectAllCheck.checked = false;
    updateCompanySelection();
    
    const filtered = globalCompanies.filter(c => {
        return (c.title || '').toLowerCase().includes(query) ||
               (c.tax_no || '').toLowerCase().includes(query) ||
               (c.city || '').toLowerCase().includes(query) ||
               (c.district || '').toLowerCase().includes(query) ||
               (c.tax_office || '').toLowerCase().includes(query);
    });
    
    if (filtered.length === 0) {
        tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; color: gray; padding: 20px;">Kayıtlı firma bulunamadı.</td></tr>`;
    } else {
        tbody.innerHTML = filtered.map(c => `
            <tr>
                <td style="text-align: center;"><input type="checkbox" class="company-checkbox" value="${c.tax_no}" onchange="updateCompanySelection()"></td>
                <td style="font-weight: 600; color: var(--accent-color); cursor: pointer;" onclick="openEditCompanyModal('${c.tax_no}')" title="Detay / Düzenle">${c.title}</td>
                <td>${c.tax_no}</td>
                <td>${c.city}</td>
                <td>${c.district}</td>
                <td>${c.tax_office}</td>
                <td style="text-align: center;">
                    <span style="cursor: pointer; margin-right: 12px; font-size: 14px;" onclick="openEditCompanyModal('${c.tax_no}')" title="Detay / Düzenle">✏️</span>
                    <span style="cursor: pointer; color: var(--danger-color); font-size: 14px;" onclick="deleteCompany('${c.tax_no}', event)" title="Sil">🗑️</span>
                </td>
            </tr>
        `).join('');
    }
}

function toggleSelectAllCompanies(checked) {
    document.querySelectorAll('.company-checkbox').forEach(cb => {
        cb.checked = checked;
    });
    updateCompanySelection();
}

function updateCompanySelection() {
    const checkboxes = document.querySelectorAll('.company-checkbox:checked');
    const bulkBar = document.getElementById('company-bulk-actions');
    const selectedCount = document.getElementById('company-selected-count');
    
    if (bulkBar && selectedCount) {
        if (checkboxes.length > 0) {
            selectedCount.innerText = `${checkboxes.length} firma seçildi`;
            bulkBar.style.display = 'flex';
        } else {
            bulkBar.style.display = 'none';
        }
    }
}

function openEditCompanyModal(taxNo) {
    const company = globalCompanies.find(c => c.tax_no === taxNo);
    if (!company) return;
    
    document.getElementById('edit-company-old-tax').value = company.tax_no;
    document.getElementById('edit-company-title').value = company.title || '';
    document.getElementById('edit-company-tax').value = company.tax_no || '';
    document.getElementById('edit-company-city').value = company.city || '';
    document.getElementById('edit-company-district').value = company.district || '';
    document.getElementById('edit-company-office').value = company.tax_office || '';
    document.getElementById('edit-company-fullname').value = company.full_name || company.title || '';
    
    document.getElementById('edit-company-modal').style.display = 'flex';
}

function closeEditCompanyModal() {
    document.getElementById('edit-company-modal').style.display = 'none';
}

function saveEditCompany() {
    const oldTax = document.getElementById('edit-company-old-tax').value;
    const title = document.getElementById('edit-company-title').value.trim();
    const taxNo = document.getElementById('edit-company-tax').value.trim();
    const city = document.getElementById('edit-company-city').value.trim();
    const district = document.getElementById('edit-company-district').value.trim();
    const office = document.getElementById('edit-company-office').value.trim();
    const fullName = document.getElementById('edit-company-fullname').value.trim();
    
    if (!title || !taxNo) {
        showCustomAlert('Firma kısa adı ve Vergi/TCKN no boş bırakılamaz.', '⚠️');
        return;
    }
    
    fetch('/api/company/update', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            old_tax_no: oldTax,
            title: title,
            tax_no: taxNo,
            city: city,
            district: district,
            tax_office: office,
            full_name: fullName
        })
    }).then(res => {
        if (res.ok) {
            showCustomAlert('Firma başarıyla güncellendi.', '✅');
            closeEditCompanyModal();
            loadCompaniesTable();
            updateStatus(); // Update company lists across sections
        } else {
            showCustomAlert('Firma güncellenirken hata oluştu.', '❌');
        }
    }).catch(err => {
        showCustomAlert('Bağlantı hatası: ' + err, '❌');
    });
}

function deleteCompany(taxNo, event) {
    if (event) event.stopPropagation();
    
    showCustomConfirm('Bu firmayı veritabanından silmek istediğinize emin misiniz?').then(confirmed => {
        if (confirmed) {
            fetch('/api/company/delete', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ tax_nos: [taxNo] })
            }).then(res => {
                if (res.ok) {
                    showCustomAlert('Firma başarıyla silindi.', '🗑️');
                    loadCompaniesTable();
                    updateStatus();
                } else {
                    showCustomAlert('Firma silinirken hata oluştu.', '❌');
                }
            }).catch(err => {
                showCustomAlert('Bağlantı hatası: ' + err, '❌');
            });
        }
    });
}

function bulkDeleteCompanies() {
    const checkboxes = document.querySelectorAll('.company-checkbox:checked');
    const taxNos = Array.from(checkboxes).map(cb => cb.value);
    
    if (taxNos.length === 0) return;
    
    showCustomConfirm(`Seçilen ${taxNos.length} firmayı silmek istediğinize emin misiniz?`).then(confirmed => {
        if (confirmed) {
            fetch('/api/company/delete', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ tax_nos: taxNos })
            }).then(res => {
                if (res.ok) {
                    showCustomAlert('Seçilen firmalar silindi.', '🗑️');
                    loadCompaniesTable();
                    updateStatus();
                } else {
                    showCustomAlert('Silme işlemi sırasında hata oluştu.', '❌');
                }
            }).catch(err => {
                showCustomAlert('Bağlantı hatası: ' + err, '❌');
            });
        }
    });
}

function bulkExportCompanies() {
    const checkboxes = document.querySelectorAll('.company-checkbox:checked');
    const taxNos = Array.from(checkboxes).map(cb => cb.value);
    
    showCustomAlert('Firma listesi Excel dosyası hazırlanıyor...', '📊');
    
    fetch('/api/companies/export', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tax_nos: taxNos })
    })
    .then(res => {
        if (!res.ok) throw new Error("Excel export failed");
        return res.blob();
    })
    .then(blob => {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'firmalar.xlsx';
        document.body.appendChild(a);
        a.click();
        a.remove();
        window.URL.revokeObjectURL(url);
        showCustomAlert('Excel başarıyla indirildi!', '✅');
    })
    .catch(err => {
        showCustomAlert('Excel aktarma hatası: ' + err.message, '❌');
    });
}

function syncCustomersFromOdeal() {
    showCustomAlert('Müşteri senkronizasyonu arka planda başlatıldı. İlerlemeyi loglardan izleyebilirsiniz.', 'ℹ️');
    fetch('/api/sync_customers', { method: 'POST' }).then(() => {
        setTimeout(loadCompanies, 5000);
    });
}

function exportHistoryToExcel() {
    window.location.href = '/api/history/export';
}

let globalHistoryList = [];

function loadHistoryList() {
    const tbody = document.getElementById('history-tbody');
    if (!tbody) return;
    
    fetch('/api/history')
        .then(r => r.json())
        .then(history => {
            globalHistoryList = history;
            filterHistoryTable();
        }).catch(err => {
            tbody.innerHTML = `<tr><td colspan="5" style="text-align: center; color: var(--danger-color);">Hata: ${err.message}</td></tr>`;
        });
}

function filterHistoryTable() {
    const query = document.getElementById('history-search-input').value.toLowerCase();
    const tbody = document.getElementById('history-tbody');
    if (!tbody) return;
    
    const filtered = globalHistoryList.filter(item => {
        return (item.company_title || '').toLowerCase().includes(query) ||
               (item.serial_no || '').toLowerCase().includes(query);
    });
    
    if (filtered.length === 0) {
        tbody.innerHTML = `<tr><td colspan="5" style="text-align: center; color: gray; padding: 20px;">Eşleşen kayıt bulunamadı.</td></tr>`;
    } else {
        tbody.innerHTML = filtered.map(item => `
            <tr>
                <td>${item.date}</td>
                <td style="font-weight: 600; color: var(--accent-color);">${item.serial_no}</td>
                <td>${item.company_title}</td>
                <td style="text-align: center;">${item.items_count}</td>
                <td style="text-align: right; font-weight: 600; color: var(--success-color);">${item.total} TL</td>
            </tr>
        `).join('');
    }
}

function viewErrorScreenshot(filename) {
    const img = document.getElementById('error-screenshot-img');
    img.src = '/api/screenshots/view?file=' + encodeURIComponent(filename);
    document.getElementById('error-screenshot-modal').style.display = 'flex';
}

function closeErrorScreenshotModal() {
    document.getElementById('error-screenshot-modal').style.display = 'none';
}

function clearLastDownloadDate() {
    showCustomConfirm('Son başarılı fatura indirme tarihini sıfırlamak istediğinize emin misiniz?').then(confirmed => {
        if (confirmed) {
            fetch('/api/settings/clear_download_date', { method: 'POST' }).then(() => {
                showCustomAlert('Son indirme tarihi sıfırlandı.', '✅');
                updateStatus();
            });
        }
    });
}

function toggleAllScratch(checked) {
    const manualDates = document.getElementById('dl-manual-dates');
    if (manualDates) {
        manualDates.style.display = checked ? 'none' : 'flex';
    }
}

function copyOnlyErrors(containerId) {
    const container = document.getElementById(containerId);
    if (!container) return;
    
    const lines = Array.from(container.getElementsByClassName('log-line'));
    const errorLines = lines
        .map(l => l.innerText)
        .filter(text => {
            const lower = text.toLowerCase();
            return lower.includes('hata') || 
                   lower.includes('error') || 
                   lower.includes('başarısız') || 
                   lower.includes('failed') || 
                   lower.includes('exception') || 
                   lower.includes('not found') || 
                   lower.includes('unable to locate');
        });
        
    if (errorLines.length === 0) {
        showCustomAlert('Kopyalanacak herhangi bir hata logu bulunamadı.', '⚠️');
        return;
    }
    
    const textToCopy = errorLines.join('\n');
    navigator.clipboard.writeText(textToCopy)
        .then(() => {
            showCustomAlert(`${errorLines.length} adet hata satırı başarıyla kopyalandı!`, '📋');
        })
        .catch(err => {
            console.error('Kopyalama hatası:', err);
        });
}

function clearLogs() {
    fetch('/api/logs/clear', { method: 'POST' })
        .then(() => {
            updateStatus();
        })
        .catch(err => console.error("Log temizleme hatası:", err));
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

updateStatus();
loadCompanies();
loadLocalExcelFiles();
loadAccounts();
