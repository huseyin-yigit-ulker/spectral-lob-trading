import asyncio
import websockets
import json
import csv
import os
import time
from datetime import datetime
import requests
import sys

# Yolu ekle ki features modullerini gorebilsin
sys.path.append(os.path.abspath(os.path.dirname(os.path.dirname(__file__))))
from features.orderbook_features import calculate_obi
from features.cvd_features import CVDTracker
from features.smc_features import SMCAnalyzer
from rich.console import Console
from rich.table import Table
from rich.live import Live

# 15 Altin Coin (Sniper Listesi)
SYMBOLS = "MANAUSDT,MAGICUSDT,TIAUSDT,SOLUSDT,ZECUSDT,AVAXUSDT,AAVEUSDT,OPUSDT,TRBUSDT,ARBUSDT,ORDIUSDT,ARUSDT,FILUSDT,KAVAUSDT,CFXUSDT".split(',')

# Hafizalar
cvd_trackers = {s: CVDTracker(window_seconds=60) for s in SYMBOLS}
smc_5m = {s: SMCAnalyzer(max_candles=30) for s in SYMBOLS}
smc_3m = {s: SMCAnalyzer(max_candles=30) for s in SYMBOLS}
market_states = {s: {'Fiyat': 0.0, 'Macro_OBI': 0.0, 'CVD': 0.0, 'SMC_Durumu': 'NEUTRAL', 'Sinyal': '⚪ BEKLE'} for s in SYMBOLS}
last_signal_time = {s: 0 for s in SYMBOLS}

