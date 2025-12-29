import flet as ft
import sqlite3
import shutil
from datetime import datetime, date, timedelta
# YENİ EKLENEN KÜTÜPHANE
from flet_contrib.color_picker import ColorPicker 

# --- YARDIMCI FONKSİYONLAR ---
AYLAR = {1: "Ocak", 2: "Şubat", 3: "Mart", 4: "Nisan", 5: "Mayıs", 6: "Haziran",
         7: "Temmuz", 8: "Ağustos", 9: "Eylül", 10: "Ekim", 11: "Kasım", 12: "Aralık"}

def tr_date_format(date_obj):
    if not date_obj: return ""
    if isinstance(date_obj, str):
        date_obj = datetime.strptime(date_obj, "%Y-%m-%d")
    return f"{date_obj.day} {AYLAR[date_obj.month]} {date_obj.year}"

def format_sure(dakika):
    if not dakika: return "0 Sa 0 Dk"
    saat = dakika // 60
    dk = dakika % 60
    return f"{saat} Sa {dk} Dk"

class MesaiApp:
    def __init__(self, page: ft.Page):
        self.page = page
        self.page.title = "Mesai Takip"
        self.page.padding = 0
        self.page.spacing = 0
        
        self.init_db()
        self.load_settings()
        self.update_theme_colors()
        
        self.editing_id = None 
        self.selected_date = datetime.now()
        self.start_time = None
        self.end_time = None
        self.current_view = "main"
        
        # Hedeflenen input ve preview kutularını tutmak için değişkenler
        self.target_color_input = None
        self.target_color_preview = None

        self.date_picker = ft.DatePicker(on_change=self.on_date_change)
        self.time_picker_start = ft.TimePicker(on_change=self.on_start_time_change)
        self.time_picker_end = ft.TimePicker(on_change=self.on_end_time_change)
        self.backup_dialog = ft.FilePicker(on_result=self.backup_result)
        self.restore_dialog = ft.FilePicker(on_result=self.restore_result)
        
        self.page.overlay.extend([self.date_picker, self.time_picker_start, self.time_picker_end, self.backup_dialog, self.restore_dialog])

        self.nav_bar = ft.NavigationBar(
            destinations=[
                ft.NavigationBarDestination(icon=ft.Icons.ADD_CIRCLE_OUTLINE, label="Ekle"),
                ft.NavigationBarDestination(icon=ft.Icons.CALENDAR_MONTH_OUTLINED, label="Bu Ay"),
                ft.NavigationBarDestination(icon=ft.Icons.ACCOUNT_BALANCE_WALLET_OUTLINED, label="Finans"),
                ft.NavigationBarDestination(icon=ft.Icons.HISTORY_OUTLINED, label="Geçmiş"),
            ],
            on_change=self.nav_change,
            selected_index=0,
        )

        self.content_area = ft.Column(expand=True, spacing=0)
        self.app_bar = ft.Container(
            content=ft.Row([
                ft.Container(width=40),
                ft.Text("MESAİ TAKİP PRO", size=18, weight="bold", color="white"),
                ft.IconButton(ft.Icons.SETTINGS, icon_color="white", on_click=self.toggle_settings),
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            bgcolor=self.v_ana_renk, padding=10,
        )

        self.page.add(self.app_bar, self.content_area, self.nav_bar)
        self.load_tab(0)

    def update_theme_colors(self):
        self.page.theme_mode = ft.ThemeMode.DARK if self.v_tema == "dark" else ft.ThemeMode.LIGHT
        self.page.theme = ft.Theme(color_scheme_seed=self.v_vurgu_renk)
        if hasattr(self, 'app_bar'): self.app_bar.bgcolor = self.v_ana_renk
        self.page.update()

    def init_db(self):
        self.db_path = "mesai_v4.db"
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.cursor.execute("CREATE TABLE IF NOT EXISTS mesailer (id INTEGER PRIMARY KEY, tarih TEXT, baslangic TEXT, bitis TEXT, maas REAL, sure_dakika INTEGER, ucret REAL)")
        self.cursor.execute("CREATE TABLE IF NOT EXISTS finans (id INTEGER PRIMARY KEY, tur TEXT, miktar REAL, tarih TEXT, aciklama TEXT)")
        self.cursor.execute("CREATE TABLE IF NOT EXISTS ayarlar (id INTEGER PRIMARY KEY, varsayilan_maas REAL, mesai_katsayisi REAL, tema_modu TEXT, ana_renk TEXT, vurgu_renk TEXT, aylik_hedef REAL)")
        self.cursor.execute("SELECT COUNT(*) FROM ayarlar")
        if self.cursor.fetchone()[0] == 0:
            self.cursor.execute("INSERT INTO ayarlar (varsayilan_maas, mesai_katsayisi, tema_modu, ana_renk, vurgu_renk, aylik_hedef) VALUES (0.0, 1.5, 'light', '#1A237E', '#00BFA5', 5000.0)")
        self.conn.commit()

    def load_settings(self):
        self.cursor.execute("SELECT varsayilan_maas, mesai_katsayisi, tema_modu, ana_renk, vurgu_renk, aylik_hedef FROM ayarlar WHERE id=1")
        res = self.cursor.fetchone()
        self.v_maas, self.v_katsayi, self.v_tema, self.v_ana_renk, self.v_vurgu_renk, self.v_hedef = res

    def load_tab(self, index):
        self.content_area.controls.clear()
        if index == 0: self.content_area.controls.append(self.build_add_tab())
        elif index == 1: self.content_area.controls.append(self.build_month_tab())
        elif index == 2: self.content_area.controls.append(self.build_finance_tab())
        elif index == 3: self.content_area.controls.append(self.build_history_tab())
        self.page.update()

    def show_settings_view(self):
        self.content_area.controls.clear()
        
        # Giriş Alanları
        txt_v_maas = ft.TextField(label="Varsayılan Maaş (TL)", value=str(self.v_maas))
        txt_v_katsayi = ft.TextField(label="Varsayılan Katsayı", value=str(self.v_katsayi))
        txt_v_hedef = ft.TextField(label="Aylık Mesai Hedefi (TL)", value=str(self.v_hedef))
        
        # Renk Text Alanları
        txt_ana_renk = ft.TextField(label="Ana Tema Rengi (HEX)", value=self.v_ana_renk, expand=True)
        txt_vurgu_renk = ft.TextField(label="Vurgu Rengi (HEX)", value=self.v_vurgu_renk, expand=True)

        # Renk Önizleme Kutuları (Tıklanabilir olacaklar)
        preview_ana = ft.Container(width=40, height=40, bgcolor=self.v_ana_renk, border_radius=5, border=ft.border.all(1, "grey"))
        preview_vurgu = ft.Container(width=40, height=40, bgcolor=self.v_vurgu_renk, border_radius=5, border=ft.border.all(1, "grey"))

        # --- RENK PALETİ MANTIĞI ---
        color_picker_ctrl = ColorPicker(color="#000000", width=300)

        def pick_color_result(e):
            # Seçilen rengi al (Hex kodu)
            selected_color = color_picker_ctrl.color
            # Hedeflediğimiz text kutusuna ve preview kutusuna uygula
            if self.target_color_input:
                self.target_color_input.value = selected_color
            if self.target_color_preview:
                self.target_color_preview.bgcolor = selected_color
            
            self.page.close(color_dialog)
            self.page.update()

        color_dialog = ft.AlertDialog(
            title=ft.Text("Renk Seç"),
            content=ft.Column([color_picker_ctrl], height=400, tight=True, alignment="center"),
            actions=[ft.TextButton("SEÇ", on_click=pick_color_result)]
        )

        def open_color_picker(e, input_field, preview_box):
            # Hangi kutu için açıldığını kaydet
            self.target_color_input = input_field
            self.target_color_preview = preview_box
            # Paleti şu anki renkle başlat (varsa)
            try:
                color_picker_ctrl.color = input_field.value
            except:
                color_picker_ctrl.color = "#000000"
            
            self.page.open(color_dialog)
            self.page.update()

        # Kutulara tıklama özelliği ekle
        preview_ana.on_click = lambda e: open_color_picker(e, txt_ana_renk, preview_ana)
        preview_vurgu.on_click = lambda e: open_color_picker(e, txt_vurgu_renk, preview_vurgu)
        
        # Hızlı Renk Seçimi (Manuel butonlar)
        def set_quick_color(ana, vurgu):
            txt_ana_renk.value = ana
            txt_vurgu_renk.value = vurgu
            preview_ana.bgcolor = ana
            preview_vurgu.bgcolor = vurgu
            self.page.update()

        quick_colors = ft.Row([
            ft.IconButton(icon=ft.Icons.CIRCLE, icon_color="#1A237E", on_click=lambda _: set_quick_color("#1A237E", "#00BFA5"), tooltip="Okyanus"),
            ft.IconButton(icon=ft.Icons.CIRCLE, icon_color="#2E7D32", on_click=lambda _: set_quick_color("#2E7D32", "#C6FF00"), tooltip="Doğa"),
            ft.IconButton(icon=ft.Icons.CIRCLE, icon_color="#B71C1C", on_click=lambda _: set_quick_color("#B71C1C", "#FFD600"), tooltip="Ateş"),
            ft.IconButton(icon=ft.Icons.CIRCLE, icon_color="#4A148C", on_click=lambda _: set_quick_color("#4A148C", "#EA80FC"), tooltip="Gece"),
            ft.IconButton(icon=ft.Icons.CIRCLE, icon_color="#37474F", on_click=lambda _: set_quick_color("#37474F", "#81D4FA"), tooltip="Metal"),
        ], alignment="center")

        def save_settings(e):
            try:
                self.v_maas, self.v_katsayi, self.v_hedef = float(txt_v_maas.value), float(txt_v_katsayi.value), float(txt_v_hedef.value)
                self.v_ana_renk, self.v_vurgu_renk = txt_ana_renk.value, txt_vurgu_renk.value
                self.cursor.execute("UPDATE ayarlar SET varsayilan_maas=?, mesai_katsayisi=?, aylik_hedef=?, ana_renk=?, vurgu_renk=? WHERE id=1", (self.v_maas, self.v_katsayi, self.v_hedef, self.v_ana_renk, self.v_vurgu_renk))
                self.conn.commit()
                self.update_theme_colors()
                self.show_msg("Ayarlar Kaydedildi!", "green")
                self.toggle_settings(None)
            except: self.show_msg("Hata: Değerleri kontrol edin", "red")

        def reset_data(e):
            def confirm_reset(e):
                self.cursor.execute("DELETE FROM mesailer"); self.cursor.execute("DELETE FROM finans")
                self.conn.commit()
                self.page.close(dlg)
                self.show_msg("Tüm veriler temizlendi!", "red")
                self.load_tab(0) # EKRANI YENİLEMEK İÇİN

            dlg = ft.AlertDialog(
                title=ft.Text("Tüm Veriler Silinsin mi?"),
                content=ft.Text("Bu işlem geri alınamaz!"),
                actions=[ft.TextButton("İptal", on_click=lambda _: self.page.close(dlg)), ft.ElevatedButton("EVET, SİL", bgcolor="red", color="white", on_click=confirm_reset)]
            )
            self.page.open(dlg)

        # Ayarlar Sayfası İçeriği
        settings_content = ft.Column([
            ft.Row([ft.IconButton(ft.Icons.ARROW_BACK, on_click=self.toggle_settings), ft.Text("AYARLAR", size=22, weight="bold")]),
            ft.Divider(),
            ft.Text("Hesaplama ve Hedef", weight="bold"),
            txt_v_maas, txt_v_katsayi, txt_v_hedef,
            ft.Divider(),
            ft.Text("Görünüm ve Renk Paleti", weight="bold"),
            # Renk kutularına tıklayınca palet açılır
            ft.Row([txt_ana_renk, preview_ana]),
            ft.Row([txt_vurgu_renk, preview_vurgu]),
            ft.Text("Kutucuklara tıklayarak renk seçebilirsiniz.", size=11, italic=True, color="grey"),
            ft.Text("Hızlı Renk Seçimi:", size=12, color="grey"),
            quick_colors,
            ft.Switch(label="Koyu Tema", value=(self.v_tema == "dark"), on_change=self.change_theme),
            ft.Divider(),
            ft.Text("Veri Yönetimi", weight="bold"),
            ft.Row([ft.ElevatedButton("Yedekle", icon=ft.Icons.UPLOAD, expand=True, on_click=lambda _: self.backup_dialog.save_file()),
                    ft.ElevatedButton("Geri Yükle", icon=ft.Icons.DOWNLOAD, expand=True, on_click=lambda _: self.restore_dialog.pick_files())]),
            ft.ElevatedButton("Tüm Verileri Sıfırla", icon=ft.Icons.DELETE_FOREVER, bgcolor=ft.Colors.RED_ACCENT_700, color="white", width=float("inf"), on_click=reset_data),
            ft.Divider(),
            ft.ElevatedButton("AYARLARI KAYDET", on_click=save_settings, bgcolor=self.v_ana_renk, color="white", width=float("inf"), height=50),
            ft.Container(height=20)
        ], spacing=15, scroll=ft.ScrollMode.ADAPTIVE)

        self.content_area.controls.append(ft.Container(padding=25, content=settings_content, expand=True))
        self.page.update()

    # --- DİĞER FONKSİYONLAR ---
    def build_add_tab(self):
        is_edit = self.editing_id is not None
        btn_label = "GÜNCELLE" if is_edit else "KAYDET"
        btn_color = ft.Colors.AMBER_700 if is_edit else self.v_ana_renk
        start_txt = self.start_time.strftime("%H:%M") if self.start_time else "Giriş"
        end_txt = self.end_time.strftime("%H:%M") if self.end_time else "Bitiş"
        self.txt_salary = ft.TextField(label="Maaş (TL)", value=str(self.v_maas if not is_edit else self.last_salary), expand=2)
        self.txt_katsayi = ft.TextField(label="Katsayı", value=str(self.v_katsayi), expand=1)
        return ft.Container(padding=25, content=ft.Column([
            ft.Text("MESAİ KAYDI", size=20, weight="bold", text_align="center", width=float("inf")),
            ft.Container(content=ft.Row([ft.Icon(ft.Icons.CALENDAR_MONTH), ft.Text(tr_date_format(self.selected_date), weight="bold")], alignment="center"), padding=15, border=ft.border.all(1, ft.Colors.GREY_400), border_radius=12, on_click=lambda _: self.open_picker(self.date_picker)),
            ft.Row([ft.ElevatedButton(start_txt, on_click=lambda _: self.open_picker(self.time_picker_start), expand=True), ft.ElevatedButton(end_txt, on_click=lambda _: self.open_picker(self.time_picker_end), expand=True)]),
            ft.Row([self.txt_salary, self.txt_katsayi]),
            ft.ElevatedButton(btn_label, on_click=self.save_mesai, bgcolor=btn_color, color="white", height=50, width=float("inf")),
            ft.ElevatedButton("VAZGEÇ", on_click=self.cancel_edit, bgcolor="red", color="white", visible=is_edit, width=float("inf"))
        ], spacing=20))

    def build_month_tab(self):
        current_ym = datetime.now().strftime("%Y-%m"); now = datetime.now()
        self.cursor.execute("SELECT * FROM mesailer WHERE strftime('%Y-%m', tarih) = ? ORDER BY tarih DESC", (current_ym,))
        rows = self.cursor.fetchall(); toplam_ucret = sum(r[6] for r in rows); toplam_dakika = sum(r[5] for r in rows)
        yuzde = min((toplam_ucret / self.v_hedef), 1.0) if self.v_hedef > 0 else 0
        hedef_container = ft.Container(padding=20, bgcolor=ft.Colors.with_opacity(0.1, self.v_vurgu_renk), border_radius=15, content=ft.Column([
            ft.Row([ft.Text(f"{AYLAR[now.month].upper()} HEDEFİ", weight="bold", size=13), ft.Text(f"%{yuzde*100:.1f}", weight="bold", color=self.v_vurgu_renk)], alignment="spaceBetween"),
            ft.ProgressBar(value=yuzde, color=self.v_vurgu_renk, bgcolor=ft.Colors.GREY_300, height=10),
            ft.Row([ft.Text(f"{toplam_ucret:.0f} ₺", size=12, weight="bold"), ft.Text(f"Hedef: {self.v_hedef:.0f} ₺", size=12)], alignment="spaceBetween")
        ], spacing=8))
        list_col = ft.Column(spacing=10, scroll=ft.ScrollMode.ADAPTIVE, expand=True)
        list_col.controls.append(hedef_container)
        for r in rows:
            list_col.controls.append(ft.Container(bgcolor=ft.Colors.with_opacity(0.05, ft.Colors.ON_SURFACE), padding=15, border_radius=10, content=ft.Row([ft.Column([ft.Text(tr_date_format(r[1]), weight="bold"), ft.Text(f"{r[2]}-{r[3]} | {format_sure(r[5])}", size=12)], expand=True), ft.Text(f"{r[6]:.2f} ₺", weight="bold", color=self.v_vurgu_renk), ft.IconButton(ft.Icons.EDIT_OUTLINED, on_click=lambda _, x=r: self.load_edit(x)), ft.IconButton(ft.Icons.DELETE_OUTLINE, icon_color="red", on_click=lambda _, x=r[0]: self.delete_mesai(x, 1))])))
        bottom_bar = ft.Container(bgcolor=self.v_ana_renk, padding=20, content=ft.Row([ft.Column([ft.Text("TOPLAM SÜRE", size=11, color="white70"), ft.Text(format_sure(toplam_dakika), color="white", weight="bold")]), ft.Column([ft.Text("TOPLAM KAZANÇ", size=11, color="white70"), ft.Text(f"{toplam_ucret:.2f} ₺", color="white", weight="bold", size=20)], horizontal_alignment="end")], alignment="spaceBetween"))
        return ft.Column([list_col, bottom_bar], expand=True, spacing=0)

    def build_finance_tab(self):
        self.cursor.execute("SELECT SUM(miktar) FROM finans WHERE tur IN ('ekstra', 'mesai_devir')"); alacak = self.cursor.fetchone()[0] or 0
        self.cursor.execute("SELECT SUM(miktar) FROM finans WHERE tur='alinan'"); alinan = self.cursor.fetchone()[0] or 0
        bakiye = alacak - alinan
        f_list = ft.Column(spacing=5, scroll=ft.ScrollMode.ADAPTIVE)
        self.cursor.execute("SELECT * FROM finans ORDER BY tarih DESC")
        for fr in self.cursor.fetchall(): f_list.controls.append(ft.ListTile(leading=ft.Icon(ft.Icons.PAYMENTS, color="green" if fr[1] != 'alinan' else "red"), title=ft.Text(fr[4]), subtitle=ft.Text(tr_date_format(fr[3])), trailing=ft.Text(f"{fr[2]:.2f} ₺")))
        self.txt_fin_amount = ft.TextField(label="Tutar", expand=1); self.txt_fin_desc = ft.TextField(label="Açıklama", expand=2)
        return ft.Column([ft.Container(padding=20, content=ft.Column([ft.Text("BAKİYE", size=12), ft.Text(f"{bakiye:.2f} ₺", size=32, weight="bold", color=self.v_vurgu_renk), ft.Row([self.txt_fin_amount, self.txt_fin_desc]), ft.Row([ft.ElevatedButton("Ödeme Al", on_click=lambda _: self.add_finance("alinan"), bgcolor="red", color="white"), ft.ElevatedButton("Ekstra", on_click=lambda _: self.add_finance("ekstra"), bgcolor=self.v_ana_renk, color="white")], alignment="spaceBetween")])), ft.Divider(), ft.Container(content=f_list, expand=True)], expand=True)

    def build_history_tab(self):
        # BURADA DÜZELTME YAPILDI: SQL sorgusuna dakika eklendi
        self.cursor.execute("SELECT strftime('%Y-%m', tarih) as ay, SUM(ucret), SUM(sure_dakika) FROM mesailer GROUP BY ay ORDER BY ay DESC"); aylar = self.cursor.fetchall()
        hist_view = ft.Column(scroll=ft.ScrollMode.ADAPTIVE, spacing=10)
        for ay_data in aylar:
            yil_ay = ay_data[0].split("-"); ay_adi = f"{AYLAR[int(yil_ay[1])]} {yil_ay[0]}"
            toplam_para = ay_data[1]
            toplam_dk = ay_data[2] # Dakika verisi çekildi
            alt_bilgi = f"{toplam_para:.2f} ₺ | {format_sure(toplam_dk)}" # Formatlandı
            
            self.cursor.execute("SELECT * FROM mesailer WHERE strftime('%Y-%m', tarih) = ? ORDER BY tarih DESC", (ay_data[0],))
            tiles = [ft.Container(padding=5, content=ft.Row([ft.Column([ft.Text(tr_date_format(m[1]), size=14), ft.Text(f"{m[2]}-{m[3]} | {format_sure(m[5])}", size=12, color="grey")], expand=True), ft.Text(f"{m[6]:.2f} ₺", weight="bold"), ft.IconButton(ft.Icons.EDIT_OUTLINED, on_click=lambda _, x=m: self.load_edit(x)), ft.IconButton(ft.Icons.DELETE_OUTLINE, icon_color="red", on_click=lambda _, x=m[0]: self.delete_mesai(x, 3))])) for m in self.cursor.fetchall()]
            hist_view.controls.append(ft.Container(content=ft.ExpansionTile(leading=ft.Icon(ft.Icons.HISTORY), title=ft.Text(ay_adi, weight="bold"), subtitle=ft.Text(alt_bilgi, color=self.v_vurgu_renk), controls=tiles), border_radius=10, bgcolor=ft.Colors.with_opacity(0.05, ft.Colors.ON_SURFACE)))
        return ft.Column([ft.Container(padding=20, content=ft.Text("GEÇMİŞ", size=18, weight="bold")), ft.Container(content=hist_view, expand=True, padding=15)], expand=True)

    def save_mesai(self, e):
        if not (self.start_time and self.end_time): return
        
        # Giriş yapılan değerleri al
        maas = float(self.txt_salary.value)
        katsayi = float(self.txt_katsayi.value)
        
        # Süre hesaplama (Gece vardiyası geçişi dahil)
        t1 = datetime.combine(date.today(), self.start_time)
        t2 = datetime.combine(date.today(), self.end_time)
        if t2 < t1: 
            t2 += timedelta(days=1)
        
        # Toplam çalışılan dakika
        dk = int((t2 - t1).total_seconds() / 60)
        
        # --- SENİN FORMÜLÜN: Maaş / 30 / 9 / 60 ---
        # 1. Günlük ücret (Maaş / 30)
        # 2. Saatlik ücret (Günlük / 9)
        # 3. Dakikalık ücret (Saatlik / 60)
        dakika_ucreti = ((maas / 30) / 9) / 60
        
        # Toplam ücret = Dakika Ücreti * Toplam Dakika * Katsayı
        ucret = round(dakika_ucreti * dk * katsayi, 2)
        
        tarih = self.selected_date.strftime("%Y-%m-%d")
        
        # Veritabanı işlemleri
        if self.editing_id: 
            self.cursor.execute("UPDATE mesailer SET tarih=?, baslangic=?, bitis=?, maas=?, sure_dakika=?, ucret=? WHERE id=?", 
                                (tarih, self.start_time.strftime("%H:%M"), self.end_time.strftime("%H:%M"), maas, dk, ucret, self.editing_id))
            self.editing_id = None
        else: 
            self.cursor.execute("INSERT INTO mesailer (tarih, baslangic, bitis, maas, sure_dakika, ucret) VALUES (?,?,?,?,?,?)", 
                                (tarih, self.start_time.strftime("%H:%M"), self.end_time.strftime("%H:%M"), maas, dk, ucret))
        
        self.conn.commit()
        self.nav_bar.selected_index = 1
        self.load_tab(1)

    def show_msg(self, t, c):
        # BURADA DÜZELTME YAPILDI: Snack bar yeni sürüme uyarlandı
        self.page.open(ft.SnackBar(ft.Text(t), bgcolor=c))
        self.page.update()

    def restore_result(self, e: ft.FilePickerResultEvent):
        if e.files:
            shutil.copy2(e.files[0].path, self.db_path); self.init_db(); self.load_settings()
            self.update_theme_colors(); self.show_msg("Yedek Yüklendi!", "green"); self.show_settings_view()

    def backup_result(self, e):
        if e.path: shutil.copy2(self.db_path, e.path); self.show_msg("Yedek Alındı", "green")

    def toggle_settings(self, e):
        self.current_view = "settings" if self.current_view == "main" else "main"
        self.nav_bar.visible = (self.current_view == "main")
        if self.current_view == "settings": self.show_settings_view()
        else: self.load_tab(self.nav_bar.selected_index)

    def change_theme(self, e):
        self.v_tema = "dark" if e.control.value else "light"
        self.cursor.execute("UPDATE ayarlar SET tema_modu=? WHERE id=1", (self.v_tema,)); self.conn.commit()
        self.update_theme_colors()

    def on_date_change(self, e): self.selected_date = self.date_picker.value; self.load_tab(0)
    def on_start_time_change(self, e): self.start_time = self.time_picker_start.value; self.load_tab(0)
    def on_end_time_change(self, e): self.end_time = self.time_picker_end.value; self.load_tab(0)
    def open_picker(self, p): p.open = True; self.page.update()
    def nav_change(self, e): self.nav_bar.selected_index = int(e.data); self.load_tab(self.nav_bar.selected_index)
    def load_edit(self, r): self.editing_id, self.selected_date, self.start_time, self.end_time, self.last_salary = r[0], datetime.strptime(r[1], "%Y-%m-%d"), datetime.strptime(r[2], "%H:%M").time(), datetime.strptime(r[3], "%H:%M").time(), r[4]; self.nav_bar.selected_index = 0; self.load_tab(0)
    def cancel_edit(self, e): self.editing_id = None; self.load_tab(0)
    def delete_mesai(self, row_id, tab): self.cursor.execute("DELETE FROM mesailer WHERE id=?", (row_id,)); self.conn.commit(); self.load_tab(tab)
    def add_finance(self, tur):
        if not self.txt_fin_amount.value: return
        self.cursor.execute("INSERT INTO finans (tur, miktar, tarih, aciklama) VALUES (?, ?, ?, ?)", (tur, float(self.txt_fin_amount.value), date.today().strftime("%Y-%m-%d"), self.txt_fin_desc.value or "İşlem")); self.conn.commit(); self.load_tab(2)

def main(page: ft.Page): MesaiApp(page)
ft.app(target=main)
