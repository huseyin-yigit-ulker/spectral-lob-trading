import asyncio
from typing import Dict, Any, Deque, Callable, Optional
from collections import deque

from loguru import logger

class DataProcessor:
    """Processes raw depth and trade data, calculating real-time metrics."""

    def __init__(
        self,
        depth_window_size: int = 100,
        trade_window_size: int = 1000,
        on_snapshot: Optional[Callable[[Dict[str, Any]], None]] = None
    ):
        self.depth_window_size = depth_window_size
        self.trade_window_size = trade_window_size
        
        self.depth_history: Deque[Dict[str, Any]] = deque(maxlen=depth_window_size)
        self.trade_history: Deque[Dict[str, Any]] = deque(maxlen=trade_window_size)
        
        self.on_snapshot = on_snapshot
        
        self._lock = asyncio.Lock()
        
    async def process_depth(self, depth_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Processes a new depth snapshot."""
        async with self._lock:
            self.depth_history.append(depth_data)
            return await self._calculate_metrics()

    async def process_trade(self, trade_data: Dict[str, Any]) -> None:
        """Processes a new trade."""
        async with self._lock:
            self.trade_history.append(trade_data)

    async def _calculate_metrics(self) -> Optional[Dict[str, Any]]:
        """Calculates real-time metrics from current state."""
        if not self.depth_history:
            return None
            
        latest_depth = self.depth_history[-1]
        
        bids = latest_depth.get("bids", [])
        asks = latest_depth.get("asks", [])
        
        if not bids or not asks:
            return None
            
        best_bid = float(bids[0][0])
        best_ask = float(asks[0][0])
        
        mid_price = (best_bid + best_ask) / 2
        spread = best_ask - best_bid
        
        # Calculate total volumes
        total_bid_vol = sum(float(bid[1]) for bid in bids)
        total_ask_vol = sum(float(ask[1]) for ask in asks)
        
        # Calculate weighted mid price
        if total_bid_vol + total_ask_vol > 0:
            weighted_mid_price = (best_bid * total_ask_vol + best_ask * total_bid_vol) / (total_bid_vol + total_ask_vol)
        else:
            weighted_mid_price = mid_price
            
        snapshot = {
            "timestamp": latest_depth.get("E", latest_depth.get("T", 0)),
            "best_bid": best_bid,
            "best_ask": best_ask,
            "mid_price": mid_price,
            "weighted_mid_price": weighted_mid_price,
            "spread": spread,
            "total_bid_vol": total_bid_vol,
            "total_ask_vol": total_ask_vol,
            "recent_trades_count": len(self.trade_history),
        }
        
        if self.on_snapshot:
            self.on_snapshot(snapshot)
            
        return snapshot
