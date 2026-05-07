import customtkinter as ctk
import threading
import json
import os
import time
import pandas as pd
from tkinter import messagebox, filedialog, ttk
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.keys import Keys

# Constants
COLOR_BG = "#0f111a"
COLOR_SIDEBAR = "#1a1d2b"
COLOR_CARD = "#1e2235"
COLOR_ACCENT = "#3d5afe"
COLOR_TEXT = "#e1e1e1"
COLOR_SUCCESS = "#00e676"
COLOR_WARNING = "#ffea00"
COLOR_DANGER = "#ff1744"

class OdealApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Ödeal | Akıllı Fatura Paneli")
        self.geometry("1150x900")
        ctk.set_appearance_mode("dark")
        
        # Data
        self.companies_file = "firmalar.json"
        self.settings_file = "ayarlar.json"
        self.companies = self.load_data(self.companies_file, [])
        self.settings = self.load_data(self.settings_file, {"serial": 42})
        self.excel_data = None
        self.driver = None
        self.selected_company = None

        self.setup_ui()

    def load_data(self, file, default):
        if os.path.exists(file):
            try:
                with open(file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except: return default
        return default

    def save_data(self, file, data):
        with open(file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

    def setup_ui(self):
        self.configure(fg_color=COLOR_BG)
        
        # Sidebar
        self.sidebar = ctk.CTkFrame(self, width=200, corner_radius=0, fg_color=COLOR_SIDEBAR)
        self.sidebar.pack(side="left", fill="y")
        self.logo_label = ctk.CTkLabel(self.sidebar, text="ÖDEAL", font=ctk.CTkFont(size=28, weight="bold"), text_color=COLOR_ACCENT)
        self.logo_label.pack(pady=(40, 10))
        self.side_stat_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.side_stat_frame.pack(fill="x", padx=20, pady=20)
        self.side_status = ctk.CTkLabel(self.side_stat_frame, text="● Sistem Hazır", text_color=COLOR_SUCCESS, font=ctk.CTkFont(size=14, weight="bold"))
        self.side_status.pack(anchor="w")
        
        # Main Scrollable Area
        self.main_container = ctk.CTkScrollableFrame(self, fg_color=COLOR_BG, corner_radius=0)
        self.main_container.pack(side="right", fill="both", expand=True, padx=20, pady=20)

        # --- SECTIONS ---
        self.auth_card = self.create_card("1. Oturum Yönetimi", "🔒")
        auth_inner = ctk.CTkFrame(self.auth_card, fg_color="transparent")
        auth_inner.pack(pady=10, fill="x")
        self.email_entry = ctk.CTkEntry(auth_inner, placeholder_text="E-mail", width=240, height=40, border_color=COLOR_ACCENT)
        self.email_entry.grid(row=0, column=0, padx=10, pady=10)
        self.password_entry = ctk.CTkEntry(auth_inner, placeholder_text="Şifre", show="*", width=240, height=40, border_color=COLOR_ACCENT)
        self.password_entry.grid(row=0, column=1, padx=10, pady=10)
        self.login_btn = ctk.CTkButton(auth_inner, text="Sistemi Başlat", command=self.start_login, width=180, height=40, fg_color=COLOR_ACCENT)
        self.login_btn.grid(row=0, column=2, padx=10, pady=10)

        self.company_card = self.create_card("2. Firma Seçimi", "🏢")
        comp_top = ctk.CTkFrame(self.company_card, fg_color="transparent")
        comp_top.pack(fill="x", pady=5)
        self.comp_select = ctk.CTkOptionMenu(comp_top, values=self.get_company_titles(), command=self.on_company_select, width=350, height=35)
        self.comp_select.pack(side="left", padx=10)
        self.new_comp_btn = ctk.CTkButton(comp_top, text="+ Yeni Firma Ekle", command=self.open_new_company_window, width=150, fg_color=COLOR_SUCCESS, text_color="black")
        self.new_comp_btn.pack(side="left", padx=10)
        self.prep_btn = ctk.CTkButton(comp_top, text="Faturayı Hazırla", command=self.start_prepare, state="disabled", fg_color="#455a64", height=35)
        self.prep_btn.pack(side="left", padx=10)
        
        self.details_grid = ctk.CTkFrame(self.company_card, fg_color="#151926", corner_radius=10)
        self.details_grid.pack(fill="x", pady=15, padx=5)
        self.detail_labels = {}
        for i, (label, key) in enumerate([("Vergi No", "tax_no"), ("Şehir", "city"), ("İlçe", "district"), ("Vergi Dairesi", "tax_office")]):
            r, c = i // 2, (i % 2) * 2
            ctk.CTkLabel(self.details_grid, text=label, text_color="gray", font=ctk.CTkFont(size=11)).grid(row=r*2, column=c, padx=20, pady=(10, 0), sticky="w")
            val_lbl = ctk.CTkLabel(self.details_grid, text="-", font=ctk.CTkFont(size=14, weight="bold"))
            val_lbl.grid(row=r*2+1, column=c, padx=20, pady=(0, 10), sticky="w")
            self.detail_labels[key] = val_lbl
        ctk.CTkLabel(self.details_grid, text="Firma Tam Adı (Sistem Kaydı)", text_color="gray", font=ctk.CTkFont(size=11)).grid(row=4, column=0, columnspan=4, padx=20, pady=(10, 0), sticky="w")
        self.fullname_lbl = ctk.CTkLabel(self.details_grid, text="-", font=ctk.CTkFont(size=14, weight="bold"), text_color=COLOR_SUCCESS)
        self.fullname_lbl.grid(row=5, column=0, columnspan=4, padx=20, pady=(0, 15), sticky="w")
        self.detail_labels["full_name"] = self.fullname_lbl

        self.excel_card = self.create_card("3. Veri ve Hesaplama", "📊")
        excel_actions = ctk.CTkFrame(self.excel_card, fg_color="transparent")
        excel_actions.pack(fill="x", pady=5)
        ctk.CTkButton(excel_actions, text="📥 Şablon İndir", command=self.download_template, width=150, fg_color="#455a64").pack(side="left", padx=10)
        ctk.CTkButton(excel_actions, text="📤 Excel Yükle", command=self.upload_excel, width=150, fg_color=COLOR_ACCENT).pack(side="left", padx=10)
        self.process_btn = ctk.CTkButton(excel_actions, text="🚀 Faturaları İşle", command=self.start_processing, state="disabled", fg_color=COLOR_SUCCESS, text_color="black")
        self.process_btn.pack(side="left", padx=10)
        
        table_frame = ctk.CTkFrame(self.excel_card, fg_color="#0f111a", corner_radius=8)
        table_frame.pack(fill="both", expand=True, pady=15)
        self.setup_treeview(table_frame)

        self.kpi_container = ctk.CTkFrame(self.excel_card, fg_color="transparent")
        self.kpi_container.pack(fill="x", pady=10)
        self.kpis = {}
        for name, key, icon in [("Kalem", "kalem", "📦"), ("Miktar", "miktar", "🔢"), ("KDV'siz", "kdvsiz", "💰"), ("İskonto", "iskonto", "🏷️"), ("Toplam", "toplam", "✅")]:
            card = ctk.CTkFrame(self.kpi_container, fg_color="#151926", width=140, height=80)
            card.pack(side="left", padx=5, fill="both", expand=True)
            card.pack_propagate(False)
            ctk.CTkLabel(card, text=f"{icon} {name}", font=ctk.CTkFont(size=11), text_color="gray").pack(pady=(5,0))
            lbl = ctk.CTkLabel(card, text="0", font=ctk.CTkFont(size=15, weight="bold"))
            lbl.pack(pady=(2,5))
            self.kpis[key] = lbl

    def create_card(self, title, icon):
        card = ctk.CTkFrame(self.main_container, fg_color=COLOR_CARD, corner_radius=15, border_width=1, border_color="#2e344e")
        card.pack(fill="x", pady=15, padx=5)
        header = ctk.CTkFrame(card, fg_color="transparent")
        header.pack(fill="x", padx=15, pady=10)
        ctk.CTkLabel(header, text=f"{icon} {title}", font=ctk.CTkFont(size=18, weight="bold"), text_color=COLOR_ACCENT).pack(side="left")
        return card

    def setup_treeview(self, parent):
        style = ttk.Style()
        style.theme_use("default")
        style.configure("Treeview", background="#1e2235", foreground="white", fieldbackground="#1e2235", borderwidth=0, rowheight=30)
        style.configure("Treeview.Heading", background="#2e344e", foreground="white", borderwidth=0)
        self.tree = ttk.Treeview(parent, columns=("urun", "miktar", "birim", "fiyat", "kdv", "iskonto"), show="headings", height=8)
        for col, text in {"urun": "Ürün Adı", "miktar": "Miktar", "birim": "Birim", "fiyat": "Birim Fiyat", "kdv": "KDV %", "iskonto": "İskonto"}.items():
            self.tree.heading(col, text=text); self.tree.column(col, width=100, anchor="center")
        self.tree.pack(side="left", fill="both", expand=True, padx=10, pady=10)

    # --- LOGIC ---
    def get_company_titles(self):
        titles = [c["title"] for c in self.companies]
        return titles if titles else ["Kayıtlı firma bulunamadı"]

    def on_company_select(self, title):
        self.selected_company = next((c for c in self.companies if c["title"] == title), None)
        if self.selected_company:
            for k, v in self.detail_labels.items():
                val = self.selected_company.get(k, "-")
                v.configure(text=val if val else "-")
            if self.driver: self.prep_btn.configure(state="normal")
        else:
            for v in self.detail_labels.values(): v.configure(text="-")

    def open_new_company_window(self):
        dialog = ctk.CTkToplevel(self)
        dialog.title("Yeni Firma Tanımla"); dialog.geometry("450x550"); dialog.attributes("-topmost", True)
        entries = {}
        for label, key in [("Firma Başlığı (Not)", "title"), ("Vergi No", "tax_no"), ("Şehir", "city"), ("İlçe", "district"), ("Vergi Dairesi", "tax_office")]:
            ctk.CTkLabel(dialog, text=label).pack(pady=(10,0))
            e = ctk.CTkEntry(dialog, width=300); e.pack(); entries[key] = e
        def save():
            data = {k: v.get() for k, v in entries.items()}; data["full_name"] = ""
            self.companies.append(data); self.save_data(self.companies_file, self.companies)
            self.comp_select.configure(values=self.get_company_titles()); dialog.destroy()
        ctk.CTkButton(dialog, text="Kaydet", command=save, fg_color=COLOR_SUCCESS).pack(pady=20)

    def download_template(self):
        path = filedialog.asksaveasfilename(defaultextension=".xlsx")
        if path: pd.DataFrame(columns=["Ürün Adı", "Miktar", "Birim", "Birim Fiyat", "KDV Oranı", "İskonto Tutarı"]).to_excel(path, index=False)

    def upload_excel(self):
        path = filedialog.askopenfilename(filetypes=[("Excel", "*.xlsx")])
        if path:
            try:
                self.excel_data = pd.read_excel(path)
                for i in self.tree.get_children(): self.tree.delete(i)
                for _, r in self.excel_data.iterrows(): self.tree.insert("", "end", values=list(r))
                self.calculate_kpis()
                if self.prep_btn.cget("text") == "✅ Hazır": self.process_btn.configure(state="normal")
            except Exception as e: messagebox.showerror("Hata", str(e))

    def calculate_kpis(self):
        if self.excel_data is not None:
            try:
                df = self.excel_data.copy(); df.columns = [c.lower() for c in df.columns]
                m = pd.to_numeric(df.iloc[:, 1]).sum(); f = pd.to_numeric(df.iloc[:, 3]); k = pd.to_numeric(df.iloc[:, 4]); i = pd.to_numeric(df.iloc[:, 5]).sum()
                ks = (pd.to_numeric(df.iloc[:, 1]) * f).sum(); kl = (pd.to_numeric(df.iloc[:, 1]) * f * (1 + k/100)).sum() - i
                self.kpis["kalem"].configure(text=str(len(df))); self.kpis["miktar"].configure(text=f"{m:.0f}")
                self.kpis["kdvsiz"].configure(text=f"{ks:.2f}"); self.kpis["iskonto"].configure(text=f"{i:.2f}"); self.kpis["toplam"].configure(text=f"{kl:.2f}")
            except: pass

    # --- AUTOMATION STAGES ---
    def start_login(self):
        self.login_btn.configure(text="⏳ Giriş Yapılıyor...", state="disabled")
        threading.Thread(target=self.login_process, daemon=True).start()

    def login_process(self):
        try:
            email, pw = self.email_entry.get(), self.password_entry.get()
            s = Service(ChromeDriverManager().install()); o = Options(); o.add_argument("--start-maximized")
            self.driver = webdriver.Chrome(service=s, options=o)
            self.driver.get("https://fatura.odeal.com/index.php")
            wait = WebDriverWait(self.driver, 10)
            wait.until(EC.presence_of_element_located((By.XPATH, "/html/body/div[1]/div/div/form/div[1]/input"))).send_keys(email)
            self.driver.find_element(By.XPATH, "/html/body/div[1]/div/div/form/div[2]/input").send_keys(pw)
            self.driver.find_element(By.XPATH, "/html/body/div[1]/div/div/form/div[3]/button").click()
            self.after(0, self.on_logged_in)
        except Exception as e: self.after(0, lambda err=e: self.handle_error(err))

    def on_logged_in(self):
        self.side_status.configure(text="● Doğrulama Bekleniyor", text_color=COLOR_WARNING)
        self.login_btn.configure(text="Onaylandı", state="normal", command=self.on_auth_confirmed)
        messagebox.showinfo("Doğrulama", "Lütfen kodu girin ve 'Onaylandı'ya basın.")

    def on_auth_confirmed(self):
        self.side_status.configure(text="● Giriş Başarılı", text_color=COLOR_SUCCESS)
        self.login_btn.configure(text="✅ Giriş Yapıldı", state="disabled", fg_color=COLOR_SUCCESS)
        if self.selected_company: self.prep_btn.configure(state="normal")

    def start_prepare(self):
        self.prep_btn.configure(state="disabled", text="⏳ Hazırlanıyor...")
        threading.Thread(target=self.prepare_process, daemon=True).start()

    def prepare_process(self, retry=True):
        try:
            wait = WebDriverWait(self.driver, 20)
            self.driver.get("https://fatura.odeal.com/hizlifatura")
            wait.until(EC.element_to_be_clickable((By.XPATH, "/html/body/div[6]/div/div[6]/button[1]"))).click()
            
            # Primary Search: Tax Number
            search_input = wait.until(EC.presence_of_element_located((By.XPATH, "/html/body/div[1]/div[8]/div[1]/div[3]/div[1]/div[3]/div/div[2]/div/div[1]/div[1]/input")))
            search_input.clear(); search_input.send_keys(self.selected_company["tax_no"]); time.sleep(2)
            
            try:
                # Try to click the result
                res_btn = self.driver.find_element(By.XPATH, "/html/body/div[1]/div[8]/div[1]/div[3]/div[1]/div[3]/div/div[2]/div/div[1]/div[1]/div/div/a/div/div[1]")
                res_btn.click()
            except:
                # LONG REGISTRATION
                self.driver.find_element(By.XPATH, "/html/body/div[1]/div[8]/div[1]/div[3]/div[1]/div[3]/div/div[2]/div/div[2]/a").click()
                time.sleep(2)
                self.driver.find_element(By.XPATH, "/html/body/div[1]/div[10]/div/div/div[2]/div[1]/div[1]/input").send_keys(self.selected_company["tax_no"])
                Select(self.driver.find_element(By.XPATH, "/html/body/div[1]/div[10]/div/div/div[2]/div[3]/div[1]/select")).select_by_index(1)
                Select(self.driver.find_element(By.XPATH, "/html/body/div[1]/div[10]/div/div/div[2]/div[3]/div[2]/select")).select_by_visible_text(self.selected_company["city"])
                time.sleep(1)
                Select(self.driver.find_element(By.XPATH, "/html/body/div[1]/div[10]/div/div/div[2]/div[4]/div[1]/select")).select_by_visible_text(self.selected_company["district"])
                tax_office_input = self.driver.find_element(By.XPATH, "/html/body/div[1]/div[10]/div/div/div[2]/div[7]/div[2]/span/span[1]/span/span[1]")
                tax_office_input.click(); time.sleep(1)
                self.driver.switch_to.active_element.send_keys(self.selected_company["tax_office"])
                time.sleep(2); wait.until(EC.element_to_be_clickable((By.XPATH, "/html/body/span/span/span[2]/ul/li"))).click()
                
                # Capture Full Name
                full_name_field = self.driver.find_element(By.XPATH, "/html/body/div[1]/div[10]/div/div/div[2]/div[1]/div[2]/input")
                captured_name = full_name_field.get_attribute("value")
                if captured_name:
                    for comp in self.companies:
                        if comp["tax_no"] == self.selected_company["tax_no"]:
                            comp["full_name"] = captured_name
                            self.selected_company["full_name"] = captured_name
                            self.after(0, lambda name=captured_name: self.detail_labels["full_name"].configure(text=name))
                            break
                    self.save_data(self.companies_file, self.companies)
                self.driver.find_element(By.XPATH, "/html/body/div[1]/div[10]/div/div/div[3]/button").click(); time.sleep(3)

            self.driver.execute_script("window.scrollBy(0, 500);")
            Select(wait.until(EC.presence_of_element_located((By.XPATH, "/html/body/div[1]/div[8]/div[1]/div[3]/div[1]/div[8]/div/div[2]/div[2]/div[1]/div[2]/div/select")))).select_by_index(1)
            serial_input = self.driver.find_element(By.XPATH, "/html/body/div[1]/div[8]/div[1]/div[3]/div[1]/div[8]/div/div[2]/div[2]/div[6]/div/div/div[1]/div[1]/div/input")
            serial_input.clear(); serial_input.send_keys(f"YRN{str(self.settings['serial']).zfill(13)}")
            self.driver.find_element(By.XPATH, "/html/body/div[1]/div[8]/div[1]/div[3]/div[1]/div[8]/div/div[2]/div[2]/div[6]/div/div/div[1]/div[2]/div/input").click()
            time.sleep(1); self.driver.find_element(By.LINK_TEXT, "Bugün").click() 
            self.driver.find_element(By.XPATH, "/html/body/div[1]/div[8]/div[1]/div[3]/div[1]/div[8]/div/div[2]/div[2]/div[6]/div/div/div[1]/div[3]").click()
            self.after(0, self.on_prep_finished)
        except Exception as e:
            if retry:
                self.after(0, lambda: self.side_status.configure(text="● Hata! Yenileniyor...", text_color=COLOR_DANGER))
                self.driver.refresh(); time.sleep(2)
                self.prepare_process(retry=False) # Only retry once
            else:
                self.after(0, lambda err=e: self.handle_error(err))

    def on_prep_finished(self):
        self.prep_btn.configure(text="✅ Hazır", fg_color=COLOR_SUCCESS, state="disabled")
        if self.excel_data is not None: self.process_btn.configure(state="normal")
        messagebox.showinfo("Hazır", "Fatura hazırlandı. Ürünleri işlemek için 'Faturaları İşle' butonuna basın.")

    def start_processing(self):
        self.process_btn.configure(state="disabled", text="⏳ İşleniyor...")
        threading.Thread(target=self.process_products, daemon=True).start()

    def process_products(self):
        try:
            wait = WebDriverWait(self.driver, 10); df = self.excel_data.copy()
            for _, row in df.iterrows():
                wait.until(EC.presence_of_element_located((By.XPATH, "/html/body/div[1]/div[8]/div[1]/div[3]/div[1]/div[9]/div[1]/div[3]/div/div/div[1]/input[1]"))).send_keys(str(row.iloc[0]))
                self.driver.find_element(By.XPATH, "/html/body/div[1]/div[8]/div[1]/div[3]/div[1]/div[9]/div[1]/div[3]/div/div/div[2]/input").send_keys(str(row.iloc[1]))
                Select(self.driver.find_element(By.XPATH, "/html/body/div[1]/div[8]/div[1]/div[3]/div[1]/div[9]/div[1]/div[3]/div/div/div[3]/select")).select_by_visible_text(str(row.iloc[2]))
                self.driver.find_element(By.XPATH, "/html/body/div[1]/div[8]/div[1]/div[3]/div[1]/div[9]/div[1]/div[3]/div/div/div[4]/div/input").send_keys(str(row.iloc[3]))
                mapping = {"0": 1, "1": 2, "10": 3, "20": 4}
                Select(self.driver.find_element(By.XPATH, "/html/body/div[1]/div[8]/div[1]/div[3]/div[1]/div[9]/div[1]/div[3]/div/div/div[6]/select")).select_by_index(mapping.get(str(row.iloc[4]), 4))
                self.driver.find_element(By.XPATH, "/html/body/div[1]/div[8]/div[1]/div[3]/div[1]/div[9]/div[1]/div[3]/div/div/div[8]/button").click(); time.sleep(2)
            for _, row in df.iterrows():
                isk = row.iloc[5]
                if pd.notna(isk) and float(isk) > 0:
                    found = -1
                    for n in range(1, len(df) + 2):
                        try:
                            if str(row.iloc[0]) in self.driver.find_element(By.XPATH, f"/html/body/div[1]/div[8]/div[1]/div[3]/div[1]/div[9]/div[1]/div[4]/div/table/tbody/tr[{n}]/td[1]").text:
                                found = n; break
                        except: break
                    if found != -1:
                        self.driver.find_element(By.XPATH, f"/html/body/div[1]/div[8]/div[1]/div[3]/div[1]/div[9]/div[1]/div[4]/div/table/tbody/tr[{found}]/td[8]/button[1]").click(); time.sleep(2)
                        self.driver.find_element(By.XPATH, "/html/body/div[1]/div[8]/div[1]/div[3]/div[1]/div[1]/div/div/div[2]/div[1]/div[2]/div/div[4]/div[3]/div[2]/input").send_keys(str(isk).replace("%",""))
                        self.driver.find_element(By.XPATH, "/html/body/div[1]/div[8]/div[1]/div[3]/div[1]/div[1]/div/div/div[2]/div[1]/div[2]/div/div[4]/div[5]/button").click(); time.sleep(1)
                        self.driver.find_element(By.XPATH, "/html/body/div[1]/div[8]/div[1]/div[3]/div[1]/div[1]/div/div/div[3]/button[1]").click(); time.sleep(1)
                        self.driver.find_element(By.XPATH, "/html/body/div[7]/div/div[6]/button[1]").click(); time.sleep(2)
            self.settings["serial"] += 1; self.save_data(self.settings_file, self.settings)
            self.after(0, lambda: messagebox.showinfo("Bitti", "İşlem başarıyla tamamlandı!"))
        except Exception as e: self.after(0, lambda err=e: self.handle_error(err))

    def handle_error(self, e):
        messagebox.showerror("Hata", str(e))
        self.side_status.configure(text="● Hata!", text_color=COLOR_DANGER)

if __name__ == "__main__":
    app = OdealApp()
    app.mainloop()
