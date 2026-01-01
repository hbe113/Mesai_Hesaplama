import flet as ft
from utils.helpers import tr_date_format

def build_add_view(app):
    is_edit = app.editing_id is not None
    btn_label = "GÜNCELLE" if is_edit else "KAYDET"
    btn_color = ft.Colors.AMBER_700 if is_edit else app.v_ana_renk
    
    start_txt = app.start_time.strftime("%H:%M") if app.start_time else "Giriş"
    end_txt = app.end_time.strftime("%H:%M") if app.end_time else "Bitiş"
    
    app.txt_salary = ft.TextField(label="Maaş (TL)", value=str(app.v_maas if not is_edit else app.last_salary), expand=2)
    app.txt_katsayi = ft.TextField(label="Katsayı", value=str(app.v_katsayi), expand=1)
    
    return ft.Container(
        padding=25, 
        content=ft.Column([
            ft.Text("MESAİ KAYDI", size=20, weight="bold", text_align="center", width=float("inf")),
            ft.Container(
                content=ft.Row([ft.Icon(ft.Icons.CALENDAR_MONTH), ft.Text(tr_date_format(app.selected_date), weight="bold")], alignment="center"), 
                padding=15, border=ft.border.all(1, ft.Colors.GREY_400), border_radius=12, 
                on_click=lambda _: app.open_picker(app.date_picker)
            ),
            ft.Row([
                ft.ElevatedButton(start_txt, on_click=lambda _: app.open_picker(app.time_picker_start), expand=True), 
                ft.ElevatedButton(end_txt, on_click=lambda _: app.open_picker(app.time_picker_end), expand=True)
            ]),
            ft.Row([app.txt_salary, app.txt_katsayi]),
            ft.ElevatedButton(btn_label, on_click=app.save_mesai, bgcolor=btn_color, color="white", height=50, width=float("inf")),
            ft.ElevatedButton("VAZGEÇ", on_click=app.cancel_edit, bgcolor="red", color="white", visible=is_edit, width=float("inf"))
        ], spacing=20)
    )