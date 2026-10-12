import os
import sys
import datetime
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
        }
    elif is_exit and sym in open_positions:
        pos = open_positions[sym]
        pos['exit_time'] = zaman_utc
        pos['exit_price'] = fiyat
        pos['exit_obi'] = float(obi or 0)
        pos['duration_sec'] = int((pos['exit_time'] - pos['entry_time']).total_seconds())
        diff = (pos['exit_price'] - pos['entry_price']) if pos['direction'] == 'LONG' else (pos['entry_price'] - pos['exit_price'])
        pos['actual_pnl'] = (diff / pos['entry_price']) * 100
        
        # SL yuzunden mi cikti, OBI yuzunden mi?
        # Long: SL bot_bound * 0.9995. Exit price <= SL?
        # Short: SL top_bound * 1.0005. Exit price >= SL?
        is_long = pos['direction'] == 'LONG'
        if is_long:
            sl_price = pos['fvg_bottom'] * 0.9995 if pos['fvg_bottom'] > 0 else 0
            stopped = pos['exit_price'] <= sl_price if sl_price > 0 else False
        else:
            sl_price = pos['fvg_top'] * 1.0005 if pos['fvg_top'] > 0 else 999999
            stopped = pos['exit_price'] >= sl_price if sl_price < 999999 else False
        
        pos['exit_reason'] = 'SL_TRIGGER' if stopped else ('OBI_REVERSAL' if abs(pos['exit_obi']) >= 0.15 else 'OTHER')
        trades.append(pos)
        del open_positions[sym]

df = pd.DataFrame(trades)
print(f"Toplam Islem: {len(df)}")
print("\nCikis Nedenleri:")
print(df['exit_reason'].value_counts())
print("\nCikis Nedenine Gore Ortalama Sure (saniye) ve PnL:")
print(df.groupby('exit_reason')[['duration_sec', 'actual_pnl']].mean())
print("\nIslem Sureleri Dagilimi:")
print(df['duration_sec'].describe())
