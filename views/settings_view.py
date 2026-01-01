import flet as ft
from flet_contrib.color_picker import ColorPicker

def build_settings_view(app):
    # TextField tanımlamaları aynı kalıyor...
    txt_v_maas = ft.TextField(label="Varsayılan Maaş (TL)", value=str(app.v_maas))
    txt_v_katsayi = ft.TextField(label="Varsayılan Katsayı", value=str(app.v_katsayi))
    txt_v_hedef = ft.TextField(label="Aylık Mesai Hedefi (TL)", value=str(app.v_hedef))
    txt_ana_renk = ft.TextField(label="Ana Tema Rengi (HEX)", value=app.v_ana_renk, expand=True)
    txt_vurgu_renk = ft.TextField(label="Vurgu Rengi (HEX)", value=app.v_vurgu_renk, expand=True)

    preview_ana = ft.Container(width=40, height=40, bgcolor=app.v_ana_renk, border_radius=5, border=ft.border.all(1, "grey"))
    preview_vurgu = ft.Container(width=40, height=40, bgcolor=app.v_vurgu_renk, border_radius=5, border=ft.border.all(1, "grey"))

    # Color Picker Diyaloğu (Aynı)
    color_picker_ctrl = ColorPicker(color="#000000", width=300)

    quick_colors = ft.Row([
        ft.IconButton(icon=ft.Icons.CIRCLE, icon_color="#1A237E", on_click=lambda _: set_quick_color("#1A237E", "#00BFA5"), tooltip="Okyanus"),
        ft.IconButton(icon=ft.Icons.CIRCLE, icon_color="#2E7D32", on_click=lambda _: set_quick_color("#2E7D32", "#C6FF00"), tooltip="Doğa"),
        ft.IconButton(icon=ft.Icons.CIRCLE, icon_color="#B71C1C", on_click=lambda _: set_quick_color("#B71C1C", "#FFD600"), tooltip="Ateş"),
        ft.IconButton(icon=ft.Icons.CIRCLE, icon_color="#4A148C", on_click=lambda _: set_quick_color("#4A148C", "#EA80FC"), tooltip="Gece"),
        ft.IconButton(icon=ft.Icons.CIRCLE, icon_color="#37474F", on_click=lambda _: set_quick_color("#37474F", "#81D4FA"), tooltip="Metal"),
    ], alignment="center")
    
    def pick_color_result(e):
        selected_color = color_picker_ctrl.color
        if app.target_color_input: app.target_color_input.value = selected_color
        if app.target_color_preview: app.target_color_preview.bgcolor = selected_color
        app.page.close(color_dialog); app.page.update()

    color_dialog = ft.AlertDialog(
        title=ft.Text("Renk Seç"), 
        content=ft.Column([color_picker_ctrl], height=400, tight=True, alignment="center"), 
        actions=[ft.TextButton("SEÇ", on_click=pick_color_result)]
    )

    def open_color_picker(e, input_field, preview_box):
        app.target_color_input = input_field; app.target_color_preview = preview_box
        try: color_picker_ctrl.color = input_field.value
        except: color_picker_ctrl.color = "#000000"
        app.page.open(color_dialog); app.page.update()

    preview_ana.on_click = lambda e: open_color_picker(e, txt_ana_renk, preview_ana)
    preview_vurgu.on_click = lambda e: open_color_picker(e, txt_vurgu_renk, preview_vurgu)

    def save_settings_action(e):
        try:
            app.db.update_settings(float(txt_v_maas.value), float(txt_v_katsayi.value), 
                                  float(txt_v_hedef.value), txt_ana_renk.value, txt_vurgu_renk.value)
            app.load_settings()
            app.update_theme_colors()
            app.show_msg("Ayarlar Kaydedildi!", "green")
            app.toggle_settings(None)
        except: app.show_msg("Hata: Değerleri kontrol edin", "red")

    def reset_data_click(e):
        def confirm_reset(e):
            app.db.cursor.execute("DELETE FROM mesailer")
            app.db.cursor.execute("DELETE FROM finans")
            app.db.conn.commit()
            app.page.close(dlg)
            app.show_msg("Tüm veriler temizlendi!", "red")
            app.load_tab(0)

        dlg = ft.AlertDialog(
            title=ft.Text("Tüm Veriler Silinsin mi?"),
            content=ft.Text("Bu işlem geri alınamaz! Tüm mesai ve finans kayıtlarınız kalıcı olarak silinecek."),
            actions=[
                ft.TextButton("İptal", on_click=lambda _: app.page.close(dlg)),
                ft.ElevatedButton("EVET, SİL", bgcolor="red", color="white", on_click=confirm_reset)
            ]
        )
        app.page.open(dlg)
    
    # Renkleri uygulama fonksiyonu
    def set_quick_color(ana, vurgu):
        txt_ana_renk.value = ana
        txt_vurgu_renk.value = vurgu
        preview_ana.bgcolor = ana
        preview_vurgu.bgcolor = vurgu
        app.page.update()

    # --- SCROLL ÇALIŞMASI İÇİN DÜZENLENEN KISIM ---
    settings_content = ft.Column(
        controls=[
            ft.Row([ft.IconButton(ft.Icons.ARROW_BACK, on_click=app.toggle_settings), ft.Text("AYARLAR", size=22, weight="bold")]),
            ft.Divider(),
            ft.Text("Hesaplama ve Hedef", weight="bold"),
            txt_v_maas, txt_v_katsayi, txt_v_hedef,
            ft.Divider(),
            ft.Text("Görünüm", weight="bold"),
            ft.Row([txt_ana_renk, preview_ana]),
            ft.Row([txt_vurgu_renk, preview_vurgu]),
            ft.Switch(label="Koyu Tema", value=(app.v_tema == "dark"), on_change=app.change_theme),
            ft.Text("Hızlı Renk Seçimi:", size=12, color="grey"),
            quick_colors,
            ft.Divider(),
            ft.Text("Veri Yönetimi", weight="bold"),
            ft.Row([
                ft.ElevatedButton("Yedekle", icon=ft.Icons.UPLOAD, on_click=lambda _: app.backup_dialog.save_file(), expand=True),
                ft.ElevatedButton("Geri Yükle", icon=ft.Icons.DOWNLOAD, on_click=lambda _: app.restore_dialog.pick_files(), expand=True),
                ]),
            ft.ElevatedButton(
                "Tüm Verileri Sıfırla", 
                icon=ft.Icons.DELETE_FOREVER, 
                bgcolor=ft.Colors.RED_ACCENT_700, 
                color="white", 
                width=float("inf"), 
                on_click=reset_data_click
                ),
            ft.Divider(),
            ft.ElevatedButton("AYARLARI KAYDET", on_click=save_settings_action, bgcolor=app.v_ana_renk, color="white", width=float("inf"), height=50),
            ft.Container(height=50) # Alt kısımda boşluk bırakarak scroll'un rahat bitmesini sağlar
        ],
        scroll=ft.ScrollMode.ADAPTIVE, # Scroll'u bu kolona verdik
        expand=True, # Kolonun tüm alanı kaplamasını sağladık
        spacing=15
    )

    return ft.Container(
        content=settings_content, 
        padding=25, 
        expand=True # Ana kapsayıcının da genişlemesini sağladık
    )