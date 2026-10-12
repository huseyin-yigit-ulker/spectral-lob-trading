import os
import sys
import requests
import datetime
import time

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.database import get_supabase_conn

def parse_utc_dt(dt_val):
    if isinstance(dt_val, datetime.datetime):
        if dt_val.tzinfo is None:
            return dt_val.replace(tzinfo=datetime.timezone.utc)
        return dt_val.astimezone(datetime.timezone.utc)
    s = str(dt_val).strip()
    if s.endswith('Z') or '+' in s:
        return datetime.datetime.fromisoformat(s.replace('Z', '+00:00'))
    return datetime.datetime.fromisoformat(s).replace(tzinfo=datetime.timezone.utc)

def main():
    conn = get_supabase_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, zaman, sembol, fiyat, sinyal, obi, cvd, context, fvg_top, fvg_bottom, fvg_depth 
        FROM quant_v5.trade_logs 
        ORDER BY id ASC;
    """)
    rows = cur.fetchall()

    open_pos = {}
    for r in rows:
        _id, zaman, sym, fiyat, sinyal, obi, cvd, ctx, f_top, f_bot, f_depth = r
        if ('AL' in sinyal or 'SAT' in sinyal) and ('BEKLE' not in sinyal):
            open_pos[sym] = {
                'id': _id, 'zaman': zaman, 'sym': sym, 'fiyat': float(fiyat),
                'sinyal': sinyal, 'f_top': float(f_top or 0), 'f_bot': float(f_bot or 0),
                'f_depth': float(f_depth or 0), 'ctx': ctx, 'obi': float(obi or 0), 'cvd': float(cvd or 0)
            }
        elif 'BEKLE' in sinyal and sym in open_pos:
            del open_pos[sym]

    print(f"Tespit edilen açıkta kalmış işlem sayısı: {len(open_pos)}")

    for sym, p in open_pos.items():
        start_ts = int(p['zaman'].timestamp() * 1000)
        end_ts = start_ts + 72 * 3600 * 1000  # 72 saat
        url = f"https://fapi.binance.com/fapi/v1/klines?symbol={sym}&interval=1m&startTime={start_ts}&endTime={end_ts}&limit=1000"
        
        exit_time = None
        exit_price = None
        
        try:
            kl = requests.get(url, timeout=6).json()
            if isinstance(kl, list) and len(kl) > 0:
                entry_p = p['fiyat']
                is_long = 'AL' in p['sinyal']
                
                # SL seviyesi: FVG sınırı veya %0.50
                if is_long:
                    sl = (p['f_bot'] * 0.998) if p['f_bot'] > 0 else (entry_p * 0.995)
                else:
                    sl = (p['f_top'] * 1.002) if p['f_top'] > 0 else (entry_p * 1.005)
                
                for k in kl:
                    c = float(k[4])
                    t_dt = datetime.datetime.fromtimestamp(k[0]/1000)
                    if is_long and c <= sl:
                        exit_time = t_dt
                        exit_price = c
                        break
                    elif not is_long and c >= sl:
                        exit_time = t_dt
                        exit_price = c
                        break
                
                if not exit_time:
                    # 120 dk sonraki mum kapanisi
                    target_idx = min(120, len(kl) - 1)
                    exit_time = datetime.datetime.fromtimestamp(kl[target_idx][0]/1000)
                    exit_price = float(kl[target_idx][4])
            else:
                # Eger vadeli kline yoksa spot dene
                url_spot = f"https://api.binance.com/api/v3/klines?symbol={sym}&interval=1m&startTime={start_ts}&endTime={end_ts}&limit=1000"
                kl_spot = requests.get(url_spot, timeout=6).json()
                if isinstance(kl_spot, list) and len(kl_spot) > 0:
                    exit_time = datetime.datetime.fromtimestamp(kl_spot[min(60, len(kl_spot)-1)][0]/1000)
                    exit_price = float(kl_spot[min(60, len(kl_spot)-1)][4])
                else:
                    exit_time = p['zaman'] + datetime.timedelta(hours=1)
                    exit_price = p['fiyat']
        except Exception as e:
            print(f"Hata {sym}: {e}")
            exit_time = p['zaman'] + datetime.timedelta(hours=1)
            exit_price = p['fiyat']

        diff_min = int((exit_time - p['zaman']).total_seconds() / 60)
        pnl = ((exit_price - p['fiyat'])/p['fiyat']*100) if ('AL' in p['sinyal']) else ((p['fiyat'] - exit_price)/p['fiyat']*100)
        print(f"-> Kapatılıyor: {sym} | Giriş: {p['zaman']} (${p['fiyat']}) -> Çıkış: {exit_time} (${exit_price}) [{diff_min} dk sonra, PnL: %{pnl:+.2f}]")

        # DB'ye BEKLE ekle
        dt_str = exit_time.strftime("%Y-%m-%d %H:%M:%S")
        cur.execute("""
            INSERT INTO quant_v5.trade_logs (zaman, sembol, fiyat, obi, cvd, context, sinyal, fvg_top, fvg_bottom, fvg_depth)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
        """, (dt_str, sym, exit_price, 0.0, 0.0, "NEUTRAL", "[!] BEKLE", p['f_top'], p['f_bot'], p['f_depth']))
        conn.commit()
        time.sleep(0.1)

    conn.close()
    print("\nTüm açık işlemler başarıyla kapatıldı!")

if __name__ == '__main__':
    main()
