import asyncio
import json
import sys
import collections
from datetime import datetime
from pathlib import Path
import numpy as np
import websockets
from loguru import logger
from rich.console import Console
from rich.table import Table
from rich.live import Live

sys.path.insert(0, str(Path(__file__).resolve().parent))
from features.state_builder import StateBuilder

# Konsolu kirletmemesi icin loguru'yu kapatiyoruz
logger.remove()

class AgentState:
    def __init__(self, symbol: str):
        self.symbol = symbol.upper()
        self.state_builder = StateBuilder()
        self.current_price = 0.0
        self.latest_time = 0.0
        self.obi_buffer = collections.deque(maxlen=600)
        self.macro_obi = 0.0
        self.internal_signal_state = 0
        self.last_signal_text = "ISINIYOR"
        self.last_signal_color = "gray"
        self.cvd_1m = 0.0

class MultiLiveSignalGenerator:
    def __init__(self, symbols: list):
        self.symbols = [s.lower() for s in symbols]
        self.agents = {s: AgentState(s) for s in self.symbols}
        
        # Max 1024 streams (Binance Multiplex)
        stream_names = []
        for s in self.symbols:
            stream_names.append(f"{s}@depth20@100ms")
            stream_names.append(f"{s}@trade")
        
        self.ws_url = f"wss://fstream.binance.com/stream?streams={'/'.join(stream_names)}"
        self.is_running = True
        
        self.log_dir = Path("logs")
        self.log_dir.mkdir(exist_ok=True)
        self.log_file = self.log_dir / f"multi_signals_{datetime.now().strftime('%Y-%m-%d')}.csv"
        
        if not self.log_file.exists():
            with open(self.log_file, "w", encoding="utf-8") as f:
                f.write("Zaman,Sembol,Fiyat,Macro_OBI,CVD_1m,Sinyal_Yonu\n")
        
        self.console = Console()
        
    async def connect(self):
        reconnect_delay = 1.0
        while self.is_running:
            try:
                async with websockets.connect(self.ws_url, ping_interval=20, ping_timeout=20) as ws:
                    async for message in ws:
                        if not self.is_running: break
                        data = json.loads(message)
                        stream = data.get("stream", "")
                        payload = data.get("data", {})
                        
                        symbol = stream.split('@')[0]
                        if symbol in self.agents:
                            agent = self.agents[symbol]
                            if "depth" in stream:
                                self._handle_depth(agent, payload)
                            elif "trade" in stream:
                                self._handle_trade(agent, payload)
            except asyncio.CancelledError: break
            except Exception as e: pass
            await asyncio.sleep(reconnect_delay)
            reconnect_delay = min(reconnect_delay * 2, 60.0)

    def _handle_trade(self, agent, payload):
        ts = float(payload.get("E", payload.get("T", 0))) / 1000.0
        agent.latest_time = ts
        price = float(payload.get("p", 0))
        qty = float(payload.get("q", 0))
        is_buyer_maker = payload.get("m", False)
        agent.state_builder.cvd_features.add_trade(ts, price, qty, is_buyer_maker)

    def _handle_depth(self, agent, payload):
        bids = np.array(payload.get("b", []), dtype=float)
        asks = np.array(payload.get("a", []), dtype=float)
        if len(bids) == 0 or len(asks) == 0: return
        agent.current_price = (bids[0][0] + asks[0][0]) / 2.0
        ts = float(payload.get("E", 0)) / 1000.0
        agent.latest_time = ts
        
        bids_qty = sum(b[1] for b in bids[:5]) if len(bids) >= 5 else sum(b[1] for b in bids)
        asks_qty = sum(a[1] for a in asks[:5]) if len(asks) >= 5 else sum(a[1] for a in asks)
        raw_obi = (bids_qty - asks_qty) / (bids_qty + asks_qty + 1e-8)
        
        agent.obi_buffer.append(raw_obi)
        agent.macro_obi = sum(agent.obi_buffer) / len(agent.obi_buffer)
        
        if len(agent.obi_buffer) < 100: return
        
        cvd_dict = agent.state_builder.cvd_features.get_multi_window_cvd(agent.latest_time)
        agent.cvd_1m = cvd_dict.get('1m', 0.0)
        
        prev_sig = agent.internal_signal_state
        
        # ALTCOIN VOLATILITESINE UYGUN GENISLETILMIS OLU BOLGE KURALI
        ENTRY = 0.40
        EXIT = 0.15 
        
        if agent.macro_obi > ENTRY and agent.cvd_1m > 0:
            agent.internal_signal_state = 1
        elif agent.macro_obi < -ENTRY and agent.cvd_1m < 0:
            agent.internal_signal_state = -1
            
        if agent.internal_signal_state == 1 and agent.macro_obi < -EXIT: agent.internal_signal_state = 0
        if agent.internal_signal_state == -1 and agent.macro_obi > EXIT: agent.internal_signal_state = 0
        
        if agent.internal_signal_state == 1:
            agent.last_signal_text = "🟢 AL (LONG)"
            agent.last_signal_color = "green"
        elif agent.internal_signal_state == -1:
            agent.last_signal_text = "🔴 SAT (SHORT)"
            agent.last_signal_color = "red"
        else:
            agent.last_signal_text = "⚪ BEKLE"
            agent.last_signal_color = "white"
            
        if agent.internal_signal_state != prev_sig:
            ts_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(f"{ts_str},{agent.symbol},{agent.current_price:.6f},{agent.macro_obi:.4f},{agent.cvd_1m:.4f},{agent.last_signal_text}\n")

    def generate_dashboard(self) -> Table:
        table = Table(title="🚀 Çoklu Altcoin Volatilite Avcısı (GERÇEK MACRO)")
        table.add_column("Sembol", style="cyan", justify="left")
        table.add_column("Fiyat", style="magenta", justify="right")
        table.add_column("Tampon", style="blue", justify="right")
        table.add_column("Macro OBI", justify="right")
        table.add_column("CVD (1m)", justify="right")
        table.add_column("Sinyal", justify="center")
        
        for s, agent in self.agents.items():
            if agent.current_price == 0: continue
            
            obi_color = "green" if agent.macro_obi > 0 else "red" if agent.macro_obi < 0 else "white"
            cvd_color = "green" if agent.cvd_1m > 0 else "red" if agent.cvd_1m < 0 else "white"
            
            table.add_row(
                agent.symbol,
                f"${agent.current_price:,.4f}",
                f"% {(len(agent.obi_buffer)/600)*100:.0f}",
                f"[{obi_color}]{agent.macro_obi:+.3f}[/{obi_color}]",
                f"[{cvd_color}]{agent.cvd_1m:+.1f}[/{cvd_color}]",
                f"[{agent.last_signal_color}]{agent.last_signal_text}[/{agent.last_signal_color}]"
            )
        return table

    async def run(self):
        task = asyncio.create_task(self.connect())
        try:
            with Live(self.generate_dashboard(), refresh_per_second=4, console=self.console) as live:
                while self.is_running:
                    await asyncio.sleep(0.25)
                    live.update(self.generate_dashboard())
        finally:
            self.is_running = False
            task.cancel()

