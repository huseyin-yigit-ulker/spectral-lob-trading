import os
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv

load_dotenv()

def get_supabase_conn():
    dsn = os.getenv("SUPABASE_DB_URL") or os.getenv("DB_CONNECTION_STRING")
    if not dsn:
        return None
    
    dsn = dsn.strip().strip('"').strip("'")
    
    try:
        conn = psycopg2.connect(dsn, connect_timeout=15)
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
                CREATE TABLE IF NOT EXISTS v5_trade_logs (
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
                INSERT INTO v5_trade_logs (zaman, sembol, fiyat, obi, cvd, context, sinyal, fvg_top, fvg_bottom, fvg_depth)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (zaman, sembol, fiyat, obi, cvd, context, signal, fvg_top, fvg_bottom, fvg_depth))
            
        conn.commit()
    except Exception as e:
        print(f"  [Supabase DB Yazma Hatasi] {e}")
    finally:
        conn.close()
