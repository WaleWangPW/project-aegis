"""Strategy candidate update proposals.

API/research inputs may propose candidate updates, but they must never mutate
accepted strategy definitions automatically.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

Market = Literal["A", "H", "US", "GLOBAL"]


class StrategyCandidateUpdateProposal(BaseModel):
    proposal_id: str
    target_strategy_id: str
    source_connector_id: str
    source_fetch_ref: str
    markets: list[Market]
    proposed_research_refs: list[str] = Field(default_factory=list)
    proposed_risk_controls: list[str] = Field(default_factory=list)
    rationale: list[str] = Field(default_factory=list)
    requires_sandbox: bool = True
    auto_applied: bool = False
    user_facing_suggestion_allowed: bool = False
    created_at: str

    @field_validator("proposal_id", "target_strategy_id", "source_connector_id", "source_fetch_ref", "created_at")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("field must not be blank")
        return value

    @model_validator(mode="after")
    def _must_remain_proposal(self) -> "StrategyCandidateUpdateProposal":
        if self.auto_applied:
            raise ValueError("strategy update proposals must not auto-apply")
        if not self.requires_sandbox:
            raise ValueError("strategy update proposals must require sandbox validation")
        if self.user_facing_suggestion_allowed:
            raise ValueError("strategy update proposals must not allow user-facing suggestions directly")
        if not self.markets:
            raise ValueError("at least one market is required")
        return self
