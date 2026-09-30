import os
import sys
import argparse
from pathlib import Path
import pandas as pd
import numpy as np
from loguru import logger

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agent.environment import TradingEnvironment
from agent.trainer import AgentTrainer

def prepare_data(data_dir: Path, symbol: str):
    logger.info(f"{symbol.upper()} iin gemi veriler ykleniyor (Precomputing)...")
    depth_files = sorted([f for f in os.listdir(data_dir) if f.startswith(f"depth_{symbol.lower()}")])
    
    if not depth_files:
        raise FileNotFoundError(f"{symbol.upper()} depth verisi bulunamad! Ltfen nce collect_data.py ile toplayn.")
        
    df = pd.read_parquet(data_dir / depth_files[-1])
    
    df['mid_price'] = (df['bid_price_0'] + df['ask_price_0']) / 2
    
    bids_qty = sum(df[f'bid_qty_{i}'] for i in range(5))
    asks_qty = sum(df[f'ask_qty_{i}'] for i in range(5))
    df['OBI'] = (bids_qty - asks_qty) / (bids_qty + asks_qty + 1e-8)
    
    df['OBI_10s'] = df['OBI'].rolling(100).mean().fillna(0)
    df['Return_1s'] = df['mid_price'].pct_change(10).fillna(0)
    df['Spread'] = (df['ask_price_0'] - df['bid_price_0']) / df['mid_price']
    
    df = df.dropna()
    
    features = ['OBI', 'OBI_10s', 'Return_1s', 'Spread']
    states = df[features].values
    prices = df['mid_price'].values
    
    logger.info(f"Veri hazr! Toplam Adm: {len(states)}")
    return states, prices

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", type=str, default="BTCUSDT", help="Eitilecek parite (rn: BTCUSDT, ETHUSDT)")
    parser.add_argument("--timesteps", type=int, default=100000, help="Eitim adm says")
    args = parser.parse_args()
    
    data_dir = Path("data")
    
    try:
        states, prices = prepare_data(data_dir, args.symbol)
        env = TradingEnvironment(states=states, prices=prices)
        trainer = AgentTrainer(env=env)
        
        logger.info(f"Yapay Zeka (PPO) modelinin {args.symbol.upper()} eitimi balatlyor... (Hedef adm: {args.timesteps})")
        trainer.train(timesteps=args.timesteps)
        
        model_path = f"models/ppo_{args.symbol.lower()}_v1.zip"
        trainer.save(model_path)
        
        logger.success(f"Tebrikler! RL Modeli '{model_path}' olarak kaydedildi.")
        
    except Exception as e:
        logger.error(f"Eitim srasnda hata olutu: {e}")

if __name__ == "__main__":
    main()
