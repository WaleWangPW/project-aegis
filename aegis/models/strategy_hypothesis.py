"""Sandbox hypothesis models for strategy research sources."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

Market = Literal["A", "H", "US"]
HypothesisFamily = Literal[
    "value",
    "quality",
    "momentum",
    "low_volatility",
    "dividend",
    "size",
    "multi_factor",
    "risk_overlay",
    "capital_flow",
    "hot_money",
    "institutional_ownership",
    "holder_concentration",
    "governance",
]


class StrategySandboxHypothesis(BaseModel):
    hypothesis_id: str
    title: str
    market: Market
    strategy_families: list[HypothesisFamily]
    thesis: str
    source_research_ids: list[str] = Field(default_factory=list)
    proposed_universe: str
    proposed_entry_logic: list[str] = Field(default_factory=list)
    proposed_exit_logic: list[str] = Field(default_factory=list)
    proposed_risk_controls: list[str] = Field(default_factory=list)
    proposed_metrics: list[str] = Field(default_factory=list)
    requires_sandbox: bool = True
    auto_applied: bool = False
    user_facing_suggestion_allowed: bool = False
    created_at: str

    @field_validator("hypothesis_id", "title", "thesis", "proposed_universe", "created_at")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("field must not be blank")
        return value

    @model_validator(mode="after")
    def _must_remain_hypothesis(self) -> "StrategySandboxHypothesis":
        if not self.source_research_ids:
            raise ValueError("strategy sandbox hypotheses require source research refs")
        if not self.strategy_families:
            raise ValueError("at least one strategy family is required")
        if not self.proposed_metrics:
            raise ValueError("sandbox hypotheses require proposed metrics")
        if not self.requires_sandbox:
            raise ValueError("strategy sandbox hypotheses must require sandbox validation")
        if self.auto_applied:
            raise ValueError("strategy sandbox hypotheses must not auto-apply")
        if self.user_facing_suggestion_allowed:
            raise ValueError("strategy sandbox hypotheses must not allow direct user-facing suggestions")
        return self


class StrategySandboxHypothesisQueue(BaseModel):
    schema_version: str
    generated_at: str
    hypothesis_count: int
    market_coverage: dict[str, int]
    strategy_family_coverage: dict[str, int]
    hypotheses: list[StrategySandboxHypothesis]
    safety: dict[str, bool]
