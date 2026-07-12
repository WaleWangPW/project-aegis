"""Phase 4 tests for Risk veto behavior in DecisionEngine — PHASE4 doc §11.3."""

from __future__ import annotations

from aegis.decision.engine import DecisionEngine
from aegis.models.candidate import Candidate
from aegis.models.common import DataQuality
from aegis.models.expert_opinion import ExpertOpinion
from aegis.models.market_snapshot import IndexSummary, MarketSnapshot

ALL_AGENTS = [
    "MarketRegimeAgent",
    "TrendAgent",
    "FundamentalAgent",
    "CapitalFlowAgent",
    "SectorAgent",
    "TimingAgent",
    "RiskAgent",
]


def _candidate() -> Candidate:
    return Candidate(
        candidate_id="cand_20260703_US_AAA",
        symbol="AAA",
        market="US",
        source="universe_builder",
        filter_reason=["liquidity_ok"],
        liquidity_ok=True,
        data_quality=DataQuality(status="complete"),
        created_at="2026-07-03T07:31:00-07:00",
    )


def _snapshot() -> MarketSnapshot:
    return MarketSnapshot(
        snapshot_id="mkt_20260703_US_pre_market",
        date="2026-07-03",
        session="pre_market",
        market="US",
        index_summary=IndexSummary(primary_index="SPX", primary_index_change_pct=0.01),
        trend_state="uptrend",
        liquidity_state="normal",
        sentiment_state="risk_on",
        sector_rotation=[],
        risk_level="low",
        summary="test snapshot",
        data_quality=DataQuality(status="complete"),
        created_at="2026-07-03T07:31:00-07:00",
    )


def _opinion(expert_name, stance, confidence=0.7, risks=None) -> ExpertOpinion:
    return ExpertOpinion(
        opinion_id=f"opn_20260703_US_AAA_{expert_name.lower()}",
        recommendation_id="rec_20260703_pre_market_US_AAA",
        expert_name=expert_name,
        stance=stance,
        confidence=confidence,
        evidence=[f"signal:sig_fixture_{expert_name.lower()}"],
        risks=risks or [],
        missing_data=[],
        summary=f"fixture {stance}",
        created_at="2026-07-03T07:31:00-07:00",
    )


def test_risk_veto_blocks_action_even_if_all_others_support():
    opinions = [_opinion(name, "support") for name in ALL_AGENTS if name != "RiskAgent"]
    opinions.append(_opinion("RiskAgent", "veto", risks=["severe_drawdown", "high_volatility"]))

    decision, recommendation = DecisionEngine().decide(
        market_snapshot=_snapshot(), candidate=_candidate(), expert_opinions=opinions, holding=None
    )

    assert decision.final_status != "Action"
    assert recommendation.status != "Action"


def test_decision_record_risk_veto_triggered_is_true():
    opinions = [_opinion(name, "support") for name in ALL_AGENTS if name != "RiskAgent"]
    opinions.append(_opinion("RiskAgent", "veto"))

    decision, _ = DecisionEngine().decide(
        market_snapshot=_snapshot(), candidate=_candidate(), expert_opinions=opinions, holding=None
    )

    assert decision.risk_veto_triggered is True


def test_veto_reason_is_preserved_in_recommendation_risks_and_oppose_reasons():
    opinions = [_opinion(name, "support") for name in ALL_AGENTS if name != "RiskAgent"]
    opinions.append(_opinion("RiskAgent", "veto", risks=["severe_drawdown", "high_volatility"]))

    _, recommendation = DecisionEngine().decide(
        market_snapshot=_snapshot(), candidate=_candidate(), expert_opinions=opinions, holding=None
    )

    assert "severe_drawdown" in recommendation.risks
    assert "high_volatility" in recommendation.risks
    assert any("RiskAgent" in reason and "veto" in reason for reason in recommendation.oppose_reasons)
