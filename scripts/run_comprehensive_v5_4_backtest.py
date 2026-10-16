import os
import sys
import time
import datetime
import requests
import pandas as pd
import numpy as np

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.database import get_supabase_conn
from features.smc_features import SMCAnalyzer

def fetch_all_klines(symbol, interval, start_ms, end_ms):
    """Binance Futures üzerinden belirtilen aralıktaki tüm mumları çeker."""
    all_k = []
    cur_start = start_ms
    while cur_start < end_ms:
        url = f"https://fapi.binance.com/fapi/v1/klines?symbol={symbol}&interval={interval}&startTime={cur_start}&endTime={end_ms}&limit=1000"
        try:
            r = requests.get(url, timeout=10).json()
            if not isinstance(r, list) or len(r) == 0:
                break
            all_k.extend(r)
            last_ts = r[-1][0]
            if last_ts <= cur_start:
                break
            cur_start = last_ts + 1
            time.sleep(0.04)
        except Exception:
            time.sleep(0.5)
            break
    return all_k

def calculate_ema(series, period):
    return series.ewm(span=period, adjust=False).mean()

def main():
    print("=== V5.4 KAPSAMLI GEÇMİŞ BACKTEST (2-16 EKİM 2026 - 30 SEMBOL) ===")
    
    start_dt = datetime.datetime(2026, 10, 2, 0, 0, 0, tzinfo=datetime.timezone.utc)
    end_dt = datetime.datetime(2026, 10, 16, 18, 0, 0, tzinfo=datetime.timezone.utc)
    start_ms = int(start_dt.timestamp() * 1000)
    end_ms = int(end_dt.timestamp() * 1000)
    
    print(f"Tarih Aralığı: {start_dt.strftime('%d.%m.%Y')} -> {end_dt.strftime('%d.%m.%Y')}")
    
    # 1. Bitcoin 1H ve 4H Trend Rejimi
    print("\n1. Bitcoin 1H ve 4H makro mumları çekiliyor...")
    btc_1h_raw = fetch_all_klines('BTCUSDT', '1h', start_ms - 100 * 3600 * 1000, end_ms)
    btc_4h_raw = fetch_all_klines('BTCUSDT', '4h', start_ms - 200 * 3600 * 1000, end_ms)
    
    df_btc_1h = pd.DataFrame(btc_1h_raw, columns=['ot', 'o', 'h', 'l', 'c', 'v', 'ct', 'qv', 'n', 'tb', 'tq', 'i'])
    df_btc_1h['c'] = df_btc_1h['c'].astype(float)
    df_btc_1h['ema50'] = calculate_ema(df_btc_1h['c'], 50)
    df_btc_1h['ot'] = df_btc_1h['ot'].astype(int)
    
    df_btc_4h = pd.DataFrame(btc_4h_raw, columns=['ot', 'o', 'h', 'l', 'c', 'v', 'ct', 'qv', 'n', 'tb', 'tq', 'i'])
    df_btc_4h['c'] = df_btc_4h['c'].astype(float)
    df_btc_4h['ema50'] = calculate_ema(df_btc_4h['c'], 50)
    df_btc_4h['ot'] = df_btc_4h['ot'].astype(int)
    
    def get_btc_regime(ts_ms):
        sub_1h = df_btc_1h[df_btc_1h['ot'] <= ts_ms]
        sub_4h = df_btc_4h[df_btc_4h['ot'] <= ts_ms]
        if sub_1h.empty or sub_4h.empty:
            return 'NEUTRAL', False
        last_1h = sub_1h.iloc[-1]
        last_4h = sub_4h.iloc[-1]
        
        is_4h_bear = last_4h['c'] < last_4h['ema50']
        dist_1h = (last_1h['c'] - last_1h['ema50']) / last_1h['ema50']
        
        if dist_1h > 0.0030:
            regime = 'BULLISH'
        elif dist_1h < -0.0030:
            regime = 'BEARISH'
        else:
            regime = 'NEUTRAL'
        return regime, is_4h_bear

    # 2. Screener'da en çok KABUL alan lider 30 altcoin
    target_symbols = [
        'ETHUSDT', 'SOLUSDT', 'XRPUSDT', 'DOGEUSDT', 'SUIUSDT', 
        'NEARUSDT', 'AVAXUSDT', 'UNIUSDT', 'LINKUSDT', 'WLDUSDT', 
        '1000PEPEUSDT', 'FILUSDT', 'ENAUSDT', 'BNBUSDT', 'ONDOUSDT',
        'TIAUSDT', 'INJUSDT', 'STRKUSDT', 'FETUSDT', 'APTUSDT', 
        'SEIUSDT', 'OPUSDT', 'RENDERUSDT', 'ARBUSDT', 'AAVEUSDT',
        'LTCUSDT', 'BCHUSDT', 'TAOUSDT', 'QNTUSDT', 'BATUSDT'
    ]
    
    print(f"\n2. {len(target_symbols)} Lider Altcoin İçin 5m Mumlar İndiriliyor...")
    symbol_data = {}
    for sym in target_symbols:
        klines_5m = fetch_all_klines(sym, '5m', start_ms - 50 * 300 * 1000, end_ms)
        if len(klines_5m) > 100:
            df = pd.DataFrame(klines_5m, columns=['ot', 'o', 'h', 'l', 'c', 'v', 'ct', 'qv', 'n', 'tb', 'tq', 'i'])
            for col in ['o', 'h', 'l', 'c', 'v', 'tb']:
                df[col] = df[col].astype(float)
            df['ot'] = df['ot'].astype(int)
            symbol_data[sym] = df
            print(f"  ✓ {sym}: {len(df)} 5m mum")
        time.sleep(0.04)

    # 3. V5.4 Prod Kuralları ile Backtest
    print("\n3. V5.4 Prod SMC Simülasyonu Çalıştırılıyor...")
    all_trades = []

    for sym, df in symbol_data.items():
        smc = SMCAnalyzer(max_candles=50)
        active_trade = None
        
        for i in range(len(df)):
            curr_row = df.iloc[i]
            ts_ms = curr_row['ot']
            curr_price = curr_row['c']
            high_price = curr_row['h']
            low_price = curr_row['l']
            
            # SMC Analyzer'a mum ekle
            smc.add_candle(curr_row['o'], high_price, low_price, curr_price, curr_row['v'])
            
            # Açık işlem varsa çıkış kontrolü
            if active_trade is not None:
                is_long = active_trade['direction'] == 'LONG'
                entry_p = active_trade['entry_price']
                
                # MFE / MAE
                high_pnl = ((high_price - entry_p) / entry_p) * 100 if is_long else ((entry_p - low_price) / entry_p) * 100
                if high_pnl > active_trade['highest_pnl']:
                    active_trade['highest_pnl'] = high_pnl
                
                # Trailing SL Güncellemesi
                if active_trade['highest_pnl'] >= 0.50 and not active_trade['is_breakeven']:
                    active_trade['is_breakeven'] = True
                    active_trade['current_sl'] = entry_p # Başa baş
                elif active_trade['highest_pnl'] >= 0.75:
                    if is_long:
                        trail_p = entry_p * (1.0 + (active_trade['highest_pnl'] - 0.25) / 100)
                        active_trade['current_sl'] = max(active_trade['current_sl'], trail_p)
                    else:
                        trail_p = entry_p * (1.0 - (active_trade['highest_pnl'] - 0.25) / 100)
                        active_trade['current_sl'] = min(active_trade['current_sl'], trail_p)
                
                exit_triggered = False
                exit_price = curr_price
                exit_reason = ''
                
                # 1. Acil Hard Stop (-%0.70 Sıkı Koruma)
                if is_long and low_price <= active_trade['emergency_sl']:
                    exit_triggered = True
                    exit_price = active_trade['emergency_sl']
                    exit_reason = 'HARD_SL_0.70'
                elif (not is_long) and high_price >= active_trade['emergency_sl']:
                    exit_triggered = True
                    exit_price = active_trade['emergency_sl']
                    exit_reason = 'HARD_SL_0.70'
                # 2. Trailing / Yapısal SL
                elif is_long and low_price <= active_trade['current_sl']:
                    exit_triggered = True
                    exit_price = active_trade['current_sl']
                    exit_reason = 'TRAILING_SL' if active_trade['is_breakeven'] else 'STRUCTURAL_SL'
                elif (not is_long) and high_price >= active_trade['current_sl']:
                    exit_triggered = True
                    exit_price = active_trade['current_sl']
                    exit_reason = 'TRAILING_SL' if active_trade['is_breakeven'] else 'STRUCTURAL_SL'
                # 3. Ters Yönlü SMC FVG Formasyonu ile Çıkış
                else:
                    context = smc.get_market_context(curr_price)
                    if is_long and context == 'BEARISH_FVG' and active_trade['highest_pnl'] >= 0.25:
                        exit_triggered = True
                        exit_price = curr_price
                        exit_reason = 'REVERSAL_FVG'
                    elif (not is_long) and context == 'BULLISH_FVG' and active_trade['highest_pnl'] >= 0.25:
                        exit_triggered = True
                        exit_price = curr_price
                        exit_reason = 'REVERSAL_FVG'
                    # 4. Maksimum Süre (18 bar = 1.5 Saat)
                    elif (i - active_trade['entry_index']) >= 18:
                        exit_triggered = True
                        exit_price = curr_price
                        exit_reason = 'TIMEOUT_1.5H'
                
                if exit_triggered:
                    final_diff = (exit_price - entry_p) if is_long else (entry_p - exit_price)
                    final_pnl = (final_diff / entry_p) * 100
                    if final_pnl < -0.70:
                        final_pnl = -0.70
                        exit_price = entry_p * (0.9930 if is_long else 1.0070)
                    
                    active_trade['exit_time'] = datetime.datetime.fromtimestamp(curr_row['ct'] / 1000, tz=datetime.timezone.utc)
                    active_trade['exit_price'] = exit_price
                    active_trade['pnl_pct'] = round(final_pnl, 2)
                    active_trade['win'] = final_pnl > 0
                    active_trade['exit_reason'] = exit_reason
                    all_trades.append(active_trade)
                    active_trade = None
                    continue

            # Açık işlem yoksa ve hedef tarih aralığındaysak Giriş Sinyali Ara
            if active_trade is None and ts_ms >= start_ms:
                context = smc.get_market_context(curr_price)
                b_bound, t_bound = smc.get_active_fvg_bounds(curr_price)
                
                if b_bound and t_bound and b_bound > 0:
                    fvg_depth = ((t_bound - b_bound) / b_bound) * 100
                    
                    # V5.4 Kuralı: %0.15 ile %1.50 arasındaki geçerli FVG'ler
                    if 0.15 <= fvg_depth <= 1.50:
                        btc_reg, is_4h_bear = get_btc_regime(ts_ms)
                        
                        # LONG Koşulları:
                        if context == 'BULLISH_FVG':
                            # V5.4 Kuralı: NEUTRAL iken 4H Ayı ise sıradan LONG engellenir
                            allow_long = False
                            if btc_reg == 'BULLISH':
                                allow_long = True
                            elif btc_reg == 'NEUTRAL' and not is_4h_bear:
                                allow_long = True
                            
                            # Hacim Teyidi
                            taker_buy = curr_row['tb']
                            taker_sell = curr_row['v'] - taker_buy
                            vol_ok = taker_buy > (taker_sell * 1.02)
                            
                            if allow_long and vol_ok:
                                entry_p = curr_price
                                struct_sl = b_bound * 0.9980
                                emerg_sl = entry_p * 0.9930 # %0.70 Hard SL
                                init_sl = max(struct_sl, emerg_sl)
                                
                                active_trade = {
                                    'symbol': sym,
                                    'direction': 'LONG',
                                    'entry_time': datetime.datetime.fromtimestamp(curr_row['ot'] / 1000, tz=datetime.timezone.utc),
                                    'entry_price': entry_p,
                                    'entry_index': i,
                                    'fvg_depth': round(fvg_depth, 2),
                                    'btc_regime': btc_reg,
                                    'initial_sl': init_sl,
                                    'current_sl': init_sl,
                                    'emergency_sl': emerg_sl,
                                    'highest_pnl': 0.0,
                                    'is_breakeven': False,
                                    'entry_reason': f"Bullish FVG (%{fvg_depth:.2f}) | BTC: {btc_reg}"
                                }

                        # SHORT Koşulları:
                        elif context == 'BEARISH_FVG':
                            # V5.4 Kuralı: BTC yükselişte değilse SHORT serbest
                            allow_short = (btc_reg != 'BULLISH')
                            
                            # Hacim Teyidi
                            taker_buy = curr_row['tb']
                            taker_sell = curr_row['v'] - taker_buy
                            vol_ok = taker_sell > (taker_buy * 1.02)
                            
                            if allow_short and vol_ok:
                                entry_p = curr_price
                                struct_sl = t_bound * 1.0020
                                emerg_sl = entry_p * 1.0070 # %0.70 Hard SL
                                init_sl = min(struct_sl, emerg_sl)
                                
                                active_trade = {
                                    'symbol': sym,
                                    'direction': 'SHORT',
                                    'entry_time': datetime.datetime.fromtimestamp(curr_row['ot'] / 1000, tz=datetime.timezone.utc),
                                    'entry_price': entry_p,
                                    'entry_index': i,
                                    'fvg_depth': round(fvg_depth, 2),
                                    'btc_regime': btc_reg,
                                    'initial_sl': init_sl,
                                    'current_sl': init_sl,
                                    'emergency_sl': emerg_sl,
                                    'highest_pnl': 0.0,
                                    'is_breakeven': False,
                                    'entry_reason': f"Bearish FVG (%{fvg_depth:.2f}) | BTC: {btc_reg}"
                                }

    all_trades.sort(key=lambda x: x['entry_time'])
    print(f"\n✓ Backtest Tamamlandı! Toplam {len(all_trades)} işlem gerçekleşti.")
    
    # 4. İstatistikler & Rapor
    if all_trades:
        df_res = pd.DataFrame(all_trades)
        csv_path = 'data/v5_4_comprehensive_backtest.csv'
        df_res.to_csv(csv_path, index=False)
        print(f"✓ Sonuçlar CSV'ye kaydedildi: {csv_path}")
        
        total_trades = len(df_res)
        wins = df_res[df_res['win'] == True]
        losses = df_res[df_res['win'] == False]
        wr = (len(wins) / total_trades) * 100
        total_pnl = df_res['pnl_pct'].sum()
        gross_profit = wins['pnl_pct'].sum() if len(wins) > 0 else 0
        gross_loss = abs(losses['pnl_pct'].sum()) if len(losses) > 0 else 0
        pf = (gross_profit / gross_loss) if gross_loss > 0 else 999.0
        avg_win = wins['pnl_pct'].mean() if len(wins) > 0 else 0
        avg_loss = losses['pnl_pct'].mean() if len(losses) > 0 else 0
        
        longs = df_res[df_res['direction'] == 'LONG']
        shorts = df_res[df_res['direction'] == 'SHORT']
        long_wr = (len(longs[longs['win']]) / len(longs) * 100) if len(longs) > 0 else 0
        short_wr = (len(shorts[shorts['win']]) / len(shorts) * 100) if len(shorts) > 0 else 0
        
        print("\n" + "="*55)
        print(f"📊 V5.4 KAPSAMLI GEÇMİŞ BACKTEST SONUÇLARI (2-16 EKİM)")
        print("="*55)
        print(f"Toplam İşlem Sayısı : {total_trades}")
        print(f"Kazanma Oranı (WR)  : %{wr:.1f} ({len(wins)} Kazanılan / {len(losses)} Kaybedilen)")
        print(f"Net Kümülatif PnL   : +%{total_pnl:.2f}")
        print(f"Profit Factor (PF)  : {pf:.2f}")
        print(f"Ortalama Kazanç     : +%{avg_win:.2f}")
        print(f"Ortalama Kayıp      : -%{abs(avg_loss):.2f}")
        print(f"LONG İşlemler       : {len(longs)} adet | WR: %{long_wr:.1f} | Net: +%{longs['pnl_pct'].sum():.2f}")
        print(f"SHORT İşlemler      : {len(shorts)} adet | WR: %{short_wr:.1f} | Net: +%{shorts['pnl_pct'].sum():.2f}")
        print("="*55)

        # 5. Supabase `quant_v5.backtest_trades` tablosuna yaz
        print("\nSonuçlar Supabase veritabanına (`quant_v5.backtest_trades`) yükleniyor...")
        conn = get_supabase_conn()
        if conn:
            cur = conn.cursor()
            cur.execute("TRUNCATE TABLE quant_v5.backtest_trades;")
            for t in all_trades:
                cur.execute("""
                    INSERT INTO quant_v5.backtest_trades 
                    (sembol, tip, giris_zaman, cikis_zaman, giris_fiyat, cikis_fiyat, pnl_yuzde, win, fvg_depth, btc_regime, cikis_nedeni, entry_reason)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
                """, (
                    t['symbol'], t['direction'], t['entry_time'], t['exit_time'],
                    float(t['entry_price']), float(t['exit_price']), float(t['pnl_pct']),
                    bool(t['win']), float(t['fvg_depth']), str(t['btc_regime']),
                    str(t['exit_reason']), str(t['entry_reason'])
                ))
            conn.commit()
            conn.close()
            print("✓ Tüm işlemler Supabase veritabanına başarıyla yüklendi!")

if __name__ == '__main__':
    main()
