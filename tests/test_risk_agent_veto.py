"""Phase 3 tests for RiskAgent veto behavior — PHASE3 doc §9.4.

RiskAgent may emit `veto` in Phase 3, but it only records the opinion — it
must never construct a DecisionRecord or RecommendationRecord itself.
"""

from __future__ import annotations

from aegis.experts.context import AnalysisContext
from aegis.experts.risk import RiskAgent
from aegis.models.candidate import Candidate
from aegis.models.common import DataQuality
from aegis.models.expert_opinion import ExpertOpinion
from aegis.models.signal import Signal


def _candidate(liquidity_ok=True, dq_status="complete") -> Candidate:
    return Candidate(
        candidate_id="cand_20260703_US_AAA",
        symbol="AAA",
        market="US",
        source="universe_builder",
        filter_reason=["liquidity_ok"],
        liquidity_ok=liquidity_ok,
        data_quality=DataQuality(status=dq_status),
        created_at="2026-07-03T07:31:00-07:00",
    )


def _risk_signal(flags: list[str], evidence_strength="strong") -> Signal:
    return Signal(
        signal_id="sig_20260703_US_AAA_risk_volatility_drawdown",
        signal_name="risk_volatility_drawdown",
        signal_type="risk",
        symbol="AAA",
        market="US",
        date="2026-07-03",
        value={"volatility": 0.08, "max_drawdown": -0.4, "flags": flags},
        interpretation="fixture risk signal",
        evidence_strength=evidence_strength,
        data_source="tushare",
    )


def test_invalid_data_flag_produces_veto():
    context = AnalysisContext(
        date="2026-07-03", session="pre_market", candidate=_candidate(),
        signals=[_risk_signal(["invalid_bars"])],
    )
    opinion = RiskAgent().analyze(context)
    assert opinion.stance == "veto"


def test_liquidity_not_ok_produces_veto_even_without_risk_signal():
    context = AnalysisContext(
        date="2026-07-03", session="pre_market", candidate=_candidate(liquidity_ok=False),
        signals=[],  # no risk signal at all
    )
    opinion = RiskAgent().analyze(context)
    assert opinion.stance == "veto"
    assert "risk_signal" in opinion.missing_data


def test_missing_data_quality_produces_veto():
    context = AnalysisContext(
        date="2026-07-03", session="pre_market", candidate=_candidate(dq_status="missing"),
        signals=[_risk_signal([])],
    )
    opinion = RiskAgent().analyze(context)
    assert opinion.stance == "veto"


def test_veto_opinion_still_has_evidence_risks_and_missing_data_fields():
    context = AnalysisContext(
        date="2026-07-03", session="pre_market", candidate=_candidate(),
        signals=[_risk_signal(["invalid_bars", "severe_drawdown"])],
    )
    opinion = RiskAgent().analyze(context)

    assert opinion.stance == "veto"
    assert isinstance(opinion.evidence, list)
    assert isinstance(opinion.risks, list)
    assert isinstance(opinion.missing_data, list)
    assert len(opinion.risks) > 0
    assert len(opinion.evidence) > 0  # a real risk signal was referenced


def test_risk_agent_does_not_create_decision_or_recommendation_records():
    context = AnalysisContext(
        date="2026-07-03", session="pre_market", candidate=_candidate(),
        signals=[_risk_signal(["invalid_bars"])],
    )
    opinion = RiskAgent().analyze(context)

    # RiskAgent's contract is "exactly one ExpertOpinion" — nothing else.
    assert isinstance(opinion, ExpertOpinion)
    assert not hasattr(opinion, "final_status")
    assert not hasattr(opinion, "recommendation_status")
