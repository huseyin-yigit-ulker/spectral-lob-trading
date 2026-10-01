import os
import sys
import argparse
from pathlib import Path
import pandas as pd
import numpy as np
from loguru import logger
from stable_baselines3 import PPO

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from agent.environment import TradingEnvironment
from agent.trainer import AgentTrainer

def prepare_data_v4(data_dir: Path, symbol: str):
    logger.info(f"{symbol.upper()} icin DEPTH ve TRADES verileri harmanlaniyor (v4 Normalizasyon)...")
    
    depth_files = sorted([f for f in os.listdir(data_dir) if f.startswith(f"depth_{symbol.lower()}")])
    trade_files = sorted([f for f in os.listdir(data_dir) if f.startswith(f"trades_{symbol.lower()}")])
    
    if not depth_files or not trade_files:
        raise FileNotFoundError("Depth veya Trade verisi eksik!")
        
    df_depth = pd.read_parquet(data_dir / depth_files[-1])
    df_depth['datetime'] = pd.to_datetime(df_depth['timestamp'], unit='ms')
    df_depth = df_depth.sort_values('datetime').reset_index(drop=True)
    
    df_trades = pd.read_parquet(data_dir / trade_files[-1])
    df_trades['datetime'] = pd.to_datetime(df_trades['timestamp'], unit='ms')
    df_trades = df_trades.sort_values('datetime')
    
    logger.info("CVD Ratio (-1 ile 1 arasi) hesaplaniyor...")
    
    qty_col = 'quantity' if 'quantity' in df_trades.columns else 'qty'
    
    # is_buyer_maker == False -> Taker Buy (Alicilar baskin)
    # is_buyer_maker == True -> Taker Sell (Saticilar baskin)
    df_trades['buy_vol'] = np.where(df_trades['is_buyer_maker'] == False, df_trades[qty_col], 0)
    df_trades['sell_vol'] = np.where(df_trades['is_buyer_maker'] == True, df_trades[qty_col], 0)
    
    df_trades = df_trades.set_index('datetime')
    roll_buy = df_trades['buy_vol'].rolling('60s').sum()
    roll_sell = df_trades['sell_vol'].rolling('60s').sum()
    
    # CVD_Ratio_60s = (-1 ile +1 arasinda kusursuz dengelenmis yuzdelik hacim baskisi)
    df_trades['CVD_Ratio_60s'] = ((roll_buy - roll_sell) / (roll_buy + roll_sell + 1e-8)).fillna(0)
    df_trades = df_trades.reset_index()
    
    logger.info("Zaman Serileri Birlestiriliyor (Merge_Asof)...")
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
    
    # 5 MATRIS DE ARTIK NORMALIZASYONLU! (Hicbiri devasa sayilar icermiyor)
    features = ['OBI', 'OBI_60s', 'CVD_Ratio_60s', 'Return_1s', 'Spread']
    states = df[features].values
    prices = df['mid_price'].values
    
    logger.info(f"v4 Veri Hazir! Egitim Adimi (Satir): {len(states)}")
    return states, prices

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", type=str, default="BTCUSDT")
    parser.add_argument("--timesteps", type=int, default=100000)
    args = parser.parse_args()
    
    data_dir = Path("data")
    
    try:
        states, prices = prepare_data_v4(data_dir, args.symbol)
        
        env = TradingEnvironment(states=states, prices=prices, commission_rate=0.0004)
        trainer = AgentTrainer(env=env, algo="PPO", config={"learning_rate": 3e-4, "n_steps": 2048})
        
        logger.info(f"Yapay Zeka v4 (Normalize CVD) Modeli egitiliyor... (Hedef: {args.timesteps})")
        trainer.model.learn(total_timesteps=args.timesteps)
        
        save_path = f"models/ppo_{args.symbol.lower()}_v4.zip"
        trainer.model.save(save_path)
        logger.success(f"Tebrikler! v4 Modeli '{save_path}' olarak kaydedildi.")
        
    except Exception as e:
        logger.error(f"Egitim sirasinda hata: {e}")

if __name__ == "__main__":
    main()
