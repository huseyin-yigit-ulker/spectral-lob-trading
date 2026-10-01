"""
Smart Money Concepts (SMC) feature calculation module.
"""
import numpy as np
from typing import List, Dict, Optional, Tuple

class SMCFeatures:
    """
    Implements SMC concepts like Order Blocks (OB), Fair Value Gaps (FVG),
    and Market Structure Shifts (MSS).
    """
    
    def __init__(self):
        self.order_blocks = []  # List of dicts {'price': float, 'type': str, 'tested': bool}
        self.fvgs = []          # List of dicts {'top': float, 'bottom': float, 'type': str, 'filled': bool}
        self.swing_highs = []
        self.swing_lows = []
        
    def detect_order_blocks_from_depth(self, bids: np.ndarray, asks: np.ndarray, current_price: float, threshold_std: float = 2.0) -> List[Dict]:
        """
        Identify price levels with significant limit order accumulation.
        """
        obs = []
        if len(bids) > 0:
            b_mean = np.mean(bids[:, 1])
            b_std = np.std(bids[:, 1])
            for p, v in bids:
                if v > b_mean + threshold_std * b_std:
                    obs.append({'price': p, 'type': 'bullish', 'tested': False})
                    
        if len(asks) > 0:
            a_mean = np.mean(asks[:, 1])
            a_std = np.std(asks[:, 1])
            for p, v in asks:
                if v > a_mean + threshold_std * a_std:
                    obs.append({'price': p, 'type': 'bearish', 'tested': False})
                    
        # Add to historical and return
        self.order_blocks.extend(obs)
        return obs

    def get_nearest_ob_distance(self, current_price: float) -> Tuple[float, float]:
        """
        Calculate distance to nearest bullish and bearish order blocks.
        Returns (dist_to_bullish, dist_to_bearish).
        """
        bullish_dists = [current_price - ob['price'] for ob in self.order_blocks if ob['type'] == 'bullish' and not ob['tested'] and current_price >= ob['price']]
        bearish_dists = [ob['price'] - current_price for ob in self.order_blocks if ob['type'] == 'bearish' and not ob['tested'] and current_price <= ob['price']]
        
        dist_bull = min(bullish_dists) if bullish_dists else -1.0
        dist_bear = min(bearish_dists) if bearish_dists else -1.0
        return dist_bull, dist_bear

    def detect_fvg(self, high_i2: float, low_i2: float, high_i: float, low_i: float) -> Optional[Dict]:
        """
        Detect Fair Value Gaps.
        Bullish FVG: low_i > high_i2
        Bearish FVG: high_i < low_i2
        """
        fvg = None
        if low_i > high_i2:
            fvg = {'top': low_i, 'bottom': high_i2, 'type': 'bullish', 'filled': False}
        elif high_i < low_i2:
            fvg = {'top': low_i2, 'bottom': high_i, 'type': 'bearish', 'filled': False}
            
        if fvg:
            self.fvgs.append(fvg)
        return fvg

    def update_fvg_status(self, current_low: float, current_high: float):
        """
        Mark open FVGs as filled if price returns to them.
        """
        for fvg in self.fvgs:
            if fvg['filled']:
                continue
            if fvg['type'] == 'bullish' and current_low <= fvg['top']:
                fvg['filled'] = True
            elif fvg['type'] == 'bearish' and current_high >= fvg['bottom']:
                fvg['filled'] = True

    def detect_market_structure(self, current_price: float, is_swing_high: bool, is_swing_low: bool) -> float:
        """
        Simple structural shift detection.
        Returns: 1.0 for bullish MSS/BOS, -1.0 for bearish MSS/BOS, 0.0 for none.
        """
        if is_swing_high:
            self.swing_highs.append(current_price)
            if len(self.swing_highs) >= 2 and self.swing_highs[-1] > self.swing_highs[-2]:
                return 1.0 # BOS/CHoCH Bullish
                
        if is_swing_low:
            self.swing_lows.append(current_price)
            if len(self.swing_lows) >= 2 and self.swing_lows[-1] < self.swing_lows[-2]:
                return -1.0 # BOS/CHoCH Bearish
                
        return 0.0
