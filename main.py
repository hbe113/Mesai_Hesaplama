import flet as ft
import shutil
import os
import threading # Hızlandırma için kritik
from datetime import datetime, date, timedelta

from database.db_manager import DBManager
from utils.helpers import tr_date_format
from views.add_view import build_add_view
from views.month_view import build_month_view
from views.finance_view import build_finance_view
from views.history_view import build_history_view
from views.settings_view import build_settings_view

class MesaiApp:
    def __init__(self, page: ft.Page):
        self.page = page
        self.page.title = "Mesai Takip"
        self.page.padding = 0
        self.page.spacing = 0
        
        # --- 1. HIZLANDIRMA: Varsayılan Değerler ---
        # Veritabanı yüklenene kadar UI'ın çökmemesi için geçici renkler
        self.v_ana_renk = "#1A237E" 
        self.v_vurgu_renk = "#00BFA5"
        self.v_tema = "dark"
        self.view_cache = {} # Sayfa önbelleği
        
        # Durum Değişkenleri
        self.editing_id = None 
        self.selected_date = datetime.now()
        self.start_time = None
        self.end_time = None
        self.current_view = "main"
        self.target_color_input = None
        self.target_color_preview = None

        # --- 2. Arayüz Bileşenlerini Hazırla (Hızlı) ---
        self.init_ui_components()
        
        # --- 3. Arka Planda Yükleme Başlat ---
        # Beyaz ekran süresini azaltmak için ağır işleri Thread içine alıyoruz
        threading.Thread(target=self.initial_boot, daemon=True).start()

    def init_ui_components(self):
        """Uygulama iskeletini hızlıca oluşturur"""
        self.date_picker = ft.DatePicker(on_change=self.on_date_change)
        self.time_picker_start = ft.TimePicker(on_change=self.on_start_time_change)
        self.time_picker_end = ft.TimePicker(on_change=self.on_end_time_change)
        self.backup_dialog = ft.FilePicker(on_result=self.backup_result)
        self.restore_dialog = ft.FilePicker(on_result=self.restore_result)
        
        self.page.overlay.extend([
            self.date_picker, self.time_picker_start, 
            self.time_picker_end, self.backup_dialog, self.restore_dialog
        ])

        self.nav_bar = ft.NavigationBar(
            destinations=[
                ft.NavigationBarDestination(icon=ft.Icons.ADD_CIRCLE_OUTLINE, label="Ekle"),
                ft.NavigationBarDestination(icon=ft.Icons.CALENDAR_MONTH_OUTLINED, label="Bu Ay"),
                ft.NavigationBarDestination(icon=ft.Icons.ACCOUNT_BALANCE_WALLET_OUTLINED, label="Finans"),
                ft.NavigationBarDestination(icon=ft.Icons.HISTORY_OUTLINED, label="Geçmiş"),
            ],
            on_change=self.nav_change,
            selected_index=0,
            visible=False # Veri gelene kadar gizli kalsın
        )

        self.content_area = ft.Column(expand=True, spacing=0)
        
        # Yükleme ekranı (Beyaz ekran yerine kullanıcı bunu görür)
        self.loader = ft.Container(
            content=ft.ProgressRing(color=self.v_vurgu_renk),
            alignment=ft.alignment.center,
            expand=True
        )

        self.app_bar = ft.Container(
            content=ft.Row([
                ft.Container(width=10), 
                ft.Text("MESAİ TAKİP", size=18, weight="bold", color="white"),
                ft.IconButton(ft.Icons.SETTINGS, icon_color="white", on_click=self.toggle_settings),
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            bgcolor=self.v_ana_renk,
            padding=ft.padding.only(top=35, bottom=5, left=10, right=10),
        )

        self.page.add(self.app_bar, self.content_area, self.nav_bar)
        self.content_area.controls.append(self.loader)
        self.page.update()

    def initial_boot(self):
        """Ağır yüklemelerin yapıldığı arka plan fonksiyonu"""
        self.db = DBManager()
        self.load_settings()
        self.db.sync_past_months_finance()
        
        # Arayüzü güncelle
        self.update_theme_colors()
        self.nav_bar.visible = True
        self.load_tab(0)

    def load_settings(self):
        res = self.db.get_settings()
        self.v_maas, self.v_katsayi, self.v_tema, self.v_ana_renk, self.v_vurgu_renk, self.v_hedef = res

    def update_theme_colors(self):
        self.page.theme_mode = ft.ThemeMode.DARK if self.v_tema == "dark" else ft.ThemeMode.LIGHT
        self.page.theme = ft.Theme(color_scheme_seed=self.v_vurgu_renk)
        if hasattr(self, 'app_bar'): self.app_bar.bgcolor = self.v_ana_renk
        self.page.update()

    def load_tab(self, index):
        """HIZLANDIRMA: Sayfa önbellekleme sistemi"""
        self.content_area.controls.clear()
        
        # Veri değişmiş olabileceği için her seferinde taze build ediyoruz 
        # (Alternatif: Sadece veri eklendiğinde cache'i temizle)
        if index == 0: view = build_add_view(self)
        elif index == 1: view = build_month_view(self)
        elif index == 2: view = build_finance_view(self)
        elif index == 3: view = build_history_view(self)
        
        self.content_area.controls.append(view)
        self.page.update()

    def nav_change(self, e):
        self.nav_bar.selected_index = int(e.data)
        self.load_tab(self.nav_bar.selected_index)

    def toggle_settings(self, e):
        self.current_view = "settings" if self.current_view == "main" else "main"
        self.nav_bar.visible = (self.current_view == "main")
        if self.current_view == "settings":
            self.content_area.controls.clear()
            self.content_area.controls.append(build_settings_view(self))
        else:
            self.load_tab(self.nav_bar.selected_index)
        self.page.update()

    def save_mesai(self, e):
        if not (self.start_time and self.end_time): return
        try:
            maas = float(self.txt_salary.value)
            katsayi = float(self.txt_katsayi.value)
            
            t1 = datetime.combine(date.today(), self.start_time)
            t2 = datetime.combine(date.today(), self.end_time)
            if t2 < t1: t2 += timedelta(days=1)
            
            dk = int((t2 - t1).total_seconds() / 60)
            dakika_ucreti = ((maas / 30) / 9) / 60
            ucret = round(dakika_ucreti * dk * katsayi, 2)
            tarih = self.selected_date.strftime("%Y-%m-%d")
            
            data = (tarih, self.start_time.strftime("%H:%M"), self.end_time.strftime("%H:%M"), maas, dk, ucret)
            self.db.save_mesai(data, self.editing_id)
            
            self.editing_id = None
            self.nav_bar.selected_index = 1
            self.load_tab(1)
        except Exception as ex:
            self.show_msg(f"Hata: {str(ex)}", "red")

    def delete_mesai(self, row_id, tab_index):
        self.db.delete_mesai(row_id)
        self.load_tab(tab_index)

    def add_finance(self, tur):
        if not self.txt_fin_amount.value: return
        try:
            self.db.add_finance_record(tur, float(self.txt_fin_amount.value), self.txt_fin_desc.value or "İşlem")
            self.load_tab(2)
        except:
            self.show_msg("Geçersiz Tutar", "red")

    def load_edit(self, r):
        self.editing_id = r[0]
        self.selected_date = datetime.strptime(r[1], "%Y-%m-%d")
        self.start_time = datetime.strptime(r[2], "%H:%M").time()
        self.end_time = datetime.strptime(r[3], "%H:%M").time()
        self.last_salary = r[4]
        self.nav_bar.selected_index = 0
        self.load_tab(0)

    def cancel_edit(self, e):
        self.editing_id = None
        self.load_tab(0)

    def change_theme(self, e):
        self.v_tema = "dark" if e.control.value else "light"
        self.db.cursor.execute("UPDATE ayarlar SET tema_modu=? WHERE id=1", (self.v_tema,))
        self.db.conn.commit()
        self.update_theme_colors()

    def show_msg(self, t, c):
        self.page.open(ft.SnackBar(ft.Text(t), bgcolor=c))

    def backup_result(self, e):
        if e.path:
            shutil.copy2(self.db.db_path, e.path)
            self.show_msg("Yedek Alındı", "green")

    def restore_result(self, e):
        if e.files:
            try:
                shutil.copy2(e.files[0].path, self.db.db_path)
                self.db = DBManager() 
                self.load_settings()
                self.update_theme_colors()
                self.show_msg("Yedek Yüklendi!", "green")
                self.content_area.controls.clear()
                self.content_area.controls.append(build_settings_view(self))
                self.page.update()
            except Exception as ex:
                self.show_msg(f"Hata: {str(ex)}", "red")

    def open_picker(self, p):
        p.open = True
        self.page.update()

    def on_date_change(self, e): self.selected_date = self.date_picker.value; self.load_tab(0)
    def on_start_time_change(self, e): self.start_time = self.time_picker_start.value; self.load_tab(0)
    def on_end_time_change(self, e): self.end_time = self.time_picker_end.value; self.load_tab(0)

def main(page: ft.Page):
    MesaiApp(page)

if __name__ == "__main__":
    ft.app(target=main)