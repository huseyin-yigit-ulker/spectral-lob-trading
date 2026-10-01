"""
State Builder module for generating state vectors for RL agents.
"""
import numpy as np
from typing import List, Dict, Any
from .orderbook_features import OrderBookFeatures
from .cvd_features import CVDFeatures
from .smc_features import SMCFeatures

class StateBuilder:
    """
    Combines features from OrderBook, CVD, and SMC modules.
    Builds a flat numpy state vector.
    """
    
    def __init__(self):
        self.ob_features = OrderBookFeatures()
        self.cvd_features = CVDFeatures()
        self.smc_features = SMCFeatures()
        
        self.feature_names = [
            "obi", "weighted_obi", "spread", "spread_vol",
            "cvd_1s", "cvd_5s", "cvd_15s", "cvd_1m", "cvd_5m",
            "cvd_roc", "taker_ratio",
            "dist_ob_bull", "dist_ob_bear", "mss_signal"
        ]
        
        # Expand for depth profile (20 bids, 20 asks) and pressure ratios (20)
        for i in range(20):
            self.feature_names.append(f"depth_bid_{i}")
        for i in range(20):
            self.feature_names.append(f"depth_ask_{i}")
        for i in range(20):
            self.feature_names.append(f"pressure_ratio_{i}")
            
        self.state_dim = len(self.feature_names)
        
        # Running statistics for normalization
        self.mean = np.zeros(self.state_dim)
        self.var = np.ones(self.state_dim)
        self.count = 1e-4

    def update_stats(self, x: np.ndarray):
        """Update running mean and variance."""
        batch_mean = np.mean(x, axis=0)
        batch_var = np.var(x, axis=0)
        batch_count = x.shape[0] if len(x.shape) > 1 else 1

        delta = batch_mean - self.mean
        tot_count = self.count + batch_count

        self.mean = self.mean + delta * batch_count / tot_count
        m_a = self.var * self.count
        m_b = batch_var * batch_count
        M2 = m_a + m_b + np.square(delta) * self.count * batch_count / tot_count
        self.var = M2 / tot_count
        self.count = tot_count

    def normalize(self, x: np.ndarray) -> np.ndarray:
        """Apply z-score normalization using running stats."""
        std = np.sqrt(self.var + 1e-8)
        return (x - self.mean) / std

    def build_state(self, bids: np.ndarray, asks: np.ndarray, current_time: float, current_price: float) -> np.ndarray:
        """
        Constructs the state vector from current market data.
        Returns normalized state ready for model input.
        """
        # Order Book
        obi = self.ob_features.calc_obi(bids, asks)
        w_obi = self.ob_features.calc_weighted_obi(bids, asks)
        spread = self.ob_features.calc_spread(bids, asks)
        spread_vol = 0.0 # Placeholder, requires history
        
        bid_prof, ask_prof = self.ob_features.calc_liquidity_depth_profile(bids, asks)
        pressure = self.ob_features.calc_pressure_ratio(bids, asks, 20)
        
        # CVD
        cvds = self.cvd_features.get_multi_window_cvd(current_time)
        cvd_roc = 0.0 # Placeholder
        tr = self.cvd_features.get_trades_in_window(current_time, 60.0)
        taker_ratio = self.cvd_features.calc_taker_buy_sell_ratio(tr)
        
        # SMC
        dist_bull, dist_bear = self.smc_features.get_nearest_ob_distance(current_price)
        mss = 0.0 # Placeholder
        
        # Assemble vector
        state = [
            obi, w_obi, spread, spread_vol,
            cvds.get('1s', 0), cvds.get('5s', 0), cvds.get('15s', 0),
            cvds.get('1m', 0), cvds.get('5m', 0),
            cvd_roc, taker_ratio,
            dist_bull, dist_bear, mss
        ]
        
        # Pad profiles to 20 if needed
        def pad(arr, length=20):
            res = np.zeros(length)
            n = min(len(arr), length)
            if n > 0:
                res[:n] = arr[:n]
            return res
            
        state.extend(pad(bid_prof).tolist())
        state.extend(pad(ask_prof).tolist())
        state.extend(pad(pressure).tolist())
        
        state_arr = np.array(state, dtype=np.float32)
        
        # Update stats and normalize
        self.update_stats(state_arr)
        return self.normalize(state_arr)

    def get_state_dim(self) -> int:
        return self.state_dim
