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
    except Exception as e:
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
            }
        elif is_exit and sym in open_positions:
            pos = open_positions[sym]
            pos['exit_time'] = zaman_utc
            pos['exit_price'] = fiyat
            diff = (pos['exit_price'] - pos['entry_price']) if pos['direction'] == 'LONG' else (pos['entry_price'] - pos['exit_price'])
            pos['actual_pnl'] = (diff / pos['entry_price']) * 100
            trades.append(pos)
            del open_positions[sym]

    print(f"Loaded {len(trades)} trades.")

    trade_stats = []
    for t in trades:
        start_ts = int(t['entry_time'].timestamp() * 1000)
        # 60 mins after entry
        end_ts = start_ts + 60 * 60 * 1000
        klines = fetch_klines(t['symbol'], start_ts, end_ts)
        if not klines:
            continue

        entry_p = t['entry_price']
        is_long = t['direction'] == 'LONG'

        max_profit_pct = 0.0
        max_drawdown_pct = 0.0

        for k in klines:
            h = float(k[2])
            l = float(k[3])
            c = float(k[4])

            if is_long:
                fav = (h - entry_p) / entry_p * 100
                adv = (entry_p - l) / entry_p * 100
            else:
                fav = (entry_p - l) / entry_p * 100
                adv = (h - entry_p) / entry_p * 100

            if fav > max_profit_pct: max_profit_pct = fav
            if adv > max_drawdown_pct: max_drawdown_pct = adv

        trade_stats.append({
            'symbol': t['symbol'],
            'direction': t['direction'],
            'entry_time': t['entry_time'].strftime('%Y-%m-%d %H:%M'),
            'entry_price': entry_p,
            'actual_pnl': t['actual_pnl'],
            'max_profit_pct': max_profit_pct,
            'max_drawdown_pct': max_drawdown_pct,
            'klines_count': len(klines)
        })

    df = pd.DataFrame(trade_stats)
    print("\n--- MFE / MAE Ozet (Giris sonrasi ilk 60 dk icindeki potansiyel hareket) ---")
    print(f"Ortalama Gerceklesen PnL (Mevcut Bot): %{df['actual_pnl'].mean():.2f}")
    print(f"Ortalama Ulasilan Max Kar (MFE):        +%{df['max_profit_pct'].mean():.2f}")
    print(f"Medyan Ulasilan Max Kar:               +%{df['max_profit_pct'].median():.2f}")
    print(f"Ortalama Gorulen Max Zarar (MAE):      -%{df['max_drawdown_pct'].mean():.2f}")
    print(f"Medyan Gorulen Max Zarar:              -%{df['max_drawdown_pct'].median():.2f}")
    
    # +0.30% ve uzeri kara ulasan islem orani
    p30 = (df['max_profit_pct'] >= 0.30).mean() * 100
    p50 = (df['max_profit_pct'] >= 0.50).mean() * 100
    p70 = (df['max_profit_pct'] >= 0.70).mean() * 100
    p100 = (df['max_profit_pct'] >= 1.00).mean() * 100

    print(f"\nİşlemlerin +%0.30 kâra ulaşma oranı: %{p30:.1f}")
    print(f"İşlemlerin +%0.50 kâra ulaşma oranı: %{p50:.1f}")
    print(f"İşlemlerin +%0.70 kâra ulaşma oranı: %{p70:.1f}")
    print(f"İşlemlerin +%1.00 kâra ulaşma oranı: %{p100:.1f}")

    # Detayli en iyi 10 islem
    print("\nEn cok kara ulasan ornek 10 islem:")
    print(df.sort_values(by='max_profit_pct', ascending=False)[['symbol', 'direction', 'entry_time', 'actual_pnl', 'max_profit_pct', 'max_drawdown_pct']].head(10).to_string(index=False))

if __name__ == '__main__':
    main()
