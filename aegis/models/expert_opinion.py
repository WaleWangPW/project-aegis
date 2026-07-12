"""ExpertOpinion — Master Spec §8.5.

One expert's opinion on one candidate/recommendation. `stance` is a plain
vote (support/oppose/neutral/veto) — never a numeric score, per the
"no composite scoring" principle (Master Spec §5.6, ADR-002).
Produced by: the 7 Expert Agents (Phase 3): MarketRegimeAgent, TrendAgent,
FundamentalAgent, CapitalFlowAgent, SectorAgent, TimingAgent, RiskAgent.
Consumed by: DecisionEngine, ReviewService, DashboardBuilder (later phases).
Storage: data/records/expert_opinions.jsonl.

Acceptance: every opinion must record missing_data explicitly — hiding a
data gap is not allowed.
"""

from __future__ import annotations

from pydantic import BaseModel

from .common import Stance


class ExpertOpinion(BaseModel):
    opinion_id: str
    recommendation_id: str
    expert_name: str
    stance: Stance
    confidence: float
    evidence: list[str]
    risks: list[str]
    missing_data: list[str]
    summary: str
    created_at: str
