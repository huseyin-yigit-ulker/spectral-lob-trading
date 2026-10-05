import requests
import time
import json
import csv
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from utils.database import log_screener_to_supabase
except ImportError:
    log_screener_to_supabase = None
from datetime import datetime
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
    # KARA LISTE (Blacklist): HFT botlari icin zehirli olan coinler
    BLACKLIST = ['PAXGUSDT', 'XAUTUSDT', 'PUMPUSDT', 'BTCDOMUSDT', 'USDCUSDT']
    for sym in symbols:
        if sym not in spreads or sym not in metrics: continue
        spread = spreads[sym]
        vol = metrics[sym]['volume_24h']
        price = metrics[sym]['price']
        
        # KATI FILTRE: Hacim 50M Altiysa veya Spread %0.06 Uzeriyse cope at
        # Kara listeye takilan coinleri ele
        if sym in BLACKLIST:
            continue

        if spread > 0.06 or vol < 50000000:
            continue
        candidates.append({'symbol': sym, 'spread': spread, 'price': price, 'vol': vol})
        
    print(f"Asama 1: Spread ve Hacim testini gecen 'Kaliteli' Coin sayisi: {len(candidates)}")
    print("Asama 2: SMC Yaklasim (Proximity) Skorlari analiz ediliyor... (~10-15 saniye)")
    
    scored_candidates = []
    # KARA LISTE (Blacklist): HFT botlari icin zehirli olan coinler
    BLACKLIST = ['PAXGUSDT', 'XAUTUSDT', 'PUMPUSDT', 'BTCDOMUSDT', 'USDCUSDT']
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
    # Dinamik Esik (Threshold): Sadece FVG'ye %1.5 veya daha yakin olanlari al!
    threshold_candidates = [c for c in scored_candidates if c['fvg_dist'] <= 1.5]
    # WS guvenligi icin ust limit 40
    threshold_candidates = threshold_candidates[:40]
    
    print(f"\n--- DINAMIK ESIK: FVG'YE YAKIN {len(threshold_candidates)} COIN BULUNDU ---")
    top_symbols = []
    for rank, c in enumerate(threshold_candidates):
    
        print(f"{rank+1}. {c['symbol']} | Skor: {c['score']:.1f} | FVG Mesafe: %{c['fvg_dist']:.2f} | Spread: %{c['spread']:.3f}")
        top_symbols.append(c['symbol'])
        
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump({"updated_at": time.time(), "symbols": top_symbols}, f)
        
    # --- YENI: BACKTEST ICIN SCREENER TARIHCESINI LOGLA ---
    os.makedirs('logs', exist_ok=True)
    date_str = datetime.utcnow().strftime("%Y-%m-%d")
    log_time = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    history_file = f'logs/screener_history_{date_str}.csv'
    
    file_exists = os.path.isfile(history_file)
    with open(history_file, mode='a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(['Zaman', 'Sembol', 'Fiyat', 'Hacim', 'Spread', 'FVG_Mesafe_Yuzde', 'Skor', 'Durum'])
        for c in scored_candidates:
            durum = 'KABUL' if c['symbol'] in top_symbols else 'RED'
            writer.writerow([log_time, c['symbol'], c['price'], c['vol'], c['spread'], c['fvg_dist'], c['score'], durum])
            if log_screener_to_supabase:
                log_screener_to_supabase(log_time, c['symbol'], c['price'], c['vol'], c['spread'], c['fvg_dist'], c['score'], durum)
        
    print(f"\n[OK] Yeni liste '{OUTPUT_FILE}' dosyasina asenkron olarak yazildi.")
    print("Siradaki tarama 15 dakika sonra otomatik baslayacak...")

if __name__ == "__main__":
    while True:
        try:
            run_screener()
        except Exception as e:
            print(f"Screener Hatasi: {e}")
            
        # Bir sonraki 15 dakikalik tam dilime (00, 15, 30, 45) kadar bekle
        now_ts = time.time()
        period_secs = 900 # 15 dakika
        next_period_ts = ((now_ts // period_secs) + 1) * period_secs
        sleep_secs = next_period_ts - now_ts
        
        next_run_str = datetime.fromtimestamp(next_period_ts).strftime('%H:%M:%00')
        print(f"\nBekleniyor... Siradaki tarama {next_run_str} (kalan: {int(sleep_secs)} saniye)")
        time.sleep(sleep_secs)
