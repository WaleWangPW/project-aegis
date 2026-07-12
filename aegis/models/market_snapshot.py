"""MarketSnapshot — Master Spec §8.1.

Records the market environment for one date/session/market combination.
Produced by: MarketDataService, MarketRegimeAnalyzer (Phase 2).
Consumed by: UniverseBuilder, ExpertCommittee, DecisionEngine,
DashboardBuilder, TimeTravelEngine (later phases).
Storage: data/records/market_snapshots.jsonl

Acceptance: every RecommendationRecord must reference a market_snapshot_id.
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

from .common import DataQuality, Market, Session

TrendState = Literal["uptrend", "downtrend", "sideways", "unknown"]
LiquidityState = Literal["strong", "weak", "normal", "unknown"]
SentimentState = Literal["risk_on", "neutral", "risk_off", "unknown"]
RiskLevel = Literal["low", "medium", "high", "unknown"]


class IndexSummary(BaseModel):
    primary_index: Optional[str] = None
    primary_index_change_pct: Optional[float] = None


class MarketSnapshot(BaseModel):
    snapshot_id: str = Field(..., description='e.g. "mkt_20260703_US_pre_market"')
    date: str
    session: Session
    market: Market
    index_summary: IndexSummary
    trend_state: TrendState
    liquidity_state: LiquidityState
    sentiment_state: SentimentState
    sector_rotation: list[str] = Field(default_factory=list)
    risk_level: RiskLevel
    summary: str
    data_quality: DataQuality
    created_at: str
