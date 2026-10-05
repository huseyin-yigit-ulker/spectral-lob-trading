import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from utils.notifier import send_telegram_message
    from utils.database import log_trade_to_supabase, update_live_metrics
except ImportError:
    send_telegram_message = None
    log_trade_to_supabase = None
    update_live_metrics = None
import websockets
import json
import csv
import os
import time
import collections
from datetime import datetime
import requests
import sys

sys.path.append(os.path.abspath(os.path.dirname(os.path.dirname(__file__))))
from features.smc_features import SMCAnalyzer
from features.state_builder import StateBuilder
from rich.console import Console
from rich.table import Table
from rich.live import Live

# Log Dosyasi
os.makedirs('logs', exist_ok=True)
date_str = datetime.now().strftime("%Y-%m-%d")
csv_file = f'logs/dynamic_smc_signals_{date_str}.csv'
if not os.path.isfile(csv_file):
    with open(csv_file, mode='a', newline='', encoding='utf-8') as f:
        csv.writer(f).writerow(['Zaman', 'Sembol', 'Fiyat', 'Macro_OBI', 'CVD_1m', 'SMC_Context', 'FVG_Top', 'FVG_Bottom', 'FVG_Depth_Pct', 'Sinyal_Yonu', 'Aktif_SL'])

class SMCAgent:
    def __init__(self, symbol):
        self.symbol = symbol
        self.state_builder = StateBuilder()
        self.current_price = 0.0
        self.latest_time = 0.0
        self.obi_buffer = collections.deque(maxlen=600)
        self.macro_obi = 0.0
        self.cvd_1m = 0.0
        self.smc_status = "ISINIYOR"
        self.internal_signal_state = 0
        self.active_trade_sl = None
        self.fvg_depth_pct = 0.0
        self.last_signal_text = "[!] BEKLE"
        self.last_signal_color = "gray"
        self.last_log_time = 0
        self.smc_5m = SMCAnalyzer(max_candles=30)
        self.smc_3m = SMCAnalyzer(max_candles=30)

agents = {}
current_symbols = []
SCREENER_FILE = 'data/active_screener.json'
last_screener_mtime = 0

