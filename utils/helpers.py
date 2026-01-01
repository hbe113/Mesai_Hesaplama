from datetime import datetime

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