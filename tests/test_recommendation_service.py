"""Phase 4 tests for RecommendationService — PHASE4 doc §11.4."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from aegis.models.candidate import Candidate
from aegis.models.common import DataQuality
from aegis.models.decision import DecisionRecord
from aegis.models.expert_opinion import ExpertOpinion
from aegis.models.market_snapshot import IndexSummary, MarketSnapshot
from aegis.recommendation.service import RecommendationService


def _candidate() -> Candidate:
    return Candidate(
        candidate_id="cand_20260703_US_AAA",
        symbol="AAA",
        name="Fixture Corp",
        market="US",
        sector="Fintech",
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


def _opinion(expert_name, stance, risks=None, missing_data=None) -> ExpertOpinion:
    return ExpertOpinion(
        opinion_id=f"opn_20260703_US_AAA_{expert_name.lower()}",
        recommendation_id="rec_20260703_pre_market_US_AAA",
        expert_name=expert_name,
        stance=stance,
        confidence=0.6,
        evidence=[f"signal:sig_fixture_{expert_name.lower()}"],
        risks=risks or [],
        missing_data=missing_data or [],
        summary=f"fixture {stance}",
        created_at="2026-07-03T07:31:00-07:00",
    )


def _decision(status="Ready", invalidation_conditions=None) -> DecisionRecord:
    return DecisionRecord(
        decision_id="dec_20260703_pre_market_US_AAA",
        recommendation_id="rec_20260703_pre_market_US_AAA",
        final_status=status,
        final_action="prepare_entry_plan",
        support_count=2,
        oppose_count=1,
        neutral_count=4,
        veto_count=0,
        risk_veto_triggered=False,
        confidence=0.6,
        decision_reason="fixture decision reason",
        invalidation_conditions=invalidation_conditions if invalidation_conditions is not None else ["fixture invalidation"],
        created_at="2026-07-03T07:31:00-07:00",
    )


def test_recommendation_contains_candidate_market_and_opinion_references():
    candidate = _candidate()
    snapshot = _snapshot()
    opinions = [_opinion("TrendAgent", "support"), _opinion("RiskAgent", "oppose")]

    record = RecommendationService().create_from_decision(
        decision=_decision(), candidate=candidate, market_snapshot=snapshot, opinions=opinions
    )

    assert record.candidate_id == candidate.candidate_id
    assert record.market_snapshot_id == snapshot.snapshot_id
    assert record.symbol == candidate.symbol
    assert record.market == candidate.market
    assert set(record.expert_opinions) == {o.opinion_id for o in opinions}


def test_support_reasons_include_source_opinion_ids():
    trend_opinion = _opinion("TrendAgent", "support")
    record = RecommendationService().create_from_decision(
        decision=_decision(), candidate=_candidate(), market_snapshot=_snapshot(), opinions=[trend_opinion]
    )

    assert len(record.support_reasons) == 1
    assert trend_opinion.opinion_id in record.support_reasons[0]
    assert "source_opinion_id=" in record.support_reasons[0]


def test_oppose_reasons_are_preserved():
    risk_opinion = _opinion("RiskAgent", "oppose", risks=["high_volatility"])
    record = RecommendationService().create_from_decision(
        decision=_decision(), candidate=_candidate(), market_snapshot=_snapshot(), opinions=[risk_opinion]
    )

    assert any(risk_opinion.opinion_id in reason for reason in record.oppose_reasons)
    assert "high_volatility" in record.risks


def test_action_without_invalidation_conditions_raises_rather_than_silently_downgrading():
    decision = _decision(status="Action", invalidation_conditions=[])

    with pytest.raises(ValidationError):
        RecommendationService().create_from_decision(
            decision=decision, candidate=_candidate(), market_snapshot=_snapshot(), opinions=[]
        )


def test_paper_trade_id_and_review_id_are_none_in_phase4():
    record = RecommendationService().create_from_decision(
        decision=_decision(), candidate=_candidate(), market_snapshot=_snapshot(), opinions=[]
    )

    assert record.paper_trade_id is None
    assert record.review_id is None
    assert record.lifecycle_status == "open"
