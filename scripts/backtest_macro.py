import sys
sys.stdout.reconfigure(encoding='utf-8')
import pandas as pd
import numpy as np
import os
from pathlib import Path

def run_true_macro_backtest_v3():
    data_dir = Path("data")
    depth_files = sorted([f for f in os.listdir(data_dir) if f.startswith("depth_btcusdt")])
    trade_files = sorted([f for f in os.listdir(data_dir) if f.startswith("trades_btcusdt")])
    
    if not depth_files or not trade_files:
        print("[!] Veri bulunamadi.")
        return
        
    df_depth = pd.read_parquet(data_dir / depth_files[-1])
    df_depth['datetime'] = pd.to_datetime(df_depth['timestamp'], unit='ms')
    df_depth = df_depth.sort_values('datetime').reset_index(drop=True)
    
    df_trades = pd.read_parquet(data_dir / trade_files[-1])
    df_trades['datetime'] = pd.to_datetime(df_trades['timestamp'], unit='ms')
    df_trades = df_trades.sort_values('datetime')
    
    qty_col = 'quantity' if 'quantity' in df_trades.columns else 'qty'
    df_trades['signed_vol'] = np.where(df_trades['is_buyer_maker'], -df_trades[qty_col], df_trades[qty_col])
    df_trades = df_trades.set_index('datetime')
    df_trades['CVD_60s'] = df_trades['signed_vol'].rolling('60s').sum()
    
    df = pd.merge_asof(df_depth, df_trades[['CVD_60s']], left_on='datetime', right_index=True, direction='backward')
    df['CVD_60s'] = df['CVD_60s'].fillna(0)
    
    df['mid_price'] = (df['bid_price_0'] + df['ask_price_0']) / 2
    bids_qty = sum(df[f'bid_qty_{i}'] for i in range(5))
    asks_qty = sum(df[f'ask_qty_{i}'] for i in range(5))
    df['OBI_Raw'] = (bids_qty - asks_qty) / (bids_qty + asks_qty + 1e-8)
    df['OBI_60s'] = df['OBI_Raw'].rolling(600).mean().fillna(0)
    
    # --- V3 GENIS OLU BOLGE (WIDE DEAD ZONE) STRATEJISI ---
    TP_PCT = 0.0030  # Kâr Al (%0.30) - Trendde daha cok otur!
    SL_PCT = 0.0015  # Zarar Kes (%0.15)
    COMMISSION_ENTRY = 0.00016 # Maker
    COMMISSION_EXIT = 0.00016  # Maker
    
    ENTRY_THRESH = 0.40 # Eskiden 0.30'du (Giris zorlastirildi)
    EXIT_THRESH = 0.15  # Eskiden 0.05'ti (Cikis zorlastirildi, Dead Zone buyudu)
    
    balance = 10000.0
    initial_balance = 10000.0
    position = 0 
    entry_price = 0.0
    entry_time = None
    
    trades = []
    win_count = 0
    total_fee_paid = 0.0
    
    obi_arr = df['OBI_60s'].values
    cvd_arr = df['CVD_60s'].values
    price_arr = df['mid_price'].values
    time_arr = df['datetime'].values
    
    for i in range(1, len(df)):
        obi = obi_arr[i]
        cvd = cvd_arr[i]
        price = price_arr[i]
        time = time_arr[i]
        
        if position == 0:
            if obi > ENTRY_THRESH and cvd > 0:
                position = 1
                entry_price = price
                entry_time = time
                fee = balance * COMMISSION_ENTRY
                balance -= fee
                total_fee_paid += fee
            elif obi < -ENTRY_THRESH and cvd < 0:
                position = -1
                entry_price = price
                entry_time = time
                fee = balance * COMMISSION_ENTRY
                balance -= fee
                total_fee_paid += fee
        
        elif position == 1:
            exit_reason = None
            if price >= entry_price * (1 + TP_PCT):
                exit_reason = "TAKE_PROFIT"
            elif price <= entry_price * (1 - SL_PCT):
                exit_reason = "STOP_LOSS"
            elif obi < -EXIT_THRESH:
                exit_reason = "TREND_REVERSAL"
                
            if exit_reason:
                pnl_pct = (price - entry_price) / entry_price
                gross_pnl = balance * pnl_pct
                fee = balance * COMMISSION_EXIT
                net_pnl = gross_pnl - fee
                balance += net_pnl
                total_fee_paid += fee
                
                if net_pnl > 0: win_count += 1
                trades.append({"Yon": "LONG", "Sebep": exit_reason, "Net PnL": net_pnl, "Giris": entry_price, "Cikis": price})
                position = 0
                
        elif position == -1:
            exit_reason = None
            if price <= entry_price * (1 - TP_PCT):
                exit_reason = "TAKE_PROFIT"
            elif price >= entry_price * (1 + SL_PCT):
                exit_reason = "STOP_LOSS"
            elif obi > EXIT_THRESH:
                exit_reason = "TREND_REVERSAL"
                
            if exit_reason:
                pnl_pct = (entry_price - price) / entry_price
                gross_pnl = balance * pnl_pct
                fee = balance * COMMISSION_EXIT
                net_pnl = gross_pnl - fee
                balance += net_pnl
                total_fee_paid += fee
                
                if net_pnl > 0: win_count += 1
                trades.append({"Yon": "SHORT", "Sebep": exit_reason, "Net PnL": net_pnl, "Giris": entry_price, "Cikis": price})
                position = 0
                
    market_return = (price_arr[-1] - price_arr[0]) / price_arr[0] * 100
    strategy_return = (balance - initial_balance) / initial_balance * 100
    win_rate = (win_count / len(trades) * 100) if trades else 0
    
    print("\n==================================================")
    print(" 🚀 KURALCI BOT V3 (GENIS OLU BOLGE + LIMIT EMIR) ")
    print("==================================================")
    print(f"Toplam Islem Sayisi: {len(trades)}")
    print(f"Odenen Toplam Komisyon Masrafi: ${total_fee_paid:.2f}")
    
    tp_count = sum(1 for t in trades if t['Sebep'] == 'TAKE_PROFIT')
    sl_count = sum(1 for t in trades if t['Sebep'] == 'STOP_LOSS')
    rev_count = sum(1 for t in trades if t['Sebep'] == 'TREND_REVERSAL')
    
    print(f"Cikislar -> TP: {tp_count} | SL: {sl_count} | Reversal: {rev_count}")
    print(f"Basari Orani (Win Rate): % {win_rate:.2f}")
    print("-" * 50)
    print(f"Sadece Bekleseydik (Piyasa): % {market_return:.4f}")
    print(f"Genisletilmis Bot (Net Kâr): % {strategy_return:.4f}")
    print("==================================================\n")

if __name__ == "__main__":
    run_true_macro_backtest_v3()
