import flet as ft
import sqlite3
import shutil
from datetime import datetime, date, timedelta

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
        
        self.editing_id = None 
        self.selected_date = datetime.now()
        self.start_time = None
        self.end_time = None
        self.current_view = "main"
        
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

        self.content_area = ft.Column(expand=True, spacing=0, scroll=ft.ScrollMode.ADAPTIVE)
        self.update_theme_colors()
        
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
        txt_v_maas = ft.TextField(label="Varsayılan Maaş", value=str(self.v_maas))
        txt_v_katsayi = ft.TextField(label="Katsayı", value=str(self.v_katsayi))
        txt_v_hedef = ft.TextField(label="Aylık Hedef (TL)", value=str(self.v_hedef))
        
        txt_ana = ft.TextField(label="Ana Renk HEX", value=self.v_ana_renk)
        txt_vurgu = ft.TextField(label="Vurgu Renk HEX", value=self.v_vurgu_renk)

        def set_color(a, v):
            txt_ana.value = a
            txt_vurgu.value = v
            self.page.update()

        palet = ft.Row([
            ft.IconButton(ft.Icons.CIRCLE, icon_color="#1A237E", on_click=lambda _: set_color("#1A237E", "#00BFA5")),
            ft.IconButton(ft.Icons.CIRCLE, icon_color="#2E7D32", on_click=lambda _: set_color("#2E7D32", "#C6FF00")),
            ft.IconButton(ft.Icons.CIRCLE, icon_color="#B71C1C", on_click=lambda _: set_color("#B71C1C", "#FFD600")),
            ft.IconButton(ft.Icons.CIRCLE, icon_color="#4A148C", on_click=lambda _: set_color("#4A148C", "#EA80FC")),
        ], alignment="center")

        def save_settings(e):
            try:
                self.v_maas, self.v_katsayi, self.v_hedef = float(txt_v_maas.value), float(txt_v_katsayi.value), float(txt_v_hedef.value)
                self.v_ana_renk, self.v_vurgu_renk = txt_ana.value, txt_vurgu.value
                self.cursor.execute("UPDATE ayarlar SET varsayilan_maas=?, mesai_katsayisi=?, aylik_hedef=?, ana_renk=?, vurgu_renk=? WHERE id=1", (self.v_maas, self.v_katsayi, self.v_hedef, self.v_ana_renk, self.v_vurgu_renk))
                self.conn.commit()
                self.update_theme_colors()
                self.toggle_settings(None)
            except: pass

        self.content_area.controls.append(ft.Container(padding=20, content=ft.Column([
            ft.Text("AYARLAR", size=22, weight="bold"),
            txt_v_maas, txt_v_katsayi, txt_v_hedef,
            ft.Divider(),
            ft.Text("Renk Seçimi"),
            txt_ana, txt_vurgu, palet,
            ft.Switch(label="Koyu Tema", value=(self.v_tema == "dark"), on_change=self.change_theme),
            ft.ElevatedButton("KAYDET", on_click=save_settings, bgcolor=self.v_ana_renk, color="white", width=float("inf"))
        ], scroll=ft.ScrollMode.ADAPTIVE)))
        self.page.update()

    def build_add_tab(self):
        is_edit = self.editing_id is not None
        start_txt = self.start_time.strftime("%H:%M") if self.start_time else "Giriş Saati"
        end_txt = self.end_time.strftime("%H:%M") if self.end_time else "Bitiş Saati"
        self.txt_salary = ft.TextField(label="Maaş", value=str(self.v_maas), expand=True)
        self.txt_katsayi = ft.TextField(label="Katsayı", value=str(self.v_katsayi), expand=True)
        
        return ft.Container(padding=20, content=ft.Column([
            ft.Text("YENİ KAYIT", size=20, weight="bold"),
            ft.ElevatedButton(tr_date_format(self.selected_date), icon=ft.Icons.CALENDAR_MONTH, on_click=lambda _: self.open_picker(self.date_picker)),
            ft.Row([
                ft.ElevatedButton(start_txt, on_click=lambda _: self.open_picker(self.time_picker_start), expand=True),
                ft.ElevatedButton(end_txt, on_click=lambda _: self.open_picker(self.time_picker_end), expand=True),
            ]),
            ft.Row([self.txt_salary, self.txt_katsayi]),
            ft.ElevatedButton("KAYDET", on_click=self.save_mesai, bgcolor=self.v_ana_renk, color="white", width=float("inf"), height=50),
        ], spacing=15))

    def build_month_tab(self):
        self.cursor.execute("SELECT * FROM mesailer WHERE strftime('%Y-%m', tarih) = ? ORDER BY tarih DESC", (datetime.now().strftime("%Y-%m"),))
        rows = self.cursor.fetchall()
        toplam_ucret = sum(r[6] for r in rows)
        
        list_col = ft.Column(spacing=10, scroll=ft.ScrollMode.ADAPTIVE, expand=True)
        for r in rows:
            list_col.controls.append(ft.Container(bgcolor=ft.Colors.with_opacity(0.1, ft.Colors.ON_SURFACE), padding=10, border_radius=10, content=ft.Row([
                ft.Column([ft.Text(tr_date_format(r[1]), weight="bold"), ft.Text(f"{r[2]}-{r[3]}")], expand=True),
                ft.Text(f"{r[6]:.2f} TL", weight="bold", color=self.v_vurgu_renk),
                ft.IconButton(ft.Icons.DELETE, icon_color="red", on_click=lambda _, x=r[0]: self.delete_mesai(x, 1))
            ])))
        
        return ft.Column([
            ft.Container(padding=20, content=ft.Text(f"Toplam: {toplam_ucret:.2f} TL", size=20, weight="bold", color=self.v_vurgu_renk)),
            list_col
        ], expand=True)

    def build_finance_tab(self):
        self.cursor.execute("SELECT SUM(miktar) FROM finans WHERE tur='ekstra'"); alacak = self.cursor.fetchone()[0] or 0
        self.cursor.execute("SELECT SUM(miktar) FROM finans WHERE tur='alinan'"); alinan = self.cursor.fetchone()[0] or 0
        self.txt_fin_amount = ft.TextField(label="Tutar", expand=True)
        return ft.Container(padding=20, content=ft.Column([
            ft.Text(f"Bakiye: {alacak-alinan:.2f} TL", size=24, weight="bold"),
            self.txt_fin_amount,
            ft.Row([
                ft.ElevatedButton("Ödeme Al", on_click=lambda _: self.add_finance("alinan"), bgcolor="red", color="white"),
                ft.ElevatedButton("Ekstra", on_click=lambda _: self.add_finance("ekstra"), bgcolor="green", color="white"),
            ])
        ]))

    def build_history_tab(self):
        self.cursor.execute("SELECT strftime('%Y-%m', tarih) as ay, SUM(ucret) FROM mesailer GROUP BY ay ORDER BY ay DESC")
        aylar = self.cursor.fetchall()
        hist_view = ft.Column(scroll=ft.ScrollMode.ADAPTIVE, expand=True)
        for ay in aylar:
            hist_view.controls.append(ft.ListTile(title=ft.Text(ay[0]), trailing=ft.Text(f"{ay[1]:.2f} TL")))
        return ft.Container(padding=20, content=hist_view)

    def save_mesai(self, e):
        if not (self.start_time and self.end_time): return
        maas, katsayi = float(self.txt_salary.value), float(self.txt_katsayi.value)
        t1, t2 = datetime.combine(date.today(), self.start_time), datetime.combine(date.today(), self.end_time)
        if t2 < t1: t2 += timedelta(days=1)
        dk = int((t2 - t1).total_seconds() / 60)
        ucret = round((((maas / 30) / 9) / 60) * dk * katsayi, 2)
        self.cursor.execute("INSERT INTO mesailer (tarih, baslangic, bitis, maas, sure_dakika, ucret) VALUES (?,?,?,?,?,?)", (self.selected_date.strftime("%Y-%m-%d"), self.start_time.strftime("%H:%M"), self.end_time.strftime("%H:%M"), maas, dk, ucret))
        self.conn.commit()
        self.nav_bar.selected_index = 1
        self.load_tab(1)

    def restore_result(self, e): # Hata veren tip tanımı kaldırıldı
        if e.files:
            shutil.copy2(e.files[0].path, self.db_path)
            self.init_db()
            self.load_settings()
            self.update_theme_colors()
            self.load_tab(0)

    def backup_result(self, e):
        if e.path: shutil.copy2(self.db_path, e.path)

    def toggle_settings(self, e):
        self.current_view = "settings" if self.current_view == "main" else "main"
        self.nav_bar.visible = (self.current_view == "main")
        if self.current_view == "settings": self.show_settings_view()
        else: self.load_tab(self.nav_bar.selected_index)

    def change_theme(self, e):
        self.v_tema = "dark" if e.control.value else "light"
        self.cursor.execute("UPDATE ayarlar SET tema_modu=? WHERE id=1", (self.v_tema,))
        self.conn.commit()
        self.update_theme_colors()

    def on_date_change(self, e): self.selected_date = self.date_picker.value; self.load_tab(0)
    def on_start_time_change(self, e): self.start_time = self.time_picker_start.value; self.load_tab(0)
    def on_end_time_change(self, e): self.end_time = self.time_picker_end.value; self.load_tab(0)
    def open_picker(self, p): p.open = True; self.page.update()
    def nav_change(self, e): self.nav_bar.selected_index = int(e.data); self.load_tab(self.nav_bar.selected_index)
    def delete_mesai(self, row_id, tab): self.cursor.execute("DELETE FROM mesailer WHERE id=?", (row_id,)); self.conn.commit(); self.load_tab(tab)
    def add_finance(self, tur):
        if self.txt_fin_amount.value:
            self.cursor.execute("INSERT INTO finans (tur, miktar, tarih, aciklama) VALUES (?, ?, ?, ?)", (tur, float(self.txt_fin_amount.value), date.today().strftime("%Y-%m-%d"), "İşlem"))
            self.conn.commit(); self.load_tab(2)

def main(page: ft.Page):
    MesaiApp(page)

ft.app(target=main)
