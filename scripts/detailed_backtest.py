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

    print(f"Toplam {len(trades)} islem verisi yuklendi. Mumlar cekiliyor...")

    for t in trades:
        start_ts = int(t['entry_time'].timestamp() * 1000)
        end_ts = start_ts + 120 * 60 * 1000
        t['klines'] = fetch_klines(t['symbol'], start_ts, end_ts)

    # 3 Stratejiyi karsilastir:
    # 1. MEVCUT BOT: 0.05% Tick SL, No TP, No BE
    # 2. SADECE MUM KAPANISI + GENIS SL (%0.20): No TP, No BE (Sadece kullanicinin sordugu)
    # 3. MUM KAPANISI (%0.20) + BE@0.35% + TP/TRAILING: Kapsamli Strateji
    # 4. MUM KAPANISI (%0.20) + SABIT TP (%0.60): Basit TP'li Strateji

    def run_backtest(strat_type, sl_buf=0.0020, be_trigger=0.0035, tp_target=0.0060, trail=0.0020):
        trade_results = []
        for t in trades:
            klines = t['klines']
            if not klines:
                continue

            entry_p = t['entry_price']
            is_long = t['direction'] == 'LONG'
            fvg_top = t['fvg_top']
            fvg_bot = t['fvg_bottom']

            if strat_type == 'mevcut':
                # Mevcut bot pnl'i doğrudan veritabanındaki pnl
                trade_results.append({
                    'symbol': t['symbol'],
                    'direction': t['direction'],
                    'entry_time': t['entry_time'],
                    'pnl': t['actual_pnl'],
                    'exit_reason': 'Mevcut Cikis'
                })
                continue

            ref_bound = (fvg_bot if fvg_bot > 0 else entry_p * 0.998) if is_long else (fvg_top if fvg_top > 0 else entry_p * 1.002)
            cur_sl = ref_bound * (1.0 - sl_buf) if is_long else ref_bound * (1.0 + sl_buf)
            emergency_sl = entry_p * 0.990 if is_long else entry_p * 1.010

            exit_p = None
            exit_reason = None
            max_fav = 0.0

            for k in klines:
                o, h, l, close_p = float(k[1]), float(k[2]), float(k[3]), float(k[4])

                fav = (h - entry_p) / entry_p if is_long else (entry_p - l) / entry_p
                if fav > max_fav: max_fav = fav

                # Acil Hard Stop (1.0% tick)
                if is_long and l <= emergency_sl:
                    exit_p = emergency_sl
                    exit_reason = 'ACIL_STOP'
                    break
                elif not is_long and h >= emergency_sl:
                    exit_p = emergency_sl
                    exit_reason = 'ACIL_STOP'
                    break

                # BE / Trailing / TP
                if 'be' in strat_type and be_trigger and max_fav >= be_trigger:
                    if is_long:
                        cur_sl = max(cur_sl, entry_p * 1.0005)
                    else:
                        cur_sl = min(cur_sl, entry_p * 0.9995)

                if 'trail' in strat_type and trail and max_fav >= be_trigger:
                    if is_long:
                        cur_sl = max(cur_sl, entry_p * (1.0 + max_fav - trail))
                    else:
                        cur_sl = min(cur_sl, entry_p * (1.0 - max_fav + trail))

                if 'tp' in strat_type and tp_target:
                    if is_long and h >= entry_p * (1.0 + tp_target):
                        exit_p = entry_p * (1.0 + tp_target)
                        exit_reason = 'TP_HEDEF'
                        break
                    elif not is_long and l <= entry_p * (1.0 - tp_target):
                        exit_p = entry_p * (1.0 - tp_target)
                        exit_reason = 'TP_HEDEF'
                        break

                # Mum kapanisi ile SL kontrolu
                if is_long and close_p <= cur_sl:
                    exit_p = close_p
                    exit_reason = 'MUM_KAPANIS_SL' if cur_sl < entry_p else 'BASABAS_CIKIS'
                    break
                elif not is_long and close_p >= cur_sl:
                    exit_p = close_p
                    exit_reason = 'MUM_KAPANIS_SL' if cur_sl > entry_p else 'BASABAS_CIKIS'
                    break

            if exit_p is None:
                exit_p = float(klines[-1][4])
                exit_reason = 'ZAMAN_DOLDU'

            pnl = ((exit_p - entry_p) / entry_p * 100) if is_long else ((entry_p - exit_p) / entry_p * 100)
            trade_results.append({
                'symbol': t['symbol'],
                'direction': t['direction'],
                'entry_time': t['entry_time'],
                'pnl': pnl,
                'exit_reason': exit_reason
            })

        return pd.DataFrame(trade_results)

    df_mevcut = run_backtest('mevcut')
    df_sadece_kapanis = run_backtest('sadece_kapanis', sl_buf=0.0020)
    df_kapanis_tp = run_backtest('be_tp', sl_buf=0.0020, be_trigger=0.0035, tp_target=0.0065)
    df_kapanis_trail = run_backtest('be_trail', sl_buf=0.0020, be_trigger=0.0035, trail=0.0020)

    strategies = {
        '1. Mevcut Canlı Bot (0.05% Tick, No TP)': df_mevcut,
        '2. Sadece %0.20 SL + Mum Kapanışı (No TP)': df_sadece_kapanis,
        '3. %0.20 SL Kapanış + BE@0.35% + TP@0.65%': df_kapanis_tp,
        '4. %0.20 SL Kapanış + BE@0.35% + Trailing %0.20': df_kapanis_trail,
    }

    summary = []
    for name, df in strategies.items():
        wins = df[df['pnl'] > 0.05]
        losses = df[df['pnl'] <= 0.05]
        wr = len(wins) / len(df) * 100
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
            'Ort. Kazanç / Ort. Kayıp': f"+%{avg_win:.2f} / %{avg_loss:.2f}",
            'Profit Factor': f"{pf:.2f}"
        })

    print("\n" + "="*110)
    print("                     BACKTEST PERFORMANS KARŞILAŞTIRMASI (59 İŞLEM)")
    print("="*110)
    print(pd.DataFrame(summary).to_string(index=False))

    # Örnek Bazı Belirgin İşlemlerin Değişimi
    print("\n" + "="*110)
    print("BELİRGİN İŞLEMLERDEKİ GETİRİ DEĞİŞİMİ ÖRNEKLERİ:")
    print("="*110)
    comp_df = pd.DataFrame({
        'Sembol': df_mevcut['symbol'],
        'Zaman': df_mevcut['entry_time'].dt.strftime('%m-%d %H:%M'),
        'Yön': df_mevcut['direction'],
        'Mevcut Bot PnL': df_mevcut['pnl'].apply(lambda x: f"%{x:+.2f}"),
        'Sadece Kapanış (%0.20 SL)': df_sadece_kapanis['pnl'].apply(lambda x: f"%{x:+.2f}"),
        'Kapanış + BE + TP (%0.65)': df_kapanis_tp['pnl'].apply(lambda x: f"%{x:+.2f}"),
        'Kapanış + BE + Trailing': df_kapanis_trail['pnl'].apply(lambda x: f"%{x:+.2f}")
    })
    
    # MAGIC, APT, LIT, ENA, ASTER gibi kritik islemleri sec
    sample_symbols = ['MAGICUSDT', 'APTUSDT', 'ENAUSDT', 'LITUSDT', 'ASTERUSDT', 'WLDUSDT', 'FILUSDT', 'RENDERUSDT']
    filtered = comp_df[comp_df['Sembol'].isin(sample_symbols)].drop_duplicates(subset=['Sembol', 'Zaman'])
    print(filtered.head(15).to_string(index=False))

if __name__ == '__main__':
    main()
