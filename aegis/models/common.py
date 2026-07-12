"""Shared enums and small value objects used across Project Aegis models.

Per Master Spec §7.1 (General conventions):
- ID prefixes: mkt_, hold_, cand_, sig_, opn_, rec_, dec_, ptr_, rev_, mem_
- Date: "YYYY-MM-DD"; Datetime: ISO 8601
- Market: A, H, US, GLOBAL
- Session: pre_market, midday, close
- Currency: CNY, HKD, USD
- Confidence: 0.0-1.0, rule-computed, never an arbitrary LLM guess
- Missing data: null + data_quality / DataGap, fabrication is not allowed
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

Market = Literal["A", "H", "US", "GLOBAL"]
Session = Literal["pre_market", "midday", "close"]
Currency = Literal["CNY", "HKD", "USD"]

# ExpertOpinion.stance (Master Spec §8.5)
Stance = Literal["support", "oppose", "neutral", "veto"]

# RecommendationRecord.status / DecisionRecord.final_status (Master Spec §5.4, §8.6-8.7)
RecommendationStatus = Literal["Watch", "Ready", "Action", "Exit"]


class DataQuality(BaseModel):
    """Explicit data-completeness marker. Never silently hide a gap.

    `status` should be one of "complete", "partial", "missing" (kept as a
    plain str rather than a closed enum since Phase 1's DataGapRegistry may
    add more granular statuses without breaking this model).
    """

    status: str = Field(..., description='e.g. "complete", "partial", "missing"')
    missing_fields: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
