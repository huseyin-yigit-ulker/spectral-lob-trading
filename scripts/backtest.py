import pandas as pd
import numpy as np
import os
from pathlib import Path
import matplotlib.pyplot as plt

def run_backtest():
    data_dir = Path("data")
    
    # Sadece BTCUSDT depth dosyalarını bul
    depth_files = sorted([f for f in os.listdir(data_dir) if f.startswith("depth_btcusdt")])
    
    if not depth_files:
        print("[!] BTCUSDT depth verisi bulunamadi. Lutfen once collect_data.py ile veri toplayin.")
        return
        
    # En güncel dosyayı yükle
    df = pd.read_parquet(data_dir / depth_files[-1])
    print(f"[OK] Veri yuklendi: {len(df)} anlik piyasa durumu.")
    
    # 1. Mid Price Hesaplama
    df['mid_price'] = (df['bid_price_0'] + df['ask_price_0']) / 2
    
    # 2. OBI (Order Book Imbalance) - İlk 5 kademe
    bids_qty = sum(df[f'bid_qty_{i}'] for i in range(5))
    asks_qty = sum(df[f'ask_qty_{i}'] for i in range(5))
    df['OBI'] = (bids_qty - asks_qty) / (bids_qty + asks_qty)
    
    # 3. Sinyal Üretimi (Geçmişe Dönük)
    df['Signal'] = 0
    df.loc[df['OBI'] > 0.3, 'Signal'] = 1   # LONG
    df.loc[df['OBI'] < -0.3, 'Signal'] = -1 # SHORT
    
    # 4. Kâr / Zarar Hesaplama
    # Bir sonraki adımdaki getiriyi (Return) hesapla
    df['Future_Return'] = df['mid_price'].pct_change().shift(-1)
    
    # Strateji Getirisi = Sinyal * Gelecek Getiri 
    # (Not: Burada komisyon ve kayma -slippage- dahil edilmemiştir, ideal laboratuvar ortamıdır)
    df['Strategy_Return'] = df['Signal'] * df['Future_Return']
    
    # Kümülatif Getiri Hesaplama
    df['Cumulative_Market'] = (1 + df['Future_Return']).cumprod() - 1
    df['Cumulative_Strategy'] = (1 + df['Strategy_Return']).cumprod() - 1
    
    # 5. İstatistikleri Çıkarma
    total_longs = (df['Signal'] == 1).sum()
    total_shorts = (df['Signal'] == -1).sum()
    
    # Son geçerli değeri al (en son satır NaN olacağı için -2'yi alıyoruz)
    market_return = df['Cumulative_Market'].iloc[-2] * 100
    strategy_return = df['Cumulative_Strategy'].iloc[-2] * 100
    
    print("\n" + "="*30)
    print(" [BACKTEST] OBI STRATEJISI SONUCLARI ")
    print("="*30)
    print(f"Incelenen Zaman Dilimi (Satir): {len(df)}")
    print(f"Uretilen LONG Sinyali:  {total_longs}")
    print(f"Uretilen SHORT Sinyali: {total_shorts}")
    print("-" * 30)
    print(f"Sadece Bekleseydik (Buy & Hold) Kar: % {market_return:.4f}")
    print(f"Ajanin OBI Stratejisi Kari:          % {strategy_return:.4f}")
    print("="*30 + "\n")
    
    # 6. Grafik Çizimi ve Kaydetme
    plt.figure(figsize=(12, 6))
    plt.style.use('dark_background')
    plt.plot(df['Cumulative_Market'] * 100, label='Piyasa (Sadece Al-Bekle)', color='cyan', alpha=0.6)
    plt.plot(df['Cumulative_Strategy'] * 100, label='Ajan (OBI Stratejisi)', color='magenta', linewidth=2)
    plt.title('Otonom Ajan Backtest Performansi (Kumulatif Kar %)', fontsize=14)
    plt.xlabel('Zaman Cizelgesi (Adim)')
    plt.ylabel('Kar / Zarar (%)')
    plt.legend()
    plt.grid(alpha=0.2)
    
    plot_path = "backtest_result.png"
    plt.savefig(plot_path)
    print(f"[OK] Kar/Zarar grafigi kaydedildi: {plot_path}")

if __name__ == "__main__":
    run_backtest()
