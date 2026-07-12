"""Dashboard JSON schema — Phase 5 §9.1.

Mirrors the static `DATA` shape already hard-coded in
`dashboard/index.html` exactly (verified by reading that file — it is
never modified by this module). Every field here must be honest: no
fabricated recommendations/prices/paper-trading returns/reviews, explicit
`DATA_GAP`/fallback text when source data is missing.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class DashboardMarketSnapshot(BaseModel):
    A: str
    H: str
    US: str


class DashboardFocusItem(BaseModel):
    type: str
    text: str


class DashboardHoldingItem(BaseModel):
    ticker: str
    market: str
    shares: float
    cost_price: float
    action: str
    action_label: str
    reason: str
    risk: str
    invalidation_condition: str


class DashboardRecommendationItem(BaseModel):
    ticker: str
    market: str
    industry: str
    reason: str
    counter_reason: str
    risk: str
    invalidation_condition: str


class DashboardRecommendationBuckets(BaseModel):
    # No defaults: DashboardBuilder always writes all three buckets
    # explicitly (empty lists when there is nothing to show), so a missing
    # bucket key is a real payload defect, not a normal empty state — it
    # must fail validation rather than silently default to [].
    action: list[DashboardRecommendationItem]
    ready: list[DashboardRecommendationItem]
    watch: list[DashboardRecommendationItem]


class DashboardPaperTrading(BaseModel):
    # Phase 5 always writes these empty — Paper Trading is Phase 6. Kept as
    # plain dicts (not a typed item model) since no Phase 6 shape exists
    # yet to conform to; inventing one now would be speculative. No
    # defaults, for the same reason as DashboardRecommendationBuckets above.
    new_today: list[dict]
    open_positions_perf: list[dict]


class DashboardPayload(BaseModel):
    date: str
    stage_note: str
    market_snapshot: DashboardMarketSnapshot
    today_focus: list[DashboardFocusItem] = Field(default_factory=list)
    holdings: list[DashboardHoldingItem] = Field(default_factory=list)
    recommendations: DashboardRecommendationBuckets
    paper_trading: DashboardPaperTrading
    review_note: str


def validate_dashboard_payload(payload: dict) -> dict:
    """Validates a plain dict against `DashboardPayload` and returns the
    normalized dict on success (via `model_dump`). Raises pydantic's
    `ValidationError` on failure — callers (`DashboardBuilder`,
    `scripts/build_dashboard.py`) must catch this and report a controlled
    error; this function itself never writes anything.
    """
    validated = DashboardPayload(**payload)
    return validated.model_dump()