def update_agents_from_screener():
    global current_symbols, last_screener_mtime
    if not os.path.exists(SCREENER_FILE): return False
    
    mtime = os.path.getmtime(SCREENER_FILE)
    if mtime == last_screener_mtime: return False
    last_screener_mtime = mtime
    
    try:
        with open(SCREENER_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            new_symbols = data.get('symbols', [])
            if not new_symbols: return False
            
            # Yeni eklenenleri isit
            for s in new_symbols:
                if s not in agents:
                    agents[s] = SMCAgent(s)
                    try:
                        r5 = requests.get(f"https://fapi.binance.com/fapi/v1/klines?symbol={s}&interval=5m&limit=30", timeout=3).json()
                        for k in r5: agents[s].smc_5m.add_candle(k[1], k[2], k[3], k[4], k[6])
                        r3 = requests.get(f"https://fapi.binance.com/fapi/v1/klines?symbol={s}&interval=3m&limit=30", timeout=3).json()
                        for k in r3: agents[s].smc_3m.add_candle(k[1], k[2], k[3], k[4], k[6])
                    except: pass
                    
            # Listeden dusenleri temizle
            to_remove = [s for s in agents if s not in new_symbols]
            for s in to_remove:
                del agents[s]
                
            current_symbols = new_symbols
            return True
    except:
        return False

def generate_table():
    table = Table(title="Dinamik V5 SMC + HFT (Oto-Tarayici Gucunde)", border_style="cyan")
    table.add_column("Sembol", justify="left", style="cyan", no_wrap=True)
    table.add_column("Fiyat", justify="right", style="magenta")
    table.add_column("Doluluk", justify="center", style="white")
    table.add_column("Macro OBI", justify="right", style="yellow")
    table.add_column("CVD (1m)", justify="right", style="blue")
    table.add_column("FVG Derinlik", justify="right", style="cyan")
    table.add_column("SMC Likidite", justify="center", style="white")
    table.add_column("Sinyal", justify="center")

    for s in current_symbols:
        if s not in agents: continue
        agent = agents[s]
        if agent.current_price == 0: continue
        
        obi = agent.macro_obi
        obi_color = "green" if obi > 0 else "red" if obi < 0 else "white"
        cvd = agent.cvd_1m
        cvd_color = "green" if cvd > 0 else "red" if cvd < 0 else "white"
        smc = agent.smc_status
        smc_color = "green bold" if smc == 'BULLISH_FVG' else "red bold" if smc == 'BEARISH_FVG' else "dim white"
        
        table.add_row(
            agent.symbol,
            f"{agent.current_price:.6f}",
            f"% {(len(agent.obi_buffer)/600)*100:.0f}",
            f"[{obi_color}]{obi:+.4f}[/{obi_color}]",
            f"[{cvd_color}]{cvd:+.2f}[/{cvd_color}]",
            f"[{ 'green' if agent.fvg_depth_pct >= 0.10 else 'red' }]% {agent.fvg_depth_pct:.2f}[/]",
            f"[{smc_color}]{smc}[/{smc_color}]",
            f"[{agent.last_signal_color}]{agent.last_signal_text}[/{agent.last_signal_color}]"
        )
    
    if update_live_metrics:
        states_dict = {}
        for s in current_symbols:
            if s in agents and agents[s].current_price > 0:
                states_dict[s.lower()] = {
                    'smc_status': agents[s].smc_status,
                    'fvg_depth': round(agents[s].fvg_depth_pct, 4)
                }
        if states_dict:
            update_live_metrics(states_dict)
            
    return table

async def binance_ws():
    console = Console()
    with Live(generate_table(), refresh_per_second=2, console=console) as live:
        while True:
            # Screener'in hazirlanmasini bekle
            while not os.path.exists(SCREENER_FILE):
                time.sleep(2)
            
            update_agents_from_screener()
            if not current_symbols:
                time.sleep(2)
                continue
                
            streams = []
            for s in current_symbols:
                ls = s.lower()
                streams.extend([f"{ls}@depth20@100ms", f"{ls}@trade", f"{ls}@kline_3m", f"{ls}@kline_5m"])
                
            stream_str = "/".join(streams)
            url = f"wss://fstream.binance.com/stream?streams={stream_str}"
            
            next_check_time = time.time() + 15
            
            try:
                async with websockets.connect(url) as ws:
                    while True:
                        # 15 saniyede bir JSON dosyasi degismis mi diye kontrol et
                        if time.time() > next_check_time:
                            if os.path.getmtime(SCREENER_FILE) != last_screener_mtime:
                                # Dosya degistiyse (Yeni coinler eklendiyse) donguyu kirip yeni baglanti ac
                                break 
                            next_check_time = time.time() + 15

                        try:
                            resp = await asyncio.wait_for(ws.recv(), timeout=2.0)
                        except asyncio.TimeoutError:
                            continue
                            
                        data = json.loads(resp)
                        stream_name = data['stream']
                        msg = data['data']
                        
                        symbol = msg.get('s', '')
                        if symbol not in agents: continue
                        agent = agents[symbol]
                        
                        if 'kline' in stream_name and msg['e'] == 'kline':
                            k = msg['k']
                            if k['x']:
                                if k['i'] == '5m': agent.smc_5m.add_candle(k['o'], k['h'], k['l'], k['c'], k['T'])
                                elif k['i'] == '3m': agent.smc_3m.add_candle(k['o'], k['h'], k['l'], k['c'], k['T'])
                        
                        elif msg.get('e') == 'trade':
                            agent.current_price = float(msg['p'])
                            agent.latest_time = msg['T']
                            agent.state_builder.cvd_features.add_trade(agent.latest_time, agent.current_price, float(msg['q']), msg['m'])
                            
                        elif msg.get('e') == 'depthUpdate':
                            bids = [[float(p), float(q)] for p, q in msg['b']]
                            asks = [[float(p), float(q)] for p, q in msg['a']]
                            b_qty = sum(b[1] for b in bids[:5]) if len(bids) >= 5 else sum(b[1] for b in bids)
                            a_qty = sum(a[1] for a in asks[:5]) if len(asks) >= 5 else sum(a[1] for a in asks)
                            raw_obi = (b_qty - a_qty) / (b_qty + a_qty + 1e-8)
                            agent.obi_buffer.append(raw_obi)
                            agent.macro_obi = sum(agent.obi_buffer) / len(agent.obi_buffer)
                            
                            if len(agent.obi_buffer) < 100: continue
                            if agent.current_price == 0.0: continue # Fiyat verisi henuz gelmediyse islem yapma
                            cvd_dict = agent.state_builder.cvd_features.get_multi_window_cvd(agent.latest_time)
                            agent.cvd_1m = cvd_dict.get('1m', 0.0)
                            
                            ctx_5 = agent.smc_5m.get_market_context(agent.current_price)
                            ctx_3 = agent.smc_3m.get_market_context(agent.current_price)
                            
                            if ctx_5 == 'BULLISH_FVG' or ctx_3 == 'BULLISH_FVG': agent.smc_status = 'BULLISH_FVG'
                            elif ctx_5 == 'BEARISH_FVG' or ctx_3 == 'BEARISH_FVG': agent.smc_status = 'BEARISH_FVG'
                            else: agent.smc_status = 'NEUTRAL'
                            
                            prev_sig = agent.internal_signal_state
                            
                            # FVG Derinlik (Boyutu) Kontrolu (>%0.10)
                            b5, t5 = agent.smc_5m.get_active_fvg_bounds(agent.current_price)
                            b3, t3 = agent.smc_3m.get_active_fvg_bounds(agent.current_price)
                            cur_b = b5 if b5 else b3
                            cur_t = t5 if t5 else t3
                            fvg_depth_ratio = ((cur_t - cur_b) / cur_b) if cur_b else 0.0
                            agent.fvg_depth_pct = fvg_depth_ratio * 100
                            is_fvg_wide_enough = fvg_depth_ratio >= 0.001 # %0.10
                            
                            if agent.macro_obi > 0.40 and agent.cvd_1m > 0 and agent.smc_status == 'BULLISH_FVG' and is_fvg_wide_enough:
                                agent.internal_signal_state = 1
                                b5, t5 = agent.smc_5m.get_active_fvg_bounds(agent.current_price)
                                b3, t3 = agent.smc_3m.get_active_fvg_bounds(agent.current_price)
                                bot_bound = b5 if b5 else b3
                                if bot_bound: agent.active_trade_sl = bot_bound * 0.9995
                            elif agent.macro_obi < -0.40 and agent.cvd_1m < 0 and agent.smc_status == 'BEARISH_FVG' and is_fvg_wide_enough:
                                agent.internal_signal_state = -1
                                b5, t5 = agent.smc_5m.get_active_fvg_bounds(agent.current_price)
                                b3, t3 = agent.smc_3m.get_active_fvg_bounds(agent.current_price)
                                top_bound = t5 if t5 else t3
                                if top_bound: agent.active_trade_sl = top_bound * 1.0005
                                
                            if agent.internal_signal_state == 1:
                                if agent.macro_obi < -0.15 or (agent.active_trade_sl and agent.current_price < agent.active_trade_sl):
                                    agent.internal_signal_state = 0
                                    agent.active_trade_sl = None
                            if agent.internal_signal_state == -1:
                                if agent.macro_obi > 0.15 or (agent.active_trade_sl and agent.current_price > agent.active_trade_sl):
                                    agent.internal_signal_state = 0
                                    agent.active_trade_sl = None
                            
                            if agent.internal_signal_state == 1:
                                agent.last_signal_text = "[+] AL (LONG)"; agent.last_signal_color = "green bold"
                            elif agent.internal_signal_state == -1:
                                agent.last_signal_text = "[-] SAT (SHORT)"; agent.last_signal_color = "red bold"
                            else:
                                agent.last_signal_text = "[!] BEKLE"; agent.last_signal_color = "gray"
                                
                            live.update(generate_table())
                            
                            if agent.internal_signal_state != prev_sig:
                                now = time.time()
                                if now - agent.last_log_time > 2:
                                    agent.last_log_time = now
                                    dt_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                    with open(csv_file, mode='a', newline='', encoding='utf-8') as f:
                                        b5, t5 = agent.smc_5m.get_active_fvg_bounds(agent.current_price)
                                    b3, t3 = agent.smc_3m.get_active_fvg_bounds(agent.current_price)
                                    f_b = b5 if b5 else (b3 if b3 else 0.0)
                                    f_t = t5 if t5 else (t3 if t3 else 0.0)
                                    f_depth = ((f_t - f_b) / f_b * 100) if f_b > 0 else 0.0
                                    
                                    csv.writer(f).writerow([
                                        dt_str, agent.symbol, agent.current_price, agent.macro_obi, agent.cvd_1m, 
                                        agent.smc_status, f_t, f_b, round(f_depth, 4), agent.last_signal_text, agent.active_trade_sl or 0.0
                                    ])
                                    
                                    # SUPABASE VE TELEGRAM ENTEGRASYONU
                                    if log_trade_to_supabase:
                                        log_trade_to_supabase(
                                            dt_str, agent.symbol, agent.current_price, agent.macro_obi, agent.cvd_1m, 
                                            agent.smc_status, agent.last_signal_text, f_t, f_b, round(f_depth, 4)
                                        )
                                        
                                    if send_telegram_message:
                                        msg = f"<b>{agent.symbol}</b>\nSinyal: {agent.last_signal_text}\nFiyat: {agent.current_price}\nOBI: {agent.macro_obi:.2f}\nSMC: {agent.smc_status}"
                                        send_telegram_message(msg)
            except Exception as e:
                time.sleep(2)

if __name__ == "__main__":
    asyncio.run(binance_ws())
