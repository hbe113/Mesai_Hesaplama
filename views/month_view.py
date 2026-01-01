import flet as ft
from datetime import datetime
from utils.helpers import tr_date_format, format_sure, AYLAR

def build_month_view(app):
    current_ym = datetime.now().strftime("%Y-%m")
    now = datetime.now()
    
    rows = app.db.get_month_mesai(current_ym)
    toplam_ucret = sum(r[6] for r in rows)
    toplam_dakika = sum(r[5] for r in rows)
    
    yuzde = min((toplam_ucret / app.v_hedef), 1.0) if app.v_hedef > 0 else 0
    
    hedef_container = ft.Container(
        padding=20, 
        bgcolor=ft.Colors.with_opacity(0.1, app.v_vurgu_renk), 
        border_radius=15, 
        content=ft.Column([
            ft.Row([
                ft.Text(f"{AYLAR[now.month].upper()} HEDEFİ", weight="bold", size=13), 
                ft.Text(f"%{yuzde*100:.1f}", weight="bold", color=app.v_vurgu_renk)
            ], alignment="spaceBetween"),
            ft.ProgressBar(value=yuzde, color=app.v_vurgu_renk, bgcolor=ft.Colors.GREY_300, height=10),
            ft.Row([
                ft.Text(f"{toplam_ucret:.0f} ₺", size=12, weight="bold"), 
                ft.Text(f"Hedef: {app.v_hedef:.0f} ₺", size=12)
            ], alignment="spaceBetween")
        ], spacing=8)
    )
    
    list_col = ft.Column(spacing=10, scroll=ft.ScrollMode.ADAPTIVE, expand=True)
    list_col.controls.append(hedef_container)
    
    for r in rows:
        list_col.controls.append(
            ft.Container(
                bgcolor=ft.Colors.with_opacity(0.05, ft.Colors.ON_SURFACE), 
                padding=15, border_radius=10, 
                content=ft.Row([
                    ft.Column([
                        ft.Text(tr_date_format(r[1]), weight="bold"), 
                        ft.Text(f"{r[2]}-{r[3]} | {format_sure(r[5])}", size=12)
                    ], expand=True), 
                    ft.Text(f"{r[6]:.2f} ₺", weight="bold", color=app.v_vurgu_renk), 
                    ft.IconButton(ft.Icons.EDIT_OUTLINED, on_click=lambda _, x=r: app.load_edit(x)), 
                    ft.IconButton(ft.Icons.DELETE_OUTLINE, icon_color="red", on_click=lambda _, x=r[0]: app.delete_mesai(x, 1))
                ])
            )
        )
    
    bottom_bar = ft.Container(
        bgcolor=app.v_ana_renk, padding=20, 
        content=ft.Row([
            ft.Column([ft.Text("TOPLAM SÜRE", size=11, color="white70"), ft.Text(format_sure(toplam_dakika), color="white", weight="bold")]), 
            ft.Column([ft.Text("TOPLAM KAZANÇ", size=11, color="white70"), ft.Text(f"{toplam_ucret:.2f} ₺", color="white", weight="bold", size=20)], horizontal_alignment="end")
        ], alignment="spaceBetween")
    )
    
    return ft.Column([list_col, bottom_bar], expand=True, spacing=0)