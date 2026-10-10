import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def parse_dsn(dsn: str) -> dict:
    body = dsn.split("://", 1)[1]
    creds, hostpart = body.rsplit("@", 1)
    user, password = creds.split(":", 1)
    hostport, db = hostpart.split("/", 1)
    host, port = hostport.rsplit(":", 1)
    return {"user": user, "password": password, "host": host, "port": int(port), "dbname": db}

def clean_v1():
    dsn = os.getenv("DB_CONNECTION_STRING_V1")
    if not dsn:
        print("V1 bağlantı bilgisi (.env DB_CONNECTION_STRING_V1) bulunamadı.")
        return
        
    dsn = dsn.strip().strip('"').strip("'")
    dsn = dsn.replace("\ufffd", "£")
    
    try:
        conn = psycopg2.connect(**parse_dsn(dsn), connect_timeout=15)
        cur = conn.cursor()
        print("V1 veritabanına bağlanıldı. 'quant_v5' şeması ve tüm verileri siliniyor...")
        cur.execute("DROP SCHEMA IF EXISTS quant_v5 CASCADE;")
        conn.commit()
        print("[OK] V1 üzerindeki quant_v5 şeması ve tüm içerikler başarıyla silindi.")
    except Exception as e:
        print(f"Hata oluştu: {e}")
    finally:
        if 'conn' in locals() and conn:
            cur.close()
            conn.close()

if __name__ == "__main__":
    clean_v1()
