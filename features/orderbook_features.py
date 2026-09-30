"""
Order book feature calculation module.
Calculates OBI, spread, liquidity depth, and other depth-based features.
"""
import numpy as np
from typing import Tuple, Optional

class OrderBookFeatures:
    """
    Calculates features based on Level 2 order book data.
    All methods expect bids and asks as numpy arrays of shape (N, 2),
    where col0 = price, col1 = quantity.
    """
    
    @staticmethod
    def calc_obi(bids: np.ndarray, asks: np.ndarray) -> float:
        """
        Calculate Order Book Imbalance (OBI).
        Range: [-1, 1], where 1 means all volume is on the bid side.
        """
        total_bid_vol = np.sum(bids[:, 1])
        total_ask_vol = np.sum(asks[:, 1])
        if total_bid_vol + total_ask_vol == 0:
            return 0.0
        return float((total_bid_vol - total_ask_vol) / (total_bid_vol + total_ask_vol))

    @staticmethod
    def calc_weighted_obi(bids: np.ndarray, asks: np.ndarray) -> float:
        """
        Calculate Weighted Order Book Imbalance.
        Closer levels are weighted more.
        """
        if len(bids) == 0 or len(asks) == 0:
            return 0.0
        
        # Simple distance weighting: 1 / (index + 1)
        weights_bid = 1.0 / (np.arange(len(bids)) + 1)
        weights_ask = 1.0 / (np.arange(len(asks)) + 1)
        
        weighted_bid_vol = np.sum(bids[:, 1] * weights_bid)
        weighted_ask_vol = np.sum(asks[:, 1] * weights_ask)
        
        if weighted_bid_vol + weighted_ask_vol == 0:
            return 0.0
        return float((weighted_bid_vol - weighted_ask_vol) / (weighted_bid_vol + weighted_ask_vol))

    @staticmethod
    def calc_spread(bids: np.ndarray, asks: np.ndarray) -> float:
        """
        Calculate Bid-Ask Spread.
        """
        if len(bids) == 0 or len(asks) == 0:
            return 0.0
        return float(asks[0, 0] - bids[0, 0])

    @staticmethod
    def calc_spread_volatility(spread_history: np.ndarray) -> float:
        """
        Calculate rolling standard deviation of spread.
        """
        if len(spread_history) < 2:
            return 0.0
        return float(np.std(spread_history))

    @staticmethod
    def calc_liquidity_depth_profile(bids: np.ndarray, asks: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        Volume at each price level as a ratio of total side volume.
        """
        total_bid_vol = np.sum(bids[:, 1]) or 1.0
        total_ask_vol = np.sum(asks[:, 1]) or 1.0
        
        bid_profile = bids[:, 1] / total_bid_vol
        ask_profile = asks[:, 1] / total_ask_vol
        return bid_profile, ask_profile

    @staticmethod
    def detect_large_orders(bids: np.ndarray, asks: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        Flag levels where volume exceeds mean + 2*std.
        Returns binary arrays of shape (N,) indicating large order presence.
        """
        def get_flags(side: np.ndarray) -> np.ndarray:
            if len(side) == 0:
                return np.array([])
            vol = side[:, 1]
            mean = np.mean(vol)
            std = np.std(vol)
            threshold = mean + 2 * std
            return (vol > threshold).astype(float)
            
        return get_flags(bids), get_flags(asks)

    @staticmethod
    def calc_pressure_ratio(bids: np.ndarray, asks: np.ndarray, levels: int = 20) -> np.ndarray:
        """
        Calculate bid_vol[i] / ask_vol[i] for up to `levels` levels.
        """
        min_len = min(len(bids), len(asks), levels)
        if min_len == 0:
            return np.zeros(levels)
            
        b_vol = bids[:min_len, 1]
        a_vol = asks[:min_len, 1]
        
        # Avoid division by zero
        a_vol_safe = np.where(a_vol == 0, 1e-8, a_vol)
        ratio = b_vol / a_vol_safe
        
        result = np.zeros(levels)
        result[:min_len] = ratio
        return result