# Log Dosyasi
os.makedirs('logs', exist_ok=True)
date_str = datetime.now().strftime("%Y-%m-%d")
csv_file = f'logs/smc_signals_{date_str}.csv'
file_exists = os.path.isfile(csv_file)
with open(csv_file, mode='a', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    if not file_exists:
        writer.writerow(['Zaman', 'Sembol', 'Fiyat', 'Macro_OBI', 'CVD_1m', 'SMC_Context', 'Sinyal_Yonu'])

def init_smc_engines():
    """Bot baslamadan once son 30 mumu API'den cekip motoru isitir"""
    print("🧠 SMC Motorlari (3m ve 5m) Gecmis Likidite Verileriyle Isitiliyor...")
    for s in SYMBOLS:
        try:
            r5 = requests.get(f"https://fapi.binance.com/fapi/v1/klines?symbol={s}&interval=5m&limit=30", timeout=5).json()
            for k in r5: smc_5m[s].add_candle(k[1], k[2], k[3], k[4], k[6])
            
            r3 = requests.get(f"https://fapi.binance.com/fapi/v1/klines?symbol={s}&interval=3m&limit=30", timeout=5).json()
            for k in r3: smc_3m[s].add_candle(k[1], k[2], k[3], k[4], k[6])
        except Exception as e:
            print(f"Hata {s}: {e}")
        time.sleep(0.05)

def generate_table():
    table = Table(title="🧠 V4 SMC + HFT (Akilli Para Keskin Nisancisi) 🧠", border_style="cyan")
    table.add_column("Sembol", justify="left", style="cyan", no_wrap=True)
    table.add_column("Fiyat", justify="right", style="magenta")
    table.add_column("Macro OBI", justify="right", style="yellow")
    table.add_column("CVD (1m)", justify="right", style="blue")
    table.add_column("SMC Likidite", justify="center", style="white")
    table.add_column("Sinyal", justify="center")

    for s in SYMBOLS:
        st = market_states[s]
        obi = st['Macro_OBI']
        obi_color = "green" if obi > 0 else "red" if obi < 0 else "white"
        
        cvd = st['CVD']
        cvd_color = "green" if cvd > 0 else "red" if cvd < 0 else "white"
        
        smc = st['SMC_Durumu']
        smc_color = "green bold" if smc == 'BULLISH_FVG' else "red bold" if smc == 'BEARISH_FVG' else "dim"
        
        sig = st['Sinyal']
        sig_color = "green bold" if "AL" in sig else "red bold" if "SAT" in sig else "dim white"
        
        table.add_row(
            s,
            f"{st['Fiyat']:.4f}",
            f"[{obi_color}]{obi:.4f}[/{obi_color}]",
            f"[{cvd_color}]{cvd:.2f}[/{cvd_color}]",
            f"[{smc_color}]{smc}[/{smc_color}]",
            f"[{sig_color}]{sig}[/{sig_color}]"
        )
    return table

async def binance_ws():
    init_smc_engines()
    
    streams = []
    for s in SYMBOLS:
        low_s = s.lower()
        streams.append(f"{low_s}@depth20@100ms")
        streams.append(f"{low_s}@trade")
        streams.append(f"{low_s}@kline_3m")
        streams.append(f"{low_s}@kline_5m")
        
    stream_str = "/".join(streams)
    url = f"wss://fstream.binance.com/stream?streams={stream_str}"
    
    console = Console()
    with Live(generate_table(), refresh_per_second=2, console=console) as live:
        while True:
            try:
                async with websockets.connect(url) as ws:
                    while True:
                        resp = await ws.recv()
                        data = json.loads(resp)
                        stream_name = data['stream']
                        msg = data['data']
                        
                        symbol = msg.get('s', '')
                        if symbol not in SYMBOLS: continue
                        
                        # 1. KLINE (SMC Guncellemesi)
                        if 'kline' in stream_name and msg['e'] == 'kline':
                            k = msg['k']
                            if k['x']: # Mum kapandiysa hafizaya al
                                if k['i'] == '5m':
                                    smc_5m[symbol].add_candle(k['o'], k['h'], k['l'], k['c'], k['T'])
                                elif k['i'] == '3m':
                                    smc_3m[symbol].add_candle(k['o'], k['h'], k['l'], k['c'], k['T'])
                                    
                        # 2. TRADE (CVD Guncellemesi)
                        elif msg.get('e') == 'trade':
                            price = float(msg['p'])
                            qty = float(msg['q'])
                            is_buyer = msg['m']
                            market_states[symbol]['Fiyat'] = price
                            cvd_trackers[symbol].add_trade(qty, is_buyer)
                            market_states[symbol]['CVD'] = cvd_trackers[symbol].get_cvd()
                            
                        # 3. DEPTH (OBI Guncellemesi ve Karar Ani)
                        elif msg.get('e') == 'depthUpdate':
                            bids = [[float(p), float(q)] for p, q in msg['b']]
                            asks = [[float(p), float(q)] for p, q in msg['a']]
                            obi, _, _ = calculate_obi(bids, asks)
                            
                            # Histerezis (Macro OBI)
                            market_states[symbol]['Macro_OBI'] = (market_states[symbol]['Macro_OBI'] * 0.95) + (obi * 0.05)
                            mac_obi = market_states[symbol]['Macro_OBI']
                            cvd_val = market_states[symbol]['CVD']
                            price_val = market_states[symbol]['Fiyat']
                            
                            # SMC Baglamini Kontrol Et (3m veya 5m)
                            ctx_5 = smc_5m[symbol].get_market_context(price_val)
                            ctx_3 = smc_3m[symbol].get_market_context(price_val)
                            
                            final_ctx = 'NEUTRAL'
                            if ctx_5 == 'BULLISH_FVG' or ctx_3 == 'BULLISH_FVG': final_ctx = 'BULLISH_FVG'
                            elif ctx_5 == 'BEARISH_FVG' or ctx_3 == 'BEARISH_FVG': final_ctx = 'BEARISH_FVG'
                            
                            market_states[symbol]['SMC_Durumu'] = final_ctx
                            
                            # SINYAL MANTIGI (HFT + SMC Kesisimi)
                            current_sig = market_states[symbol]['Sinyal']
                            new_sig = current_sig
                            
                            # LONG: OBI Sismis, CVD Pozitif VE Fiyat Bullish Boslukta
                            if mac_obi > 0.40 and cvd_val > 0 and final_ctx == 'BULLISH_FVG':
                                new_sig = '🟢 AL (LONG)'
                            # SHORT: OBI Cokmus, CVD Negatif VE Fiyat Bearish Boslukta
                            elif mac_obi < -0.40 and cvd_val < 0 and final_ctx == 'BEARISH_FVG':
                                new_sig = '🔴 SAT (SHORT)'
                            # BEKLE (Cikis Durumu): OBI Tersine Donduyse
                            elif (mac_obi < -0.15 and current_sig == '🟢 AL (LONG)') or (mac_obi > 0.15 and current_sig == '🔴 SAT (SHORT)'):
                                new_sig = '⚪ BEKLE'
                                
                            market_states[symbol]['Sinyal'] = new_sig
                            live.update(generate_table())
                            
                            # Loglama (Sadece Sinyal Degisirse Kaydet)
                            now = time.time()
                            if new_sig != current_sig and (now - last_signal_time[symbol] > 5):
                                last_signal_time[symbol] = now
                                dt_str = datetime.fromtimestamp(now).strftime('%Y-%m-%d %H:%M:%S')
                                with open(csv_file, mode='a', newline='', encoding='utf-8') as f:
                                    csv.writer(f).writerow([dt_str, symbol, price_val, mac_obi, cvd_val, final_ctx, new_sig])
                                    
            except Exception as e:
                time.sleep(3) # Baglanti koparsa bekle ve yeniden baglan

if __name__ == "__main__":
    asyncio.run(binance_ws())
