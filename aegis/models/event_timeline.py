"""Event timeline and scenario models for V2.0-D."""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator

from aegis.models.common import Market

EventType = Literal[
    "earnings",
    "filing",
    "press_release",
    "price_move",
    "macro",
    "sector",
    "social_statement",
    "user_note",
]
EvidenceLevel = Literal[
    "verified_primary",
    "licensed_provider",
    "verified_social_statement",
    "community_discussion",
    "llm_summary",
    "unverified_web",
]


class EventRecord(BaseModel):
    event_id: str
    symbol: str
    market: Market
    event_date: str
    event_type: EventType
    title: str
    summary: str
    source_id: str
    source_url: Optional[str] = None
    evidence_level: EvidenceLevel
    verified: bool
    decision_relevance: str
    created_at: str

    @model_validator(mode="after")
    def _unverified_levels_cannot_be_verified(self) -> "EventRecord":
        if self.evidence_level in {"llm_summary", "unverified_web", "community_discussion"} and self.verified:
            raise ValueError(f"{self.evidence_level} must not be marked verified")
        return self


ScenarioImpact = Literal["positive", "negative", "mixed", "unknown"]


class ScenarioRecord(BaseModel):
    scenario_id: str
    symbol: str
    market: Market
    title: str
    assumption: str
    impact: ScenarioImpact
    rationale: str
    evidence_event_ids: list[str] = Field(default_factory=list)
    confidence: float
    created_at: str

    @model_validator(mode="after")
    def _requires_evidence_events(self) -> "ScenarioRecord":
        if not self.evidence_event_ids:
            raise ValueError("ScenarioRecord requires at least one evidence_event_id")
        if not 0 <= self.confidence <= 1:
            raise ValueError("ScenarioRecord.confidence must be between 0 and 1")
        return self
