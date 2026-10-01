import os
import sys
import pandas as pd
import numpy as np
from pathlib import Path
from stable_baselines3 import PPO
from collections import deque

sys.stdout.reconfigure(encoding='utf-8')

def run_ai_backtest():
    print("[1] V4 (Hafizali) AI Modeli ve Veriler yukleniyor...")
    model_path = "models/ppo_btcusdt_v4.zip"
    try:
        model = PPO.load(model_path)
    except:
        print("[!] Hata: ppo_btcusdt_v4.zip bulunamadi. Lutfen once V4 modelini egitin.")
        return
        
    data_dir = Path("data")
    depth_files = sorted([f for f in os.listdir(data_dir) if f.startswith("depth_btcusdt")])
    trade_files = sorted([f for f in os.listdir(data_dir) if f.startswith("trades_btcusdt")])
    
    df_depth = pd.read_parquet(data_dir / depth_files[-1])
    df_depth['datetime'] = pd.to_datetime(df_depth['timestamp'], unit='ms')
    df_depth = df_depth.sort_values('datetime').reset_index(drop=True)
    
    df_trades = pd.read_parquet(data_dir / trade_files[-1])
    df_trades['datetime'] = pd.to_datetime(df_trades['timestamp'], unit='ms')
    df_trades = df_trades.sort_values('datetime')
    
    print("[2] CVD Ratio ve Matrix hesaplaniyor...")
    qty_col = 'quantity' if 'quantity' in df_trades.columns else 'qty'
    
    df_trades['buy_vol'] = np.where(df_trades['is_buyer_maker'] == False, df_trades[qty_col], 0)
    df_trades['sell_vol'] = np.where(df_trades['is_buyer_maker'] == True, df_trades[qty_col], 0)
    
    df_trades = df_trades.set_index('datetime')
    roll_buy = df_trades['buy_vol'].rolling('60s').sum()
    roll_sell = df_trades['sell_vol'].rolling('60s').sum()
    df_trades['CVD_Ratio_60s'] = ((roll_buy - roll_sell) / (roll_buy + roll_sell + 1e-8)).fillna(0)
    df_trades = df_trades.reset_index()
    
    df = pd.merge_asof(df_depth, df_trades[['datetime', 'CVD_Ratio_60s']], left_on='datetime', right_on='datetime', direction='backward')
    df['CVD_Ratio_60s'] = df['CVD_Ratio_60s'].fillna(0)
    
    df['mid_price'] = (df['bid_price_0'] + df['ask_price_0']) / 2
    bids_qty = sum(df[f'bid_qty_{i}'] for i in range(5))
    asks_qty = sum(df[f'ask_qty_{i}'] for i in range(5))
    df['OBI'] = (bids_qty - asks_qty) / (bids_qty + asks_qty + 1e-8)
    
    df = df.set_index('datetime')
    df['OBI_60s'] = df['OBI'].rolling('60s').mean().fillna(0)
    df = df.reset_index()
    
    df['Return_1s'] = df['mid_price'].pct_change(10).fillna(0)
    df['Spread'] = (df['ask_price_0'] - df['bid_price_0']) / df['mid_price']
    
    df = df.dropna().reset_index(drop=True)
    
    states = df[['OBI', 'OBI_60s', 'CVD_Ratio_60s', 'Return_1s', 'Spread']].values
    
    print("[3] Yapay Zeka V4 Dinamik (Hafizali) Tahmin ve PnL Hesaplamasi Yapiyor...")
    # Not: Ajanin karari artik kendi pozisyonuna bagli oldugu icin vektorize edemeyiz, adim adim donmeliyiz.
    
    balance = 10000.0
    initial_balance = 10000.0
    commission = 0.0004
    position = 0 
    entry_price = 0.0
    trades_count = 0
    win_count = 0
    
    buffer = deque(maxlen=20)
    confirmed_position = 0 # Baslangicta Flat
    
    total_steps = len(df)
    
    for i in range(1, total_steps):
        # Ajanin o anki gozlemine MEVCUT POZISYONUNU (confirmed_position) ekliyoruz!
        obs = np.append(states[i], confirmed_position).astype(np.float32)
        
        raw_action, _ = model.predict(obs, deterministic=True)
        raw_action = int(raw_action.item())
        
        # Eminlik Filtresi
        buffer.append(raw_action)
        if len(buffer) == 20 and buffer.count(buffer[0]) == 20:
            target_pos = buffer[0] - 1
        else:
            target_pos = confirmed_position
            
        price = df['mid_price'].iloc[i]
        
        if target_pos != confirmed_position:
            if confirmed_position != 0:
                pnl_pct = (price - entry_price) / entry_price * confirmed_position
                gross_pnl = balance * pnl_pct
                fee = balance * commission
                net_pnl = gross_pnl - fee
                balance += net_pnl
                if net_pnl > 0: win_count += 1
            
            confirmed_position = target_pos
            if confirmed_position != 0:
                entry_price = price
                balance -= balance * commission
                trades_count += 1
                
        if i % 100000 == 0:
            print(f"... Ilerleme: % {int((i/total_steps)*100)} (Islem: {trades_count})")
                
    market_return = (df['mid_price'].iloc[-1] - df['mid_price'].iloc[0]) / df['mid_price'].iloc[0] * 100
    ai_return = (balance - initial_balance) / initial_balance * 100
    win_rate = (win_count / trades_count * 100) if trades_count > 0 else 0
    
    print("\n==================================================")
    print(" 🤖 V4 YAPAY ZEKA (HAFIZALI + CVD) BACKTEST SONUCU ")
    print("==================================================")
    print(f"Toplam Islem Sayisi: {trades_count}")
    print(f"Basari Orani (Win Rate): % {win_rate:.2f}")
    print("-" * 50)
    print(f"Sadece Bekleseydik (Piyasa): % {market_return:.4f}")
    print(f"Yapay Zeka (PPO V4) Kârı:    % {ai_return:.4f}")
    print("==================================================\n")

if __name__ == "__main__":
    run_ai_backtest()
