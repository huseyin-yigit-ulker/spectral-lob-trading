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
    if not conn:
        print("DB bağlantısı kurulamadı.")
        sys.exit(1)

    cur = conn.cursor()
    cur.execute("""
        SELECT id, zaman, sembol, fiyat, sinyal, obi, cvd, context, fvg_top, fvg_bottom, fvg_depth, btc_regime, entry_reason
        FROM quant_v5.trade_logs
        ORDER BY zaman ASC;
    """)
    rows = cur.fetchall()
    conn.close()

    trades = []
    open_positions = {}

    for r in rows:
        log_id, log_zaman, sym, fiyat, sinyal, obi, cvd, ctx, fvg_top, fvg_bot, fvg_depth, btc_reg, ent_reas = r
        zaman_utc = parse_utc_dt(log_zaman)
        fiyat = float(fiyat)
        fvg_top = float(fvg_top or 0)
        fvg_bot = float(fvg_bot or 0)
        fvg_depth = float(fvg_depth or 0)

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
                'fvg_depth': fvg_depth,
                'obi': float(obi or 0),
                'cvd': float(cvd or 0),
                'btc_regime': str(btc_reg or 'UNKNOWN'),
                'entry_reason': str(ent_reas or ''),
            }
        elif is_exit and sym in open_positions:
            pos = open_positions[sym]
            pos['exit_time'] = zaman_utc
            pos['exit_price'] = fiyat
            pos['exit_obi'] = float(obi or 0)
            diff = (pos['exit_price'] - pos['entry_price']) if pos['direction'] == 'LONG' else (pos['entry_price'] - pos['exit_price'])
            pos['actual_pnl'] = (diff / pos['entry_price']) * 100
            trades.append(pos)
            del open_positions[sym]

    print(f"Toplam {len(trades)} işlem veritabanından çekildi. Binance 1m mumları alınıyor...")

    for i, t in enumerate(trades):
        start_ts = int(t['entry_time'].timestamp() * 1000)
        end_ts = start_ts + 120 * 60 * 1000
        t['klines'] = fetch_klines(t['symbol'], start_ts, end_ts)

    def simulate_trade(t, cfg):
        # Filtre 1: Aşırı Geniş FVG Filtresi (SIREN %11.7, WAL %1.38 gibi manipülatif tahtalar)
        if cfg.get('max_fvg_depth') and t['fvg_depth'] > cfg['max_fvg_depth']:
            return None, 'FILTERED_EXCESSIVE_FVG'

        # Filtre 2: Katı BTC Trend Filtresi (4H Düşüşteyken NEUTRAL altcoin LONG'larını engelle)
        if cfg.get('filter_neutral_long') and t['direction'] == 'LONG':
            is_sniper = 'Sniper' in t['entry_reason'] or abs(t['obi']) >= 0.70
            if not is_sniper and ('NEUTRAL' in t['btc_regime'] or 'UNKNOWN' in t['btc_regime'] or 'BEARISH' in t['btc_regime']):
                return None, 'FILTERED_BTC_TREND_CONFLICT'

        klines = t['klines']
        if not klines:
            return t['actual_pnl'], 'NO_KLINES'

        entry_p = t['entry_price']
        is_long = t['direction'] == 'LONG'
        fvg_top = t['fvg_top']
        fvg_bot = t['fvg_bottom']

        # Başlangıç SL
        if is_long:
            ref_bound = fvg_bot if fvg_bot > 0 else entry_p * 0.998
            initial_sl = ref_bound * (1.0 - cfg.get('sl_buffer', 0.0020))
            if cfg.get('hard_sl_cap'):
                initial_sl = max(initial_sl, entry_p * (1.0 - cfg['hard_sl_cap']))
        else:
            ref_bound = fvg_top if fvg_top > 0 else entry_p * 1.002
            initial_sl = ref_bound * (1.0 + cfg.get('sl_buffer', 0.0020))
            if cfg.get('hard_sl_cap'):
                initial_sl = min(initial_sl, entry_p * (1.0 + cfg['hard_sl_cap']))

        cur_sl = initial_sl
        max_fav = 0.0
        exit_price = None
        exit_type = None

        # Gerçek canlıda çıkış zamanı sınırı
        actual_exit_ts = t['exit_time'].timestamp() * 1000

        for k in klines:
            k_ts = k[0]
            o, h, l, c = float(k[1]), float(k[2]), float(k[3]), float(k[4])

            fav = (h - entry_p) / entry_p if is_long else (entry_p - l) / entry_p
            if fav > max_fav: max_fav = fav

            # 1. Take Profit (TP) Kontrolü (Geniş Runner Hedefi: %2.00)
            if cfg.get('tp_target') and max_fav >= cfg['tp_target']:
                exit_price = entry_p * (1.0 + cfg['tp_target']) if is_long else entry_p * (1.0 - cfg['tp_target'])
                exit_type = f"TAKE_PROFIT_LIMIT (+%{cfg['tp_target']*100:.1f})"
                break

            # 2. Break-Even Kontrolü (Kâr %0.45'e ulaştığında SL'i komisyon payıyla girişe çek)
            if cfg.get('be_trigger') and max_fav >= cfg['be_trigger']:
                if is_long:
                    cur_sl = max(cur_sl, entry_p * 1.0005)
                else:
                    cur_sl = min(cur_sl, entry_p * 0.9995)

            # 3. Anlık Dinamik Trailing Stop Kontrolü (Zirveden %0.30 çekilme)
            if cfg.get('trail_start') and max_fav >= cfg['trail_start']:
                cb = cfg.get('trail_callback', 0.0030)
                if is_long:
                    trail_level = entry_p * (1.0 + max_fav - cb)
                    cur_sl = max(cur_sl, trail_level)
                else:
                    trail_level = entry_p * (1.0 - max_fav + cb)
                    cur_sl = min(cur_sl, trail_level)

            # 4. Stop Loss Kontrolü
            if cfg.get('sl_mode') == 'tick':
                # Anlık Tick SL (Mum kapanışı beklemeden anında stop)
                if is_long and l <= cur_sl:
                    exit_price = cur_sl
                    exit_type = "TRAILING_STOP_TICK" if cur_sl > initial_sl else "STOP_LOSS_TICK"
                    break
                elif not is_long and h >= cur_sl:
                    exit_price = cur_sl
                    exit_type = "TRAILING_STOP_TICK" if cur_sl < initial_sl else "STOP_LOSS_TICK"
                    break
            else:
                # Eski Model: Sadece mum kapandığında kontrol et
                if is_long and c <= cur_sl:
                    exit_price = c
                    exit_type = "CANDLE_CLOSE_SL"
                    break
                elif not is_long and c >= cur_sl:
                    exit_price = c
                    exit_type = "CANDLE_CLOSE_SL"
                    break

            # Eğer canlı botun gerçek çıkış zamanına geldiysek ve OBI Reversal ile çıktıysa
            if k_ts >= actual_exit_ts:
                exit_price = t['exit_price']
                exit_type = "OBI_REVERSAL_EXIT"
                break

        if exit_price is None:
            exit_price = t['exit_price']
            exit_type = "ACTUAL_EXIT"

        pnl = ((exit_price - entry_p) / entry_p * 100) if is_long else ((entry_p - exit_price) / entry_p * 100)
        return pnl, exit_type

    # Karşılaştırılacak Adım Adım Versiyonlar
    version_configs = [
        {
            'name': '1. V5.3 Mevcut Canlı Bot (Baseline)',
            'desc': 'Veritabanındaki gerçekleşen ham canlı sonuçlar',
            'is_actual': True
        },
        {
            'name': '2. + Anlık Tick Trailing Stop',
            'desc': '1m mum kapanışı beklemeden kâr zirvesinden %0.30 çekilmede anında çıkış',
            'sl_mode': 'tick', 'sl_buffer': 0.0020, 'be_trigger': 0.0045, 'trail_start': 0.0060, 'trail_callback': 0.0030
        },
        {
            'name': '3. + Sıkı Hard Stop Cap (%0.70)',
            'desc': 'Uçurum zararları (-%1.5) önleyen %0.70 acil tavan',
            'sl_mode': 'tick', 'sl_buffer': 0.0020, 'be_trigger': 0.0045, 'trail_start': 0.0060, 'trail_callback': 0.0030,
            'hard_sl_cap': 0.0070
        },
        {
            'name': '4. + Aşırı FVG Filtresi (Cap %1.20)',
            'desc': 'SIREN (%11.7) ve WAL (%1.38) gibi manipülatif derin FVG coinleri eler',
            'sl_mode': 'tick', 'sl_buffer': 0.0020, 'be_trigger': 0.0045, 'trail_start': 0.0060, 'trail_callback': 0.0030,
            'hard_sl_cap': 0.0070, 'max_fvg_depth': 1.20
        },
        {
            'name': '5. V5.4 PROD (Tüm 4 İyileştirme + Katı BTC Filtresi)',
            'desc': 'Tick Trailing + %0.70 Cap + FVG %1.20 Cap + Ayıda Zayıf LONG Filtresi',
            'sl_mode': 'tick', 'sl_buffer': 0.0020, 'be_trigger': 0.0045, 'trail_start': 0.0060, 'trail_callback': 0.0030,
            'hard_sl_cap': 0.0070, 'max_fvg_depth': 1.20, 'filter_neutral_long': True
        }
    ]

    summary_rows = []
    v_prod = version_configs[-1]
    trade_comp_list = []

    for v in version_configs:
        pnls = []
        filtered_cnt = 0
        for t in trades:
            if v.get('is_actual'):
                pnl = t['actual_pnl']
            else:
                pnl, st = simulate_trade(t, v)
                if pnl is None:
                    filtered_cnt += 1
                    continue
            pnls.append(pnl)

        s = pd.Series(pnls)
        wins = s[s > 0.02]
        losses = s[s <= 0.02]
        tot = s.sum()
        wr = (len(wins) / len(s) * 100) if len(s) > 0 else 0
        gross_w = wins.sum()
        gross_l = abs(losses.sum())
        pf = (gross_w / gross_l) if gross_l > 0 else 999.0
        avg_w = wins.mean() if len(wins) > 0 else 0
        avg_l = losses.mean() if len(losses) > 0 else 0

        cum = s.cumsum()
        peak = cum.cummax()
        dd = peak - cum
        max_dd = dd.max() if not dd.empty else 0

        summary_rows.append({
            'Versiyon': v['name'],
            'İşlem': f"{len(s)} ({filtered_cnt} filtre)" if filtered_cnt > 0 else f"{len(s)}",
            'Win Rate': f"%{wr:.1f}",
            'W / L': f"{len(wins)}W / {len(losses)}L",
            'Toplam PnL': f"%{tot:+.2f}",
            'Profit Factor': f"{pf:.2f}",
            'Ort. Kazanç': f"%{avg_w:+.2f}",
            'Ort. Kayıp': f"%{avg_l:+.2f}",
            'Max Drawdown': f"%{max_dd:.2f}"
        })

    sum_df = pd.DataFrame(summary_rows)
    print("\n" + "="*115)
    print("                       SMC V5.3 vs V5.4 PROD KARŞILAŞTIRMA MATRİSİ")
    print("="*115)
    print(sum_df.to_string(index=False))

    # İşlem bazlı karşılaştırma tablosu
    for t in trades:
        pnl_prod, st_prod = simulate_trade(t, v_prod)
        trade_comp_list.append({
            'Symbol': t['symbol'],
            'Direction': t['direction'],
            'Entry_Time': t['entry_time'].strftime('%m-%d %H:%M'),
            'FVG_Depth': round(t['fvg_depth'], 2),
            'BTC_Regime': t['btc_regime'],
            'V5_3_Actual_PnL': f"{t['actual_pnl']:+.2f}%",
            'V5_4_Prod_PnL': f"{pnl_prod:+.2f}%" if pnl_prod is not None else "FİLTRELENDİ",
            'PnL_Farkı': f"{(pnl_prod - t['actual_pnl']):+.2f}%" if pnl_prod is not None else f"{-t['actual_pnl']:+.2f}% (Kurtarıldı)",
            'V5_4_Çıkış_Aksiyonu': st_prod
        })

    comp_df = pd.DataFrame(trade_comp_list)
    comp_df.to_csv('data/v5_3_vs_v5_4_trade_comparison.csv', index=False)
    print("\n[+] İşlem bazlı detaylı karşılaştırma tablosu 'data/v5_3_vs_v5_4_trade_comparison.csv' dosyasına yazıldı.")

if __name__ == '__main__':
    main()
