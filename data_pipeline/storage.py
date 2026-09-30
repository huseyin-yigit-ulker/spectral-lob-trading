import os
import json
from typing import Dict, Any
from datetime import datetime
import threading

class LocalStorage:
    """Local storage handler saving data to JSON lines files."""

    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        self._ensure_dir(self.data_dir)
        self._lock = threading.Lock()
        
    def _ensure_dir(self, path: str):
        if not os.path.exists(path):
            os.makedirs(path)

    def _get_filepath(self, prefix: str, date: datetime) -> str:
        date_str = date.strftime("%Y-%m-%d")
        return os.path.join(self.data_dir, f"{prefix}_{date_str}.jsonl")

    def save_depth_snapshot(self, data: Dict[str, Any]) -> None:
        """Appends a depth snapshot to today's depth file."""
        now = datetime.utcnow()
        filepath = self._get_filepath("depth", now)
        
        with self._lock:
            with open(filepath, "a") as f:
                f.write(json.dumps(data) + "\n")

    def save_trade(self, data: Dict[str, Any]) -> None:
        """Appends a trade to today's trade file."""
        now = datetime.utcnow()
        filepath = self._get_filepath("trades", now)
        
        with self._lock:
            with open(filepath, "a") as f:
                f.write(json.dumps(data) + "\n")


class ClickHouseStorage:
    """Placeholder for ClickHouse storage."""
    
    def __init__(self):
        # TODO: Initialize ClickHouse client connection
        pass
        
    def save_depth_snapshot(self, data: Dict[str, Any]) -> None:
        # TODO: Implement insert to ClickHouse
        pass
        
    def save_trade(self, data: Dict[str, Any]) -> None:
        # TODO: Implement insert to ClickHouse
        pass


class PostgresStorage:
    """Placeholder for Postgres storage."""
    
    def __init__(self):
        # TODO: Initialize asyncpg pool or similar
        pass
        
    def save_depth_snapshot(self, data: Dict[str, Any]) -> None:
        # TODO: Implement insert to PostgreSQL
        pass
        
    def save_trade(self, data: Dict[str, Any]) -> None:
        # TODO: Implement insert to PostgreSQL
        pass
