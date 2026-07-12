"""compute_decision_confidence — Phase 4 §7.

Confidence measures *decision reliability*, not expected return or stock
attractiveness (Master Spec ADR-002 / PHASE4 doc §5.4 rule 8: "No composite
score. Confidence is allowed only as decision-reliability metadata."). It is
a simple, deterministic blend of the components the doc lists as "Allowed",
followed by hard caps — never a weighted formula tuned to make a stock look
more attractive.
"""

from __future__ import annotations

from typing import Optional

from aegis.models.candidate import Candidate
from aegis.models.expert_opinion import ExpertOpinion
from aegis.models.market_snapshot import MarketSnapshot

_DATA_QUALITY_SCORES = {"complete": 1.0, "partial": 0.65, "poor": 0.35, "missing": 0.0, "unavailable": 0.0}
_RISK_STANCE_SCORES = {"veto": 0.0, "oppose": 0.5, "neutral": 0.75, "support": 1.0}
_HISTORICAL_RELIABILITY_DEFAULT = 1.0  # P0: interface only, no real history DB yet


def _data_quality_score(status: str) -> float:
    return _DATA_QUALITY_SCORES.get(status, 0.35)  # unrecognized status -> treat as "poor"


def _evidence_quality_score(expert_opinions: list[ExpertOpinion]) -> float:
    if not expert_opinions:
        return 0.25
    avg_conf = sum(o.confidence for o in expert_opinions) / len(expert_opinions)
    if avg_conf >= 0.65:
        return 1.0
    if avg_conf >= 0.5:
        return 0.75
    if avg_conf >= 0.3:
        return 0.5
    return 0.25


def _expert_consistency_score(expert_opinions: list[ExpertOpinion]) -> float:
    non_neutral = [o for o in expert_opinions if o.stance != "neutral"]
    if not non_neutral:
        return 0.25  # nothing decisive at all
    support = sum(1 for o in non_neutral if o.stance == "support")
    return support / len(non_neutral)


def _risk_factor_score(expert_opinions: list[ExpertOpinion]) -> float:
    risk_opinion = next((o for o in expert_opinions if o.expert_name == "RiskAgent"), None)
    if risk_opinion is None:
        return 0.75  # risk stance unknown -> treat like "neutral"
    return _RISK_STANCE_SCORES.get(risk_opinion.stance, 0.75)


def compute_decision_confidence(
    *,
    expert_opinions: list[ExpertOpinion],
    market_snapshot: Optional[MarketSnapshot],
    candidate: Candidate,
    has_critical_data: bool,
) -> float:
    components = [
        _expert_consistency_score(expert_opinions),
        _evidence_quality_score(expert_opinions),
        _data_quality_score(candidate.data_quality.status),
        _risk_factor_score(expert_opinions),
        _HISTORICAL_RELIABILITY_DEFAULT,
    ]
    confidence = sum(components) / len(components)

    has_veto = any(o.stance == "veto" for o in expert_opinions)
    if has_veto:
        confidence = min(confidence, 0.25)

    if not has_critical_data:
        confidence = min(confidence, 0.45)

    market_unknown = (
        market_snapshot is None
        or market_snapshot.risk_level == "unknown"
        or market_snapshot.trend_state == "unknown"
    )
    if market_unknown:
        confidence = min(confidence, 0.50)

    return max(0.0, min(1.0, confidence))