def main():
    import argparse
    parser = argparse.ArgumentParser()
    # Eger terminalden bir sey girilmezse bu 5'ini ayni anda tarar:
    parser.add_argument("--symbols", type=str, default="BTCUSDT,ETHUSDT,SOLUSDT,BNBUSDT,XRPUSDT,DOGEUSDT,PEPEUSDT,WIFUSDT,AVAXUSDT,LINKUSDT,NEARUSDT,RENDERUSDT,FETUSDT,SUIUSDT,APTUSDT,INJUSDT,ORDIUSDT,TIAUSDT,ARBUSDT,SHIBUSDT,ADAUSDT,DOTUSDT,TRXUSDT,TONUSDT,BONKUSDT,FLOKIUSDT,BOMEUSDT,NOTUSDT,STRKUSDT,OPUSDT,SEIUSDT,GALAUSDT,SANDUSDT,FTMUSDT,ATOMUSDT,STXUSDT,LDOUSDT,FILUSDT,ICPUSDT,VETUSDT,THETAUSDT,GRTUSDT,AAVEUSDT,MKRUSDT,SNXUSDT,CRVUSDT,DYDXUSDT,WLDUSDT,PENDLEUSDT,JUPUSDT,LTCUSDT,BCHUSDT,ETCUSDT,EOSUSDT,XLMUSDT,XMRUSDT,ZECUSDT,DASHUSDT,ALGOUSDT,MANAUSDT,AXSUSDT,ENJUSDT,CHZUSDT,RUNEUSDT,EGLDUSDT,KAVAUSDT,BANDUSDT,OCEANUSDT,COMPUSDT,YFIUSDT,SUSHIUSDT,UNIUSDT,1INCHUSDT,BATUSDT,ZRXUSDT,KNCUSDT,ZILUSDT,ONTUSDT,NEOUSDT,QTUMUSDT,IOTAUSDT,WAVESUSDT,XTZUSDT,ROSEUSDT,GMXUSDT,MAGICUSDT,CFXUSDT,ACHUSDT,SSVUSDT,LQTYUSDT,LINAUSDT,MTLUSDT,TOMOUSDT,TRBUSDT,YGGUSDT,BLURUSDT,SFPUSDT,C98USDT,APEUSDT,ARUSDT")
    args = parser.parse_args()
    
    symbols = [s.strip() for s in args.symbols.split(",")]
    generator = MultiLiveSignalGenerator(symbols)
    try: asyncio.run(generator.run())
    except KeyboardInterrupt: print("\n[!] Sistem durduruldu.")

if __name__ == "__main__":
    main()

