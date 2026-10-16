import collections

class SMCAnalyzer:
    """
    SMC (Smart Money Concepts) Analiz Motoru.
    Gelen 5 dakikalik (5m) kline (mum) verilerini okuyarak 
    Fair Value Gap (FVG) ve Order Block (OB) bolgelerini tespit eder.
    """
    def __init__(self, max_candles=50):
        # Son 50 mumu hafizada tutar (5m mumlar icin ~4 saatlik veri)
        self.max_candles = max_candles
        self.candles = collections.deque(maxlen=max_candles)
        
        self.active_fvgs = []
        
    def add_candle(self, open_p, high_p, low_p, close_p, timestamp):
        """Yeni kapanan mumu hafizaya ekler ve bolgeleri gunceller."""
        self.candles.append({
            'open': float(open_p),
            'high': float(high_p),
            'low': float(low_p),
            'close': float(close_p),
            'time': timestamp
        })
        self._detect_fvg()

    def _detect_fvg(self):
        """
        Gecmis mumlari tarayarak doldurulmamis (Mitigate edilmemis) 
        FVG (Adil Deger Bosluklari) tespit eder.
        """
        if len(self.candles) < 3:
            return
            
        self.active_fvgs = []
        c_list = list(self.candles)
        
        # Sadece son mumlarda olusan FVG'leri bul
        for i in range(2, len(c_list)):
            c1 = c_list[i-2] # 1. Mum
            c2 = c_list[i-1] # 2. Mum (Buyuk patlama mumu)
            c3 = c_list[i]   # 3. Mum
            
            # BULLISH (Yukselis) FVG: 1. Mumun Tepesi ile 3. Mumun Dibi arasindaki bosluk
            if c3['low'] > c1['high']:
                gap_top = c3['low']
                gap_bottom = c1['high']
                
                # Bu bosluk daha sonraki mumlar (i'den sonraki) tarafindan dolduruldu mu (Mitigate)?
                is_mitigated = False
                for j in range(i+1, len(c_list)):
                    if c_list[j]['low'] <= gap_top: # Iceri igne atildiysa dolduruldu varsay (Kisaca)
                        is_mitigated = True
                        break
                        
                if not is_mitigated:
                    self.active_fvgs.append({
                        'type': 'BULLISH_FVG',
                        'top': gap_top,
                        'bottom': gap_bottom,
                        'created_at': c2['time']
                    })
                    
            # BEARISH (Dusus) FVG: 1. Mumun Dibi ile 3. Mumun Tepesi arasindaki bosluk
            elif c3['high'] < c1['low']:
                gap_top = c1['low']
                gap_bottom = c3['high']
                
                is_mitigated = False
                for j in range(i+1, len(c_list)):
                    if c_list[j]['high'] >= gap_bottom:
                        is_mitigated = True
                        break
                        
                if not is_mitigated:
                    self.active_fvgs.append({
                        'type': 'BEARISH_FVG',
                        'top': gap_top,
                        'bottom': gap_bottom,
                        'created_at': c2['time']
                    })

    def get_market_context(self, current_price):
        """
        Anlik fiyatin herhangi bir FVG (Likidite Boslugu) icinde 
        olup olmadigini kontrol eder. 
        Donus: 'IN_BULLISH_FVG', 'IN_BEARISH_FVG' veya 'NEUTRAL'
        """
        for fvg in self.active_fvgs:
            if fvg['bottom'] <= current_price <= fvg['top']:
                return fvg['type']
        return 'NEUTRAL'

    def get_adx(self, period=14):
        """
        Mum listesi üzerinden 14 periyotluk ADX (Trend Gücü) hesaplar.
        ADX < 18 ise piyasa testere/yatay (chop) noise bandındadır.
        """
        c_list = list(self.candles)
        if len(c_list) < period + 5:
            return 25.0
        
        tr_list = []
        plus_dm_list = []
        minus_dm_list = []
        
        for i in range(1, len(c_list)):
            h = float(c_list[i]['high'])
            l = float(c_list[i]['low'])
            prev_c = float(c_list[i-1]['close'])
            prev_h = float(c_list[i-1]['high'])
            prev_l = float(c_list[i-1]['low'])
            
            tr = max(h - l, abs(h - prev_c), abs(l - prev_c))
            tr_list.append(tr)
            
            up_move = h - prev_h
            down_move = prev_l - l
            
            plus_dm = up_move if (up_move > down_move and up_move > 0) else 0.0
            minus_dm = down_move if (down_move > up_move and down_move > 0) else 0.0
            
            plus_dm_list.append(plus_dm)
            minus_dm_list.append(minus_dm)
            
        if len(tr_list) < period:
            return 25.0
            
        alpha = 1.0 / period
        atr = tr_list[0]
        plus_di_smooth = plus_dm_list[0]
        minus_di_smooth = minus_dm_list[0]
        
        dx_list = []
        for i in range(1, len(tr_list)):
            atr = alpha * tr_list[i] + (1 - alpha) * atr
            plus_di_smooth = alpha * plus_dm_list[i] + (1 - alpha) * plus_di_smooth
            minus_di_smooth = alpha * minus_dm_list[i] + (1 - alpha) * minus_di_smooth
            
            if atr > 0:
                p_di = 100 * (plus_di_smooth / atr)
                m_di = 100 * (minus_di_smooth / atr)
                sum_di = p_di + m_di
                if sum_di > 0:
                    dx = 100 * abs(p_di - m_di) / sum_di
                    dx_list.append(dx)
                    
        if not dx_list:
            return 25.0
            
        adx = dx_list[0]
        for d in dx_list[1:]:
            adx = alpha * d + (1 - alpha) * adx
            
        return adx

    def get_active_fvg_bounds(self, current_price):
        for fvg in self.active_fvgs:
            if fvg['bottom'] <= current_price <= fvg['top']:
                return fvg['bottom'], fvg['top']
        return None, None

    def is_choppy(self, threshold=18.0):
        """ADX eşiğinin altında piyasa testere bandındaysa True döner."""
        return self.get_adx() < threshold

class SMCFeatures:
    """RL ajani icin geriye donuk uyumluluk saglayan dummy sinif"""
    def __init__(self):
        pass
    def get_nearest_ob_distance(self, current_price):
        return 0.0, 0.0
