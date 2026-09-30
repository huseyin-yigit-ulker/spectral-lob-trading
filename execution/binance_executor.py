import logging
import asyncio
from typing import Dict, Any, Optional
from binance.client import AsyncClient
from binance.exceptions import BinanceAPIException

logger = logging.getLogger(__name__)

class BinanceExecutor:
    def __init__(self, api_key: str, api_secret: str, testnet: bool = True, dry_run: bool = False):
        self.api_key = api_key
        self.api_secret = api_secret
        self.testnet = testnet
        self.dry_run = dry_run
        self.client: Optional[AsyncClient] = None
        self.symbol = "BTCUSDT"

    async def initialize(self):
        self.client = await AsyncClient.create(
            api_key=self.api_key,
            api_secret=self.api_secret,
            testnet=self.testnet
        )
        logger.info(f"BinanceExecutor initialized. Testnet: {self.testnet}, Dry Run: {self.dry_run}")

    async def close(self):
        if self.client:
            await self.client.close_connection()

    async def place_market_order(self, side: str, quantity: float, symbol: Optional[str] = None) -> dict:
        target_symbol = symbol or self.symbol
        if self.dry_run:
            logger.info(f"[DRY RUN] Market {side} order for {quantity} {target_symbol}")
            return {"status": "DRY_RUN", "side": side, "quantity": quantity, "symbol": target_symbol}
        
        try:
            order = await self.client.futures_create_order(
                symbol=target_symbol,
                side=side,
                type="MARKET",
                quantity=quantity
            )
            logger.info(f"Market order placed: {order}")
            return order
        except BinanceAPIException as e:
            logger.error(f"Error placing market order: {e}")
            return {"error": str(e)}

    async def place_limit_order(self, side: str, quantity: float, price: float, symbol: Optional[str] = None) -> dict:
        target_symbol = symbol or self.symbol
        if self.dry_run:
            logger.info(f"[DRY RUN] Limit {side} order for {quantity} {target_symbol} at {price}")
            return {"status": "DRY_RUN", "side": side, "quantity": quantity, "price": price, "symbol": target_symbol}
        
        try:
            order = await self.client.futures_create_order(
                symbol=target_symbol,
                side=side,
                type="LIMIT",
                timeInForce="GTC",
                quantity=quantity,
                price=price
            )
            logger.info(f"Limit order placed: {order}")
            return order
        except BinanceAPIException as e:
            logger.error(f"Error placing limit order: {e}")
            return {"error": str(e)}

    async def cancel_order(self, order_id: str, symbol: Optional[str] = None) -> dict:
        target_symbol = symbol or self.symbol
        if self.dry_run:
            logger.info(f"[DRY RUN] Cancel order {order_id} for {target_symbol}")
            return {"status": "DRY_RUN", "order_id": order_id, "symbol": target_symbol}
        
        try:
            result = await self.client.futures_cancel_order(
                symbol=target_symbol,
                orderId=order_id
            )
            logger.info(f"Order {order_id} cancelled: {result}")
            return result
        except BinanceAPIException as e:
            logger.error(f"Error cancelling order: {e}")
            return {"error": str(e)}

    async def get_position(self, symbol: Optional[str] = None) -> dict:
        target_symbol = symbol or self.symbol
        try:
            positions = await self.client.futures_position_information(symbol=target_symbol)
            if positions:
                return positions[0]
            return {}
        except BinanceAPIException as e:
            logger.error(f"Error getting position: {e}")
            return {"error": str(e)}

    async def get_account_balance(self, asset: str = "USDT") -> float:
        try:
            balances = await self.client.futures_account_balance()
            for balance in balances:
                if balance["asset"] == asset:
                    return float(balance["balance"])
            return 0.0
        except BinanceAPIException as e:
            logger.error(f"Error getting account balance: {e}")
            return 0.0

    async def set_leverage(self, leverage: int, symbol: Optional[str] = None) -> dict:
        target_symbol = symbol or self.symbol
        if self.dry_run:
            logger.info(f"[DRY RUN] Set leverage to {leverage} for {target_symbol}")
            return {"status": "DRY_RUN", "leverage": leverage, "symbol": target_symbol}
        
        try:
            result = await self.client.futures_change_leverage(
                symbol=target_symbol,
                leverage=leverage
            )
            logger.info(f"Leverage set to {leverage} for {target_symbol}")
            return result
        except BinanceAPIException as e:
            logger.error(f"Error setting leverage: {e}")
            return {"error": str(e)}
