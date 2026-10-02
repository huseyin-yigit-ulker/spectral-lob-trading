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

class SMCFeatures:
    """RL ajani icin geriye donuk uyumluluk saglayan dummy sinif"""
    def __init__(self):
        pass
    def get_nearest_ob_distance(self, current_price):
        return 0.0, 0.0
