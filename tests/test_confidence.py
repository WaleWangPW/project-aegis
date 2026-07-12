"""Phase 4 tests for compute_decision_confidence — PHASE4 doc §11.1."""

from __future__ import annotations

from aegis.decision.confidence import compute_decision_confidence
from aegis.models.candidate import Candidate
from aegis.models.common import DataQuality
from aegis.models.expert_opinion import ExpertOpinion
from aegis.models.market_snapshot import IndexSummary, MarketSnapshot


def _candidate(dq_status="complete", liquidity_ok=True) -> Candidate:
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


def _snapshot(trend="uptrend", risk="low") -> MarketSnapshot:
    return MarketSnapshot(
        snapshot_id="mkt_20260703_US_pre_market",
        date="2026-07-03",
        session="pre_market",
        market="US",
        index_summary=IndexSummary(primary_index="SPX", primary_index_change_pct=0.01),
        trend_state=trend,
        liquidity_state="normal",
        sentiment_state="risk_on",
        sector_rotation=[],
        risk_level=risk,
        summary="test snapshot",
        data_quality=DataQuality(status="complete"),
        created_at="2026-07-03T07:31:00-07:00",
    )


def _opinion(expert_name, stance, confidence=0.6) -> ExpertOpinion:
    return ExpertOpinion(
        opinion_id=f"opn_20260703_US_AAA_{expert_name.lower()}",
        recommendation_id="rec_20260703_pre_market_US_AAA",
        expert_name=expert_name,
        stance=stance,
        confidence=confidence,
        evidence=[],
        risks=[],
        missing_data=[],
        summary="fixture",
        created_at="2026-07-03T07:31:00-07:00",
    )


ALL_SUPPORT = [
    _opinion("MarketRegimeAgent", "support", 0.7),
    _opinion("TrendAgent", "support", 0.7),
    _opinion("FundamentalAgent", "support", 0.6),
    _opinion("CapitalFlowAgent", "support", 0.6),
    _opinion("SectorAgent", "support", 0.6),
    _opinion("TimingAgent", "support", 0.6),
    _opinion("RiskAgent", "support", 0.6),
]

MOSTLY_NEUTRAL = [_opinion(name, "neutral", 0.4) for name in ["MarketRegimeAgent", "TrendAgent", "FundamentalAgent", "CapitalFlowAgent", "SectorAgent", "TimingAgent", "RiskAgent"]]


def test_support_consistency_increases_confidence():
    high = compute_decision_confidence(
        expert_opinions=ALL_SUPPORT, market_snapshot=_snapshot(), candidate=_candidate(), has_critical_data=True
    )
    low = compute_decision_confidence(
        expert_opinions=MOSTLY_NEUTRAL, market_snapshot=_snapshot(), candidate=_candidate(), has_critical_data=True
    )
    assert high > low


def test_unknown_evidence_lowers_confidence():
    known_confidence = compute_decision_confidence(
        expert_opinions=ALL_SUPPORT, market_snapshot=_snapshot(), candidate=_candidate(), has_critical_data=True
    )
    unknown_evidence = [_opinion(name, "neutral", 0.0) for name in ["TrendAgent", "RiskAgent"]]
    unknown_confidence = compute_decision_confidence(
        expert_opinions=unknown_evidence, market_snapshot=_snapshot(), candidate=_candidate(), has_critical_data=True
    )
    assert unknown_confidence < known_confidence


def test_veto_caps_confidence_at_or_below_0_25():
    opinions = ALL_SUPPORT[:-1] + [_opinion("RiskAgent", "veto", 0.9)]
    confidence = compute_decision_confidence(
        expert_opinions=opinions, market_snapshot=_snapshot(), candidate=_candidate(), has_critical_data=True
    )
    assert confidence <= 0.25


def test_missing_critical_data_caps_confidence_at_or_below_0_45():
    confidence = compute_decision_confidence(
        expert_opinions=ALL_SUPPORT, market_snapshot=_snapshot(), candidate=_candidate(), has_critical_data=False
    )
    assert confidence <= 0.45


def test_confidence_is_always_bounded_0_to_1():
    scenarios = [ALL_SUPPORT, MOSTLY_NEUTRAL, [], ALL_SUPPORT[:-1] + [_opinion("RiskAgent", "veto", 1.0)]]
    for opinions in scenarios:
        for has_critical in (True, False):
            confidence = compute_decision_confidence(
                expert_opinions=opinions, market_snapshot=_snapshot(), candidate=_candidate(), has_critical_data=has_critical
            )
            assert 0.0 <= confidence <= 1.0
