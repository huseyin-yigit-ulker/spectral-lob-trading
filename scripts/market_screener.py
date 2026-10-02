import requests
import time
import json
import os
import sys
from datetime import datetime

# SMC Ozelliklerini İceri Aktar
sys.path.append(os.path.abspath(os.path.dirname(os.path.dirname(__file__))))
from features.smc_features import SMCAnalyzer

DATA_DIR = 'data'
os.makedirs(DATA_DIR, exist_ok=True)
OUTPUT_FILE = os.path.join(DATA_DIR, 'active_screener.json')

def get_all_usdt_futures():
    res = requests.get("https://fapi.binance.com/fapi/v1/exchangeInfo").json()
    symbols = []
    for s in res['symbols']:
        if s['quoteAsset'] == 'USDT' and s['contractType'] == 'PERPETUAL' and s['status'] == 'TRADING':
            symbols.append(s['symbol'])
    return symbols

def get_spreads_and_volumes():
    book_res = requests.get("https://fapi.binance.com/fapi/v1/ticker/bookTicker").json()
    spreads = {}
    for b in book_res:
        if 'USDT' in b['symbol']:
            bp, ap = float(b['bidPrice']), float(b['askPrice'])
            if bp > 0:
                spreads[b['symbol']] = ((ap - bp) / bp) * 100

    ticker_res = requests.get("https://fapi.binance.com/fapi/v1/ticker/24hr").json()
    metrics = {}
    for t in ticker_res:
        if 'USDT' in t['symbol']:
            metrics[t['symbol']] = {'volume_24h': float(t['quoteVolume']), 'price': float(t['lastPrice'])}
            
    return spreads, metrics

def get_fvg_proximity(symbol, current_price):
    try:
        r5 = requests.get(f"https://fapi.binance.com/fapi/v1/klines?symbol={symbol}&interval=5m&limit=30", timeout=3).json()
        smc5 = SMCAnalyzer(max_candles=30)
        for k in r5: smc5.add_candle(k[1], k[2], k[3], k[4], k[6])
        
        r3 = requests.get(f"https://fapi.binance.com/fapi/v1/klines?symbol={symbol}&interval=3m&limit=30", timeout=3).json()
        smc3 = SMCAnalyzer(max_candles=30)
        for k in r3: smc3.add_candle(k[1], k[2], k[3], k[4], k[6])
        
        min_dist = 999.0
        for fvg in smc5.active_fvgs + smc3.active_fvgs:
            if fvg['bottom'] <= current_price <= fvg['top']:
                return 0.0 # FVG icinde
            
            dist_top = abs(current_price - fvg['top']) / current_price * 100
            dist_bot = abs(current_price - fvg['bottom']) / current_price * 100
            min_dist = min(min_dist, dist_top, dist_bot)
            
        return min_dist
    except Exception as e:
        return 999.0

def run_screener():
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Dinamik Screener Taramasi Basliyor...")
    symbols = get_all_usdt_futures()
    spreads, metrics = get_spreads_and_volumes()
    
    candidates = []
    for sym in symbols:
        if sym not in spreads or sym not in metrics: continue
        spread = spreads[sym]
        vol = metrics[sym]['volume_24h']
        price = metrics[sym]['price']
        
        # KATI FILTRE: Hacim 50M Altiysa veya Spread %0.06 Uzeriyse cope at
        if spread > 0.06 or vol < 50000000:
            continue
        candidates.append({'symbol': sym, 'spread': spread, 'price': price, 'vol': vol})
        
    print(f"Asama 1: Spread ve Hacim testini gecen 'Kaliteli' Coin sayisi: {len(candidates)}")
    print("Asama 2: SMC Yaklasim (Proximity) Skorlari analiz ediliyor... (~10-15 saniye)")
    
    scored_candidates = []
    for cand in candidates:
        dist = get_fvg_proximity(cand['symbol'], cand['price'])
        
        # Puanlama Algoritmasi
        score = (cand['vol'] / 100000000) # Hacim katkisi
        if dist == 0.0: score += 200     # Fiyat su an likidite boslugunda!
        elif dist <= 0.5: score += 100   # Bosluga girmek uzere! (Cok yakin)
        elif dist <= 1.0: score += 50    # Yakin sayilir
            
        cand['fvg_dist'] = dist
        cand['score'] = score
        scored_candidates.append(cand)
        time.sleep(0.02) # API Engeli Yememek Icin
        
    scored_candidates.sort(key=lambda x: x['score'], reverse=True)
    top_15 = scored_candidates[:15]
    
    print("\n--- SECILEN TOP 15 SMC PUSU COINI ---")
    top_symbols = []
    for rank, c in enumerate(top_15):
        print(f"{rank+1}. {c['symbol']} | Skor: {c['score']:.1f} | FVG Mesafe: %{c['fvg_dist']:.2f} | Spread: %{c['spread']:.3f}")
        top_symbols.append(c['symbol'])
        
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump({"updated_at": time.time(), "symbols": top_symbols}, f)
        
    print(f"\n[OK] Yeni liste '{OUTPUT_FILE}' dosyasina asenkron olarak yazildi.")
    print("Siradaki tarama 15 dakika sonra otomatik baslayacak...")

if __name__ == "__main__":
    while True:
        try:
            run_screener()
        except Exception as e:
            print(f"Screener Hatasi: {e}")
        time.sleep(900)
