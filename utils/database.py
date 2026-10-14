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
    import time
    for attempt in range(3):
        conn = get_supabase_conn()
        if not conn:
            time.sleep(1)
            continue
            
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO quant_v5.trade_logs (zaman, sembol, fiyat, obi, cvd, context, sinyal, fvg_top, fvg_bottom, fvg_depth)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (zaman, sembol, fiyat, obi, cvd, context, signal, fvg_top, fvg_bottom, fvg_depth))
                
            conn.commit()
            return True
        except Exception as e:
            print(f"  [Supabase DB Yazma Hatasi (Deneme {attempt+1})] {e}")
            time.sleep(1)
        finally:
            if conn:
                try: conn.close()
                except: pass
    return False

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

def update_live_metrics(states_dict):
    if not states_dict:
        return
        
    conn = get_supabase_conn()
    if not conn:
        return
        
    try:
        from psycopg2.extras import execute_values
        rows = [
            (sym, data.get('smc_status', ''), data.get('fvg_depth', 0.0))
            for sym, data in states_dict.items()
        ]
        with conn.cursor() as cur:
            query = """
                INSERT INTO quant_v5.live_metrics (sembol, smc_status, fvg_depth, updated_at)
                VALUES %s
                ON CONFLICT (sembol) DO UPDATE SET 
                    smc_status = EXCLUDED.smc_status,
                    fvg_depth = EXCLUDED.fvg_depth,
                    updated_at = EXCLUDED.updated_at
            """
            execute_values(cur, query, rows, template="(%s, %s, %s, CURRENT_TIMESTAMP)", page_size=100)
        conn.commit()
    except Exception as e:
        pass # print(f"  [Supabase Live Metrics Hatasi] {e}")
    finally:
        try: conn.close()
        except: pass

def update_active_screener(json_data):
    conn = get_supabase_conn()
    if not conn:
        return
        
    try:
        import json
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO quant_v5.active_screener (id, updated_at, data)
                VALUES (1, CURRENT_TIMESTAMP, %s)
                ON CONFLICT (id) DO UPDATE SET 
                    updated_at = CURRENT_TIMESTAMP,
                    data = EXCLUDED.data
            """, (json.dumps(json_data),))
        conn.commit()
    except Exception as e:
        print(f"  [Supabase Active Screener Hatasi] {e}")
    finally:
        conn.close()

