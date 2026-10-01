import asyncio
import json
import numpy as np
from collections import deque
import websockets
from stable_baselines3 import PPO
from rich.console import Console
from rich.table import Table
from rich.live import Live
import csv
from datetime import datetime
from pathlib import Path

console = Console()

MODEL_PATH = "models/ppo_btcusdt_v1.zip"
try:
    model = PPO.load(MODEL_PATH)
except Exception as e:
    console.print(f"[red]Model yuklenemedi! Hata: {e}[/red]")
    exit(1)

obi_history = deque(maxlen=100)
price_history = deque(maxlen=10)

# Sinyal gurultusunu (flip-flop) engellemek icin "Eminlik" tamponu (2 saniye)
ai_confidence_buffer = deque(maxlen=20) 

log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)
log_file = log_dir / f"ai_live_signals_btcusdt_{datetime.now().strftime('%Y-%m-%d')}.csv"

if not log_file.exists():
    with open(log_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Timestamp', 'Price', 'Anlik_OBI', 'Trend_OBI_10s', 'Volatilite_1s', 'Spread', 'AI_Karari'])

async def run_ai_live():
    url = "wss://fstream.binance.com/stream?streams=btcusdt@depth20@100ms"
    console.print("[yellow]RL Modeli Isiniyor (Anti-Gurultu Filtresi Aktif)...[/yellow]")
    
    confirmed_action = 1 # FLAT
    last_logged_action = -1
    
    async with websockets.connect(url) as ws:
        with Live(console=console, refresh_per_second=5) as live:
            while True:
                resp = json.loads(await ws.recv())
                data = resp['data']
                
                bids, asks = data['b'], data['a']
                bid_p_0, ask_p_0 = float(bids[0][0]), float(asks[0][0])
                mid_price = (bid_p_0 + ask_p_0) / 2.0
                
                bids_qty = sum(float(b[1]) for b in bids[:5])
                asks_qty = sum(float(a[1]) for a in asks[:5])
                obi = (bids_qty - asks_qty) / (bids_qty + asks_qty + 1e-8)
                
                obi_history.append(obi)
                price_history.append(mid_price)
                
                if len(obi_history) < 100 or len(price_history) < 10:
                    continue
                    
                obi_10s = sum(obi_history) / len(obi_history)
                return_1s = (mid_price - price_history[0]) / price_history[0]
                spread = (ask_p_0 - bid_p_0) / mid_price
                
                state = np.array([[obi, obi_10s, return_1s, spread]], dtype=np.float32)
                raw_action, _ = model.predict(state, deterministic=True)
                raw_action = int(raw_action.item())
                
                # Ajanin anlik fikrini tampona ekle
                ai_confidence_buffer.append(raw_action)
                
                # Ajan son 2 saniyedeki (20 tick) fikrinden tamamen eminse (hepsi ayniysa) sinyali onayla!
                if len(ai_confidence_buffer) == 20 and ai_confidence_buffer.count(raw_action) == 20:
                    confirmed_action = raw_action
                
                if confirmed_action == 2:
                    action_str, log_action = "🟢 LONG (AL)", "LONG"
                elif confirmed_action == 0:
                    action_str, log_action = "🔴 SHORT (SAT)", "SHORT"
                else:
                    action_str, log_action = "⚪ BEKLE (NOTR)", "FLAT"
                
                if confirmed_action != last_logged_action and last_logged_action != -1:
                    with open(log_file, 'a', newline='', encoding='utf-8') as f:
                        writer = csv.writer(f)
                        writer.writerow([
                            datetime.now().strftime('%H:%M:%S.%f')[:-3],
                            f"{mid_price:.2f}",
                            f"{obi:.4f}",
                            f"{obi_10s:.4f}",
                            f"{return_1s*100:.4f}%",
                            f"{spread*100:.4f}%",
                            log_action
                        ])
                last_logged_action = confirmed_action
                
                table = Table(title="🤖 PPO YAPAY ZEKA CANLI GÖSTERGE - BTCUSDT")
                table.add_column("Metrik", style="cyan")
                table.add_column("Deger", justify="right")
                table.add_row("Piyasa Fiyati", f"${mid_price:.2f}")
                table.add_row("Anlik OBI", f"{obi:+.3f}")
                table.add_row("Trend OBI (10s)", f"{obi_10s:+.3f}")
                table.add_row("AI TAHMINI (Filtreli)", action_str)
                live.update(table)

if __name__ == "__main__":
    try:
        asyncio.run(run_ai_live())
    except KeyboardInterrupt:
        console.print("[red]Sonlandirildi.[/red]")
