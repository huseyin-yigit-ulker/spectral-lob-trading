import argparse
import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import websockets
import pandas as pd
from loguru import logger

class DataCollector:
    def __init__(self, symbol: str, data_dir: str = "data"):
        self.symbol = symbol.lower()
        self.combined_url = (
            f"wss://fstream.binance.com/stream?streams="
            f"{self.symbol}@depth20@100ms/{self.symbol}@trade"
        )
        self.is_running = True
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.depth_buffer = []
        self.trade_buffer = []

        self.depth_count = 0
        self.trade_count = 0
        self.total_bytes = 0
        self.start_time = datetime.now(timezone.utc)

    async def connect(self) -> None:
        reconnect_delay = 1.0

        while self.is_running:
            try:
                logger.info(f"Connecting to {self.combined_url}")
                async with websockets.connect(
                    self.combined_url,
                    ping_interval=20,
                    ping_timeout=20,
                    max_size=10 * 1024 * 1024,
                ) as ws:
                    reconnect_delay = 1.0
                    logger.success(f"Connected to Binance Futures - Symbol: {self.symbol.upper()}")

                    async for message in ws:
                        if not self.is_running:
                            break

                        self.total_bytes += len(message)
                        data = json.loads(message)
                        stream = data.get("stream", "").lower()
                        payload = data.get("data", {})
                        payload["_local_ts"] = datetime.now(timezone.utc).isoformat()

                        if "depth" in stream:
                            self.depth_count += 1
                            self._process_depth(payload)
                        elif "trade" in stream:
                            self.trade_count += 1
                            self._process_trade(payload)

                        if len(self.depth_buffer) >= 500:
                            self._flush_depth()
                        if len(self.trade_buffer) >= 2000:
                            self._flush_trades()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"WebSocket error: {e}")

            if not self.is_running:
                break

            await asyncio.sleep(reconnect_delay)
            reconnect_delay = min(reconnect_delay * 2, 60.0)

    def _process_depth(self, data: dict) -> None:
        record = {
            "timestamp": data.get("E", 0),
            "last_update_id": data.get("u", data.get("lastUpdateId", 0)),
            "local_ts": data.get("_local_ts", ""),
        }
        bids = data.get("b", data.get("bids", []))
        asks = data.get("a", data.get("asks", []))

        for i in range(min(20, len(bids))):
            record[f"bid_price_{i}"] = float(bids[i][0])
            record[f"bid_qty_{i}"] = float(bids[i][1])
        for i in range(min(20, len(asks))):
            record[f"ask_price_{i}"] = float(asks[i][0])
            record[f"ask_qty_{i}"] = float(asks[i][1])

        self.depth_buffer.append(record)

    def _process_trade(self, data: dict) -> None:
        record = {
            "agg_trade_id": data.get("t", data.get("a", 0)),
            "price": float(data.get("p", 0)),
            "quantity": float(data.get("q", 0)),
            "timestamp": data.get("T", 0),
            "is_buyer_maker": data.get("m", False),
            "local_ts": data.get("_local_ts", ""),
        }
        self.trade_buffer.append(record)

    def _flush_depth(self) -> None:
        if not self.depth_buffer: return
        filepath = self.data_dir / f"depth_{self.symbol}_{datetime.now().strftime('%Y-%m-%d')}.parquet"
        df = pd.DataFrame(self.depth_buffer)
        if filepath.exists():
            df = pd.concat([pd.read_parquet(filepath), df], ignore_index=True)
        df.to_parquet(filepath, index=False)
        self.depth_buffer.clear()

    def _flush_trades(self) -> None:
        if not self.trade_buffer: return
        filepath = self.data_dir / f"trades_{self.symbol}_{datetime.now().strftime('%Y-%m-%d')}.parquet"
        df = pd.DataFrame(self.trade_buffer)
        if filepath.exists():
            df = pd.concat([pd.read_parquet(filepath), df], ignore_index=True)
        df.to_parquet(filepath, index=False)
        self.trade_buffer.clear()

    async def print_stats(self) -> None:
        prev_depth = 0
        prev_trade = 0
        while self.is_running:
            await asyncio.sleep(5)
            elapsed = (datetime.now(timezone.utc) - self.start_time).total_seconds()
            logger.info(
                f"[{elapsed:.0f}s] Depth: {self.depth_count} ({(self.depth_count - prev_depth)/5:.1f}/s) | "
                f"Trades: {self.trade_count} ({(self.trade_count - prev_trade)/5:.1f}/s)"
            )
            prev_depth = self.depth_count
            prev_trade = self.trade_count

    def shutdown(self) -> None:
        self.is_running = False
        self._flush_depth()
        self._flush_trades()
        logger.success("Buffers flushed. Shutdown complete.")

    async def run(self, duration: int = None) -> None:
        connect_task = asyncio.create_task(self.connect())
        stats_task = asyncio.create_task(self.print_stats())
        try:
            if duration:
                await asyncio.sleep(duration)
            else:
                while self.is_running:
                    await asyncio.sleep(1)
        except asyncio.CancelledError:
            pass
        finally:
            self.shutdown()
            connect_task.cancel()
            stats_task.cancel()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", type=str, default="BTCUSDT")
    parser.add_argument("--duration", type=int, default=None)
    args = parser.parse_args()
    collector = DataCollector(symbol=args.symbol)
    try:
        asyncio.run(collector.run(duration=args.duration))
    except KeyboardInterrupt:
        collector.shutdown()

if __name__ == "__main__":
    main()
