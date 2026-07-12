"""Phase 4 tests for DecisionEngine — PHASE4 doc §11.2."""

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


def _snapshot(risk="low") -> MarketSnapshot:
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
        evidence=[f"signal:sig_fixture_{expert_name.lower()}"],
        risks=[],
        missing_data=[],
        summary=f"fixture {stance}",
        created_at="2026-07-03T07:31:00-07:00",
    )


def _opinions(stances: dict[str, str], confidences: dict[str, float] | None = None) -> list[ExpertOpinion]:
    confidences = confidences or {}
    return [_opinion(name, stances.get(name, "neutral"), confidences.get(name, 0.6)) for name in ALL_AGENTS]


def test_three_supports_no_veto_good_data_becomes_action():
    stances = {"MarketRegimeAgent": "support", "TrendAgent": "support", "RiskAgent": "support"}
    opinions = _opinions(stances)

    decision, recommendation = DecisionEngine().decide(
        market_snapshot=_snapshot(), candidate=_candidate(), expert_opinions=opinions, holding=None
    )

    assert decision.final_status == "Action"
    assert recommendation.status == "Action"
    assert decision.risk_veto_triggered is False


def test_two_supports_becomes_ready():
    stances = {"TrendAgent": "support", "RiskAgent": "support"}
    opinions = _opinions(stances, confidences={"TrendAgent": 0.6, "RiskAgent": 0.6})

    decision, _ = DecisionEngine().decide(
        market_snapshot=_snapshot(), candidate=_candidate(), expert_opinions=opinions, holding=None
    )

    assert decision.final_status == "Ready"


def test_weak_evidence_becomes_watch():
    opinions = _opinions({}, confidences={name: 0.4 for name in ALL_AGENTS})  # all neutral

    decision, _ = DecisionEngine().decide(
        market_snapshot=_snapshot(), candidate=_candidate(), expert_opinions=opinions, holding=None
    )

    assert decision.final_status == "Watch"


def test_timing_oppose_caps_status_at_ready_even_with_strong_support():
    stances = {
        "MarketRegimeAgent": "support",
        "TrendAgent": "support",
        "FundamentalAgent": "support",
        "RiskAgent": "support",
        "TimingAgent": "oppose",
    }
    opinions = _opinions(stances)

    decision, _ = DecisionEngine().decide(
        market_snapshot=_snapshot(), candidate=_candidate(), expert_opinions=opinions, holding=None
    )

    assert decision.final_status == "Ready"


def test_bad_market_downgrades_status_one_level():
    stances = {"MarketRegimeAgent": "support", "TrendAgent": "support", "RiskAgent": "support"}
    opinions = _opinions(stances)

    decision_good_market, _ = DecisionEngine().decide(
        market_snapshot=_snapshot(risk="low"), candidate=_candidate(), expert_opinions=opinions, holding=None
    )
    decision_bad_market, _ = DecisionEngine().decide(
        market_snapshot=_snapshot(risk="high"), candidate=_candidate(), expert_opinions=opinions, holding=None
    )

    assert decision_good_market.final_status == "Action"
    assert decision_bad_market.final_status == "Ready"  # downgraded one level from Action
