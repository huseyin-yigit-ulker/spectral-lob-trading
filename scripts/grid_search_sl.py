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

    print(f"Loaded {len(trades)} trades.")

    for t in trades:
        start_ts = int(t['entry_time'].timestamp() * 1000)
        end_ts = start_ts + 120 * 60 * 1000
        t['klines'] = fetch_klines(t['symbol'], start_ts, end_ts)

    # Grid search:
    # sl_buf: [0.10%, 0.15%, 0.20%, 0.25%]
    # be_thresh: [None, 0.30%, 0.35%, 0.40%]
    # tp_thresh: [0.50%, 0.65%, 0.80%, 1.00%, None]
    # trail_drop: [None, 0.20%, 0.25%]

    configs = []
    # Baseline
    configs.append({'name': 'MEVCUT SİSTEM (0.05% Tick, No TP)', 'buf': 0.0005, 'method': 'tick', 'be': None, 'tp': None, 'trail': None})
    
    # Candle close comparisons
    for buf in [0.0015, 0.0020, 0.0025]:
        for be in [None, 0.0030, 0.0035]:
            for tp in [0.0050, 0.0070, 0.0090]:
                configs.append({
                    'name': f"SL %{buf*100:.2f} (Kapanış) | BE: {f'%{be*100:.2f}' if be else 'YOK'} | TP: %{tp*100:.2f}",
                    'buf': buf,
                    'method': 'close',
                    'be': be,
                    'tp': tp,
                    'trail': None
                })
        # With Trailing
        configs.append({
            'name': f"SL %{buf*100:.2f} (Kapanış) | Trailing (BE@0.35%, Trail 0.20%)",
            'buf': buf,
            'method': 'close',
            'be': 0.0035,
            'tp': None,
            'trail': 0.0020
        })

    results = []

    for c in configs:
        pnls = []
        wins = 0
        losses = 0

        for t in trades:
            klines = t['klines']
            if not klines: continue

            entry_p = t['entry_price']
            is_long = t['direction'] == 'LONG'
            fvg_top = t['fvg_top']
            fvg_bot = t['fvg_bottom']

            ref_bound = (fvg_bot if fvg_bot > 0 else entry_p * 0.998) if is_long else (fvg_top if fvg_top > 0 else entry_p * 1.002)
            initial_sl = ref_bound * (1.0 - c['buf']) if is_long else ref_bound * (1.0 + c['buf'])
            emergency_sl = entry_p * 0.990 if is_long else entry_p * 1.010 # 1.0% acil hard stop

            cur_sl = initial_sl
            exit_p = None
            max_fav = 0.0

            for k in klines:
                o, h, l, close_p = float(k[1]), float(k[2]), float(k[3]), float(k[4])

                # Fav takibi
                fav = (h - entry_p) / entry_p if is_long else (entry_p - l) / entry_p
                if fav > max_fav: max_fav = fav

                # 1. Acil tick stop (Catastrophic 1% koruması)
                if is_long and l <= emergency_sl:
                    exit_p = emergency_sl
                    break
                elif not is_long and h >= emergency_sl:
                    exit_p = emergency_sl
                    break

                # 2. Break-even kuralı
                if c['be'] and max_fav >= c['be']:
                    if is_long:
                        cur_sl = max(cur_sl, entry_p * 1.0005)
                    else:
                        cur_sl = min(cur_sl, entry_p * 0.9995)

                # 3. Trailing kuralı
                if c['trail'] and max_fav >= (c['be'] or 0.0035):
                    if is_long:
                        trail_val = entry_p * (1.0 + max_fav - c['trail'])
                        cur_sl = max(cur_sl, trail_val)
                    else:
                        trail_val = entry_p * (1.0 - max_fav + c['trail'])
                        cur_sl = min(cur_sl, trail_val)

                # 4. Take Profit Target
                if c['tp']:
                    if is_long and h >= entry_p * (1.0 + c['tp']):
                        exit_p = entry_p * (1.0 + c['tp'])
                        break
                    elif not is_long and l <= entry_p * (1.0 - c['tp']):
                        exit_p = entry_p * (1.0 - c['tp'])
                        break

                # 5. Stop Loss Kontrolü
                if c['method'] == 'tick':
                    if is_long and l <= cur_sl:
                        exit_p = cur_sl
                        break
                    elif not is_long and h >= cur_sl:
                        exit_p = cur_sl
                        break
                elif c['method'] == 'close':
                    if is_long and close_p <= cur_sl:
                        exit_p = close_p
                        break
                    elif not is_long and close_p >= cur_sl:
                        exit_p = close_p
                        break

            if exit_p is None:
                exit_p = float(klines[-1][4])

            pnl = ((exit_p - entry_p) / entry_p * 100) if is_long else ((entry_p - exit_p) / entry_p * 100)
            pnls.append(pnl)
            if pnl > 0.05: wins += 1
            else: losses += 1

        tot_pnl = sum(pnls)
        avg_pnl = np.mean(pnls)
        wr = (wins / (wins + losses)) * 100
        sum_win = sum([p for p in pnls if p > 0])
        sum_loss = abs(sum([p for p in pnls if p < 0]))
        pf = (sum_win / sum_loss) if sum_loss > 0 else 999.0

        results.append({
            'Strateji': c['name'],
            'WinRate': wr,
            'W/L': f"{wins}/{losses}",
            'TotalPnL': tot_pnl,
            'AvgPnL': avg_pnl,
            'ProfitFactor': pf
        })

    df = pd.DataFrame(results).sort_values(by='TotalPnL', ascending=False)
    print("\n" + "="*100)
    print("                EN İYİ 15 STRATEJİ KARŞILAŞTIRMASI")
    print("="*100)
    print(df.head(15).to_string(index=False))

    print("\n" + "="*100)
    print("Mevcut Durum:")
    print(df[df['Strateji'].str.contains('MEVCUT')].to_string(index=False))

if __name__ == '__main__':
    main()
