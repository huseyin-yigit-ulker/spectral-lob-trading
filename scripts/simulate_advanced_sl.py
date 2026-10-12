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
            }
        elif is_exit and sym in open_positions:
            pos = open_positions[sym]
            pos['exit_time'] = zaman_utc
            pos['exit_price'] = fiyat
            diff = (pos['exit_price'] - pos['entry_price']) if pos['direction'] == 'LONG' else (pos['entry_price'] - pos['exit_price'])
            pos['actual_pnl'] = (diff / pos['entry_price']) * 100
            trades.append(pos)
            del open_positions[sym]

    print(f"Loaded {len(trades)} trades. Fetching klines...")

    for t in trades:
        start_ts = int(t['entry_time'].timestamp() * 1000)
        end_ts = start_ts + 90 * 60 * 1000  # 90 dakika
        t['klines'] = fetch_klines(t['symbol'], start_ts, end_ts)

    # Parametreler:
    # sl_method: 'tick' vs 'candle_close'
    # sl_buffer: %0.05, %0.15, %0.20, %0.25, %0.30
    # be_trigger: Break-even tetikleme seviyesi (örn: %0.30 kâra ulaşınca SL'i girişe çek)
    # tp_target: Sabit Take-profit (örn: %0.60, %0.80, %1.00 veya None)
    # trailing_callback: Zirveden geri çekilme (örn: %0.25)

    sim_configs = [
        # Mevcut durum
        {'name': 'Mevcut (0.05% Tick, No TP)', 'sl_method': 'tick', 'sl_buf': 0.0005, 'be_trigger': None, 'tp_target': None, 'trail': None},
        
        # Sadece SL genisleterek
        {'name': 'Geniş SL 0.20% (Tick, No TP)', 'sl_method': 'tick', 'sl_buf': 0.0020, 'be_trigger': None, 'tp_target': None, 'trail': None},
        {'name': 'Geniş SL 0.20% (Kapanış, No TP)', 'sl_method': 'candle_close', 'sl_buf': 0.0020, 'be_trigger': None, 'tp_target': None, 'trail': None},

        # Genis SL + TP
        {'name': 'Geniş SL 0.20% + TP 0.60% (Tick)', 'sl_method': 'tick', 'sl_buf': 0.0020, 'be_trigger': None, 'tp_target': 0.0060, 'trail': None},
        {'name': 'Geniş SL 0.20% + TP 0.60% (Kapanış)', 'sl_method': 'candle_close', 'sl_buf': 0.0020, 'be_trigger': None, 'tp_target': 0.0060, 'trail': None},
        {'name': 'Geniş SL 0.25% + TP 0.75% (Kapanış)', 'sl_method': 'candle_close', 'sl_buf': 0.0025, 'be_trigger': None, 'tp_target': 0.0075, 'trail': None},

        # Genis SL + Break-Even (Başa Baş) + TP
        {'name': 'Geniş SL 0.20% (Kapanış) + BE@0.30% + TP 0.60%', 'sl_method': 'candle_close', 'sl_buf': 0.0020, 'be_trigger': 0.0030, 'tp_target': 0.0060, 'trail': None},
        {'name': 'Geniş SL 0.25% (Kapanış) + BE@0.35% + TP 0.70%', 'sl_method': 'candle_close', 'sl_buf': 0.0025, 'be_trigger': 0.0035, 'tp_target': 0.0070, 'trail': None},
        {'name': 'Geniş SL 0.25% (Kapanış) + BE@0.35% + TP 0.85%', 'sl_method': 'candle_close', 'sl_buf': 0.0025, 'be_trigger': 0.0035, 'tp_target': 0.0085, 'trail': None},

        # Genis SL + Trailing Stop
        {'name': 'Geniş SL 0.20% (Kapanış) + Trailing (Start@0.35%, Drop 0.20%)', 'sl_method': 'candle_close', 'sl_buf': 0.0020, 'be_trigger': 0.0035, 'tp_target': None, 'trail': 0.0020},
        {'name': 'Geniş SL 0.25% (Kapanış) + Trailing (Start@0.40%, Drop 0.25%)', 'sl_method': 'candle_close', 'sl_buf': 0.0025, 'be_trigger': 0.0040, 'tp_target': None, 'trail': 0.0025},
    ]

    results = []

    for cfg in sim_configs:
        trade_pnls = []
        wins = 0
        losses = 0

        for t in trades:
            klines = t['klines']
            if not klines: continue

            entry_p = t['entry_price']
            is_long = t['direction'] == 'LONG'
            fvg_top = t['fvg_top']
            fvg_bot = t['fvg_bottom']

            # Ilk SL seviyesi
            if is_long:
                ref_bound = fvg_bot if fvg_bot > 0 else entry_p * 0.998
                initial_sl = ref_bound * (1.0 - cfg['sl_buf'])
            else:
                ref_bound = fvg_top if fvg_top > 0 else entry_p * 1.002
                initial_sl = ref_bound * (1.0 + cfg['sl_buf'])

            cur_sl = initial_sl
            exit_price = None
            max_fav = 0.0

            for k in klines:
                o, h, l, c = float(k[1]), float(k[2]), float(k[3]), float(k[4])

                # Kâr / Zarar takibi
                if is_long:
                    fav_high = (h - entry_p) / entry_p
                    if fav_high > max_fav: max_fav = fav_high
                else:
                    fav_low = (entry_p - l) / entry_p
                    if fav_low > max_fav: max_fav = fav_low

                # 1. Break-Even Kontrolu
                if cfg['be_trigger'] and max_fav >= cfg['be_trigger']:
                    # SL'i giris seviyesine (komisyon payiyla) cek
                    if is_long:
                        cur_sl = max(cur_sl, entry_p * 1.0005)
                    else:
                        cur_sl = min(cur_sl, entry_p * 0.9995)

                # 2. Trailing Stop Kontrolu
                if cfg['trail'] and max_fav >= (cfg['be_trigger'] or 0.0030):
                    if is_long:
                        trail_sl = entry_p * (1.0 + max_fav - cfg['trail'])
                        cur_sl = max(cur_sl, trail_sl)
                    else:
                        trail_sl = entry_p * (1.0 - max_fav + cfg['trail'])
                        cur_sl = min(cur_sl, trail_sl)

                # 3. Take Profit Hedefi Kontrolu
                if cfg['tp_target']:
                    if is_long and h >= entry_p * (1.0 + cfg['tp_target']):
                        exit_price = entry_p * (1.0 + cfg['tp_target'])
                        break
                    elif not is_long and l <= entry_p * (1.0 - cfg['tp_target']):
                        exit_price = entry_p * (1.0 - cfg['tp_target'])
                        break

                # 4. Stop Loss Kontrolu
                hit_sl = False
                if cfg['sl_method'] == 'tick':
                    if is_long and l <= cur_sl:
                        hit_sl = True
                        exit_price = cur_sl
                    elif not is_long and h >= cur_sl:
                        hit_sl = True
                        exit_price = cur_sl
                elif cfg['sl_method'] == 'candle_close':
                    if is_long and c <= cur_sl:
                        hit_sl = True
                        exit_price = c
                    elif not is_long and c >= cur_sl:
                        hit_sl = True
                        exit_price = c

                if hit_sl:
                    break

            # Mumlar bittiyse ve cikilmadiysa son mum kapanisi
            if exit_price is None:
                exit_price = float(klines[-1][4])

            pnl = ((exit_price - entry_p) / entry_p * 100) if is_long else ((entry_p - exit_price) / entry_p * 100)
            trade_pnls.append(pnl)
            if pnl > 0.05:
                wins += 1
            else:
                losses += 1

        tot = wins + losses
        wr = (wins / tot * 100) if tot > 0 else 0
        tot_pnl = sum(trade_pnls)
        avg_pnl = np.mean(trade_pnls) if trade_pnls else 0
        sum_win = sum([p for p in trade_pnls if p > 0])
        sum_loss = abs(sum([p for p in trade_pnls if p < 0]))
        pf = (sum_win / sum_loss) if sum_loss > 0 else 999.0

        results.append({
            'Strateji': cfg['name'],
            'Win Rate': f"%{wr:.1f}",
            'W/L': f"{wins}/{losses}",
            'Toplam PnL': f"%{tot_pnl:+.2f}",
            'Ort. PnL': f"%{avg_pnl:+.3f}",
            'Profit Factor': f"{pf:.2f}"
        })

    df = pd.DataFrame(results)
    print("\n" + "="*95)
    print("                     GELİŞMİŞ SL + KÂR AL (TP) SİMÜLASYONU")
    print("="*95)
    print(df.to_string(index=False))

if __name__ == '__main__':
    main()
