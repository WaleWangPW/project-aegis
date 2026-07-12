"""DataCache — Master Spec §10.1 / Phase 1 §4.3.

Simple file-based cache for provider results, CSV only in Phase 1 (avoids
requiring pyarrow/parquet). Never caches tokens or secrets — it only ever
receives DataFrames of market data from callers.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import pandas as pd


class DataCache:
    def __init__(self, root_dir: str | Path):
        self.root_dir = Path(root_dir)

    def get_path(self, market: str, data_type: str, key: str, ext: str = "csv") -> Path:
        safe_key = key.replace("/", "_").replace(" ", "_")
        return self.root_dir / market / data_type / f"{safe_key}.{ext}"

    def write_dataframe(self, df: pd.DataFrame, market: str, data_type: str, key: str) -> Path:
        path = self.get_path(market, data_type, key)
        path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(path, index=False)
        return path

    def read_dataframe(self, market: str, data_type: str, key: str) -> Optional[pd.DataFrame]:
        path = self.get_path(market, data_type, key)
        if not path.exists():
            return None
        return pd.read_csv(path)

    def exists(self, market: str, data_type: str, key: str) -> bool:
        return self.get_path(market, data_type, key).exists()
