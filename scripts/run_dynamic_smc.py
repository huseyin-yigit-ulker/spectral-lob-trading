import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from utils.notifier import send_telegram_message
    from utils.database import log_trade_to_supabase, update_live_metrics, get_supabase_conn
except ImportError:
    send_telegram_message = None
    log_trade_to_supabase = None
    update_live_metrics = None
    get_supabase_conn = None
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
from features.frequency_features import LOBSpectralAnalyzer
from rich.console import Console
from rich.table import Table
from rich.live import Live
from utils.btc_regime import get_btc_regime, is_trade_allowed_by_btc

# Log Dosyasi Kaldirildi (Sadece DB)

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
        self.entry_price = 0.0
        self.highest_pnl = 0.0
        self.active_trade_sl = None
        self.emergency_sl = None
        self.is_break_even = False
        self.fvg_depth_pct = 0.0
        self.last_signal_text = "[!] BEKLE"
        self.last_signal_color = "gray"
        self.last_log_time = 0
        self.smc_5m = SMCAnalyzer(max_candles=30)
        self.smc_3m = SMCAnalyzer(max_candles=30)
        self.spectral_analyzer = LOBSpectralAnalyzer(window_size=128, sample_rate_hz=10.0)
        self.rlr = 1.0
        self.bsi = 0.0
        self.clean_obi = 0.0
        self.spectral_state = "ISINIYOR"
        self.adx_5m = 25.0
        self.btc_regime = "NEUTRAL"
        self.entry_reason = ""
        self.exit_reason = ""
        self.is_sniper = False
        self.entry_time = 0.0
        self.last_exit_time = 0.0

def format_price(p):
    """
    Kripto fiyatlarini sembole/büyüklüğe göre dinamik ve temiz formatlar.
    Gereksiz son sıfırları temizler, virgülden sonraki basamakları korur.
    """
    if p is None or p == "" or p == "Belirleniyor":
        return "Belirleniyor"
    try:
        p = float(p)
    except (ValueError, TypeError):
        return str(p)
    if p == 0:
        return "0.00"
    abs_p = abs(p)
    if abs_p >= 1000:
        return f"{p:,.2f}"
    elif abs_p >= 1:
        s = f"{p:.4f}".rstrip('0')
        if s.endswith('.'):
            s += "00"
        elif len(s.split('.')[1]) == 1:
            s += "0"
        return s
    elif abs_p >= 0.01:
        s = f"{p:.6f}".rstrip('0')
        if s.endswith('.'):
            s += "0000"
        elif len(s.split('.')[1]) < 4:
            s += "0" * (4 - len(s.split('.')[1]))
        return s
    else:
        s = f"{p:.8f}".rstrip('0')
        if s.endswith('.'):
            s += "00"
        return s

