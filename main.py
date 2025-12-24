import flet as ft
import sqlite3
from datetime import datetime

class MesaiApp:
    def __init__(self, page: ft.Page):
        self.page = page
        self.page.title = "Mesai Takip Pro"
        
        # TÜRKÇE DİL AYARI
        self.page.locale_configuration = ft.LocaleConfiguration(
            current_locale=ft.Locale("tr", "TR")
        )
        
        self.page.theme_mode = ft.ThemeMode.LIGHT
        self.page.padding = 10

        self.init_db()

        # Değişkenler
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
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10))
        )

        self.btn_start_time = ft.OutlinedButton("Başlangıç Seç", on_click=lambda _: self.page.open(self.time_picker_start), icon=ft.Icons.ACCESS_TIME)
        self.btn_end_time = ft.OutlinedButton("Bitiş Seç", on_click=lambda _: self.page.open(self.time_picker_end), icon=ft.Icons.ACCESS_TIME_FILLED)

        self.txt_salary = ft.TextField(label="Maaş (TL)", keyboard_type=ft.KeyboardType.NUMBER, prefix_icon=ft.Icons.MONEY, border_radius=10)
        self.btn_save = ft.ElevatedButton("Mesaiyi Kaydet", on_click=self.save_record, bgcolor=ft.Colors.BLUE, color=ft.Colors.WHITE, height=50)

        self.main_list_view = ft.ListView(expand=True, spacing=10, padding=ft.padding.only(bottom=20))
        self.txt_total_hours_main = ft.Text("Bu Ay: 0 Saat 0 Dk", size=15, weight=ft.FontWeight.W_500)
        self.txt_total_pay_main = ft.Text("Bu Ay Ücret: 0.00 TL", size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN_700)

        # --- GEÇMİŞ SAYFASI ---
        self.history_column = ft.Column(scroll=ft.ScrollMode.AUTO)
        self.txt_grand_total = ft.Text("Toplam Alacak: 0.00 TL", size=22, weight=ft.FontWeight.BOLD)
        self.txt_finance_amount = ft.TextField(label="Miktar", keyboard_type=ft.KeyboardType.NUMBER, width=120, height=45)

        self.tabs = ft.Tabs(
            selected_index=0,
            tabs=[
                ft.Tab(text="Mesai Ekle", icon=ft.Icons.ADD_TASK, content=self.build_add_page()),
                ft.Tab(text="Finans & Geçmiş", icon=ft.Icons.ACCOUNT_BALANCE_WALLET, content=self.build_history_page()),
            ],
            expand=1,
            on_change=self.on_tab_change
        )

        self.page.add(self.tabs)
        self.load_main_list()

    def init_db(self):
        self.conn = sqlite3.connect("mesai.db", check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.cursor.execute("CREATE TABLE IF NOT EXISTS mesailer (id INTEGER PRIMARY KEY AUTOINCREMENT, tarih TEXT, baslangic TEXT, bitis TEXT, maas REAL, sure_dakika INTEGER, ucret REAL)")
        self.cursor.execute("CREATE TABLE IF NOT EXISTS finans (id INTEGER PRIMARY KEY AUTOINCREMENT, tur TEXT, miktar REAL, tarih TEXT)")
        self.conn.commit()

    def build_add_page(self):
        return ft.Container(
            padding=15,
            content=ft.Column([
                ft.Card(
                    elevation=5,
                    content=ft.Container(
                        padding=20,
                        content=ft.Column([
                            ft.Container(content=self.btn_date, alignment=ft.alignment.center),
                            ft.Container(height=15), 
                            ft.Row([
                                ft.Column([ft.Text("Başlangıç", size=12), self.btn_start_time], horizontal_alignment="center"),
                                ft.Column([ft.Text("Bitiş", size=12), self.btn_end_time], horizontal_alignment="center"),
                            ], alignment=ft.MainAxisAlignment.SPACE_AROUND),
                            ft.Container(height=15),
                            self.txt_salary,
                            ft.Container(height=15),
                            ft.Container(content=self.btn_save, alignment=ft.alignment.center, width=float("inf")),
                        ])
                    )
                ),
                ft.Divider(height=20),
                ft.Text("Bu Ayın Özet Listesi", weight="bold"),
                ft.Container(content=self.main_list_view, expand=True),
                ft.Card(color=ft.Colors.GREY_100, content=ft.Container(padding=10, content=ft.Column([self.txt_total_hours_main, self.txt_total_pay_main], horizontal_alignment="center")))
            ])
        )

    def build_history_page(self):
        finance_header = ft.Card(
            elevation=8,
            content=ft.Container(
                padding=20,
                content=ft.Column([
                    ft.Container(content=self.txt_grand_total, alignment=ft.alignment.center),
                    ft.Container(height=10),
                    ft.Row([
                         ft.Text("İşlem:"),
                         self.txt_finance_amount,
                         ft.IconButton(ft.Icons.REMOVE_CIRCLE, icon_color="red", on_click=lambda e: self.manage_finance(e, "alinan")),
                         ft.IconButton(ft.Icons.ADD_CIRCLE, icon_color="green", on_click=lambda e: self.manage_finance(e, "ekstra"))
                    ], alignment=ft.MainAxisAlignment.CENTER),
                ], horizontal_alignment="center")
            )
        )
        return ft.Container(padding=10, content=ft.Column([finance_header, ft.Divider(height=25), self.history_column], expand=True))

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
            return
        maas = float(self.txt_salary.value)
        t1 = datetime.combine(datetime.today(), self.start_time)
        t2 = datetime.combine(datetime.today(), self.end_time)
        toplam_dakika = int((t2 - t1).total_seconds() / 60)
        ucret = (maas / 30 / 9 / 60) * toplam_dakika * 1.5

        if self.editing_id:
            self.cursor.execute("UPDATE mesailer SET tarih=?, baslangic=?, bitis=?, maas=?, sure_dakika=?, ucret=? WHERE id=?",
                                (self.selected_date.strftime("%Y-%m-%d"), self.start_time.strftime("%H:%M"), self.end_time.strftime("%H:%M"), maas, toplam_dakika, ucret, self.editing_id))
            self.editing_id = None
            self.btn_save.text = "Mesaiyi Kaydet"
        else:
            self.cursor.execute("INSERT INTO mesailer (tarih, baslangic, bitis, maas, sure_dakika, ucret) VALUES (?,?,?,?,?,?)",
                                (self.selected_date.strftime("%Y-%m-%d"), self.start_time.strftime("%H:%M"), self.end_time.strftime("%H:%M"), maas, toplam_dakika, ucret))
        self.conn.commit()
        self.load_main_list()
        self.page.update()

    def manage_finance(self, e, tur):
        try:
            val = float(self.txt_finance_amount.value)
            self.cursor.execute("INSERT INTO finans (tur, miktar, tarih) VALUES (?, ?, ?)", (tur, val, datetime.now().strftime("%Y-%m-%d")))
            self.conn.commit()
            self.txt_finance_amount.value = ""
            self.load_history_page()
        except: pass

    def load_main_list(self):
        self.main_list_view.controls.clear()
        bu_ay = datetime.now().strftime("%Y-%m")
        self.cursor.execute("SELECT id, tarih, baslangic, bitis, maas, sure_dakika, ucret FROM mesailer WHERE tarih LIKE ? ORDER BY tarih DESC", (f"{bu_ay}%",))
        rows = self.cursor.fetchall()
        dk, tl = 0, 0
        for r in rows:
            dk += r[5]; tl += r[6]
            self.main_list_view.controls.append(ft.Card(content=ft.ListTile(
                leading=ft.IconButton(ft.Icons.EDIT, on_click=lambda _, row=r: self.edit_record(row)),
                title=ft.Text(f"{datetime.strptime(r[1], '%Y-%m-%d').strftime('%d %B')} | {r[5]//60}S {r[5]%60}D"),
                trailing=ft.IconButton(ft.Icons.DELETE, icon_color="red", on_click=lambda _, i=r[0]: self.delete_record(i))
            )))
        self.txt_total_hours_main.value = f"Bu Ay: {dk//60} Sa {dk%60} Dk"
        self.txt_total_pay_main.value = f"Ücret: {tl:.2f} TL"
        self.page.update()

    def delete_record(self, idx):
        self.cursor.execute("DELETE FROM mesailer WHERE id=?", (idx,))
        self.conn.commit()
        self.load_main_list()
        self.load_history_page()

    def edit_record(self, r):
        self.editing_id = r[0]
        self.selected_date = datetime.strptime(r[1], "%Y-%m-%d")
        self.btn_date.text = self.selected_date.strftime('%d %B %Y')
        self.txt_salary.value = str(r[4])
        self.btn_save.text = "Güncellemeyi Kaydet"
        self.tabs.selected_index = 0
        self.page.update()

    def on_tab_change(self, e):
        if self.tabs.selected_index == 1: self.load_history_page()
        else: self.load_main_list()

    def load_history_page(self):
        self.history_column.controls.clear()
        self.cursor.execute("SELECT SUM(ucret) FROM mesailer")
        m_top = self.cursor.fetchone()[0] or 0
        self.cursor.execute("SELECT SUM(miktar) FROM finans WHERE tur='ekstra'")
        e_top = self.cursor.fetchone()[0] or 0
        self.cursor.execute("SELECT SUM(miktar) FROM finans WHERE tur='alinan'")
        a_top = self.cursor.fetchone()[0] or 0
        g_top = (m_top + e_top) - a_top
        self.txt_grand_total.value = f"Toplam Alacak: {g_top:.2f} TL"
        self.txt_grand_total.color = ft.Colors.GREEN if g_top >= 0 else ft.Colors.RED
        
        self.cursor.execute("SELECT strftime('%Y-%m', tarih) as ay, SUM(sure_dakika), SUM(ucret) FROM mesailer GROUP BY ay ORDER BY ay DESC")
        for ay in self.cursor.fetchall():
            detaylar = []
            self.cursor.execute("SELECT id, tarih, baslangic, bitis, maas, sure_dakika, ucret FROM mesailer WHERE strftime('%Y-%m', tarih) = ? ORDER BY tarih DESC", (ay[0],))
            for d in self.cursor.fetchall():
                detaylar.append(ft.ListTile(title=ft.Text(f"{d[1]} | {d[5]//60}S {d[5]%60}D"), trailing=ft.IconButton(ft.Icons.EDIT, on_click=lambda _, r=d: self.edit_record(r))))
            self.history_column.controls.append(ft.Card(content=ft.ExpansionTile(title=ft.Text(datetime.strptime(ay[0], "%Y-%m").strftime("%B %Y")), subtitle=ft.Text(f"{ay[1]//60}S {ay[1]%60}D | {ay[2]:.2f} TL"), controls=detaylar)))
        self.page.update()

def main(page: ft.Page):
    app = MesaiApp(page)

if __name__ == "__main__":
    ft.app(target=main, assets_dir="assets")
