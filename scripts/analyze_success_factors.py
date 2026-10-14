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
            'symbol': sym,
            'direction': 'LONG' if is_long else 'SHORT',
            'entry_time': zaman_utc,
            'entry_price': fiyat,
            'fvg_top': fvg_top,
            'fvg_bottom': fvg_bot,
            'fvg_depth': float(fvg_depth or 0),
            'context': ctx,
            'obi': float(obi or 0),
            'cvd': float(cvd or 0),
        }
    elif is_exit and sym in open_positions:
        pos = open_positions[sym]
        trades.append(pos)
        del open_positions[sym]

for t in trades:
    start_ts = int(t['entry_time'].timestamp() * 1000)
    end_ts = start_ts + 60 * 60 * 1000
    klines = fetch_klines(t['symbol'], start_ts, end_ts)
    if not klines: continue
    
    entry_p = t['entry_price']
    is_long = t['direction'] == 'LONG'
    
    max_fav = 0.0
    max_adv = 0.0
    for k in klines:
        h, l, c = float(k[2]), float(k[3]), float(k[4])
        fav = (h - entry_p)/entry_p*100 if is_long else (entry_p - l)/entry_p*100
        adv = (entry_p - l)/entry_p*100 if is_long else (h - entry_p)/entry_p*100
        if fav > max_fav: max_fav = fav
        if adv > max_adv: max_adv = adv
    t['max_fav'] = max_fav
    t['max_adv'] = max_adv

df = pd.DataFrame(trades)
df['success'] = df['max_fav'] >= 0.50 # %0.50 ve ustu kara ulasanlar

print("=== BAŞARILI (%0.50+ KÂR GÖREN) vs BAŞARISIZ İŞLEMLERİN KARŞILAŞTIRMASI ===")
print(df.groupby('success')[['fvg_depth', 'obi', 'cvd', 'max_fav', 'max_adv']].mean())
print("\nYÖNLERE GÖRE (LONG vs SHORT) BAŞARI ORANI:")
print(df.groupby('direction')['success'].agg(['count', 'mean']))
print("\nFVG DEPTH SEGMENTLERİNE GÖRE BAŞARI ORANI:")
df['fvg_tier'] = pd.qcut(df['fvg_depth'], 3, duplicates='drop')
print(df.groupby('fvg_tier')['success'].agg(['count', 'mean', lambda x: df.loc[x.index, 'max_fav'].mean()]))