def sync_signal_state(agent, prev_sig):
    if agent.internal_signal_state == 1:
        agent.last_signal_text = "[+] AL (LONG)"
        agent.last_signal_color = "green bold"
    elif agent.internal_signal_state == -1:
        agent.last_signal_text = "[-] SAT (SHORT)"
        agent.last_signal_color = "red bold"
    else:
        agent.last_signal_text = "[!] BEKLE"
        agent.last_signal_color = "gray"

    if agent.internal_signal_state != prev_sig:
        agent.last_log_time = time.time()
        dt_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        b5, t5 = agent.smc_5m.get_active_fvg_bounds(agent.current_price)
        b3, t3 = agent.smc_3m.get_active_fvg_bounds(agent.current_price)
        f_b = b5 if b5 else (b3 if b3 else 0.0)
        f_t = t5 if t5 else (t3 if t3 else 0.0)
        f_depth = ((f_t - f_b) / f_b * 100) if f_b > 0 else 0.0
        
        # SUPABASE VE TELEGRAM ENTEGRASYONU
        if log_trade_to_supabase:
            reason_to_log = agent.exit_reason if agent.internal_signal_state == 0 else agent.entry_reason
            logged_price = agent.current_price if (agent.current_price and agent.current_price > 0) else (agent.emergency_sl if (getattr(agent, 'emergency_sl', None) and agent.emergency_sl > 0) else agent.entry_price)
            log_trade_to_supabase(
                dt_str, agent.symbol, logged_price, agent.macro_obi, agent.cvd_1m, 
                agent.smc_status, agent.last_signal_text, f_t, f_b, round(f_depth, 4),
                round(agent.rlr, 3), round(agent.bsi, 3), round(agent.clean_obi, 4),
                agent.btc_regime, reason_to_log
            )
            
        if send_telegram_message:
            if agent.internal_signal_state in (1, -1):
                is_long = agent.internal_signal_state == 1
                dir_str = "LONG (AL)" if is_long else "SHORT (SAT)"
                dir_emoji = "🟢" if is_long else "🔴"
                sniper_line = "🎯 <b>ÖZEL MOD: SNİPER İSTİSNASI (BTC'den Bağımsız Pozitif Ayrışma)</b>\n" if agent.is_sniper else ""
                btc_emoji = "🟢" if agent.btc_regime == "BULLISH" else ("🔴" if agent.btc_regime == "BEARISH" else "⚪")
                
                sl_text = format_price(agent.active_trade_sl) if agent.active_trade_sl else "Belirleniyor"
                em_text = format_price(agent.emergency_sl) if agent.emergency_sl else "Belirleniyor"
                entry_text = format_price(agent.current_price)

                msg = (
                    f"⚡ <b>SMC V5.5 YENİ İŞLEM AÇILDI</b>\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n"
                    f"{sniper_line}"
                    f"🪙 <b>Sembol:</b> #{agent.symbol}\n"
                    f"{dir_emoji} <b>Yön:</b> <b>{dir_str}</b>\n"
                    f"💵 <b>Giriş Fiyatı:</b> <code>{entry_text}</code>\n"
                    f"🛡️ <b>Teknik SL:</b> <code>{sl_text}</code>\n"
                    f"🚨 <b>Acil Hard Stop:</b> <code>{em_text}</code>\n\n"
                    f"📊 <b>Piyasa & Giriş Nedeni:</b>\n"
                    f"• <b>BTC Makro:</b> {btc_emoji} {agent.btc_regime}\n"
                    f"• <b>Karar Nedeni:</b> {agent.entry_reason or 'Mikro Akış Onayı'}\n\n"
                    f"🔬 <b>SMC & LOB Metrikleri:</b>\n"
                    f"• <b>SMC Yapı:</b> {agent.smc_status} (FVG: %{agent.fvg_depth_pct:.2f})\n"
                    f"• <b>Macro OBI:</b> {agent.macro_obi:+.3f} | <b>Clean OBI:</b> {agent.clean_obi:+.3f}\n"
                    f"• <b>CVD (1m):</b> {agent.cvd_1m:+.2f}\n"
                    f"• <b>Spektrum:</b> {agent.spectral_state} (RLR: %{agent.rlr*100:.0f}, BSI: {agent.bsi:.2f})\n"
                    f"━━━━━━━━━━━━━━━━━━━━"
                )
            else:
                # İşlem Kapandı (BEKLE)
                entry_p = agent.entry_price
                if entry_p <= 0:
                    try:
                        open_pos = get_open_positions_from_db()
                        if agent.symbol in open_pos:
                            entry_p = open_pos[agent.symbol].get('entry_price', 0.0)
                    except Exception:
                        pass

                if entry_p > 0:
                    if prev_sig == 1:
                        pnl_val = ((agent.current_price - entry_p) / entry_p) * 100
                    else:
                        pnl_val = ((entry_p - agent.current_price) / entry_p) * 100
                else:
                    pnl_val = 0.0

                if pnl_val > 0.0001:
                    pnl_emoji = "🟢 KÂR"
                elif pnl_val < -0.0001:
                    pnl_emoji = "🔴 ZARAR"
                else:
                    pnl_emoji = "⚪ BAŞABAŞ"
                
                exit_price_str = format_price(agent.current_price)
                entry_price_str = format_price(entry_p) if entry_p > 0 else "Bilinmiyor"
                reason_str = agent.exit_reason if agent.exit_reason else "Sinyal Sonu"

                msg = (
                    f"🏁 <b>SMC V5.5 İŞLEM KAPANDI</b>\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n"
                    f"🪙 <b>Sembol:</b> #{agent.symbol}\n"
                    f"💵 <b>Çıkış Fiyatı:</b> <code>{exit_price_str}</code> (Giriş: <code>{entry_price_str}</code>)\n"
                    f"💰 <b>Net PnL:</b> {pnl_emoji} <b>%{pnl_val:+.2f}</b>\n"
                    f"🛑 <b>Kapanış Nedeni:</b> {reason_str}\n"
                    f"📊 <b>Giriş Tipi:</b> {'🎯 Sniper İstisnası' if agent.is_sniper else 'BTC Uyumlu Trend'}\n"
                    f"━━━━━━━━━━━━━━━━━━━━"
                )
            try:
                send_telegram_message(msg)
            except Exception as e:
                pass

        # İşlem kapandıysa pozisyon değişkenlerini telegram ve supabase bildiriminden SONRA sıfırla
        if agent.internal_signal_state == 0 and prev_sig != 0:
            agent.last_exit_time = time.time()
            agent.entry_price = 0.0
            agent.entry_time = 0.0
            agent.active_trade_sl = None
            agent.emergency_sl = None
            agent.highest_pnl = 0.0
            agent.is_break_even = False
            agent.exit_reason = ""

