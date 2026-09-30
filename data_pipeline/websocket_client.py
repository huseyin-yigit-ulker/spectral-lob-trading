import asyncio
import json
import traceback
from typing import Callable, Optional, Dict, Any

import websockets
from loguru import logger

class BinanceFuturesWS:
    """Async WebSocket client for Binance Futures streams."""

    def __init__(
        self,
        symbol: str = "BTCUSDT",
        on_depth: Optional[Callable[[Dict[str, Any]], None]] = None,
        on_trade: Optional[Callable[[Dict[str, Any]], None]] = None,
        on_connect: Optional[Callable[[], None]] = None,
        on_disconnect: Optional[Callable[[], None]] = None,
    ):
        self.symbol = symbol.lower()
        self.stream_url = f"wss://fstream.binance.com/stream?streams={self.symbol}@depth20@100ms/{self.symbol}@aggTrade"
        
        self.on_depth = on_depth
        self.on_trade = on_trade
        self.on_connect = on_connect
        self.on_disconnect = on_disconnect
        
        self.ws = None
        self._running = False
        self._reconnect_delay = 1.0
        self._max_reconnect_delay = 60.0
        
        self.depth_queue: asyncio.Queue = asyncio.Queue()
        self.trade_queue: asyncio.Queue = asyncio.Queue()
        
    async def connect(self) -> None:
        """Connects to the WebSocket and manages reconnection."""
        self._running = True
        
        while self._running:
            try:
                logger.info(f"Connecting to Binance Futures WS: {self.stream_url}")
                async with websockets.connect(self.stream_url, ping_interval=20, ping_timeout=20) as ws:
                    self.ws = ws
                    self._reconnect_delay = 1.0  # Reset delay on successful connection
                    logger.info("Connected to Binance Futures WS")
                    
                    if self.on_connect:
                        self.on_connect()
                        
                    await self._consume()
            except asyncio.CancelledError:
                logger.info("Connection cancelled.")
                break
            except Exception as e:
                logger.error(f"WebSocket connection error: {e}")
                
            if not self._running:
                break
                
            if self.on_disconnect:
                self.on_disconnect()
                
            logger.info(f"Reconnecting in {self._reconnect_delay} seconds...")
            await asyncio.sleep(self._reconnect_delay)
            self._reconnect_delay = min(self._reconnect_delay * 2, self._max_reconnect_delay)
            
    async def _consume(self) -> None:
        """Consumes messages from the WebSocket."""
        if self.ws is None:
            return
            
        async for message in self.ws:
            try:
                data = json.loads(message)
                await self._route_message(data)
            except Exception as e:
                logger.error(f"Error processing message: {e}\n{traceback.format_exc()}")
                
    async def _route_message(self, data: Dict[str, Any]) -> None:
        """Routes parsed JSON to the appropriate handlers."""
        stream = data.get("stream", "")
        payload = data.get("data", {})
        
        if "depth" in stream:
            await self.depth_queue.put(payload)
            if self.on_depth:
                self.on_depth(payload)
        elif "aggTrade" in stream:
            await self.trade_queue.put(payload)
            if self.on_trade:
                self.on_trade(payload)
        else:
            logger.warning(f"Unknown stream: {stream}")

    async def disconnect(self) -> None:
        """Gracefully disconnects."""
        self._running = False
        if self.ws:
            await self.ws.close()
            logger.info("WebSocket disconnected.")

async def main():
    def handle_depth(data):
        logger.debug(f"Depth update received (bids: {len(data.get('bids', []))}, asks: {len(data.get('asks', []))})")

    def handle_trade(data):
        logger.debug(f"Trade received: {data.get('p')} x {data.get('q')} (maker: {data.get('m')})")

    client = BinanceFuturesWS(
        symbol="BTCUSDT",
        on_depth=handle_depth,
        on_trade=handle_trade
    )
    
    # Run the client
    task = asyncio.create_task(client.connect())
    
    try:
        # Run for 10 seconds then shut down
        await asyncio.sleep(10)
    except KeyboardInterrupt:
        pass
    finally:
        logger.info("Shutting down...")
        await client.disconnect()
        await task

if __name__ == "__main__":
    asyncio.run(main())
