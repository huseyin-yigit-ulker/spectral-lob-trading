import os
import sys
import time
import datetime
import requests
import pandas as pd
import numpy as np

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from features.smc_features import SMCAnalyzer

def fetch_all_klines(symbol, interval, start_ms, end_ms):
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

def calculate_adx(df, period=14):
    high = df['h']
    low = df['l']
    close = df['c']
    
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1/period, adjust=False).mean()
    
    up_move = high - high.shift(1)
    down_move = low.shift(1) - low
    
    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)
    
    plus_di = 100 * (pd.Series(plus_dm).ewm(alpha=1/period, adjust=False).mean() / (atr + 1e-9))
    minus_di = 100 * (pd.Series(minus_dm).ewm(alpha=1/period, adjust=False).mean() / (atr + 1e-9))
    
    dx = 100 * ((plus_di - minus_di).abs() / (plus_di + minus_di + 1e-9))
    adx = dx.ewm(alpha=1/period, adjust=False).mean()
    return adx

def main():
    print("=== V5.5 GELİŞTİRME VE OPTİMİZASYON SİMÜLASYONU (2-16 EKİM 2026) ===")
    
    start_dt = datetime.datetime(2026, 10, 2, 0, 0, 0, tzinfo=datetime.timezone.utc)
    end_dt = datetime.datetime(2026, 10, 16, 18, 0, 0, tzinfo=datetime.timezone.utc)
    start_ms = int(start_dt.timestamp() * 1000)
    end_ms = int(end_dt.timestamp() * 1000)
    
    # 1. Bitcoin 1H ve 4H Mumları
    print("1. BTC verileri çekiliyor...")
    btc_1h_raw = fetch_all_klines('BTCUSDT', '1h', start_ms - 100 * 3600 * 1000, end_ms)
    btc_4h_raw = fetch_all_klines('BTCUSDT', '4h', start_ms - 200 * 3600 * 1000, end_ms)
    
    df_btc_1h = pd.DataFrame(btc_1h_raw, columns=['ot', 'o', 'h', 'l', 'c', 'v', 'ct', 'qv', 'n', 'tb', 'tq', 'i'])
    for col in ['o', 'h', 'l', 'c', 'v']: df_btc_1h[col] = df_btc_1h[col].astype(float)
    df_btc_1h['ema50'] = calculate_ema(df_btc_1h['c'], 50)
    df_btc_1h['adx'] = calculate_adx(df_btc_1h, 14)
    df_btc_1h['ot'] = df_btc_1h['ot'].astype(int)
    
    df_btc_4h = pd.DataFrame(btc_4h_raw, columns=['ot', 'o', 'h', 'l', 'c', 'v', 'ct', 'qv', 'n', 'tb', 'tq', 'i'])
    for col in ['o', 'h', 'l', 'c', 'v']: df_btc_4h[col] = df_btc_4h[col].astype(float)
    df_btc_4h['ema50'] = calculate_ema(df_btc_4h['c'], 50)
    df_btc_4h['ot'] = df_btc_4h['ot'].astype(int)
    
    def get_btc_info(ts_ms):
        sub_1h = df_btc_1h[df_btc_1h['ot'] <= ts_ms]
        sub_4h = df_btc_4h[df_btc_4h['ot'] <= ts_ms]
        if sub_1h.empty or sub_4h.empty:
            return 'NEUTRAL', False, 25.0
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
        adx_val = float(last_1h['adx'])
        return regime, is_4h_bear, adx_val

    # 2. 30 Lider Altcoin
    target_symbols = [
        'ETHUSDT', 'SOLUSDT', 'XRPUSDT', 'DOGEUSDT', 'SUIUSDT', 
        'NEARUSDT', 'AVAXUSDT', 'UNIUSDT', 'LINKUSDT', 'WLDUSDT', 
        '1000PEPEUSDT', 'FILUSDT', 'ENAUSDT', 'BNBUSDT', 'ONDOUSDT',
        'TIAUSDT', 'INJUSDT', 'STRKUSDT', 'FETUSDT', 'APTUSDT', 
        'SEIUSDT', 'OPUSDT', 'RENDERUSDT', 'ARBUSDT', 'AAVEUSDT',
        'LTCUSDT', 'BCHUSDT', 'TAOUSDT', 'QNTUSDT', 'BATUSDT'
    ]
    
    print(f"2. {len(target_symbols)} Altcoin İçin 5m Mumlar İndiriliyor...")
    symbol_data = {}
    for sym in target_symbols:
        klines_5m = fetch_all_klines(sym, '5m', start_ms - 50 * 300 * 1000, end_ms)
        if len(klines_5m) > 100:
            df = pd.DataFrame(klines_5m, columns=['ot', 'o', 'h', 'l', 'c', 'v', 'ct', 'qv', 'n', 'tb', 'tq', 'i'])
            for col in ['o', 'h', 'l', 'c', 'v', 'tb']: df[col] = df[col].astype(float)
            df['ot'] = df['ot'].astype(int)
            df['adx'] = calculate_adx(df, 14)
            symbol_data[sym] = df
        time.sleep(0.04)

    # Simülasyon Fonksiyonu
    def run_simulation(config_name, use_strict_trend=False, use_partial_tp=False, min_adx=0.0):
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
                
                smc.add_candle(curr_row['o'], high_price, low_price, curr_price, curr_row['v'])
                
                # Açık işlem yönetimi
                if active_trade is not None:
                    is_long = active_trade['direction'] == 'LONG'
                    entry_p = active_trade['entry_price']
                    
                    high_pnl = ((high_price - entry_p) / entry_p) * 100 if is_long else ((entry_p - low_price) / entry_p) * 100
                    if high_pnl > active_trade['highest_pnl']:
                        active_trade['highest_pnl'] = high_pnl
                    
                    # Kısmi Kâr Alma (Partial TP) Tetikleyicisi (+%0.50'de pozisyonun %50'sini kârla kapat)
                    if use_partial_tp and active_trade['highest_pnl'] >= 0.50 and not active_trade['partial_tp_taken']:
                        active_trade['partial_tp_taken'] = True
                        active_trade['partial_tp_pnl'] = 0.50 # %0.50 kâr kilitlendi
                    
                    # Trailing SL
                    if active_trade['highest_pnl'] >= 0.50 and not active_trade['is_breakeven']:
                        active_trade['is_breakeven'] = True
                        active_trade['current_sl'] = entry_p
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
                    
                    # 1. Hard SL (-%0.70)
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
                    # 3. Ters Yönlü SMC FVG Formasyonu
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
                        elif (i - active_trade['entry_index']) >= 18: # 1.5 saat
                            exit_triggered = True
                            exit_price = curr_price
                            exit_reason = 'TIMEOUT_1.5H'
                    
                    if exit_triggered:
                        final_diff = (exit_price - entry_p) if is_long else (entry_p - exit_price)
                        runner_pnl = (final_diff / entry_p) * 100
                        if runner_pnl < -0.70:
                            runner_pnl = -0.70
                            exit_price = entry_p * (0.9930 if is_long else 1.0070)
                        
                        # Eğer Partial TP alındıysa: %50 TP (%0.50) + %50 Kalan
                        if use_partial_tp and active_trade['partial_tp_taken']:
                            combined_pnl = 0.50 * 0.50 + 0.50 * runner_pnl
                        else:
                            combined_pnl = runner_pnl
                        
                        active_trade['exit_time'] = datetime.datetime.fromtimestamp(curr_row['ct'] / 1000, tz=datetime.timezone.utc)
                        active_trade['exit_price'] = exit_price
                        active_trade['pnl_pct'] = round(combined_pnl, 2)
                        active_trade['win'] = combined_pnl > 0
                        active_trade['exit_reason'] = exit_reason
                        all_trades.append(active_trade)
                        active_trade = None
                        continue

                # Giriş Sinyali Ara
                if active_trade is None and ts_ms >= start_ms:
                    context = smc.get_market_context(curr_price)
                    b_bound, t_bound = smc.get_active_fvg_bounds(curr_price)
                    
                    if b_bound and t_bound and b_bound > 0:
                        fvg_depth = ((t_bound - b_bound) / b_bound) * 100
                        
                        if 0.15 <= fvg_depth <= 1.50:
                            btc_reg, is_4h_bear, btc_adx = get_btc_info(ts_ms)
                            coin_adx = float(curr_row['adx'])
                            
                            # Testere Filtresi: ADX eşiği (Chop Kalkanı)
                            if min_adx > 0:
                                if btc_adx < min_adx and coin_adx < min_adx:
                                    continue # Testere/yatay piyasada işlem açma
                            
                            if context == 'BULLISH_FVG':
                                allow_long = False
                                if use_strict_trend:
                                    # Katı Trend: 4H Ayı iken LONG kesinlikle açılmaz!
                                    if btc_reg == 'BULLISH' and not is_4h_bear:
                                        allow_long = True
                                else:
                                    if btc_reg == 'BULLISH':
                                        allow_long = True
                                    elif btc_reg == 'NEUTRAL' and not is_4h_bear:
                                        allow_long = True
                                
                                taker_buy = curr_row['tb']
                                taker_sell = curr_row['v'] - taker_buy
                                vol_ok = taker_buy > (taker_sell * 1.02)
                                
                                if allow_long and vol_ok:
                                    entry_p = curr_price
                                    struct_sl = b_bound * 0.9980
                                    emerg_sl = entry_p * 0.9930
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
                                        'partial_tp_taken': False,
                                        'partial_tp_pnl': 0.0,
                                        'entry_reason': f"Bullish FVG (%{fvg_depth:.2f}) | BTC: {btc_reg}"
                                    }

                            elif context == 'BEARISH_FVG':
                                allow_short = (btc_reg != 'BULLISH')
                                taker_buy = curr_row['tb']
                                taker_sell = curr_row['v'] - taker_buy
                                vol_ok = taker_sell > (taker_buy * 1.02)
                                
                                if allow_short and vol_ok:
                                    entry_p = curr_price
                                    struct_sl = t_bound * 1.0020
                                    emerg_sl = entry_p * 1.0070
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
                                        'partial_tp_taken': False,
                                        'partial_tp_pnl': 0.0,
                                        'entry_reason': f"Bearish FVG (%{fvg_depth:.2f}) | BTC: {btc_reg}"
                                    }

        # Metrikler
        if not all_trades:
            return {'name': config_name, 'trades': 0, 'wr': 0, 'pnl': 0, 'pf': 0, 'trades_list': []}
        df_r = pd.DataFrame(all_trades)
        wins = df_r[df_r['win'] == True]
        losses = df_r[df_r['win'] == False]
        wr = (len(wins) / len(df_r)) * 100
        pnl = df_r['pnl_pct'].sum()
        gp = wins['pnl_pct'].sum() if len(wins) > 0 else 0
        gl = abs(losses['pnl_pct'].sum()) if len(losses) > 0 else 0
        pf = (gp / gl) if gl > 0 else 999.0
        return {
            'name': config_name,
            'trades': len(df_r),
            'wins': len(wins),
            'losses': len(losses),
            'wr': round(wr, 1),
            'pnl': round(pnl, 2),
            'pf': round(pf, 2),
            'trades_list': all_trades
        }

    # 4 Senaryoyu Çalıştır
    print("\nSimülasyonlar Koşturuluyor...")
    res_baseline = run_simulation("V5.4 Baseline (Mevcut)", use_strict_trend=False, use_partial_tp=False, min_adx=0.0)
    res_partial_tp = run_simulation("+ Partial TP (%50 Kâr Kilitleme)", use_strict_trend=False, use_partial_tp=True, min_adx=0.0)
    res_strict_trend = run_simulation("+ Katı 4H Trend Filtresi", use_strict_trend=True, use_partial_tp=False, min_adx=0.0)
    res_chop_filter = run_simulation("+ ADX Chop Kalkanı (ADX > 20)", use_strict_trend=False, use_partial_tp=False, min_adx=20.0)
    res_combined = run_simulation("⚡ V5.5 PROD (Tüm Geliştirmeler Bir Arada)", use_strict_trend=True, use_partial_tp=True, min_adx=18.0)

    print("\n" + "="*75)
    print("📊 GELİŞTİRME KARŞILAŞTIRMA MATRİSİ (2-16 EKİM 2026 - 30 COİN)")
    print("="*75)
    print(f"{'Konfigürasyon':<40} | {'İşlem':<6} | {'Win Rate':<9} | {'Net PnL':<10} | {'Profit Factor':<13}")
    print("-" * 75)
    for r in [res_baseline, res_partial_tp, res_strict_trend, res_chop_filter, res_combined]:
        print(f"{r['name']:<40} | {r['trades']:<6} | %{r['wr']:<8} | +%{r['pnl']:<8} | {r['pf']:<13}")
    print("="*75)

    # En iyi sonucu V5.5 olarak CSV'ye kaydet
    if res_combined['trades_list']:
        df_c = pd.DataFrame(res_combined['trades_list'])
        df_c.to_csv('data/v5_5_optimized_backtest.csv', index=False)
        print("\n✓ En iyi V5.5 sonuçları `data/v5_5_optimized_backtest.csv` dosyasına kaydedildi.")

if __name__ == '__main__':
    main()
