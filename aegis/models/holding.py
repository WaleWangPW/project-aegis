"""Holding — Master Spec §8.2.

A real position. CRCL is already known (see config/holdings.yaml) and must
be readable without asking the user again.
Produced by: HoldingLoader (Phase 1).
Consumed by: PortfolioSnapshotService, RiskAgent, DashboardBuilder,
UniverseBuilder (later phases).
Storage: config/holdings.yaml (source of truth), data/records/holdings_snapshots.jsonl (history).
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

from .common import Currency, Market

HoldingStatus = Literal["open", "closed"]


class Holding(BaseModel):
    holding_id: str = Field(..., description='e.g. "hold_US_CRCL_20260701"')
    symbol: str
    name: Optional[str] = None
    market: Market
    shares: float
    avg_cost: float
    currency: Currency
    entry_date: Optional[str] = None
    current_price: Optional[float] = None
    market_value: Optional[float] = None
    unrealized_pnl: Optional[float] = None
    unrealized_pnl_pct: Optional[float] = None
    linked_recommendation_id: Optional[str] = None
    status: HoldingStatus
    notes: Optional[str] = None
