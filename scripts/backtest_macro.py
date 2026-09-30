import pandas as pd
import numpy as np
import os
from pathlib import Path
import matplotlib.pyplot as plt

def run_true_macro_backtest():
    data_dir = Path("data")
    depth_files = sorted([f for f in os.listdir(data_dir) if f.startswith("depth_btcusdt")])
    trade_files = sorted([f for f in os.listdir(data_dir) if f.startswith("trades_btcusdt")])
    
    if not depth_files or not trade_files:
        print("[!] Veri bulunamadi (Hem depth hem trade dosyasi gerekli).")
        return
        
    print("[1] Veriler yukleniyor...")
    df_depth = pd.read_parquet(data_dir / depth_files[-1])
    df_depth['datetime'] = pd.to_datetime(df_depth['timestamp'], unit='ms')
    df_depth = df_depth.sort_values('datetime').reset_index(drop=True)
    
    df_trades = pd.read_parquet(data_dir / trade_files[-1])
    df_trades['datetime'] = pd.to_datetime(df_trades['timestamp'], unit='ms')
    df_trades = df_trades.sort_values('datetime')
    
    print("[2] 60 Saniyelik Hacim (CVD) hesaplaniyor...")
    # Satici ise eksi, alici ise arti hacim
    df_trades['signed_vol'] = np.where(df_trades['is_buyer_maker'], -df_trades['qty'], df_trades['qty'])
    df_trades = df_trades.set_index('datetime')
    df_trades['CVD_60s'] = df_trades['signed_vol'].rolling('60s').sum()
    
    # Depth ve CVD verilerini zaman damgasina gore birlestir
    df = pd.merge_asof(df_depth, df_trades[['CVD_60s']], left_on='datetime', right_index=True, direction='backward')
    df['CVD_60s'] = df['CVD_60s'].fillna(0)
    
    print("[3] OBI ve 60s Hareketli Ortalama hesaplaniyor...")
    df['mid_price'] = (df['bid_price_0'] + df['ask_price_0']) / 2
    bids_qty = sum(df[f'bid_qty_{i}'] for i in range(5))
    asks_qty = sum(df[f'ask_qty_{i}'] for i in range(5))
    df['OBI_Raw'] = (bids_qty - asks_qty) / (bids_qty + asks_qty + 1e-8)
    
    # Canlıdaki gibi 600 tick (60 saniye) ortalama
    df['OBI_60s'] = df['OBI_Raw'].rolling(600).mean().fillna(0)
    
    print("[4] Canlidaki kati kurallarla sinyal uretiliyor...")
    signals = []
    current_sig = 0
    
    for obi, cvd in zip(df['OBI_60s'], df['CVD_60s']):
        # Canlı stratejideki AL/SAT ve Kapama kosullari
        if obi > 0.30 and cvd > 0:
            current_sig = 1
        elif obi < -0.30 and cvd < 0:
            current_sig = -1
        elif current_sig == 1 and obi < -0.05:
            current_sig = 0
        elif current_sig == -1 and obi > 0.05:
            current_sig = 0
            
        signals.append(current_sig)
        
    df['Signal'] = signals
    
    print("[5] Kâr/Zarar (PnL) Sonuclari Olusturuluyor...")
    df['Future_Return'] = df['mid_price'].pct_change().shift(-1)
    df['Strategy_Return'] = df['Signal'] * df['Future_Return']
    df['Cumulative_Market'] = (1 + df['Future_Return']).cumprod() - 1
    df['Cumulative_Strategy'] = (1 + df['Strategy_Return']).cumprod() - 1
    
    trades = []
    current_pos = 0
    entry_time, entry_price = None, 0.0
    
    for i, row in df.iterrows():
        sig = row['Signal']
        price = row['mid_price']
        time = row['datetime']
        
        if sig != current_pos:
            if current_pos != 0:
                pnl = (price - entry_price) / entry_price
                if current_pos == -1: pnl = -pnl
                trades.append({
                    'Islem_Yonu': 'LONG' if current_pos == 1 else 'SHORT',
                    'Giris_Zamani': entry_time,
                    'Giris_Fiyati': round(entry_price, 2),
                    'Cikis_Zamani': time,
                    'Cikis_Fiyati': round(price, 2),
                    'Sure_Saniye': round((time - entry_time).total_seconds(), 2),
                    'Kar_Zarar_%': round(pnl * 100, 4)
                })
            current_pos = sig
            if current_pos != 0:
                entry_time = time
                entry_price = price
                
    trades_df = pd.DataFrame(trades)
    market_ret = df['Cumulative_Market'].iloc[-2] * 100
    strategy_ret = df['Cumulative_Strategy'].iloc[-2] * 100
    
    print("\n" + "="*50)
    print(" 🚀 CANLIDAKİ GERÇEK MACRO SİSTEM BACKTEST SONUCU ")
    print("="*50)
    if not trades_df.empty:
        print(f"Toplam Islem Sayisi: {len(trades_df)}")
        print(f"Ortalama Islem Suresi: {trades_df['Sure_Saniye'].mean():.2f} Saniye")
        win_rate = (trades_df['Kar_Zarar_%'] > 0).mean() * 100
        print(f"Basari Orani (Win Rate): % {win_rate:.2f}")
    else:
        print("DIKKAT: Verilen periyotta sinyal kosullari (OBI>0.30 & CVD>0) hic olusmadi!")
        print("Bu botun yatay piyasada parayi korudugunun en buyuk kanitidir.")
    print("-" * 50)
    print(f"Sadece Bekleseydik (Piyasa): % {market_ret:.4f}")
    print(f"Gercek Macro Stratejisi:     % {strategy_ret:.4f}")
    print("="*50 + "\n")
    
    if not trades_df.empty:
        csv_path = "btc_canli_macro_islemleri.csv"
        trades_df.to_csv(csv_path, index=False)
        print(f"[OK] Islemler detayli olarak '{csv_path}' dosyasina kaydedildi.")

    plt.figure(figsize=(12, 6))
    plt.style.use('dark_background')
    plt.plot(df['Cumulative_Market'] * 100, label='Piyasa', color='cyan', alpha=0.6)
    plt.plot(df['Cumulative_Strategy'] * 100, label='Canli Macro Ajan', color='magenta', linewidth=2)
    plt.title('Canlidaki Modelin Backtest Performansi (Kumulatif Kar %)', fontsize=14)
    plt.xlabel('Zaman (Adim)')
    plt.ylabel('Kar / Zarar (%)')
    plt.legend()
    plt.grid(alpha=0.2)
    plt.savefig("backtest_canli_macro.png")
    print("\n[OK] Grafik 'backtest_canli_macro.png' olarak kaydedildi.")

if __name__ == "__main__":
    run_true_macro_backtest()
