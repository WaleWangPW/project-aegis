"""Candidate — Master Spec §8.3.

A candidate stock that has passed basic universe filters.
Produced by: UniverseBuilder (Phase 2).
Consumed by: SignalLibrary, ExpertCommittee, DecisionEngine (later phases).
Storage: data/processed/YYYY-MM-DD/candidates_*.json, optionally
data/records/candidates.jsonl.

Acceptance: current holdings must always be forced into the candidate set,
even if they would otherwise fail a filter (holdings.always_include in
config/universe.yaml).
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from .common import DataQuality, Market


class Candidate(BaseModel):
    candidate_id: str
    symbol: str
    name: Optional[str] = None
    market: Market
    sector: Optional[str] = None
    source: str = Field(..., description='e.g. "universe_builder", "holding_forced"')
    filter_reason: list[str] = Field(default_factory=list)
    liquidity_ok: bool
    data_quality: DataQuality
    created_at: str
