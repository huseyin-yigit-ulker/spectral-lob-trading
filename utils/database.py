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

def get_supabase_conn():
    dsn = os.getenv("SUPABASE_DB_URL") or os.getenv("DB_CONNECTION_STRING")
    if not dsn:
        return None
    
    dsn = dsn.strip().strip('"').strip("'")
    dsn = dsn.replace("\ufffd", "£")
    
    try:
        conn = psycopg2.connect(**parse_dsn(dsn), connect_timeout=15)
        return conn
    except Exception as e:
        print(f"  [Supabase Baglanti Hatasi] {e}")
        return None

def log_trade_to_supabase(zaman, sembol, fiyat, obi, cvd, context, signal, fvg_top, fvg_bottom, fvg_depth):
    conn = get_supabase_conn()
    if not conn:
        return
        
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS quant_v5.trade_logs (
                    id SERIAL PRIMARY KEY,
                    zaman TIMESTAMP,
                    sembol VARCHAR(50),
                    fiyat NUMERIC,
                    obi NUMERIC,
                    cvd NUMERIC,
                    context VARCHAR(50),
                    sinyal VARCHAR(50),
                    fvg_top NUMERIC,
                    fvg_bottom NUMERIC,
                    fvg_depth NUMERIC,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            cur.execute("""
                INSERT INTO quant_v5.trade_logs (zaman, sembol, fiyat, obi, cvd, context, sinyal, fvg_top, fvg_bottom, fvg_depth)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (zaman, sembol, fiyat, obi, cvd, context, signal, fvg_top, fvg_bottom, fvg_depth))
            
        conn.commit()
    except Exception as e:
        print(f"  [Supabase DB Yazma Hatasi] {e}")
    finally:
        conn.close()

def log_screener_to_supabase(zaman, sembol, fiyat, hacim, spread, fvg_mesafe_yuzde, skor, durum):
    conn = get_supabase_conn()
    if not conn:
        return
        
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO quant_v5.screener_history (zaman, sembol, fiyat, hacim, spread, fvg_mesafe_yuzde, skor, durum)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (zaman, sembol, fiyat, hacim, spread, fvg_mesafe_yuzde, skor, durum))
        conn.commit()
    except Exception as e:
        print(f"  [Supabase Screener DB Yazma Hatasi] {e}")
    finally:
        conn.close()
