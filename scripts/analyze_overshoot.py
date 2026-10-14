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
            trades.append(pos)
            del open_positions[sym]

    print(f"Loaded {len(trades)} trades.")

    stats = []
    for t in trades:
        start_ts = int(t['entry_time'].timestamp() * 1000)
        end_ts = start_ts + 60 * 60 * 1000
        klines = fetch_klines(t['symbol'], start_ts, end_ts)
        if not klines: continue

        entry_p = t['entry_price']
        is_long = t['direction'] == 'LONG'
        fvg_top = t['fvg_top']
        fvg_bot = t['fvg_bottom']

        # FVG sınırını ne kadar aştı? (Wick vs Close)
        # Long icin: fvg_bot altina inen min deger ve min kapanis
        # Short icin: fvg_top ustune cikan max deger ve max kapanis
        ref_boundary = fvg_bot if is_long else fvg_top
        if ref_boundary <= 0:
            continue

        wick_overshoot_pct = 0.0 # Igne (Wick) asimi
        close_overshoot_pct = 0.0 # Mum Kapanisi asimi

        for k in klines:
            h = float(k[2])
            l = float(k[3])
            c = float(k[4])

            if is_long:
                # Eger l < fvg_bot ise ne kadar altinda?
                if l < ref_boundary:
                    diff_pct = (ref_boundary - l) / ref_boundary * 100
                    if diff_pct > wick_overshoot_pct: wick_overshoot_pct = diff_pct
                if c < ref_boundary:
                    diff_pct = (ref_boundary - c) / ref_boundary * 100
                    if diff_pct > close_overshoot_pct: close_overshoot_pct = diff_pct
            else:
                # Eger h > fvg_top ise ne kadar ustunde?
                if h > ref_boundary:
                    diff_pct = (h - ref_boundary) / ref_boundary * 100
                    if diff_pct > wick_overshoot_pct: wick_overshoot_pct = diff_pct
                if c > ref_boundary:
                    diff_pct = (c - ref_boundary) / ref_boundary * 100
                    if diff_pct > close_overshoot_pct: close_overshoot_pct = diff_pct

        stats.append({
            'symbol': t['symbol'],
            'direction': t['direction'],
            'fvg_depth': t['fvg_depth'],
            'wick_overshoot_pct': wick_overshoot_pct,
            'close_overshoot_pct': close_overshoot_pct
        })

    df = pd.DataFrame(stats)
    print("\n--- FVG SINIRINI ASMA ISTATISTIKLERI (Overshoot) ---")
    print(f"FVG Sinirini Igne (Wick) ile Asan Islem Orani: %{(df['wick_overshoot_pct'] > 0.05).mean()*100:.1f}")
    print(f"FVG Sinirini Mum Kapanisi ile Asan Islem Orani: %{(df['close_overshoot_pct'] > 0.05).mean()*100:.1f}")
    print("\nIgne (Wick) Asim Yuzdeleri Ozeti:")
    print(df['wick_overshoot_pct'].describe())
    print("\nMum Kapanisi (Close) Asim Yuzdeleri Ozeti:")
    print(df['close_overshoot_pct'].describe())

    # Yuzdelik dilimler
    print("\nIgne Asim Persentilleri:")
    for p in [25, 50, 75, 80, 90]:
        print(f"  %{p}: %{np.percentile(df['wick_overshoot_pct'], p):.3f}")

if __name__ == '__main__':
    main()
