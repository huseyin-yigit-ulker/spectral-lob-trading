import sys
import os
sys.path.append(os.path.abspath(os.path.dirname(os.path.dirname(__file__))))
from utils.database import get_supabase_conn

def main():
    conn = get_supabase_conn()
    if not conn:
        print("Baglanti hatasi")
        return
    try:
        cur = conn.cursor()
        cur.execute("""
        CREATE TABLE IF NOT EXISTS quant_v5.active_screener (
            id INT PRIMARY KEY,
            updated_at TIMESTAMP,
            data JSONB
        );
        """)
        conn.commit()
        cur.close()
        print("Tablo olusturuldu.")
    except Exception as e:
        print(f"Hata: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    main()
