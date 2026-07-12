"""DecisionRecord — Master Spec §8.7.

Output of the Decision Engine's evidence-voting process. Never a weighted
composite score (ADR-002).
Produced by: DecisionEngine (Phase 4).
Consumed by: RecommendationService, DashboardBuilder, ReviewService (later phases).
Storage: data/records/decisions.jsonl.

Acceptance: if risk_veto_triggered is True, final_status must not be "Action".
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, model_validator

from .common import RecommendationStatus


class DecisionRecord(BaseModel):
    decision_id: str
    recommendation_id: str
    final_status: RecommendationStatus
    final_action: str
    support_count: int
    oppose_count: int
    neutral_count: int
    veto_count: int
    risk_veto_triggered: bool
    confidence: float
    decision_reason: str
    why_not_action: Optional[str] = None
    invalidation_conditions: list[str]
    created_at: str

    @model_validator(mode="after")
    def _veto_blocks_action(self) -> "DecisionRecord":
        if self.risk_veto_triggered and self.final_status == "Action":
            raise ValueError(
                "risk_veto_triggered=True must never coexist with "
                "final_status='Action' (Master Spec §5.5 / §8.7 acceptance)."
            )
        return self
