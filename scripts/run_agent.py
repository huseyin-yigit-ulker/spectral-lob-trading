import asyncio
import json
import sys
import time
import collections
from datetime import datetime, timezone
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import websockets
from loguru import logger
from features.state_builder import StateBuilder
from rich.console import Console
from rich.table import Table
from rich.live import Live

class LiveSignalGenerator:
    def __init__(self, symbol: str):
        self.symbol = symbol.lower()
        self.base_asset = self.symbol.replace("usdt", "").upper()
        # Binance stream URL'si: Kucuk harflerle
        self.ws_url = f"wss://fstream.binance.com/stream?streams={self.symbol}@depth20@100ms/{self.symbol}@trade"
        self.is_running = True
        self.state_builder = StateBuilder()
        self.current_price = 0.0
        self.latest_exchange_time = 0.0 
        
        # --- GERCEK MACRO STRATEJI (60 SANIYE) ---
        self.obi_buffer = collections.deque(maxlen=600) # 60 saniyelik tampon (600 * 100ms)
        self.macro_obi = 0.0
        self.last_signal = "BEKLE"
        self.last_signal_color = "white"
        self.internal_signal_state = 0 # 0: Bekle, 1: Long, -1: Short
        
        self.previous_log_state = 0
        self.log_dir = Path("logs")
        self.log_dir.mkdir(exist_ok=True)
        self.log_file = self.log_dir / f"live_signals_{self.symbol}_{datetime.now().strftime('%Y-%m-%d')}.csv"
        
        if not self.log_file.exists():
            with open(self.log_file, "w", encoding="utf-8") as f:
                f.write("Zaman,Sembol,Fiyat,Macro_OBI,CVD_1m,Sinyal_Yonu\n")
        
        self.console = Console()
        
    async def connect(self):
        reconnect_delay = 1.0
        while self.is_running:
            try:
                async with websockets.connect(self.ws_url, ping_interval=20, ping_timeout=20) as ws:
                    reconnect_delay = 1.0
                    async for message in ws:
                        if not self.is_running: break
                        data = json.loads(message)
                        stream = data.get("stream", "")
                        payload = data.get("data", {})
                        
                        # Stream isimleri binance tarafindan kucuk harf gelir
                        if "depth" in stream: 
                            self._handle_depth(payload)
                        elif "trade" in stream: 
                            self._handle_trade(payload)
            except asyncio.CancelledError: break
            except Exception as e: pass
            if not self.is_running: break
            await asyncio.sleep(reconnect_delay)
            reconnect_delay = min(reconnect_delay * 2, 60.0)

    def _handle_trade(self, payload: dict):
        ts = float(payload.get("E", payload.get("T", 0))) / 1000.0
        self.latest_exchange_time = ts
        price = float(payload.get("p", 0))
        qty = float(payload.get("q", 0))
        is_buyer_maker = payload.get("m", False) # m: true ise Satici (Taker Sell), false ise Alici (Taker Buy)
        self.state_builder.cvd_features.add_trade(ts, price, qty, is_buyer_maker)

    def _handle_depth(self, payload: dict):
        bids = np.array(payload.get("b", payload.get("bids", [])), dtype=float)
        asks = np.array(payload.get("a", payload.get("asks", [])), dtype=float)
        if len(bids) == 0 or len(asks) == 0: return
        self.current_price = (bids[0][0] + asks[0][0]) / 2.0
        current_time = float(payload.get("E", 0)) / 1000.0
        self.latest_exchange_time = current_time 
        try:
            self._generate_macro_signal(bids, asks, current_time)
        except Exception as e: pass

    def _generate_macro_signal(self, bids: np.ndarray, asks: np.ndarray, current_time: float):
        bids_qty = sum(b[1] for b in bids[:5]) if len(bids) >= 5 else sum(b[1] for b in bids)
        asks_qty = sum(a[1] for a in asks[:5]) if len(asks) >= 5 else sum(a[1] for a in asks)
        raw_obi = (bids_qty - asks_qty) / (bids_qty + asks_qty) if bids_qty + asks_qty > 0 else 0.0
        
        self.obi_buffer.append(raw_obi)
        self.macro_obi = sum(self.obi_buffer) / len(self.obi_buffer)
        
        # En az 10 saniye veri dolsun (100 veri). Ama gercek ortalama 60 sn'ye ulasacak
        if len(self.obi_buffer) < 100:
            self.last_signal = "ISINIYOR... (Veri Toplaniyor)"
            self.last_signal_color = "yellow"
            return

        cvd_dict = self.state_builder.cvd_features.get_multi_window_cvd(self.latest_exchange_time)
        cvd_1m = cvd_dict.get('1m', 0.0)

        # 3. Genisletilmis Tolerans/Hysteresis Mantigi (60 Sn. Uyumlu)
        # Sadece OBI degil, Hacim (CVD) onayini da ariyoruz
        if self.macro_obi > 0.30 and cvd_1m > 0: 
            self.internal_signal_state = 1
        elif self.macro_obi < -0.30 and cvd_1m < 0: 
            self.internal_signal_state = -1
            
        # Kapatma sartlari (Eski yonun tam tersine hafif bir kayma gerektirir)
        if self.internal_signal_state == 1 and self.macro_obi < -0.05: self.internal_signal_state = 0
        if self.internal_signal_state == -1 and self.macro_obi > 0.05: self.internal_signal_state = 0
            
        if self.internal_signal_state == 1:
            self.last_signal = "🟢 AL (LONG)"
            self.last_signal_color = "green"
        elif self.internal_signal_state == -1:
            self.last_signal = "🔴 SAT (SHORT)"
            self.last_signal_color = "red"
        else:
            self.last_signal = "⚪ BEKLE (NOTR)"
            self.last_signal_color = "white"
            
        if self.internal_signal_state != self.previous_log_state:
            sig_text = "BEKLE"
            if self.internal_signal_state == 1: sig_text = "LONG"
            elif self.internal_signal_state == -1: sig_text = "SHORT"
            
            ts_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(f"{ts_str},{self.symbol.upper()},{self.current_price:.2f},{self.macro_obi:.4f},{cvd_1m:.4f},{sig_text}\n")
                
            self.previous_log_state = self.internal_signal_state

    def generate_dashboard(self) -> Table:
        table = Table(title=f"🤖 Otonom Trading Ajanı (GERCEK MACRO) - {self.symbol.upper()}")
        table.add_column("Metrik", justify="left", style="cyan", no_wrap=True)
        table.add_column("Deger", justify="right", style="magenta")
        
        decimals = 5 if self.current_price < 10.0 else 2
        table.add_row("Piyasa Fiyati", f"${self.current_price:,.{decimals}f}")
        
        # 60 Saniyelik (600 Tick) Buffer doluluk orani
        buffer_pct = (len(self.obi_buffer) / 600) * 100
        table.add_row("Tampon Doluluk (60sn)", f"% {buffer_pct:.0f}")
        table.add_row("Macro OBI (60sn Ort)", f"{self.macro_obi:+.3f}")
        
        cvd_dict = self.state_builder.cvd_features.get_multi_window_cvd(self.latest_exchange_time)
        cvd_60s = cvd_dict.get('1m', 0.0)
        table.add_row("1 Dk Kumulatif Hacim (CVD)", f"{cvd_60s:+.2f} {self.base_asset}")
        
        signal = getattr(self, "last_signal", "BEKLE")
        color = getattr(self, "last_signal_color", "white")
        table.add_row("URETILEN SINYAL", f"[{color} bold]{signal}[/]")
        return table

    async def run(self):
        task = asyncio.create_task(self.connect())
        try:
            with Live(self.generate_dashboard(), refresh_per_second=2, console=self.console) as live:
                while self.is_running:
                    live.update(self.generate_dashboard())
                    await asyncio.sleep(0.5)
        except asyncio.CancelledError: pass
        finally:
            self.is_running = False
            task.cancel()

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", type=str, default="BTCUSDT")
    args = parser.parse_args()
    generator = LiveSignalGenerator(args.symbol)
    try: asyncio.run(generator.run())
    except KeyboardInterrupt: print("\n[!] Sistem durduruldu.")

if __name__ == "__main__":
    main()
