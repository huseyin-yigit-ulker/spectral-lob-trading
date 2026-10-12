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
        print("DB bağlantısı kurulamadı.")
        return
    cur = conn.cursor()
    cur.execute("""
        SELECT id, zaman, sembol, fiyat, sinyal, obi, cvd, context, fvg_top, fvg_bottom, fvg_depth
        FROM quant_v5.trade_logs
        ORDER BY zaman ASC;
    """)
    rows = cur.fetchall()
    conn.close()

    print(f"Toplam {len(rows)} log kaydı okundu.")

    open_pos = {}
    trades = []
    for r in rows:
        _id, zaman, sym, fiyat, sinyal, obi, cvd, ctx, f_top, f_bot, f_depth = r
        fiyat = float(fiyat)
        obi = float(obi or 0)
        f_top = float(f_top or 0)
        f_bot = float(f_bot or 0)
        zaman_utc = parse_utc_dt(zaman)

        is_entry = ('AL' in sinyal or 'SAT' in sinyal) and ('BEKLE' not in sinyal)
        is_exit = 'BEKLE' in sinyal

        if is_entry:
            is_long = ('AL' in sinyal or 'LONG' in sinyal)
            open_pos[sym] = {
                'id': _id, 'entry_time': zaman_utc, 'symbol': sym,
                'direction': 'LONG' if is_long else 'SHORT',
                'entry_price': fiyat, 'entry_obi': obi, 'entry_ctx': ctx,
                'fvg_top': f_top, 'fvg_bot': f_bot, 'fvg_depth': float(f_depth or 0)
            }
        elif is_exit and sym in open_pos:
            p = open_pos[sym]
            p['exit_time'] = zaman_utc
            p['exit_price'] = fiyat
            p['exit_obi'] = obi
            diff = (fiyat - p['entry_price']) if p['direction'] == 'LONG' else (p['entry_price'] - fiyat)
            p['actual_pnl'] = (diff / p['entry_price']) * 100
            p['duration_min'] = (p['exit_time'] - p['entry_time']).total_seconds() / 60
            trades.append(p)
            del open_pos[sym]

    print(f"Toplam {len(trades)} tamamlanmış işlem tespit edildi. 1m klines çekiliyor...")
    
    for i, t in enumerate(trades):
        start_ts = int(t['entry_time'].timestamp() * 1000)
        # En az 180 dk veya işlem süresinden uzun çek
        dur_ms = max(180, int(t['duration_min']) + 60) * 60 * 1000
        end_ts = start_ts + dur_ms
        t['klines'] = fetch_klines(t['symbol'], start_ts, end_ts)

    # Simülasyon Fonksiyonu
    # strat_mode:
    #   'mevcut': OBI 0.15'te çıkış (tarihsel gerçekleşen gerçek PnL)
    #   'strong_obi_030': OBI eşiği 0.30
    #   'strong_obi_035': OBI eşiği 0.35
    #   'fvg_conditional_030': FVG içindeyse 0.30, FVG dışındaysa 0.15
    #   'fvg_conditional_035': FVG içindeyse 0.35, FVG dışındaysa 0.15
    #   'fvg_only_sl_trail': FVG içindeyken OBI çıkışı yok (sadece SL + Trailing)

    def simulate(strat_mode, sl_buf=0.0020, be_trigger=0.0030, trail_trigger=0.0035, trail_cb=0.0020, tp_target=None):
        results = []
        for t in trades:
            klines = t.get('klines', [])
            if not klines:
                results.append({'symbol': t['symbol'], 'pnl': t['actual_pnl'], 'reason': 'NO_KLINES'})
                continue

            entry_p = t['entry_price']
            is_long = (t['direction'] == 'LONG')
            fvg_top = t['fvg_top']
            fvg_bot = t['fvg_bot']

            # Eğer mevcut bot ise doğrudan gerçekleşen actual_pnl
            if strat_mode == 'mevcut':
                results.append({
                    'symbol': t['symbol'],
                    'direction': t['direction'],
                    'entry_time': t['entry_time'],
                    'pnl': t['actual_pnl'],
                    'reason': 'CANLI_GERCEKLESEN'
                })
                continue

            # SL Başlangıç Seviyesi
            ref_bound = (fvg_bot if fvg_bot > 0 else entry_p * 0.9980) if is_long else (fvg_top if fvg_top > 0 else entry_p * 1.0020)
            active_sl = ref_bound * (1.0 - sl_buf) if is_long else ref_bound * (1.0 + sl_buf)
            emergency_sl = entry_p * 0.9900 if is_long else entry_p * 1.0100

            highest_pnl = 0.0
            is_break_even = False
            exit_p = None
            exit_reason = None

            # Gerçekleşen işlem OBI reversal ile mi çıkmıştı?
            # Eğer gerçekleşen çıkış OBI yüzünden olduysa (exit_obi > 0.15 Short için, < -0.15 Long için):
            # OBI seviyesi exit_obi_abs
            exit_obi_abs = abs(t['exit_obi'])
            was_obi_exit = (exit_obi_abs >= 0.15) and (
                (not is_long and t['exit_obi'] > 0.15) or (is_long and t['exit_obi'] < -0.15)
            )

            # Eşik belirleme
            if strat_mode == 'strong_obi_030':
                obi_threshold = 0.30
            elif strat_mode == 'strong_obi_035':
                obi_threshold = 0.35
            elif strat_mode == 'fvg_conditional_030':
                obi_threshold = 0.30
            elif strat_mode == 'fvg_conditional_035':
                obi_threshold = 0.35
            elif strat_mode == 'fvg_only_sl_trail':
                obi_threshold = 999.0 # FVG varken OBI çıkışı yok
            else:
                obi_threshold = 0.15

            # Mum simülasyonu
            actual_exit_ts = int(t['exit_time'].timestamp() * 1000)

            for k in klines:
                k_open_ts = k[0]
                o, h, l, c = float(k[1]), float(k[2]), float(k[3]), float(k[4])

                # Anlık PnL takibi
                cur_high_gain = (h - entry_p) / entry_p * 100 if is_long else (entry_p - l) / entry_p * 100
                if cur_high_gain > highest_pnl:
                    highest_pnl = cur_high_gain

                # 1. Acil Hard Stop Tick
                if is_long and l <= emergency_sl:
                    exit_p = emergency_sl
                    exit_reason = 'ACIL_HARD_STOP'
                    break
                elif not is_long and h >= emergency_sl:
                    exit_p = emergency_sl
                    exit_reason = 'ACIL_HARD_STOP'
                    break

                # 2. Break-Even Güncellemesi (@ %0.30)
                if highest_pnl >= (be_trigger * 100) and not is_break_even:
                    is_break_even = True
                    if is_long:
                        active_sl = max(active_sl, entry_p * 1.0005)
                    else:
                        active_sl = min(active_sl, entry_p * 0.9995)

                # 3. Trailing Stop (@ %0.35+ kâr, %0.20 callback)
                if highest_pnl >= (trail_trigger * 100):
                    if is_long:
                        trail_p = entry_p * (1.0 + (highest_pnl - trail_cb * 100) / 100)
                        active_sl = max(active_sl, trail_p)
                    else:
                        trail_p = entry_p * (1.0 - (highest_pnl - trail_cb * 100) / 100)
                        active_sl = min(active_sl, trail_p)

                # 3.5. Take Profit (TP) Hedefi Kontrolü
                if tp_target:
                    if is_long and h >= entry_p * (1.0 + tp_target):
                        exit_p = entry_p * (1.0 + tp_target)
                        exit_reason = f'TP_HEDEF (%{tp_target*100:.2f})'
                        break
                    elif not is_long and l <= entry_p * (1.0 - tp_target):
                        exit_p = entry_p * (1.0 - tp_target)
                        exit_reason = f'TP_HEDEF (%{tp_target*100:.2f})'
                        break

                # 4. Mum Kapanışı SL Kontrolü
                if is_long and c <= active_sl:
                    exit_p = c
                    exit_reason = 'TRAILING_VEYA_SL' if is_break_even else 'FVG_MUM_SL'
                    break
                elif not is_long and c >= active_sl:
                    exit_p = c
                    exit_reason = 'TRAILING_VEYA_SL' if is_break_even else 'FVG_MUM_SL'
                    break

                # 5. OBI Reversal Kontrolü (Orijinal botun çıktığı dakika geldiysek):
                if was_obi_exit and abs(k_open_ts - actual_exit_ts) <= 60000:
                    # Eğer OBI eşiğimiz exit_obi'den küçükse (yani 0.15 eşiğindeyse) çıkardı
                    if exit_obi_abs >= obi_threshold:
                        exit_p = t['exit_price']
                        exit_reason = f'KUVVETLI_OBI_CIKIS ({exit_obi_abs:.2f}>={obi_threshold})'
                        break
                    else:
                        # OBI yeterince kuvvetli DEĞİL! Pozisyonda kalmaya devam et!
                        pass

            if exit_p is None:
                # Klines bitti veya işlem devam etti
                exit_p = float(klines[-1][4])
                exit_reason = 'ZAMAN_SONU'

            pnl = ((exit_p - entry_p) / entry_p * 100) if is_long else ((entry_p - exit_p) / entry_p * 100)
            results.append({
                'symbol': t['symbol'],
                'direction': t['direction'],
                'entry_time': t['entry_time'],
                'pnl': pnl,
                'exit_reason': exit_reason
            })

        return pd.DataFrame(results)

    # Test Stratejileri
    df_1_mevcut = simulate('mevcut')
    df_2_obi_030 = simulate('strong_obi_030')
    df_3_obi_035 = simulate('strong_obi_035')
    df_4_fvg_obi_035 = simulate('fvg_conditional_035')
    df_5_fvg_only_trail = simulate('fvg_only_sl_trail')
    df_6_fvg_tp060 = simulate('fvg_conditional_035', tp_target=0.0060)
    df_7_fvg_tp080 = simulate('fvg_conditional_035', tp_target=0.0080)
    df_8_fvg_tp100 = simulate('fvg_conditional_035', tp_target=0.0100)

    strats = {
        '1. Mevcut Canlı Bot (Zayıf OBI 0.15 Çıkışı)': df_1_mevcut,
        '2. Kuvvetli OBI (Sabit ±0.30 Çıkış)': df_2_obi_030,
        '3. Kuvvetli OBI (Sabit ±0.35 Çıkış)': df_3_obi_035,
        '4. FVG Varken Kuvvetli OBI (±0.35), Yoksa 0.15': df_4_fvg_obi_035,
        '5. FVG Varken OBI Çıkışı Yok (Sadece SL+Trail)': df_5_fvg_only_trail,
        '6. FVG Kuvvetli OBI + TP %0.60': df_6_fvg_tp060,
        '7. FVG Kuvvetli OBI + TP %0.80': df_7_fvg_tp080,
        '8. FVG Kuvvetli OBI + TP %1.00': df_8_fvg_tp100,
    }

    summary = []
    for name, df in strats.items():
        wins = df[df['pnl'] > 0.05]
        losses = df[df['pnl'] <= 0.05]
        wr = len(wins) / len(df) * 100 if len(df) > 0 else 0
        tot_pnl = df['pnl'].sum()
        avg_win = wins['pnl'].mean() if len(wins) > 0 else 0
        avg_loss = losses['pnl'].mean() if len(losses) > 0 else 0
        pf = (wins['pnl'].sum() / abs(losses['pnl'].sum())) if abs(losses['pnl'].sum()) > 0 else 999.0

        summary.append({
            'Strateji': name,
            'Kazanma Oranı (WinRate)': f"%{wr:.1f}",
            'W / L': f"{len(wins)} / {len(losses)}",
            'Toplam Kümülatif Getiri': f"%{tot_pnl:+.2f}",
            'Ortalama İşlem PnL': f"%{df['pnl'].mean():+.3f}",
            'Ort. Kazanç / Kayıp': f"+%{avg_win:.2f} / %{avg_loss:.2f}",
            'Profit Factor': f"{pf:.2f}"
        })

    print("\n" + "="*120)
    print("                     OBI ÇIKIŞ OPTİMİZASYONU BACKTEST SONUÇLARI (74 İŞLEM)")
    print("="*120)
    print(pd.DataFrame(summary).to_string(index=False))

    # TAOUSDT ve Benzeri Belirgin İşlemlerin Karşılaştırması
    print("\n" + "="*120)
    print("ÖRNEK İŞLEMLERDEKİ GETİRİ DEĞİŞİMİ:")
    print("="*120)
    comp = pd.DataFrame({
        'Sembol': df_1_mevcut['symbol'],
        'Zaman': df_1_mevcut['entry_time'].dt.strftime('%m-%d %H:%M'),
        'Yön': df_1_mevcut['direction'],
        'Mevcut (0.15)': df_1_mevcut['pnl'].apply(lambda x: f"%{x:+.2f}"),
        'Kuvvetli OBI (0.35)': df_4_fvg_obi_035['pnl'].apply(lambda x: f"%{x:+.2f}"),
        'FVG SL + Trailing': df_5_fvg_only_trail['pnl'].apply(lambda x: f"%{x:+.2f}"),
        'Çıkış Nedeni': df_4_fvg_obi_035['exit_reason']
    })
    
    crit_syms = ['TAOUSDT', 'MAGICUSDT', 'APTUSDT', 'ENAUSDT', 'ASTERUSDT', 'WLDUSDT', 'FILUSDT', 'LITUSDT']
    print(comp[comp['Sembol'].isin(crit_syms)].drop_duplicates(subset=['Sembol', 'Zaman']).head(15).to_string(index=False))

if __name__ == '__main__':
    main()
