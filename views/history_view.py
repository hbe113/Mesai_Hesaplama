import flet as ft
import sqlite3
from utils.helpers import tr_date_format, format_sure, AYLAR

def build_history_view(app):
    # Geçmiş verileri için doğrudan db_manager'da bir fonksiyon da yazılabilir 
    # veya db nesnesi üzerinden cursor kullanılabilir.
    app.db.cursor.execute("SELECT strftime('%Y-%m', tarih) as ay, SUM(ucret), SUM(sure_dakika) FROM mesailer GROUP BY ay ORDER BY ay DESC")
    aylar = app.db.cursor.fetchall()
    
    hist_view = ft.Column(scroll=ft.ScrollMode.ADAPTIVE, spacing=10)
    
    for ay_data in aylar:
        yil_ay = ay_data[0].split("-")
        ay_adi = f"{AYLAR[int(yil_ay[1])]} {yil_ay[0]}"
        toplam_para = ay_data[1]
        toplam_dk = ay_data[2]
        alt_bilgi = f"{toplam_para:.2f} ₺ | {format_sure(toplam_dk)}"
        
        app.db.cursor.execute("SELECT * FROM mesailer WHERE strftime('%Y-%m', tarih) = ? ORDER BY tarih DESC", (ay_data[0],))
        mesailer = app.db.cursor.fetchall()
        
        tiles = [
            ft.Container(
                padding=5, 
                content=ft.Row([
                    ft.Column([
                        ft.Text(tr_date_format(m[1]), size=14), 
                        ft.Text(f"{m[2]}-{m[3]} | {format_sure(m[5])}", size=12, color="grey")
                    ], expand=True), 
                    ft.Text(f"{m[6]:.2f} ₺", weight="bold"), 
                    ft.IconButton(ft.Icons.EDIT_OUTLINED, on_click=lambda _, x=m: app.load_edit(x)), 
                    ft.IconButton(ft.Icons.DELETE_OUTLINE, icon_color="red", on_click=lambda _, x=m[0]: app.delete_mesai(x, 3))
                ])
            ) for m in mesailer
        ]
        
        hist_view.controls.append(
            ft.Container(
                content=ft.ExpansionTile(
                    leading=ft.Icon(ft.Icons.HISTORY), 
                    title=ft.Text(ay_adi, weight="bold"), 
                    subtitle=ft.Text(alt_bilgi, color=app.v_vurgu_renk), 
                    controls=tiles
                ), 
                border_radius=10, 
                bgcolor=ft.Colors.with_opacity(0.05, ft.Colors.ON_SURFACE)
            )
        )
        
    return ft.Column([
        ft.Container(padding=20, content=ft.Text("GEÇMİŞ", size=18, weight="bold")), 
        ft.Container(content=hist_view, expand=True, padding=15)
    ], expand=True)