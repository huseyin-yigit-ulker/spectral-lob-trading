import os
import sys
import datetime
import requests
import pandas as pd
import numpy as np

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

def main():
    conn = get_supabase_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, zaman, sembol, fiyat, sinyal, obi, cvd, context, fvg_top, fvg_bottom, fvg_depth
        FROM quant_v5.trade_logs
        ORDER BY zaman ASC;
    """)
    rows = cur.fetchall()
    conn.close()

    trades = []
    open_positions = {}

    for r in rows:
        log_id, log_zaman, sym, fiyat, sinyal, obi, cvd, ctx, fvg_top, fvg_bot, fvg_depth = r
        zaman_utc = parse_utc_dt(log_zaman)
        fiyat = float(fiyat)
        fvg_top = float(fvg_top or 0)
        fvg_bot = float(fvg_bot or 0)

        is_entry = ('AL' in sinyal or 'SAT' in sinyal) and ('BEKLE' not in sinyal)
        is_exit = 'BEKLE' in sinyal

        if is_entry:
            is_long = ('AL' in sinyal or 'LONG' in sinyal)
            open_positions[sym] = {
                'id': log_id,
                'symbol': sym,
                'direction': 'LONG' if is_long else 'SHORT',
                'entry_time': zaman_utc,
                'entry_price': fiyat,
                'fvg_top': fvg_top,
                'fvg_bottom': fvg_bot,
                'fvg_depth': float(fvg_depth or 0),
            }
        elif is_exit and sym in open_positions:
            pos = open_positions[sym]
            pos['exit_time'] = zaman_utc
            pos['exit_price'] = fiyat
            diff = (pos['exit_price'] - pos['entry_price']) if pos['direction'] == 'LONG' else (pos['entry_price'] - pos['exit_price'])
            pos['actual_pnl'] = (diff / pos['entry_price']) * 100
            trades.append(pos)
            del open_positions[sym]

    for t in trades:
        start_ts = int(t['entry_time'].timestamp() * 1000)
        end_ts = start_ts + 120 * 60 * 1000
        t['klines'] = fetch_klines(t['symbol'], start_ts, end_ts)

    # Let's test combinations with different filters and parameters
    tests = [
        {'name': '1. Sadece Kapanış (%0.20 SL, No TP, Tüm İşlemler)', 'min_depth': 0.0, 'sl_buf': 0.0020, 'be': None, 'tp': None, 'trail': None},
        {'name': '2. Sadece Kapanış (%0.10 SL, No TP, Tüm İşlemler)', 'min_depth': 0.0, 'sl_buf': 0.0010, 'be': None, 'tp': None, 'trail': None},
        {'name': '3. Sadece Kapanış (%0.05 SL, No TP, Tüm İşlemler)', 'min_depth': 0.0, 'sl_buf': 0.0005, 'be': None, 'tp': None, 'trail': None},
        {'name': '4. Kapanış %0.15 SL + TP %0.45 (1:3 Scalp)', 'min_depth': 0.0, 'sl_buf': 0.0015, 'be': 0.0025, 'tp': 0.0045, 'trail': None},
        {'name': '5. Kapanış %0.20 SL + TP %0.60', 'min_depth': 0.0, 'sl_buf': 0.0020, 'be': 0.0030, 'tp': 0.0060, 'trail': None},
        {'name': '6. Kapanış %0.20 SL + Trailing 0.20% (BE@0.30%)', 'min_depth': 0.0, 'sl_buf': 0.0020, 'be': 0.0030, 'tp': None, 'trail': 0.0020},
        {'name': '7. FVG Derinlik >%0.15 Filtreli + Kapanış %0.15 + TP %0.50', 'min_depth': 0.15, 'sl_buf': 0.0015, 'be': 0.0025, 'tp': 0.0050, 'trail': None},
        {'name': '8. FVG Derinlik >%0.15 Filtreli + Kapanış %0.20 + Trailing', 'min_depth': 0.15, 'sl_buf': 0.0020, 'be': 0.0030, 'tp': None, 'trail': 0.0020},
    ]

    out = []
    for cfg in tests:
        subset = [t for t in trades if t['fvg_depth'] >= cfg['min_depth']]
        pnls = []
        wins = 0
        losses = 0

        for t in subset:
            klines = t['klines']
            if not klines: continue
            entry_p = t['entry_price']
            is_long = t['direction'] == 'LONG'
            fvg_top = t['fvg_top']
            fvg_bot = t['fvg_bottom']

            ref_bound = (fvg_bot if fvg_bot > 0 else entry_p * 0.998) if is_long else (fvg_top if fvg_top > 0 else entry_p * 1.002)
            cur_sl = ref_bound * (1.0 - cfg['sl_buf']) if is_long else ref_bound * (1.0 + cfg['sl_buf'])
            emergency_sl = entry_p * 0.990 if is_long else entry_p * 1.010

            exit_p = None
            max_fav = 0.0

            for k in klines:
                o, h, l, c = float(k[1]), float(k[2]), float(k[3]), float(k[4])
                fav = (h - entry_p)/entry_p if is_long else (entry_p - l)/entry_p
                if fav > max_fav: max_fav = fav

                # Catastrophic stop
                if is_long and l <= emergency_sl: exit_p = emergency_sl; break
                elif not is_long and h >= emergency_sl: exit_p = emergency_sl; break

                # BE
                if cfg['be'] and max_fav >= cfg['be']:
                    if is_long: cur_sl = max(cur_sl, entry_p * 1.0005)
                    else: cur_sl = min(cur_sl, entry_p * 0.9995)

                # Trail
                if cfg['trail'] and max_fav >= (cfg['be'] or 0.0030):
                    if is_long: cur_sl = max(cur_sl, entry_p * (1.0 + max_fav - cfg['trail']))
                    else: cur_sl = min(cur_sl, entry_p * (1.0 - max_fav + cfg['trail']))

                # TP
                if cfg['tp']:
                    if is_long and h >= entry_p * (1.0 + cfg['tp']): exit_p = entry_p * (1.0 + cfg['tp']); break
                    elif not is_long and l <= entry_p * (1.0 - cfg['tp']): exit_p = entry_p * (1.0 - cfg['tp']); break

                # Candle close SL
                if is_long and c <= cur_sl: exit_p = c; break
                elif not is_long and c >= cur_sl: exit_p = c; break

            if exit_p is None: exit_p = float(klines[-1][4])

            pnl = ((exit_p - entry_p)/entry_p*100) if is_long else ((entry_p - exit_p)/entry_p*100)
            pnls.append(pnl)
            if pnl > 0.05: wins += 1
            else: losses += 1

        tot_pnl = sum(pnls)
        wr = (wins / (wins + losses) * 100) if (wins + losses) > 0 else 0
        w_sum = sum([p for p in pnls if p > 0])
        l_sum = abs(sum([p for p in pnls if p < 0]))
        pf = (w_sum / l_sum) if l_sum > 0 else 999.0

        out.append({
            'Strateji': cfg['name'],
            'İşlem Sayısı': len(pnls),
            'Win Rate': f"%{wr:.1f}",
            'W/L': f"{wins}/{losses}",
            'Toplam PnL': f"%{tot_pnl:+.2f}",
            'Ort. PnL': f"%{np.mean(pnls):+.3f}",
            'Profit Factor': f"{pf:.2f}"
        })

    print(pd.DataFrame(out).to_string(index=False))

if __name__ == '__main__':
    main()
