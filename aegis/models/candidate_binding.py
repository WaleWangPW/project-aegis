"""Candidate bindings for simulation-only suggestion drafts."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from aegis.models.common import Market

BindingStatus = Literal["bound", "blocked"]


class BoundCandidate(BaseModel):
    symbol: str
    market: Market
    name: str | None = None
    source: str
    score: float | None = None
    status: str | None = None
    evidence_refs: list[str] = Field(default_factory=list)

    @field_validator("symbol", "source")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("field must not be blank")
        return value


class SuggestionCandidateBinding(BaseModel):
    binding_id: str
    suggestion_id: str
    strategy_id: str
    market: Market
    binding_status: BindingStatus
    bound_candidates: list[BoundCandidate] = Field(default_factory=list)
    blocked_by: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    simulation_only: bool = True
    user_must_execute_externally: bool = True
    no_live_order: bool = True
    created_at: str

    @model_validator(mode="after")
    def _status_consistency(self) -> "SuggestionCandidateBinding":
        if self.binding_status == "bound" and not self.bound_candidates:
            raise ValueError("bound bindings require candidates")
        if self.binding_status == "blocked" and not self.blocked_by:
            raise ValueError("blocked bindings require blocked_by reasons")
        if self.binding_status == "bound" and self.blocked_by:
            raise ValueError("bound bindings must not carry blocked_by reasons")
        if not self.simulation_only or not self.user_must_execute_externally or not self.no_live_order:
            raise ValueError("candidate bindings must remain simulation-only and manually executed externally")
        return self

