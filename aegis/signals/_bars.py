"""Internal helpers shared by the signal modules. Not part of the public
`aegis.signals` API — import from the concrete signal files only.

Deliberately similar to `aegis/market/regime.py`'s metric helpers, but
these operate on a single symbol's own bars rather than an index's.
"""

from __future__ import annotations

from typing import Optional

import pandas as pd


def sorted_closes(df: Optional[pd.DataFrame]) -> Optional[pd.DataFrame]:
    if df is None or df.empty or "close" not in df.columns:
        return None
    if "trade_date" in df.columns:
        df = df.sort_values("trade_date")
    return df.reset_index(drop=True)


def recent_return(df: pd.DataFrame, lookback: int) -> Optional[float]:
    n = len(df)
    window = min(lookback, n - 1)
    if window < 1:
        return None
    latest_close = float(df["close"].iloc[-1])
    prior_close = float(df["close"].iloc[-1 - window])
    if not prior_close:
        return None
    return (latest_close - prior_close) / prior_close


def moving_average(df: pd.DataFrame, window: int) -> Optional[float]:
    n = len(df)
    if n < 1:
        return None
    w = min(window, n)
    return float(df["close"].tail(w).mean())
