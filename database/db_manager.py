import sqlite3
import os
from datetime import date, datetime

class DBManager:
    def __init__(self):
        try:
            self.db_path = os.path.join(os.getenv("FLET_APP_STORAGE_DATA", "."), "mesai_v4.db")
        except:
            self.db_path = "mesai_v4.db"
            
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self._init_tables()

    def _init_tables(self):
        self.cursor.execute("CREATE TABLE IF NOT EXISTS mesailer (id INTEGER PRIMARY KEY, tarih TEXT, baslangic TEXT, bitis TEXT, maas REAL, sure_dakika INTEGER, ucret REAL)")
        self.cursor.execute("CREATE TABLE IF NOT EXISTS finans (id INTEGER PRIMARY KEY, tur TEXT, miktar REAL, tarih TEXT, aciklama TEXT)")
        self.cursor.execute("CREATE TABLE IF NOT EXISTS ayarlar (id INTEGER PRIMARY KEY, varsayilan_maas REAL, mesai_katsayisi REAL, tema_modu TEXT, ana_renk TEXT, vurgu_renk TEXT, aylik_hedef REAL)")
        self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_tarih ON mesailer(tarih)")
        self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_finans_tarih ON finans(tarih)")
        
        self.cursor.execute("SELECT COUNT(*) FROM ayarlar")
        if self.cursor.fetchone()[0] == 0:
            self.cursor.execute("INSERT INTO ayarlar (varsayilan_maas, mesai_katsayisi, tema_modu, ana_renk, vurgu_renk, aylik_hedef) VALUES (0.0, 1.5, 'light', '#1A237E', '#00BFA5', 5000.0)")
        self.conn.commit()

    def get_settings(self):
        self.cursor.execute("SELECT varsayilan_maas, mesai_katsayisi, tema_modu, ana_renk, vurgu_renk, aylik_hedef FROM ayarlar WHERE id=1")
        return self.cursor.fetchone()

    def update_settings(self, maas, katsayi, hedef, ana, vurgu):
        self.cursor.execute("UPDATE ayarlar SET varsayilan_maas=?, mesai_katsayisi=?, aylik_hedef=?, ana_renk=?, vurgu_renk=? WHERE id=1", (maas, katsayi, hedef, ana, vurgu))
        self.conn.commit()

    def save_mesai(self, data, m_id=None):
        if m_id:
            self.cursor.execute("UPDATE mesailer SET tarih=?, baslangic=?, bitis=?, maas=?, sure_dakika=?, ucret=? WHERE id=?", (*data, m_id))
        else:
            self.cursor.execute("INSERT INTO mesailer (tarih, baslangic, bitis, maas, sure_dakika, ucret) VALUES (?,?,?,?,?,?)", data)
        self.conn.commit()
        self.sync_past_months_finance()

    def delete_mesai(self, m_id):
        self.cursor.execute("DELETE FROM mesailer WHERE id=?", (m_id,))
        self.conn.commit()
        self.sync_past_months_finance()

    def get_month_mesai(self, ym_str):
        self.cursor.execute("SELECT * FROM mesailer WHERE strftime('%Y-%m', tarih) = ? ORDER BY tarih DESC", (ym_str,))
        return self.cursor.fetchall()

    def get_finance_data(self):
        self.cursor.execute("SELECT SUM(miktar) FROM finans WHERE tur IN ('ekstra', 'mesai_devir')")
        alacak = self.cursor.fetchone()[0] or 0
        self.cursor.execute("SELECT SUM(miktar) FROM finans WHERE tur='alinan'")
        alinan = self.cursor.fetchone()[0] or 0
        
        self.cursor.execute("SELECT * FROM finans ORDER BY tarih DESC")
        logs = self.cursor.fetchall()
        return alacak, alinan, logs

    def add_finance_record(self, tur, miktar, aciklama):
        self.cursor.execute("INSERT INTO finans (tur, miktar, tarih, aciklama) VALUES (?, ?, ?, ?)", 
                            (tur, miktar, date.today().strftime("%Y-%m-%d"), aciklama))
        self.conn.commit()

    def sync_past_months_finance(self):
        # AYLAR sözlüğünü burada yerel olarak veya utils'den alarak kullanacağız
        AYLAR_L = {1: "Ocak", 2: "Şubat", 3: "Mart", 4: "Nisan", 5: "Mayıs", 6: "Haziran",
                   7: "Temmuz", 8: "Ağustos", 9: "Eylül", 10: "Ekim", 11: "Kasım", 12: "Aralık"}
        
        try:
            today_str = date.today().strftime("%Y-%m")
            
            # Aşama 1: Temizlik
            self.cursor.execute("SELECT id, aciklama FROM finans WHERE tur = 'mesai_devir'")
            for f_id, aciklama in self.cursor.fetchall():
                parts = aciklama.split()
                if len(parts) >= 2:
                    ay_adi, yil = parts[0], parts[1]
                    ay_no = next((k for k, v in AYLAR_L.items() if v == ay_adi), 0)
                    if ay_no > 0:
                        q_date = f"{yil}-{ay_no:02d}"
                        self.cursor.execute("SELECT COUNT(*) FROM mesailer WHERE strftime('%Y-%m', tarih) = ?", (q_date,))
                        if self.cursor.fetchone()[0] == 0:
                            self.cursor.execute("DELETE FROM finans WHERE id = ?", (f_id,))

            # Aşama 2: Güncelleme
            self.cursor.execute("SELECT strftime('%Y-%m', tarih) as ay, SUM(ucret) FROM mesailer WHERE ay < ? GROUP BY ay", (today_str,))
            for ay_str, toplam in self.cursor.fetchall():
                yil, ay = map(int, ay_str.split("-"))
                aciklama = f"{AYLAR_L[ay]} {yil} Maaş Devri"
                self.cursor.execute("SELECT id, miktar FROM finans WHERE aciklama = ?", (aciklama,))
                res = self.cursor.fetchone()
                if res:
                    if abs(res[1] - toplam) > 0.01:
                        self.cursor.execute("UPDATE finans SET miktar = ? WHERE id = ?", (toplam, res[0]))
                else:
                    self.cursor.execute("INSERT INTO finans (tur, miktar, tarih, aciklama) VALUES (?, ?, ?, ?)", 
                                        ("mesai_devir", toplam, date.today().strftime("%Y-%m-%d"), aciklama))
            self.conn.commit()
        except Exception as e:
            print(f"Sync hatası: {e}")