agents = {}
current_symbols = []
SCREENER_FILE = 'data/active_screener.json'
last_screener_mtime = 0

def get_open_positions_from_db():
    if not get_supabase_conn:
        return {}
    conn = get_supabase_conn()
    if not conn:
        return {}
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, zaman, sembol, fiyat, sinyal, fvg_top, fvg_bottom, fvg_depth, COALESCE(btc_regime, 'NEUTRAL'), COALESCE(entry_reason, '')
                FROM quant_v5.trade_logs
                ORDER BY id ASC;
            """)
            rows = cur.fetchall()
            
        open_pos = {}
        for r in rows:
            _id, zaman, sym, fiyat, sinyal, f_top, f_bot, f_depth, btc_reg, ent_reas = r
            if ('AL' in sinyal or 'SAT' in sinyal) and ('BEKLE' not in sinyal):
                open_pos[sym] = {
                    'id': _id,
                    'zaman': zaman,
                    'direction': 1 if ('AL' in sinyal or 'LONG' in sinyal) else -1,
                    'entry_price': float(fiyat),
                    'fvg_top': float(f_top or 0),
                    'fvg_bottom': float(f_bot or 0),
                    'fvg_depth': float(f_depth or 0),
                    'signal_text': sinyal,
                    'btc_regime': str(btc_reg or 'NEUTRAL'),
                    'entry_reason': str(ent_reas or '')
                }
            elif 'BEKLE' in sinyal and sym in open_pos:
                del open_pos[sym]
        return open_pos
    except Exception as e:
        return {}
    finally:
        try: conn.close()
        except: pass

def update_agents_from_screener():
    global current_symbols, last_screener_mtime
    if not os.path.exists(SCREENER_FILE): return False
    
    # 1. DB'den açık pozisyonları çek (State Persistence)
    open_positions = get_open_positions_from_db()

    mtime = os.path.getmtime(SCREENER_FILE)
    screener_changed = (mtime != last_screener_mtime)
    has_missing_open_pos = any(s not in agents for s in open_positions)
    
    # Eger screener degismediyse, eksik acik pozisyon da yoksa ve agents doluysa devam et
    if not screener_changed and not has_missing_open_pos and len(agents) > 0:
        return False
        
    last_screener_mtime = mtime
    
    try:
        with open(SCREENER_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            screener_symbols = data.get('symbols', [])
            
            # Açık pozisyonlu sembolleri listeye ZORUNLU olarak dahil et
            merged_symbols = list(screener_symbols)
            for open_sym in open_positions:
                if open_sym not in merged_symbols:
                    merged_symbols.append(open_sym)
            
            if not merged_symbols: return False
            
            # Yeni eklenenleri isit
            for s in merged_symbols:
                if s not in agents:
                    agents[s] = SMCAgent(s)
                    
                    # Eğer bu coin veritabanında zaten açık bir işlemse hafızasını ve SL'ini geri yükle!
                    if s in open_positions:
                        pos_info = open_positions[s]
                        agents[s].internal_signal_state = pos_info['direction']
                        agents[s].entry_price = pos_info['entry_price']
                        agents[s].last_signal_text = pos_info['signal_text']
                        agents[s].last_signal_color = "green bold" if pos_info['direction'] == 1 else "red bold"
                        agents[s].btc_regime = pos_info.get('btc_regime', 'NEUTRAL')
                        agents[s].entry_reason = pos_info.get('entry_reason', '')
                        agents[s].is_sniper = 'Sniper' in agents[s].entry_reason
                        
                        top_b = pos_info['fvg_top']
                        bot_b = pos_info['fvg_bottom']
                        if pos_info['direction'] == 1:
                            agents[s].active_trade_sl = (bot_b * 0.9980) if bot_b > 0 else (agents[s].entry_price * 0.9980)
                            agents[s].emergency_sl = agents[s].entry_price * 0.9900
                        else:
                            agents[s].active_trade_sl = (top_b * 1.0020) if top_b > 0 else (agents[s].entry_price * 1.0020)
                            agents[s].emergency_sl = agents[s].entry_price * 1.0100
                            
                    try:
                        r5 = requests.get(f"https://fapi.binance.com/fapi/v1/klines?symbol={s}&interval=5m&limit=30", timeout=3).json()
                        for k in r5: agents[s].smc_5m.add_candle(k[1], k[2], k[3], k[4], k[6])
                        r3 = requests.get(f"https://fapi.binance.com/fapi/v1/klines?symbol={s}&interval=3m&limit=30", timeout=3).json()
                        for k in r3: agents[s].smc_3m.add_candle(k[1], k[2], k[3], k[4], k[6])
                    except: pass
                    
            # Listeden dusenleri temizle (AMA acik pozisyonu olanlari ASLA silme!)
            to_remove = [s for s in agents if s not in merged_symbols]
            for s in to_remove:
                if agents[s].internal_signal_state != 0 or s in open_positions:
                    # Islem acik, silme ve websocket'te dinlemeye devam et (Zombi modu)
                    merged_symbols.append(s)
                else:
                    del agents[s]
                
            current_symbols = merged_symbols
            return True
    except:
        return False

def generate_table():
    btc_info = get_btc_regime()
    btc_summary = btc_info.get('summary', 'BTC: Yükleniyor...')
    badge_color = btc_info.get('badge_color', 'white')

    table = Table(
        title=f"Dinamik V5.3 LOB Spectral Terminal | BTC: [{badge_color}]{btc_summary}[/{badge_color}]",
        border_style="cyan"
    )
    table.add_column("Sembol", justify="left", style="cyan", no_wrap=True)
    table.add_column("Fiyat", justify="right", style="magenta")
    table.add_column("Doluluk", justify="center", style="white")
    table.add_column("Macro OBI", justify="right", style="yellow")
    table.add_column("CVD (1m)", justify="right", style="blue")
    table.add_column("FVG Derinlik", justify="right", style="cyan")
    table.add_column("LOB Spektrum", justify="center")
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
        
        spec_color = "green" if agent.spectral_state == 'ORGANIC' else "red bold" if agent.spectral_state == 'SPOOFING_ALERT' else "yellow" if agent.spectral_state == 'HFT_NOISE' else "dim white"
        spec_text = f"[{spec_color}]{agent.spectral_state} (%{agent.rlr*100:.0f})[/{spec_color}]"

        table.add_row(
            agent.symbol,
            f"{agent.current_price:.6f}",
            f"% {(len(agent.obi_buffer)/600)*100:.0f}",
            f"[{obi_color}]{obi:+.4f}[/{obi_color}]",
            f"[{cvd_color}]{cvd:+.2f}[/{cvd_color}]",
            f"[{ 'green' if agent.fvg_depth_pct >= 0.10 else 'red' }]% {agent.fvg_depth_pct:.2f}[/]",
            spec_text,
            f"[{smc_color}]{smc}[/{smc_color}]",
            f"[{agent.last_signal_color}]{agent.last_signal_text}[/{agent.last_signal_color}]"
        )
    return table

async def periodic_db_metrics_sync():
    """
    Periyodik olarak (10 saniyede bir) live_metrics tablosuna yazar.
    Sadece coinlerin durumlarinda (SMC durumu / FVG derinligi / Spektral metrikler)
    gercek bir degisiklik varsa Supabase'e sorgu atar. Boylece gereksiz Log Ingestion onlenir.
    """
    last_synced_states = {}
    while True:
        try:
            await asyncio.sleep(10)
            if not update_live_metrics or not current_symbols:
                continue
                
            states_dict = {}
            for s in current_symbols:
                if s in agents and agents[s].current_price > 0:
                    states_dict[s.lower()] = {
                        'smc_status': agents[s].smc_status,
                        'fvg_depth': round(agents[s].fvg_depth_pct, 4),
                        'rlr': round(agents[s].rlr, 3),
                        'bsi': round(agents[s].bsi, 3),
                        'clean_obi': round(agents[s].clean_obi, 4)
                    }
                    
            # BTC Piyasa Rejimini de live_metrics'e ekle
            btc_info = get_btc_regime()
            states_dict['_btc_'] = {
                'smc_status': btc_info.get('regime', 'NEUTRAL'),
                'fvg_depth': round(btc_info.get('btc_price', 0.0), 2),
                'rlr': 1.0,
                'bsi': 0.0,
                'clean_obi': 0.0
            }
                    
            if states_dict and states_dict != last_synced_states:
                loop = asyncio.get_running_loop()
                await loop.run_in_executor(None, update_live_metrics, states_dict)
                last_synced_states = states_dict
        except asyncio.CancelledError:
            break
        except Exception as e:
            pass

async def binance_ws():
    console = Console()
    sync_task = asyncio.create_task(periodic_db_metrics_sync())
    last_table_render = 0
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
                streams.extend([f"{ls}@depth20@100ms", f"{ls}@trade", f"{ls}@kline_1m", f"{ls}@kline_3m", f"{ls}@kline_5m"])
                
            stream_str = "/".join(streams)
            url = f"wss://fstream.binance.com/stream?streams={stream_str}"
            
            next_check_time = time.time() + 15
            
            try:
                async with websockets.connect(url, ping_interval=20, ping_timeout=60, max_size=None) as ws:
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
                                elif k['i'] == '1m':
                                    close_p = float(k['c'])
                                    prev_sig = agent.internal_signal_state
                                    # 1 Dakikalık Mum Kapanışı Onaylı SL / Trailing Çıkışı (Backtest ile Birebir Uyumlu)
                                    # Mikro tik gürültüsüyle saniyelik komisyon erimelerini engeller, 1m kapanışı teyit eder
                                    if agent.internal_signal_state == 1 and agent.active_trade_sl and close_p <= agent.active_trade_sl:
                                        agent.internal_signal_state = 0
                                        agent.exit_reason = "🎯 Trailing Stop (Kâr Koruma)" if agent.is_break_even else "Teknik Stop-Loss (1m Mum Kapanışı)"
                                        sync_signal_state(agent, prev_sig)
                                    elif agent.internal_signal_state == -1 and agent.active_trade_sl and close_p >= agent.active_trade_sl:
                                        agent.internal_signal_state = 0
                                        agent.exit_reason = "🎯 Trailing Stop (Kâr Koruma)" if agent.is_break_even else "Teknik Stop-Loss (1m Mum Kapanışı)"
                                        sync_signal_state(agent, prev_sig)
                        
                        elif msg.get('e') == 'trade':
                            agent.current_price = float(msg['p'])
                            agent.latest_time = msg['T']
                            agent.state_builder.cvd_features.add_trade(agent.latest_time, agent.current_price, float(msg['q']), msg['m'])
                            
                            # Pozisyondaysak Anlık PnL, Break-Even ve Trailing Takibi
                            if agent.internal_signal_state != 0 and agent.entry_price > 0:
                                cur_pnl = ((agent.current_price - agent.entry_price) / agent.entry_price * 100) if agent.internal_signal_state == 1 else ((agent.entry_price - agent.current_price) / agent.entry_price * 100)
                                if cur_pnl > agent.highest_pnl:
                                    agent.highest_pnl = cur_pnl
                                
                                # Break-Even (@ %0.45 kâr görüldüğünde SL'i başa başa çek)
                                if agent.highest_pnl >= 0.45:
                                    agent.is_break_even = True
                                    if agent.internal_signal_state == 1:
                                        agent.active_trade_sl = max(agent.active_trade_sl or 0, agent.entry_price * 1.0005)
                                    else:
                                        agent.active_trade_sl = min(agent.active_trade_sl or 999999, agent.entry_price * 0.9995)
                                
                                # Trailing Stop (@ %0.50+ kâr ve zirveden %0.25 çekilme)
                                if agent.highest_pnl >= 0.50:
                                    if agent.internal_signal_state == 1:
                                        trail_sl = agent.entry_price * (1.0 + (agent.highest_pnl - 0.25) / 100)
                                        agent.active_trade_sl = max(agent.active_trade_sl or 0, trail_sl)
                                    else:
                                        trail_sl = agent.entry_price * (1.0 - (agent.highest_pnl - 0.25) / 100)
                                        agent.active_trade_sl = min(agent.active_trade_sl or 999999, trail_sl)
                                
                                # Acil Hard Stop (%0.70): Ani çöküş / sert manipülasyonlara karşı anında tik seviyesinde korur
                                prev_sig = agent.internal_signal_state
                                if agent.internal_signal_state == 1 and agent.emergency_sl and agent.current_price > 0 and agent.current_price <= agent.emergency_sl:
                                    agent.internal_signal_state = 0
                                    agent.exit_reason = "🚨 Acil Hard Stop (%0.70)"
                                    sync_signal_state(agent, prev_sig)
                                elif agent.internal_signal_state == -1 and agent.emergency_sl and agent.current_price > 0 and agent.current_price >= agent.emergency_sl:
                                    agent.internal_signal_state = 0
                                    agent.exit_reason = "🚨 Acil Hard Stop (%0.70)"
                                    sync_signal_state(agent, prev_sig)
                            
                        elif msg.get('e') == 'depthUpdate':
                            bids = [[float(p), float(q)] for p, q in msg['b']]
                            asks = [[float(p), float(q)] for p, q in msg['a']]
                            b_qty = sum(b[1] for b in bids[:5]) if len(bids) >= 5 else sum(b[1] for b in bids)
                            a_qty = sum(a[1] for a in asks[:5]) if len(asks) >= 5 else sum(a[1] for a in asks)
                            raw_obi = (b_qty - a_qty) / (b_qty + a_qty + 1e-8)
                            agent.obi_buffer.append(raw_obi)
                            agent.macro_obi = sum(agent.obi_buffer) / len(agent.obi_buffer)
                            agent.spectral_analyzer.add_tick(raw_obi)
                            
                            if len(agent.obi_buffer) < 100: continue
                            if agent.current_price == 0.0: continue # Fiyat verisi henuz gelmediyse islem yapma
                            cvd_dict = agent.state_builder.cvd_features.get_multi_window_cvd(agent.latest_time)
                            agent.cvd_1m = cvd_dict.get('1m', 0.0)
                            
                            # LOB Frekans & Spektral Analiz
                            spec = agent.spectral_analyzer.analyze()
                            agent.rlr = spec['rlr']
                            agent.bsi = spec['bsi']
                            agent.clean_obi = spec['clean_obi']
                            agent.spectral_state = spec['state']

                            ctx_5 = agent.smc_5m.get_market_context(agent.current_price)
                            ctx_3 = agent.smc_3m.get_market_context(agent.current_price)
                            
                            if ctx_5 == 'BULLISH_FVG' or ctx_3 == 'BULLISH_FVG': agent.smc_status = 'BULLISH_FVG'
                            elif ctx_5 == 'BEARISH_FVG' or ctx_3 == 'BEARISH_FVG': agent.smc_status = 'BEARISH_FVG'
                            else: agent.smc_status = 'NEUTRAL'
                            
                            prev_sig = agent.internal_signal_state
                            
                            # FVG Derinlik (Boyutu) Kontrolu (%0.15 ile %1.50 arası; manipülatif aşırı FVG'leri eler)
                            b5, t5 = agent.smc_5m.get_active_fvg_bounds(agent.current_price)
                            b3, t3 = agent.smc_3m.get_active_fvg_bounds(agent.current_price)
                            cur_b = b5 if b5 else b3
                            cur_t = t5 if t5 else t3
                            fvg_depth_ratio = ((cur_t - cur_b) / cur_b) if cur_b else 0.0
                            agent.fvg_depth_pct = fvg_depth_ratio * 100
                            is_fvg_wide_enough = 0.0015 <= fvg_depth_ratio <= 0.0150 # %0.15 ile %1.50 arası
                            
                            # HFT Spoofing / Ghost Liquidity Tespiti
                            is_spoofed = (spec['state'] == 'SPOOFING_ALERT' or spec['bsi'] >= 0.40)
                            
                            # ADX Testere (Chop) Kalkanı: ADX < 18 ise piyasa yönsüzdür, sahte kırılımları engelle
                            agent.adx_5m = agent.smc_5m.get_adx()
                            is_choppy = agent.smc_5m.is_choppy(18.0)
                            
                            # Cooldown kontrolü: Aynı sembolde son çıkıştan sonra en az 3 dakika (180s) bekle
                            COOLDOWN_SECONDS = 180
                            is_in_cooldown = (time.time() - getattr(agent, 'last_exit_time', 0)) < COOLDOWN_SECONDS
                            
                            if agent.macro_obi > 0.30 and agent.cvd_1m > 0 and agent.smc_status == 'BULLISH_FVG' and is_fvg_wide_enough:
                                # 1. BTC Makro Trend Filtresi: BTC düşüşteyken altcoin LONG'unu engelle
                                allowed, btc_reason, is_sniper, btc_regime = is_trade_allowed_by_btc('LONG', agent.macro_obi, agent.fvg_depth_pct)
                                # 2. Arındırılmış OBI Teyidi
                                is_clean_confirmed = (spec['clean_obi'] >= 0.18 or not agent.spectral_analyzer.is_ready())
                                
                                if is_in_cooldown:
                                    pass # Sinyal bekletildi (Cooldown süresi devam ediyor)
                                elif not allowed:
                                    pass # Sinyal reddedildi (BTC trend engeli)
                                elif is_choppy:
                                    pass # Sinyal reddedildi (ADX < 18 Chop / Testere Piyasası Kalkanı)
                                elif is_spoofed:
                                    pass # Sinyal reddedildi (HFT Spoofing / Sahte Duvar)
                                elif not is_clean_confirmed:
                                    pass # Sinyal reddedildi (Arındırılmış gerçek OBI yetersiz)
                                elif agent.internal_signal_state == 0:
                                    agent.internal_signal_state = 1
                                    agent.entry_price = agent.current_price
                                    agent.entry_time = time.time()
                                    agent.highest_pnl = 0.0
                                    agent.is_break_even = False
                                    agent.btc_regime = btc_regime
                                    agent.entry_reason = btc_reason
                                    agent.is_sniper = is_sniper
                                    agent.exit_reason = ""
                                    b5, t5 = agent.smc_5m.get_active_fvg_bounds(agent.current_price)
                                    b3, t3 = agent.smc_3m.get_active_fvg_bounds(agent.current_price)
                                    bot_bound = b5 if b5 else b3
                                    if bot_bound:
                                        agent.active_trade_sl = bot_bound * 0.9980 # %0.20 Genişletilmiş SL
                                    else:
                                        agent.active_trade_sl = agent.entry_price * 0.9980
                                    agent.emergency_sl = agent.entry_price * 0.9930 # %0.70 Sıkılaştırılmış Acil Hard Stop
                            elif agent.macro_obi < -0.30 and agent.cvd_1m < 0 and agent.smc_status == 'BEARISH_FVG' and is_fvg_wide_enough:
                                # 1. BTC Makro Trend Filtresi: BTC yükselişteyken altcoin SHORT'unu engelle
                                allowed, btc_reason, is_sniper, btc_regime = is_trade_allowed_by_btc('SHORT', agent.macro_obi, agent.fvg_depth_pct)
                                # 2. Arındırılmış OBI Teyidi
                                is_clean_confirmed = (spec['clean_obi'] <= -0.18 or not agent.spectral_analyzer.is_ready())
                                
                                if is_in_cooldown:
                                    pass # Sinyal bekletildi (Cooldown süresi devam ediyor)
                                elif not allowed:
                                    pass # Sinyal reddedildi (BTC trend engeli)
                                elif is_choppy:
                                    pass # Sinyal reddedildi (ADX < 18 Chop / Testere Piyasası Kalkanı)
                                elif is_spoofed:
                                    pass # Sinyal reddedildi (HFT Spoofing / Sahte Duvar)
                                elif not is_clean_confirmed:
                                    pass # Sinyal reddedildi (Arındırılmış gerçek OBI yetersiz)
                                elif agent.internal_signal_state == 0:
                                    agent.internal_signal_state = -1
                                    agent.entry_price = agent.current_price
                                    agent.entry_time = time.time()
                                    agent.highest_pnl = 0.0
                                    agent.is_break_even = False
                                    agent.btc_regime = btc_regime
                                    agent.entry_reason = btc_reason
                                    agent.is_sniper = is_sniper
                                    agent.exit_reason = ""
                                    b5, t5 = agent.smc_5m.get_active_fvg_bounds(agent.current_price)
                                    b3, t3 = agent.smc_3m.get_active_fvg_bounds(agent.current_price)
                                    top_bound = t5 if t5 else t3
                                    if top_bound:
                                        agent.active_trade_sl = top_bound * 1.0020 # %0.20 Genişletilmiş SL
                                    else:
                                        agent.active_trade_sl = agent.entry_price * 1.0020
                                    agent.emergency_sl = agent.entry_price * 1.0070 # %0.70 Sıkılaştırılmış Acil Hard Stop
                                
                            # Pozisyondan Çıkış Kontrolleri (Acil Stop & Dinamik OBI Reversal)
                            # 1. Acil Hard Stop (%0.70): Zamana bakılmaksızın anında tetiklenir.
                            # 2. Minimum Hold Time (60 sn): Tahta (LOB) gürültüsüyle mikrosaniyede çıkışı engeller.
                            # 3. Kâr Koruma: Fiyat kâr bölgesindeyken OBI eşiği gevşetilmez (±0.35 korunur) ve CVD karşıt teyidi aranır.
                            MIN_HOLD_SECONDS = 60
                            time_in_pos = time.time() - getattr(agent, 'entry_time', 0) if getattr(agent, 'entry_time', 0) > 0 else 999
                            can_obi_exit = time_in_pos >= MIN_HOLD_SECONDS
                            
                            if agent.internal_signal_state == 1:
                                if agent.emergency_sl and agent.current_price > 0 and agent.current_price <= agent.emergency_sl:
                                    agent.internal_signal_state = 0
                                    agent.exit_reason = "🚨 Acil Hard Stop (%0.70)"
                                elif can_obi_exit:
                                    is_in_profit = agent.current_price > agent.entry_price
                                    obi_exit_threshold = -0.35 if (agent.smc_status == 'BULLISH_FVG' or is_in_profit) else -0.20
                                    if agent.macro_obi < obi_exit_threshold and agent.cvd_1m < 0:
                                        agent.internal_signal_state = 0
                                        agent.exit_reason = f"Dinamik OBI Karşıt Akış ({agent.macro_obi:+.2f})"
                            elif agent.internal_signal_state == -1:
                                if agent.emergency_sl and agent.current_price > 0 and agent.current_price >= agent.emergency_sl:
                                    agent.internal_signal_state = 0
                                    agent.exit_reason = "🚨 Acil Hard Stop (%0.70)"
                                elif can_obi_exit:
                                    is_in_profit = agent.current_price < agent.entry_price
                                    obi_exit_threshold = 0.35 if (agent.smc_status == 'BEARISH_FVG' or is_in_profit) else 0.20
                                    if agent.macro_obi > obi_exit_threshold and agent.cvd_1m > 0:
                                        agent.internal_signal_state = 0
                                        agent.exit_reason = f"Dinamik OBI Karşıt Akış ({agent.macro_obi:+.2f})"
                            
                            sync_signal_state(agent, prev_sig)
                            now_t = time.time()
                            if now_t - last_table_render >= 0.25:
                                live.update(generate_table())
                                last_table_render = now_t
            except Exception as e:
                time.sleep(2)

if __name__ == "__main__":
    asyncio.run(binance_ws())
