import flet as ft
import sqlite3
import os
from datetime import datetime, date, timedelta

# Excel kütüphaneleri
try:
    import pandas as pd
except ImportError:
    pd = None

# --- RENK PALETİ VE YARDIMCI FONKSİYONLAR (Değişmedi) ---
PRIMARY = "#1A237E"
ACCENT = "#00BFA5"
BG_COLOR = "#F4F7F9"
CARD_COLOR = "#FFFFFF"
TEXT_MAIN = "#263238"
WHITE_COLOR = "#FFFFFF"

AYLAR = {
    1: "Ocak", 2: "Şubat", 3: "Mart", 4: "Nisan", 5: "Mayıs", 6: "Haziran",
    7: "Temmuz", 8: "Ağustos", 9: "Eylül", 10: "Ekim", 11: "Kasım", 12: "Aralık"
}

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
        self.page.title = "Mesai Takip Pro"
        self.page.bgcolor = BG_COLOR
        self.page.theme_mode = ft.ThemeMode.LIGHT
        self.page.padding = 0
        self.page.spacing = 0

        self.init_db()
        self.check_monthly_rollover()

        self.editing_id = None 
        self.selected_date = datetime.now()
        self.start_time = None
        self.end_time = None
        self.last_salary = ""

        # --- FILE PICKER (Yeni Eklenen Kısım) ---
        self.save_file_dialog = ft.FilePicker(on_result=self.save_file_result)
        self.page.overlay.append(self.save_file_dialog)

        # --- PICKERLAR ---
        self.date_picker = ft.DatePicker(on_change=self.on_date_change)
        self.time_picker_start = ft.TimePicker(on_change=self.on_start_time_change)
        self.time_picker_end = ft.TimePicker(on_change=self.on_end_time_change)
        self.page.overlay.extend([self.date_picker, self.time_picker_start, self.time_picker_end])

        # --- NAVBAR ---
        self.nav_bar = ft.NavigationBar(
            destinations=[
                ft.NavigationBarDestination(icon=ft.Icons.ADD_CIRCLE_OUTLINE, label="Ekle"),
                ft.NavigationBarDestination(icon=ft.Icons.CALENDAR_MONTH_OUTLINED, label="Bu Ay"),
                ft.NavigationBarDestination(icon=ft.Icons.WALLET_OUTLINED, label="Finans"),
                ft.NavigationBarDestination(icon=ft.Icons.HISTORY_OUTLINED, label="Geçmiş"),
            ],
            on_change=self.nav_change,
            selected_index=0,
            bgcolor=CARD_COLOR,
        )

        self.content_area = ft.Column(expand=True, spacing=0)

        self.page.add(
            ft.Container(
                content=ft.Row([
                    ft.Icon(ft.Icons.TRACK_CHANGES, color=WHITE_COLOR, size=24),
                    ft.Text("MESAİ TAKİP PRO", size=18, weight="bold", color=WHITE_COLOR),
                ], alignment=ft.MainAxisAlignment.CENTER),
                bgcolor=PRIMARY,
                padding=15,
            ),
            self.content_area,
            self.nav_bar
        )
        self.load_tab(0)

    # --- EXCEL KAYDETME MANTIĞI (GÜNCELLENDİ) ---
    def export_to_excel_click(self, e):
        if pd is None:
            self.show_msg("Hata: pandas kütüphanesi eksik!", "red")
            return
        
        # Kullanıcıya dosyayı nereye kaydedeceğini soran pencereyi aç
        # Varsayılan dosya adını tarihle birlikte veriyoruz
        default_name = f"Mesai_Raporu_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
        self.save_file_dialog.save_file(
            file_name=default_name,
            allowed_extensions=["xlsx"]
        )

    def save_file_result(self, e: ft.FilePickerResultEvent):
        if not e.path: # Kullanıcı vazgeçerse
            return
        
        try:
            self.cursor.execute("SELECT tarih, baslangic, bitis, sure_dakika, maas, ucret FROM mesailer ORDER BY tarih DESC")
            rows = self.cursor.fetchall()
            
            data = []
            for r in rows:
                data.append({
                    "Tarih": r[0],
                    "Giriş": r[1],
                    "Çıkış": r[2],
                    "Süre": format_sure(r[3]),
                    "Baz Maaş": r[4],
                    "Kazanç (TL)": r[5]
                })
            
            df = pd.DataFrame(data)
            # Seçilen yola (e.path) kaydet
            df.to_excel(e.path, index=False)
            self.show_msg(f"Dosya başarıyla kaydedildi: {os.path.basename(e.path)}", "green")
            
        except Exception as ex:
            self.show_msg(f"Excel hatası: {str(ex)}", "red")

    def show_msg(self, text, color):
        self.page.snack_bar = ft.SnackBar(ft.Text(text), bgcolor=color)
        self.page.snack_bar.open = True
        self.page.update()

    # --- DİĞER FONKSİYONLAR (Değişmedi, v7.1 ile aynı) ---
    def init_db(self):
        self.conn = sqlite3.connect("mesai_v4.db", check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.cursor.execute("CREATE TABLE IF NOT EXISTS mesailer (id INTEGER PRIMARY KEY, tarih TEXT, baslangic TEXT, bitis TEXT, maas REAL, sure_dakika INTEGER, ucret REAL)")
        self.cursor.execute("CREATE TABLE IF NOT EXISTS finans (id INTEGER PRIMARY KEY, tur TEXT, miktar REAL, tarih TEXT, aciklama TEXT)")
        self.conn.commit()

    def nav_change(self, e):
        self.nav_bar.selected_index = int(e.data)
        self.load_tab(self.nav_bar.selected_index)

    def load_tab(self, index):
        self.content_area.controls.clear()
        if index == 0: self.content_area.controls.append(self.build_add_tab())
        elif index == 1: self.content_area.controls.append(self.build_month_tab())
        elif index == 2: self.content_area.controls.append(self.build_finance_tab())
        elif index == 3: self.content_area.controls.append(self.build_history_tab())
        self.page.update()

    def build_add_tab(self):
        start_txt = self.start_time.strftime("%H:%M") if self.start_time else "Giriş"
        end_txt = self.end_time.strftime("%H:%M") if self.end_time else "Bitiş"
        action_text = "GÜNCELLE" if self.editing_id else "MESAİ KAYDET"
        action_icon = ft.Icons.EDIT if self.editing_id else ft.Icons.ADD_TASK_ROUNDED
        self.txt_salary = ft.TextField(label="Maaş (TL)", value=self.last_salary, keyboard_type=ft.KeyboardType.NUMBER, border_radius=12, bgcolor=WHITE_COLOR)
        self.btn_date_display = ft.Container(content=ft.Row([ft.Icon(ft.Icons.CALENDAR_MONTH, color=PRIMARY), ft.Text(tr_date_format(self.selected_date), weight="bold")], alignment=ft.MainAxisAlignment.CENTER), padding=15, border=ft.border.all(1, ft.Colors.BLACK12), border_radius=12, bgcolor=WHITE_COLOR, on_click=lambda _: self.open_picker(self.date_picker))
        return ft.Container(padding=25, expand=True, content=ft.Column([ft.Container(ft.Icon(action_icon, size=60, color=PRIMARY), alignment=ft.alignment.center), ft.Text(action_text, size=22, weight="bold", color=TEXT_MAIN, text_align=ft.TextAlign.CENTER, width=float("inf")), self.btn_date_display, ft.Row([ft.ElevatedButton(start_txt, icon=ft.Icons.ACCESS_TIME, on_click=lambda _: self.open_picker(self.time_picker_start), expand=True), ft.ElevatedButton(end_txt, icon=ft.Icons.ACCESS_TIME_FILLED, on_click=lambda _: self.open_picker(self.time_picker_end), expand=True)], spacing=15), self.txt_salary, ft.ElevatedButton(content=ft.Text(action_text, color=WHITE_COLOR, weight="bold"), on_click=self.save_mesai, bgcolor=ACCENT if not self.editing_id else ft.Colors.ORANGE_700, height=50, width=float("inf"), style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=12))), ft.TextButton("Vazgeç", on_click=self.cancel_edit, visible=self.editing_id is not None)], spacing=20, scroll=ft.ScrollMode.ADAPTIVE))

    def build_month_tab(self):
        current_ym = datetime.now().strftime("%Y-%m")
        self.cursor.execute("SELECT * FROM mesailer WHERE strftime('%Y-%m', tarih) = ? ORDER BY tarih DESC", (current_ym,))
        rows = self.cursor.fetchall()
        toplam_ucret = sum(r[6] for r in rows); toplam_dakika = sum(r[5] for r in rows)
        list_col = ft.Column(spacing=12, scroll=ft.ScrollMode.ADAPTIVE)
        for r in rows:
            dt = datetime.strptime(r[1], "%Y-%m-%d"); sure_str = format_sure(r[5])
            list_col.controls.append(ft.Container(bgcolor=CARD_COLOR, padding=12, border_radius=12, content=ft.Row([ft.Column([ft.Text(tr_date_format(dt), weight="bold", size=14), ft.Text(f"{r[2]} - {r[3]} | {sure_str}", size=12, color=ft.Colors.BLUE_GREY_600)], expand=True), ft.Text(f"{r[6]:.2f} TL", weight="bold", color=PRIMARY), ft.IconButton(ft.Icons.EDIT, icon_size=20, on_click=lambda _, x=r: self.load_edit(x)), ft.IconButton(ft.Icons.DELETE, icon_size=20, icon_color=ft.Colors.RED, on_click=lambda _, x=r[0]: self.delete_mesai(x, 1))])))
        return ft.Column([ft.Container(content=list_col, expand=True, padding=15), ft.Container(bgcolor=PRIMARY, padding=15, content=ft.Row([ft.Column([ft.Text("TOPLAM SÜRE", size=10, color=ft.Colors.BLUE_GREY_100), ft.Text(format_sure(toplam_dakika), color=WHITE_COLOR, weight="bold", size=15)]), ft.Column([ft.Text("TOPLAM KAZANÇ", size=10, color=ft.Colors.BLUE_GREY_100, text_align=ft.TextAlign.RIGHT), ft.Text(f"{toplam_ucret:.2f} TL", color=ACCENT, weight="bold", size=20)], horizontal_alignment=ft.CrossAxisAlignment.END)], alignment=ft.MainAxisAlignment.SPACE_BETWEEN))], expand=True, spacing=0)

    def build_history_tab(self):
        self.cursor.execute("SELECT strftime('%Y-%m', tarih) as ay, SUM(ucret), SUM(sure_dakika) FROM mesailer GROUP BY ay ORDER BY ay DESC")
        aylar = self.cursor.fetchall()
        header = ft.Row([ft.Text("GEÇMİŞ MESAİLER", size=16, weight="bold", color=TEXT_MAIN), ft.IconButton(ft.Icons.FILE_DOWNLOAD, tooltip="Excel'e Aktar", on_click=self.export_to_excel_click)], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
        history_items = ft.Column(scroll=ft.ScrollMode.ADAPTIVE)
        for ay_data in aylar:
            ay_kodu = ay_data[0]; toplam_ucret = ay_data[1]; toplam_dakika = ay_data[2]
            dt_ay = datetime.strptime(ay_kodu, "%Y-%m")
            self.cursor.execute("SELECT * FROM mesailer WHERE strftime('%Y-%m', tarih) = ? ORDER BY tarih DESC", (ay_kodu,))
            alt_mesailer = self.cursor.fetchall()
            tile_content = []
            for m in alt_mesailer:
                sure_str = format_sure(m[5])
                tile_content.append(ft.ListTile(leading=ft.Icon(ft.Icons.SCHEDULE, size=20), title=ft.Text(f"{tr_date_format(m[1])}", size=13, weight="bold"), subtitle=ft.Text(f"{m[2]}-{m[3]} | {sure_str}", size=12), trailing=ft.Row([ft.Text(f"{m[6]:.2f} TL", color=PRIMARY, weight="bold"), ft.IconButton(ft.Icons.EDIT, scale=0.8, on_click=lambda _, x=m: self.load_edit(x)), ft.IconButton(ft.Icons.DELETE, scale=0.8, icon_color="red", on_click=lambda _, x=m[0]: self.delete_mesai(x, 3))], tight=True)))
            history_items.controls.append(ft.ExpansionTile(title=ft.Text(f"{AYLAR[dt_ay.month]} {dt_ay.year}", weight="bold"), subtitle=ft.Row([ft.Text(f"{toplam_ucret:.2f} TL", color=ACCENT, weight="bold"), ft.Text(f"| {format_sure(toplam_dakika)}", size=12, color=ft.Colors.GREY_700)], spacing=5), leading=ft.Icon(ft.Icons.HISTORY), controls=tile_content))
        return ft.Column([ft.Container(content=header, padding=15, bgcolor=WHITE_COLOR), ft.Container(content=history_items, expand=True, padding=15)], expand=True, spacing=0)

    # --- YARDIMCI METODLAR ---
    def open_picker(self, picker):
        picker.open = True
        self.page.update()

    def on_date_change(self, e):
        self.selected_date = self.date_picker.value
        self.load_tab(0)

    def on_start_time_change(self, e):
        self.start_time = self.time_picker_start.value
        self.load_tab(0)

    def on_end_time_change(self, e):
        self.end_time = self.time_picker_end.value
        self.load_tab(0)

    def load_edit(self, r):
        self.editing_id = r[0]; self.selected_date = datetime.strptime(r[1], "%Y-%m-%d"); self.start_time = datetime.strptime(r[2], "%H:%M").time(); self.end_time = datetime.strptime(r[3], "%H:%M").time(); self.last_salary = str(r[4]); self.nav_bar.selected_index = 0; self.load_tab(0)

    def cancel_edit(self, e):
        self.editing_id = None; self.start_time = None; self.end_time = None; self.load_tab(0)

    def save_mesai(self, e):
        if not (self.start_time and self.end_time and self.txt_salary.value): return
        self.last_salary = self.txt_salary.value; maas = float(self.last_salary); t1 = datetime.combine(date.today(), self.start_time); t2 = datetime.combine(date.today(), self.end_time)
        if t2 < t1: t2 += timedelta(days=1)
        dk = int((t2 - t1).total_seconds() / 60); ucret = (maas / 225 / 60) * dk * 1.5; tarih_db = self.selected_date.strftime("%Y-%m-%d")
        if self.editing_id:
            self.cursor.execute("UPDATE mesailer SET tarih=?, baslangic=?, bitis=?, maas=?, sure_dakika=?, ucret=? WHERE id=?", (tarih_db, self.start_time.strftime("%H:%M"), self.end_time.strftime("%H:%M"), maas, dk, ucret, self.editing_id)); self.editing_id = None
        else:
            self.cursor.execute("INSERT INTO mesailer (tarih, baslangic, bitis, maas, sure_dakika, ucret) VALUES (?,?,?,?,?,?)", (tarih_db, self.start_time.strftime("%H:%M"), self.end_time.strftime("%H:%M"), maas, dk, ucret))
        self.conn.commit(); self.check_monthly_rollover(); self.nav_bar.selected_index = 1; self.load_tab(1)

    def delete_mesai(self, row_id, tab_to_return):
        self.cursor.execute("DELETE FROM mesailer WHERE id=?", (row_id,)); self.conn.commit(); self.check_monthly_rollover(); self.load_tab(tab_to_return)

    def build_finance_tab(self):
        self.cursor.execute("SELECT SUM(miktar) FROM finans WHERE tur IN ('ekstra', 'mesai_devir')"); alacak = self.cursor.fetchone()[0] or 0
        self.cursor.execute("SELECT SUM(miktar) FROM finans WHERE tur='alinan'"); alinan = self.cursor.fetchone()[0] or 0
        bakiye = alacak - alinan; self.cursor.execute("SELECT * FROM finans ORDER BY tarih DESC"); rows = self.cursor.fetchall()
        hist_col = ft.Column(spacing=2, scroll=ft.ScrollMode.ADAPTIVE)
        for r in rows:
            is_inc = r[1] in ['ekstra', 'mesai_devir']
            hist_col.controls.append(ft.ListTile(leading=ft.Icon(ft.Icons.ARROW_UPWARD if is_inc else ft.Icons.ARROW_DOWNWARD, color="green" if is_inc else "red"), title=ft.Text(r[4] or "İşlem", weight="bold"), subtitle=ft.Text(tr_date_format(r[3])), trailing=ft.Text(f"{r[2]:.2f} TL", color="green" if is_inc else "red", weight="bold")))
        self.txt_fin_amount = ft.TextField(label="Tutar", width=110, bgcolor=WHITE_COLOR); self.txt_fin_desc = ft.TextField(label="Açıklama", expand=True, bgcolor=WHITE_COLOR)
        return ft.Column([ft.Container(padding=20, bgcolor=WHITE_COLOR, content=ft.Column([ft.Text("TOPLAM BAKİYE", size=12, color="bluegrey"), ft.Text(f"{bakiye:.2f} TL", size=32, weight="bold", color=PRIMARY), ft.Row([self.txt_fin_amount, self.txt_fin_desc]), ft.Row([ft.ElevatedButton("Ödeme Al", on_click=lambda _: self.add_finance("alinan"), color=WHITE_COLOR, bgcolor="red"), ft.ElevatedButton("Ekstra Ekle", on_click=lambda _: self.add_finance("ekstra"), color=WHITE_COLOR, bgcolor=ACCENT)], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)])), ft.Container(content=ft.Text("İŞLEMLER", size=13, weight="bold"), padding=15), ft.Container(content=hist_col, expand=True)], expand=True)

    def add_finance(self, tur):
        if not self.txt_fin_amount.value: return
        self.cursor.execute("INSERT INTO finans (tur, miktar, tarih, aciklama) VALUES (?, ?, ?, ?)", (tur, float(self.txt_fin_amount.value), date.today().strftime("%Y-%m-%d"), self.txt_fin_desc.value or "İşlem")); self.conn.commit(); self.load_tab(2)

    def check_monthly_rollover(self):
        try:
            today = date.today(); first_day_curr = date(today.year, today.month, 1); self.cursor.execute("SELECT MIN(tarih) FROM mesailer"); res = self.cursor.fetchone()
            if not res or not res[0]: return
            sd = datetime.strptime(res[0], "%Y-%m-%d").date(); sd = date(sd.year, sd.month, 1)
            while sd < first_day_curr:
                ym = sd.strftime("%Y-%m"); aciklama = f"{AYLAR[sd.month]} {sd.year} Mesai Ücreti"
                self.cursor.execute("SELECT SUM(ucret) FROM mesailer WHERE strftime('%Y-%m', tarih) = ?", (ym,)); total = self.cursor.fetchone()[0] or 0.0
                self.cursor.execute("SELECT id FROM finans WHERE tur='mesai_devir' AND aciklama=?", (aciklama,)); fin_row = self.cursor.fetchone()
                if total > 0:
                    if fin_row: self.cursor.execute("UPDATE finans SET miktar=? WHERE id=?", (total, fin_row[0]))
                    else: self.cursor.execute("INSERT INTO finans (tur, miktar, tarih, aciklama) VALUES ('mesai_devir', ?, ?, ?)", (total, date.today().strftime("%Y-%m-%d"), aciklama))
                elif fin_row: self.cursor.execute("DELETE FROM finans WHERE id=?", (fin_row[0],))
                nm = sd.month % 12 + 1; ny = sd.year + (sd.month // 12); sd = date(ny, nm, 1)
            self.conn.commit()
        except: pass

def main(page: ft.Page):
    MesaiApp(page)

if __name__ == "__main__":
    ft.app(target=main)
