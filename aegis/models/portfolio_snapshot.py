"""PortfolioSnapshot — Master Spec §8.10.

A point-in-time summary of the whole real portfolio (not a single holding).
Storage: data/records/portfolio_snapshots.jsonl.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class PortfolioSnapshot(BaseModel):
    snapshot_id: str
    date: str
    total_cost: float
    total_market_value: Optional[float] = None
    cash: Optional[float] = None
    exposure_pct: Optional[float] = None
    market_allocation: dict[str, float]
    sector_allocation: dict[str, float]
    unrealized_pnl: Optional[float] = None
    risk_level: str
    summary: str
