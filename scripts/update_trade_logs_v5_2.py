import os
import sys
import datetime
import requests
import pandas as pd

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

def fetch_klines(symbol, start_ms, end_ms):
    url = f"https://fapi.binance.com/fapi/v1/klines?symbol={symbol}&interval=1m&startTime={start_ms}&endTime={end_ms}&limit=500"
    try:
        r = requests.get(url, timeout=5).json()
        if isinstance(r, list) and len(r) > 0:
            return r
        url_spot = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=1m&startTime={start_ms}&endTime={end_ms}&limit=500"
        r_spot = requests.get(url_spot, timeout=5).json()
        if isinstance(r_spot, list):
            return r_spot
    except:
        pass
    return []

def main(commit_to_db=False):
    conn = get_supabase_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, zaman, sembol, fiyat, sinyal, obi, cvd, context, fvg_top, fvg_bottom, fvg_depth
        FROM quant_v5.trade_logs
        ORDER BY id ASC;
    """)
    rows = cur.fetchall()

    open_pos = {}
    trade_pairs = []

    for r in rows:
        _id, zaman, sym, fiyat, sinyal, obi, cvd, ctx, f_top, f_bot, f_depth = r
        if ('AL' in sinyal or 'SAT' in sinyal) and ('BEKLE' not in sinyal):
            open_pos[sym] = {
                'entry_id': _id, 'sym': sym, 'entry_price': float(fiyat),
                'entry_time': parse_utc_dt(zaman), 'direction': 'LONG' if 'AL' in sinyal else 'SHORT',
                'fvg_top': float(f_top or 0), 'fvg_bot': float(f_bot or 0),
                'fvg_depth': float(f_depth or 0)
            }
        elif 'BEKLE' in sinyal and sym in open_pos:
            p = open_pos[sym]
            p['exit_id'] = _id
            p['old_exit_price'] = float(fiyat)
            p['old_exit_time'] = parse_utc_dt(zaman)
            p['old_exit_obi'] = float(obi or 0)
            old_diff = (p['old_exit_price'] - p['entry_price']) if p['direction'] == 'LONG' else (p['entry_price'] - p['old_exit_price'])
            p['old_pnl'] = (old_diff / p['entry_price']) * 100
            trade_pairs.append(p)
            del open_pos[sym]

    print(f"Toplam {len(trade_pairs)} işlem eşleşti. V5.2 simülasyonu çalıştırılıyor...")

    updated_updates = []
    
    for i, p in enumerate(trade_pairs):
        sym = p['sym']
        entry_p = p['entry_price']
        entry_time = p['entry_time']
        is_long = (p['direction'] == 'LONG')
        fvg_top = p['fvg_top']
        fvg_bot = p['fvg_bot']

        start_ms = int(entry_time.timestamp() * 1000)
        end_ms = start_ms + 180 * 60 * 1000 # 3 saat
        klines = fetch_klines(sym, start_ms, end_ms)

        if not klines:
            # Kline verisi yoksa eski değerini koru
            p['new_exit_price'] = p['old_exit_price']
            p['new_exit_time'] = p['old_exit_time']
            p['new_pnl'] = p['old_pnl']
            p['reason'] = 'ESKI_KORUNDU'
            continue

        ref_bound = (fvg_bot if fvg_bot > 0 else entry_p * 0.9980) if is_long else (fvg_top if fvg_top > 0 else entry_p * 1.0020)
        active_sl = ref_bound * 0.9980 if is_long else ref_bound * 1.0020
        emergency_sl = entry_p * 0.9900 if is_long else entry_p * 1.0100

        highest_pnl = 0.0
        is_break_even = False
        new_exit_p = None
        new_exit_time = None
        new_reason = None

        actual_exit_ts = int(p['old_exit_time'].timestamp() * 1000)
        was_obi_exit = abs(p['old_exit_obi']) >= 0.15

        for k in klines:
            k_ts = k[0]
            o, h, l, c = float(k[1]), float(k[2]), float(k[3]), float(k[4])
            k_dt = datetime.datetime.fromtimestamp(k_ts / 1000, tz=datetime.timezone.utc)

            cur_gain = (h - entry_p) / entry_p * 100 if is_long else (entry_p - l) / entry_p * 100
            if cur_gain > highest_pnl:
                highest_pnl = cur_gain

            # 1. Acil Hard Stop Tick (%1.00)
            if is_long and l <= emergency_sl:
                new_exit_p = emergency_sl
                new_exit_time = k_dt
                new_reason = 'ACIL_STOP'
                break
            elif not is_long and h >= emergency_sl:
                new_exit_p = emergency_sl
                new_exit_time = k_dt
                new_reason = 'ACIL_STOP'
                break

            # 2. Break-Even (@ %0.45)
            if highest_pnl >= 0.45 and not is_break_even:
                is_break_even = True
                if is_long:
                    active_sl = max(active_sl, entry_p * 1.0005)
                else:
                    active_sl = min(active_sl, entry_p * 0.9995)

            # 3. Trailing Stop (@ %0.50+, 0.25 cb)
            if highest_pnl >= 0.50:
                if is_long:
                    trail_p = entry_p * (1.0 + (highest_pnl - 0.25) / 100)
                    active_sl = max(active_sl, trail_p)
                else:
                    trail_p = entry_p * (1.0 - (highest_pnl - 0.25) / 100)
                    active_sl = min(active_sl, trail_p)

            # 4. Mum Kapanışı SL Kontrolü
            if is_long and c <= active_sl:
                new_exit_p = c
                new_exit_time = k_dt
                new_reason = 'TRAILING_VEYA_BE' if is_break_even else 'FVG_MUM_SL'
                break
            elif not is_long and c >= active_sl:
                new_exit_p = c
                new_exit_time = k_dt
                new_reason = 'TRAILING_VEYA_BE' if is_break_even else 'FVG_MUM_SL'
                break

            # 5. OBI Reversal (Eğer eski bot burada çıktıysa, OBI 0.35'ten büyük müydü?):
            if was_obi_exit and abs(k_ts - actual_exit_ts) <= 60000:
                if abs(p['old_exit_obi']) >= 0.35:
                    new_exit_p = p['old_exit_price']
                    new_exit_time = p['old_exit_time']
                    new_reason = 'KUVVETLI_OBI_CIKIS'
                    break

        if new_exit_p is None:
            # Klines sonu
            last_k = klines[-1]
            new_exit_p = float(last_k[4])
            new_exit_time = datetime.datetime.fromtimestamp(last_k[0] / 1000, tz=datetime.timezone.utc)
            new_reason = 'TREND_SONU'

        p['new_exit_price'] = new_exit_p
        p['new_exit_time'] = new_exit_time
        new_diff = (new_exit_p - entry_p) if is_long else (entry_p - new_exit_p)
        p['new_pnl'] = (new_diff / entry_p) * 100
        p['reason'] = new_reason

        updated_updates.append((round(new_exit_p, 6), new_exit_time.strftime("%Y-%m-%d %H:%M:%S"), p['exit_id']))

    df = pd.DataFrame(trade_pairs)
    old_wins = df[df['old_pnl'] > 0]
    new_wins = df[df['new_pnl'] > 0]

    print("\n" + "="*80)
    print("                     GÜNCELLEME KARŞILAŞTIRMASI")
    print("="*80)
    print(f"Eski Win Rate:  %{len(old_wins)/len(df)*100:.1f} ({len(old_wins)}W / {len(df)-len(old_wins)}L) | Toplam PnL: %{df['old_pnl'].sum():+.2f}")
    print(f"Yeni Win Rate:  %{len(new_wins)/len(df)*100:.1f} ({len(new_wins)}W / {len(df)-len(new_wins)}L) | Toplam PnL: %{df['new_pnl'].sum():+.2f}")
    print("="*80)

    print("\nÖrnek Güncellenen İşlemler:")
    sample_df = df[['sym', 'direction', 'entry_time', 'entry_price', 'old_exit_price', 'old_pnl', 'new_exit_price', 'new_pnl', 'reason']]
    sample_df = sample_df.sort_values(by='new_pnl', ascending=False)
    print(sample_df.head(10).to_string(index=False))

    if commit_to_db:
        print("\nVeritabanı güncelleniyor (PostgreSQL quant_v5.trade_logs)...")
        for u in updated_updates:
            cur.execute("""
                UPDATE quant_v5.trade_logs
                SET fiyat = %s, zaman = %s
                WHERE id = %s;
            """, (u[0], u[1], u[2]))
        conn.commit()
        print("Tüm 74 işlem başarıyla güncellendi!")
    else:
        print("\n[BİLGİ] 'commit_to_db=False' modunda çalıştırıldı. Veritabanına yazmak için '--apply' parametresi ile çalıştırın.")

    conn.close()

if __name__ == '__main__':
    apply = '--apply' in sys.argv
    main(commit_to_db=apply)
