"""Small date helpers — Phase 2, optional per PHASE2 doc §4.

Only what MarketSnapshotService/UniverseBuilder need: turning a
"YYYY-MM-DD" date plus a lookback window into a Tushare-style
"YYYYMMDD" start/end pair. No calendar/holiday awareness — that is
`get_trading_calendar`'s job (Phase 1), not this module's.
"""

from __future__ import annotations

from datetime import datetime, timedelta


def to_compact(date_str: str) -> str:
    """"2026-07-03" -> "20260703"."""
    return date_str.replace("-", "")


def lookback_range(date_str: str, days: int) -> tuple[str, str]:
    """Return (start, end) as "YYYYMMDD" strings, `days` calendar days
    before `date_str` (inclusive of `date_str` as end). Calendar days, not
    trading days — this is a coarse fetch window, real trading-day
    filtering happens on whatever bars the provider actually returns.
    """
    end_dt = datetime.strptime(date_str, "%Y-%m-%d")
    start_dt = end_dt - timedelta(days=days)
    return start_dt.strftime("%Y%m%d"), end_dt.strftime("%Y%m%d")
