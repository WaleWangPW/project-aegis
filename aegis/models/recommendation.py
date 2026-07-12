"""RecommendationRecord — Master Spec §8.6.

The single canonical object of Project Aegis (ADR-001). Everything else —
Dashboard, PaperTrade, ReviewRecord, InvestmentMemory, Backtest — traces
back to a recommendation_id.
Produced by: RecommendationService (Phase 4).
Consumed by: Dashboard, PaperTrade, Review, Memory, Backtest (later phases).
Storage: data/records/recommendations.jsonl.

Acceptance: an "Action" status must carry at least one non-empty
invalidation condition. Every downstream object must be traceable back to
recommendation_id.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field, model_validator

from .common import Market, RecommendationStatus, Session


class RecommendationRecord(BaseModel):
    recommendation_id: str
    date: str
    session: Session
    symbol: str
    name: Optional[str] = None
    market: Market
    sector: Optional[str] = None
    status: RecommendationStatus
    action_label: str
    market_snapshot_id: str
    candidate_id: str
    expert_opinions: list[str] = Field(default_factory=list, description="opinion_id list")
    support_reasons: list[str] = Field(default_factory=list)
    oppose_reasons: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    invalidation_conditions: list[str] = Field(default_factory=list)
    confidence: float
    decision_summary: str
    paper_trade_id: Optional[str] = None
    review_id: Optional[str] = None
    lifecycle_status: str
    created_at: str
    updated_at: str

    @model_validator(mode="after")
    def _action_requires_invalidation_conditions(self) -> "RecommendationRecord":
        if self.status == "Action" and not self.invalidation_conditions:
            raise ValueError(
                "RecommendationRecord.status == 'Action' requires a non-empty "
                "invalidation_conditions list (Master Spec §8.6 acceptance)."
            )
        return self
