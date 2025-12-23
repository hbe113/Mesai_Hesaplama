import flet as ft
import sqlite3
from datetime import datetime
import locale

# Türkçe tarih formatı ayarı
try:
    locale.setlocale(locale.LC_ALL, 'Turkish_Turkey.1254')
except:
    try:
        locale.setlocale(locale.LC_ALL, 'tr_TR') 
    except:
        pass 

class MesaiApp:
    def __init__(self, page: ft.Page):
        self.page = page
        self.page.title = "Mesai Takip"
        self.page.theme_mode = ft.ThemeMode.LIGHT
        self.page.window_width = 400
        self.page.window_height = 750

        self.init_db()

        # Düzenleme modu için değişken
        self.editing_id = None 
        self.selected_date = datetime.now()
        self.start_time = None
        self.end_time = None
        
        # --- UI ELEMANLARI ---
        self.date_picker = ft.DatePicker(on_change=self.on_date_change)
        self.time_picker_start = ft.TimePicker(on_change=self.on_start_time_change)
        self.time_picker_end = ft.TimePicker(on_change=self.on_end_time_change)

        self.btn_date = ft.ElevatedButton(
            text=f"{self.selected_date.strftime('%d %B %Y')}",
            icon=ft.Icons.CALENDAR_MONTH,
            on_click=lambda _: self.page.open(self.date_picker),
            width=300
        )

        self.btn_start_time = ft.ElevatedButton("Seçilmedi", on_click=lambda _: self.page.open(self.time_picker_start))
        self.btn_end_time = ft.ElevatedButton("Seçilmedi", on_click=lambda _: self.page.open(self.time_picker_end))

        self.txt_salary = ft.TextField(label="Maaş (TL)", keyboard_type=ft.KeyboardType.NUMBER, width=300)
        self.btn_save = ft.ElevatedButton("Mesaiyi Kaydet", on_click=self.save_record, bgcolor=ft.Colors.BLUE, color=ft.Colors.WHITE)

        self.main_list_view = ft.ListView(expand=True, spacing=10)
        self.txt_total_hours_main = ft.Text("Bu Ay: 0 Saat 0 Dk", size=16, weight=ft.FontWeight.BOLD)
        self.txt_total_pay_main = ft.Text("Bu Ay Ücret: 0.00 TL", size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN)

        self.history_column = ft.Column(scroll=ft.ScrollMode.AUTO)

        self.tabs = ft.Tabs(
            selected_index=0,
            tabs=[
                ft.Tab(text="Mesai Ekle", icon=ft.Icons.ADD, content=self.build_add_page()),
                ft.Tab(text="Geçmiş", icon=ft.Icons.HISTORY, content=self.build_history_page()),
            ],
            expand=1,
            on_change=self.on_tab_change
        )

        self.page.add(self.tabs)
        self.load_main_list()

    def init_db(self):
        self.conn = sqlite3.connect("mesai.db", check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS mesailer (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tarih TEXT, baslangic TEXT, bitis TEXT, maas REAL, sure_dakika INTEGER, ucret REAL
            )
        """)
        self.conn.commit()

    def build_add_page(self):
        return ft.Container(
            padding=20,
            content=ft.Column([
                ft.Container(content=self.btn_date, alignment=ft.alignment.center),
                ft.Row([
                    ft.Column([ft.Text("Başlangıç"), self.btn_start_time], horizontal_alignment="center"),
                    ft.Column([ft.Text("Bitiş"), self.btn_end_time], horizontal_alignment="center"),
                ], alignment=ft.MainAxisAlignment.SPACE_EVENLY),
                ft.Container(content=self.txt_salary, alignment=ft.alignment.center),
                ft.Container(content=self.btn_save, alignment=ft.alignment.center),
                ft.Divider(),
                ft.Text(f"Bu Ayın Mesaileri ({datetime.now().strftime('%B')})", weight="bold"),
                ft.Container(content=self.main_list_view, expand=True),
                ft.Column([self.txt_total_hours_main, self.txt_total_pay_main], horizontal_alignment="center")
            ])
        )

    def build_history_page(self):
        return ft.Container(padding=10, content=self.history_column)

    def on_date_change(self, e):
        self.selected_date = self.date_picker.value
        self.btn_date.text = self.selected_date.strftime('%d %B %Y')
        self.page.update()

    def on_start_time_change(self, e):
        self.start_time = self.time_picker_start.value
        self.btn_start_time.text = self.start_time.strftime("%H:%M")
        self.page.update()

    def on_end_time_change(self, e):
        self.end_time = self.time_picker_end.value
        self.btn_end_time.text = self.end_time.strftime("%H:%M")
        self.page.update()

    def save_record(self, e):
        if not self.start_time or not self.end_time or not self.txt_salary.value:
            self.page.open(ft.SnackBar(ft.Text("Eksik alan bırakmayın!")))
            return

        maas = float(self.txt_salary.value)
        t1 = datetime.combine(datetime.today(), self.start_time)
        t2 = datetime.combine(datetime.today(), self.end_time)
        if t2 < t1: return # Basit kontrol

        toplam_dakika = int((t2 - t1).total_seconds() / 60)
        ucret = (maas / 30 / 9 / 60) * toplam_dakika * 1.5

        if self.editing_id:
            self.cursor.execute("UPDATE mesailer SET tarih=?, baslangic=?, bitis=?, maas=?, sure_dakika=?, ucret=? WHERE id=?",
                                (self.selected_date.strftime("%Y-%m-%d"), self.start_time.strftime("%H:%M"), 
                                 self.end_time.strftime("%H:%M"), maas, toplam_dakika, ucret, self.editing_id))
            self.editing_id = None
            self.btn_save.text = "Mesaiyi Kaydet"
            self.btn_save.bgcolor = ft.Colors.BLUE
        else:
            self.cursor.execute("INSERT INTO mesailer (tarih, baslangic, bitis, maas, sure_dakika, ucret) VALUES (?,?,?,?,?,?)",
                                (self.selected_date.strftime("%Y-%m-%d"), self.start_time.strftime("%H:%M"), 
                                 self.end_time.strftime("%H:%M"), maas, toplam_dakika, ucret))
        
        self.conn.commit()
        self.load_main_list()
        self.page.open(ft.SnackBar(ft.Text("Başarıyla kaydedildi!")))
        self.page.update()

    def delete_record(self, record_id):
        self.cursor.execute("DELETE FROM mesailer WHERE id=?", (record_id,))
        self.conn.commit()
        self.load_main_list()
        self.load_history_page()

    def edit_record(self, row):
        # row: (id, tarih, baslangic, bitis, maas)
        self.editing_id = row[0]
        self.selected_date = datetime.strptime(row[1], "%Y-%m-%d")
        self.btn_date.text = self.selected_date.strftime('%d %B %Y')
        self.txt_salary.value = str(row[4])
        self.btn_save.text = "Güncellemeyi Kaydet"
        self.btn_save.bgcolor = ft.Colors.ORANGE
        self.page.update()

    def load_main_list(self):
        self.main_list_view.controls.clear()
        bu_ay = datetime.now().strftime("%Y-%m")
        
        # Sadece bu ayın verileri ve tarihe göre sıralı
        self.cursor.execute("SELECT id, tarih, baslangic, bitis, maas, sure_dakika, ucret FROM mesailer WHERE tarih LIKE ? ORDER BY tarih DESC", (f"{bu_ay}%",))
        rows = self.cursor.fetchall()

        toplam_dk = 0
        toplam_tl = 0

        for r in rows:
            toplam_dk += r[5]
            toplam_tl += r[6]
            t_guzel = datetime.strptime(r[1], "%Y-%m-%d").strftime("%d %B")
            
            self.main_list_view.controls.append(
                ft.ListTile(
                    leading=ft.IconButton(ft.Icons.EDIT, on_click=lambda _, row=r: self.edit_record(row)),
                    title=ft.Text(f"{t_guzel} | {r[5]//60} Sa {r[5]%60} Dk"),
                    subtitle=ft.Text(f"{r[2]}-{r[3]} | {r[6]:.2f} TL"),
                    trailing=ft.IconButton(ft.Icons.DELETE, icon_color="red", on_click=lambda _, idx=r[0]: self.delete_record(idx))
                )
            )

        self.txt_total_hours_main.value = f"Bu Ay Toplam: {toplam_dk // 60} Saat {toplam_dk % 60} Dk"
        self.txt_total_pay_main.value = f"Bu Ay Ücret: {toplam_tl:.2f} TL"
        self.page.update()

    def on_tab_change(self, e):
        if self.tabs.selected_index == 1: self.load_history_page()
        else: self.load_main_list()

    def load_history_page(self):
        self.history_column.controls.clear()
        self.cursor.execute("SELECT strftime('%Y-%m', tarih) as ay_yil, SUM(sure_dakika), SUM(ucret) FROM mesailer GROUP BY ay_yil ORDER BY ay_yil DESC")
        aylar = self.cursor.fetchall()
        for ay in aylar:
            self.history_column.controls.append(ft.Card(ft.ExpansionTile(
                title=ft.Text(datetime.strptime(ay[0], "%Y-%m").strftime("%B %Y"), weight="bold"),
                subtitle=ft.Text(f"{ay[1]//60} Sa {ay[1]%60} Dk | {ay[2]:.2f} TL", color=ft.Colors.GREEN),
                controls=[ft.ListTile(title=ft.Text("Detaylar geçmişte saklanır."))]
            )))
        self.page.update()

def main(page: ft.Page):
    app = MesaiApp(page)
ft.app(target=main)