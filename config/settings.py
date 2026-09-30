import os
from functools import lru_cache
from typing import Optional
from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

class BinanceSettings(BaseSettings):
    api_key: str = Field(..., env="BINANCE_API_KEY")
    api_secret: str = Field(..., env="BINANCE_API_SECRET")
    testnet: bool = Field(True, env="BINANCE_TESTNET")

    @computed_field
    @property
    def base_url(self) -> str:
        if self.testnet:
            return "https://testnet.binance.vision"
        return "https://api.binance.com"
        
    model_config = SettingsConfigDict(env_prefix="BINANCE_", extra="ignore")

class DatabaseSettings(BaseSettings):
    clickhouse_host: str = Field("localhost", env="CLICKHOUSE_HOST")
    clickhouse_port: int = Field(9000, env="CLICKHOUSE_PORT")
    clickhouse_db: str = Field("orders_signal", env="CLICKHOUSE_DB")
    
    postgres_host: str = Field("localhost", env="POSTGRES_HOST")
    postgres_port: int = Field(5432, env="POSTGRES_PORT")
    postgres_db: str = Field("orders_signal", env="POSTGRES_DB")
    postgres_user: str = Field("postgres", env="POSTGRES_USER")
    postgres_password: str = Field("postgres", env="POSTGRES_PASSWORD")
    
    model_config = SettingsConfigDict(extra="ignore")

class TradingSettings(BaseSettings):
    symbol: str = Field("BTCUSDT", env="TRADING_SYMBOL")
    leverage: int = Field(5, env="TRADING_LEVERAGE")
    max_position_size: float = Field(0.01, env="MAX_POSITION_SIZE")
    risk_per_trade: float = Field(0.02, env="RISK_PER_TRADE")
    
    model_config = SettingsConfigDict(extra="ignore")

class AppSettings(BaseSettings):
    log_level: str = Field("INFO", env="LOG_LEVEL")
    log_dir: str = Field("logs", env="LOG_DIR")
    
    # Nested settings can be initialized explicitly
    binance: BinanceSettings = BinanceSettings()
    database: DatabaseSettings = DatabaseSettings()
    trading: TradingSettings = TradingSettings()
    
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

@lru_cache()
def get_settings() -> AppSettings:
    return AppSettings()
