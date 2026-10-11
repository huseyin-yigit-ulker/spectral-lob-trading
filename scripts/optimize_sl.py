import os
import sys
import datetime
import time
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
    if not conn:
        print("Veritabani baglantisi basarisiz.")
        return

    cur = conn.cursor()
    cur.execute("""
        SELECT id, zaman, sembol, fiyat, sinyal, obi, cvd, context, fvg_top, fvg_bottom, fvg_depth
        FROM quant_v5.trade_logs
        ORDER BY zaman ASC;
    """)
    rows = cur.fetchall()
    conn.close()

    print(f"Toplam {len(rows)} adet log kaydi okundu.")

    # 1. Islemleri grupla (Reconstruct trades)
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
                'context': ctx,
                'obi': float(obi or 0),
                'cvd': float(cvd or 0),
            }
        elif is_exit and sym in open_positions:
            pos = open_positions[sym]
            pos['exit_time'] = zaman_utc
            pos['exit_price'] = fiyat
            diff = (pos['exit_price'] - pos['entry_price']) if pos['direction'] == 'LONG' else (pos['entry_price'] - pos['exit_price'])
            pos['actual_pnl'] = (diff / pos['entry_price']) * 100
            trades.append(pos)
            del open_positions[sym]

    print(f"Toplam {len(trades)} adet tamamlanmis islem tespit edildi.")

    # 2. Mum verilerini cek
    print("\nBinance uzerinden gecmis 1m mumlari cekiliyor...")
    for i, t in enumerate(trades):
        start_ts = int(t['entry_time'].timestamp() * 1000)
        end_ts = start_ts + 120 * 60 * 1000
        t['klines'] = fetch_klines(t['symbol'], start_ts, end_ts)
        if (i + 1) % 15 == 0 or (i + 1) == len(trades):
            print(f"  [{i+1}/{len(trades)}] {t['symbol']} verileri indirildi...")
        time.sleep(0.04)

    # 3. Karsilastirmali Stratejiler
    configs = [
        {
            'name': '1. Mevcut Canlı Bot (Eski: %0.05 Tick, No TP)',
            'mode': 'mevcut'
        },
        {
            'name': '2. Sadece Kapanış (%0.20 Geniş SL, No TP)',
            'mode': 'sim',
            'sl_buf': 0.0020,
            'be_thresh': None,
            'trail': None,
            'min_depth': 0.0
        },
        {
            'name': '3. Yeni Model (%0.20 SL Kapanış + BE@0.30% + Trailing %0.20)',
            'mode': 'sim',
            'sl_buf': 0.0020,
            'be_thresh': 0.0030,
            'trail': 0.0020,
            'min_depth': 0.0
        },
        {
            'name': '4. Yeni Model + FVG >%0.15 Filtresi (Tavsiye Edilen)',
            'mode': 'sim',
            'sl_buf': 0.0020,
            'be_thresh': 0.0030,
            'trail': 0.0020,
            'min_depth': 0.15
        }
    ]

    report = []
    trade_comparisons = []

    for cfg in configs:
        pnls = []
        wins = 0
        losses = 0
        results_map = {}

        subset = [t for t in trades if t['fvg_depth'] >= cfg.get('min_depth', 0.0)]

        for t in subset:
            if cfg['mode'] == 'mevcut':
                pnl = t['actual_pnl']
                pnls.append(pnl)
                results_map[t['id']] = pnl
                if pnl > 0.05: wins += 1
                else: losses += 1
                continue

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
                o, h, l, close_p = float(k[1]), float(k[2]), float(k[3]), float(k[4])

                fav = (h - entry_p)/entry_p if is_long else (entry_p - l)/entry_p
                if fav > max_fav: max_fav = fav

                # 1. Acil Hard Stop (%1.00 anlık fiyat)
                if is_long and l <= emergency_sl: exit_p = emergency_sl; break
                elif not is_long and h >= emergency_sl: exit_p = emergency_sl; break

                # 2. Break-Even kuralı (@ %0.30 kâr)
                if cfg['be_thresh'] and max_fav >= cfg['be_thresh']:
                    if is_long: cur_sl = max(cur_sl, entry_p * 1.0005)
                    else: cur_sl = min(cur_sl, entry_p * 0.9995)

                # 3. Trailing Stop kuralı (@ %0.35+ kâr, %0.20 çekilme)
                if cfg['trail'] and max_fav >= 0.0035:
                    if is_long:
                        trail_val = entry_p * (1.0 + max_fav - cfg['trail'])
                        cur_sl = max(cur_sl, trail_val)
                    else:
                        trail_val = entry_p * (1.0 - max_fav + cfg['trail'])
                        cur_sl = min(cur_sl, trail_val)

                # 4. Mum Kapanışı ile SL Kontrolü
                if is_long and close_p <= cur_sl: exit_p = close_p; break
                elif not is_long and close_p >= cur_sl: exit_p = close_p; break

            if exit_p is None:
                exit_p = float(klines[-1][4])

            pnl = ((exit_p - entry_p)/entry_p*100) if is_long else ((entry_p - exit_p)/entry_p*100)
            pnls.append(pnl)
            results_map[t['id']] = pnl
            if pnl > 0.05: wins += 1
            else: losses += 1

        tot_pnl = sum(pnls)
        tot_trades = wins + losses
        wr = (wins / tot_trades * 100) if tot_trades > 0 else 0
        w_sum = sum([p for p in pnls if p > 0])
        l_sum = abs(sum([p for p in pnls if p < 0]))
        pf = (w_sum / l_sum) if l_sum > 0 else 999.0

        report.append({
            'Strateji': cfg['name'],
            'İşlem': tot_trades,
            'Win Rate': f"%{wr:.1f}",
            'W / L': f"{wins}/{losses}",
            'Toplam PnL': f"%{tot_pnl:+.2f}",
            'Ort. PnL': f"%{np.mean(pnls):+.3f}",
            'Profit Factor': f"{pf:.2f}"
        })

    print("\n" + "="*105)
    print("                     BACKTEST PERFORMANS KARŞILAŞTIRMASI")
    print("="*105)
    print(pd.DataFrame(report).to_string(index=False))

    print("\n" + "="*105)
    print("YENİ MODEL ÖZETİ:")
    print("  * SL Buffer:           %0.20 FVG dışı (SHORT: top*1.0020, LONG: bot*0.9980)")
    print("  * Tetiklenme:          1 Dakikalık Mum Kapanışı (kline_1m, k['x'] == True)")
    print("  * Acil Hard Stop:      %1.00 Anlık Tick (Catastrophic Protection)")
    print("  * Başa Baş (BE):       +%0.30 kârda SL giriş seviyesine çekilir")
    print("  * Trailing Stop:       +%0.35 kârda başlar, zirveden %0.20 çekilmede kâr alınır")
    print("="*105 + "\n")

if __name__ == '__main__':
    main()
