"""TradingCalendarRepository — P1A §2.2.

CSV cache at `data/cache/calendar/{market}/trading_calendar.csv`, per
P1A's suggested cache path. Columns: `date` ("YYYY-MM-DD" string),
`is_trading_day` (0/1). Same CSV-only convention as
`aegis/data/cache.py::DataCache` (Phase 1) — no pyarrow/parquet
dependency.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import pandas as pd


class TradingCalendarRepository:
    def __init__(self, cache_root: str | Path):
        self.cache_root = Path(cache_root)

    def _path(self, market: str) -> Path:
        return self.cache_root / "calendar" / market / "trading_calendar.csv"

    def read(self, market: str) -> Optional[pd.DataFrame]:
        path = self._path(market)
        if not path.exists():
            return None
        return pd.read_csv(path, dtype={"date": str})

    def write(self, market: str, df: pd.DataFrame) -> Path:
        path = self._path(market)
        path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(path, index=False)
        return path

    def exists(self, market: str) -> bool:
        return self._path(market).exists()
