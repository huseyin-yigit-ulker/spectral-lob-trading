import time
import requests
import pandas as pd

class BTCRegimeWatcher:
    """
    Bitcoin (BTCUSDT) Yüksek Zaman Dilimi (1H & 4H) Piyasa Rejimi Takipçisi.
    Altcoinlerin BTC ile olan yüksek korelasyonundan (Beta) yararlanarak,
    BTC düşüş trendindeyken altcoin LONG'larını, yükseliş trendindeyken altcoin SHORT'larını filtreler.
    """
    def __init__(self, cache_ttl_seconds=60):
        self.cache_ttl = cache_ttl_seconds
        self.last_fetch_time = 0
        self.cached_state = {
            'regime': 'NEUTRAL',
            'btc_price': 0.0,
            'ema50_1h': 0.0,
            'ema200_1h': 0.0,
            'ema50_4h': 0.0,
            'allow_long': True,
            'allow_short': True,
            'summary': 'BTC: Yükleniyor...',
            'badge_color': 'gray'
        }

    def _fetch_klines(self, interval='1h', limit=100):
        url = f"https://fapi.binance.com/fapi/v1/klines?symbol=BTCUSDT&interval={interval}&limit={limit}"
        try:
            r = requests.get(url, timeout=4).json()
            if isinstance(r, list) and len(r) > 0:
                return r
        except Exception:
            pass

        # Spot fallback
        try:
            url_spot = f"https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval={interval}&limit={limit}"
            r_spot = requests.get(url_spot, timeout=4).json()
            if isinstance(r_spot, list) and len(r_spot) > 0:
                return r_spot
        except Exception:
            pass
        return []

    def get_regime(self, force_refresh=False) -> dict:
        now = time.time()
        if not force_refresh and (now - self.last_fetch_time < self.cache_ttl) and self.cached_state['btc_price'] > 0:
            return self.cached_state

        kl_1h = self._fetch_klines('1h', 100)
        kl_4h = self._fetch_klines('4h', 50)

        if not kl_1h:
            # API geçici yanıt vermezse eski durumu koru
            return self.cached_state

        try:
            # 1H Klines Analizi
            df_1h = pd.DataFrame(kl_1h)
            closes_1h = df_1h[4].astype(float)
            cur_price = closes_1h.iloc[-1]
            ema50_1h = closes_1h.ewm(span=50).mean().iloc[-1]
            ema200_1h = closes_1h.ewm(span=200).mean().iloc[-1]

            # 4H Klines Analizi
            ema50_4h = ema50_1h
            if kl_4h and len(kl_4h) > 20:
                df_4h = pd.DataFrame(kl_4h)
                closes_4h = df_4h[4].astype(float)
                ema50_4h = closes_4h.ewm(span=50).mean().iloc[-1]

            # Rejim Karar Motoru (Market Regime Logic)
            # Fiyat 1H EMA50'nin altındaysa ve 4H EMA50'nin de altındaysa veya EMA50 < EMA200 ise -> BEARISH
            # Fiyat 1H EMA50'nin üstündeyse ve 4H EMA50'nin de üstündeyse veya EMA50 > EMA200 ise -> BULLISH
            # Aksi halde -> NEUTRAL (Yatay / Karışık)
            is_1h_bear = cur_price < ema50_1h
            is_4h_bear = cur_price < ema50_4h
            is_1h_bull = cur_price > ema50_1h
            is_4h_bull = cur_price > ema50_4h

            if is_1h_bear and (is_4h_bear or ema50_1h < ema200_1h):
                regime = 'BEARISH'
                allow_long = False
                allow_short = True
                badge_color = 'red bold'
                summary = f"🔴 BEARISH (${cur_price:,.0f} < EMA50: ${ema50_1h:,.0f}) | Sadece SHORT"
            elif is_1h_bull and (is_4h_bull or ema50_1h > ema200_1h):
                regime = 'BULLISH'
                allow_long = True
                allow_short = False
                badge_color = 'green bold'
                summary = f"🟢 BULLISH (${cur_price:,.0f} > EMA50: ${ema50_1h:,.0f}) | Sadece LONG"
            else:
                regime = 'NEUTRAL'
                # 4H EMA50 altındaysak makro ayı baskısındadır; sıradan LONG'ları engelle, sadece SHORT ve Sniper'a izin ver
                allow_long = not is_4h_bear
                allow_short = True
                badge_color = 'yellow'
                if is_4h_bear:
                    summary = f"⚪ NEUTRAL-BEAR (${cur_price:,.0f} < 4H EMA50) | Sadece SHORT + Sniper"
                else:
                    summary = f"⚪ NEUTRAL (${cur_price:,.0f}) | Her İki Yön"

            self.cached_state = {
                'regime': regime,
                'btc_price': cur_price,
                'ema50_1h': ema50_1h,
                'ema200_1h': ema200_1h,
                'ema50_4h': ema50_4h,
                'allow_long': allow_long,
                'allow_short': allow_short,
                'summary': summary,
                'badge_color': badge_color,
                'updated_at': now
            }
            self.last_fetch_time = now
        except Exception as e:
            pass

        return self.cached_state

    def check_sniper_exception(self, direction: str, obi: float, fvg_depth_pct: float) -> bool:
        """
        BTC trendine zıt olsa bile aşırı güçlü ayrışan (decoupled) coinler için
        Sniper İstisna Kuralı (OBI >= 0.70 ve FVG Derinliği >= %0.40).
        """
        if direction == 'LONG' and obi >= 0.70 and fvg_depth_pct >= 0.40:
            return True
        if direction == 'SHORT' and obi <= -0.70 and fvg_depth_pct >= 0.40:
            return True
        return False

# Tekil (Singleton) nesne
btc_watcher = BTCRegimeWatcher()

def get_btc_regime(force_refresh=False):
    return btc_watcher.get_regime(force_refresh=force_refresh)

def is_trade_allowed_by_btc(direction: str, obi: float, fvg_depth_pct: float) -> tuple[bool, str, bool, str]:
    state = btc_watcher.get_regime()
    regime = state['regime']
    btc_price = state.get('btc_price', 0.0)

    if direction == 'LONG':
        if state['allow_long']:
            reg_desc = "Trend Uyumlu" if regime == "BULLISH" else "Yatay / Nötr Piyasa"
            return True, f"BTC {reg_desc} ({regime} - ${btc_price:,.0f})", False, regime
        # İstisna kontrolü
        if btc_watcher.check_sniper_exception('LONG', obi, fvg_depth_pct):
            return True, f"Sniper İstisnası: BTC {regime} (${btc_price:,.0f}) İken Pozitif Ayrışma (OBI: {obi:+.2f}, FVG: %{fvg_depth_pct:.2f})", True, regime
        return False, f"BTC Ayı Trendinde ({state['summary']}) - LONG İptal Edildi", False, regime

    elif direction == 'SHORT':
        if state['allow_short']:
            reg_desc = "Trend Uyumlu" if regime == "BEARISH" else "Yatay / Nötr Piyasa"
            return True, f"BTC {reg_desc} ({regime} - ${btc_price:,.0f})", False, regime
        # İstisna kontrolü
        if btc_watcher.check_sniper_exception('SHORT', obi, fvg_depth_pct):
            return True, f"Sniper İstisnası: BTC {regime} (${btc_price:,.0f}) İken Negatif Ayrışma (OBI: {obi:+.2f}, FVG: %{fvg_depth_pct:.2f})", True, regime
        return False, f"BTC Boğa Trendinde ({state['summary']}) - SHORT İptal Edildi", False, regime

    return True, "Bilinmeyen Yön", False, regime
