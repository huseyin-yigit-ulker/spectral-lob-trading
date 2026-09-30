"""
Cumulative Volume Delta feature calculation module.
"""
import numpy as np
import collections
from typing import List, Dict, Optional

class CVDFeatures:
    """
    Calculates Cumulative Volume Delta and related features.
    Maintains a rolling buffer of trades.
    """
    
    def __init__(self, max_buffer_size: int = 10000):
        # Store trades as (timestamp, price, qty, is_buyer_maker)
        self.trades = collections.deque(maxlen=max_buffer_size)
        
    def add_trade(self, timestamp: float, price: float, qty: float, is_buyer_maker: bool):
        """
        Add a trade to the rolling buffer.
        """
        self.trades.append((timestamp, price, qty, is_buyer_maker))
        
    def get_trades_in_window(self, current_time: float, window_seconds: float) -> List[tuple]:
        """
        Get trades within the specified time window.
        """
        min_time = current_time - window_seconds
        # Assuming trades are ordered by timestamp
        window_trades = []
        for trade in reversed(self.trades):
            if trade[0] >= min_time:
                window_trades.append(trade)
            else:
                break
        return list(reversed(window_trades))

    def calc_cvd(self, window_trades: List[tuple]) -> float:
        """
        Calculate CVD for a given list of trades.
        buyer_is_maker=False means taker buy (positive volume)
        buyer_is_maker=True means taker sell (negative volume)
        """
        cvd = 0.0
        for _, _, qty, is_buyer_maker in window_trades:
            if not is_buyer_maker:
                cvd += qty
            else:
                cvd -= qty
        return cvd

    def get_multi_window_cvd(self, current_time: float) -> Dict[str, float]:
        """
        Calculate CVD over multiple windows: 1s, 5s, 15s, 1min, 5min.
        """
        windows = {
            '1s': 1.0,
            '5s': 5.0,
            '15s': 15.0,
            '1m': 60.0,
            '5m': 300.0
        }
        results = {}
        for name, seconds in windows.items():
            tr = self.get_trades_in_window(current_time, seconds)
            results[name] = self.calc_cvd(tr)
        return results

    @staticmethod
    def calc_cvd_roc(cvd_current: float, cvd_previous: float, time_diff: float) -> float:
        """
        Calculate Rate of Change of CVD.
        """
        if time_diff == 0:
            return 0.0
        return (cvd_current - cvd_previous) / time_diff

    @staticmethod
    def detect_cvd_divergence(price_delta: float, cvd_delta: float) -> float:
        """
        Returns divergence magnitude.
        Positive if price up but CVD down (bearish div).
        Negative if price down but CVD up (bullish div).
        0 if no divergence.
        """
        if price_delta > 0 and cvd_delta < 0:
            return 1.0  # Bearish divergence
        elif price_delta < 0 and cvd_delta > 0:
            return -1.0 # Bullish divergence
        return 0.0

    def calc_taker_buy_sell_ratio(self, window_trades: List[tuple]) -> float:
        """
        Calculate ratio of taker buy volume to taker sell volume.
        """
        buy_vol = sum(qty for _, _, qty, is_maker in window_trades if not is_maker)
        sell_vol = sum(qty for _, _, qty, is_maker in window_trades if is_maker)
        if sell_vol == 0:
            return float('inf') if buy_vol > 0 else 1.0
        return buy_vol / sell_vol

    def detect_volume_spikes(self, current_time: float, window_seconds: float = 60.0, num_std: float = 2.0) -> bool:
        """
        Detect if current volume rate exceeds N std above mean.
        Simplified approach dividing window into sub-windows.
        """
        if len(self.trades) < 10:
            return False
            
        tr = self.get_trades_in_window(current_time, window_seconds)
        if not tr:
            return False
            
        vols = [qty for _, _, qty, _ in tr]
        if len(vols) < 5:
            return False
            
        mean_vol = np.mean(vols[:-1])
        std_vol = np.std(vols[:-1])
        
        return vols[-1] > mean_vol + num_std * std_vol
