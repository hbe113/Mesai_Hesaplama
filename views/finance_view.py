import flet as ft
from utils.helpers import tr_date_format

def build_finance_view(app):
    alacak, alinan, logs = app.db.get_finance_data()
    bakiye = alacak - alinan
    
    f_list = ft.Column(spacing=5, scroll=ft.ScrollMode.ADAPTIVE)
    for fr in logs:
        f_list.controls.append(
            ft.ListTile(
                leading=ft.Icon(ft.Icons.PAYMENTS, color="green" if fr[1] != 'alinan' else "red"), 
                title=ft.Text(fr[4]), 
                subtitle=ft.Text(tr_date_format(fr[3])), 
                trailing=ft.Text(f"{fr[2]:.2f} ₺")
            )
        )
    
    app.txt_fin_amount = ft.TextField(label="Tutar", expand=1)
    app.txt_fin_desc = ft.TextField(label="Açıklama", expand=2)
    
    return ft.Column([
        ft.Container(padding=20, content=ft.Column([
            ft.Text("BAKİYE", size=12), 
            ft.Text(f"{bakiye:.2f} ₺", size=32, weight="bold", color=app.v_vurgu_renk), 
            ft.Row([app.txt_fin_amount, app.txt_fin_desc]), 
            ft.Row([
                ft.ElevatedButton("Ödeme Al", on_click=lambda _: app.add_finance("alinan"), bgcolor="red", color="white"), 
                ft.ElevatedButton("Ekstra", on_click=lambda _: app.add_finance("ekstra"), bgcolor=app.v_ana_renk, color="white")
            ], alignment="spaceBetween")
        ])), 
        ft.Divider(), 
        ft.Container(content=f_list, expand=True)
    ], expand=True)