"""Simulation-only suggestion drafts.

SuggestionDraft is a gated user-facing draft. It is not an order, not broker
execution, and not a substitute for the user's own final decision.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

Market = Literal["A", "H", "US"]
SuggestionAction = Literal["paper_entry_candidate", "paper_watch", "blocked"]


class SuggestionOpportunity(BaseModel):
    opportunity_id: str
    strategy_id: str
    symbol: str
    market: Market
    name: str | None = None
    risk_veto: bool = False
    evidence_refs: list[str] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)
    risk_warnings: list[str] = Field(default_factory=list)

    @field_validator("opportunity_id", "strategy_id", "symbol")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("field must not be blank")
        return value


class SuggestionDraft(BaseModel):
    suggestion_id: str
    opportunity_id: str
    strategy_id: str
    symbol: str
    market: Market
    action: SuggestionAction
    simulation_only: bool = True
    user_must_execute_externally: bool = True
    reasons: list[str] = Field(default_factory=list)
    risk_warnings: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    blocked_by: list[str] = Field(default_factory=list)
    created_at: str

    @model_validator(mode="after")
    def _blocked_requires_reason(self) -> "SuggestionDraft":
        if self.action == "blocked" and not self.blocked_by:
            raise ValueError("blocked suggestions require blocked_by reasons")
        if self.action != "blocked" and self.blocked_by:
            raise ValueError("non-blocked suggestions must not carry blocked_by")
        if not self.simulation_only or not self.user_must_execute_externally:
            raise ValueError("suggestions must remain simulation-only and manually executed by user elsewhere")
        return self
