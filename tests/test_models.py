"""Phase 0 model tests.

These only prove the typed skeletons in aegis/models/ can represent the
exact examples given in Project_Aegis_MASTER_SPEC.md, and that the two
acceptance rules encoded as validators actually hold:
- Action requires a non-empty invalidation_conditions list (§8.6).
- risk_veto_triggered=True must block final_status="Action" (§5.5, §8.7).

No business logic, no Tushare, no Decision Engine is exercised here — this
is schema-level testing only, per the Phase 0 boundary.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from aegis.models import (
    Candidate,
    DataQuality,
    DecisionRecord,
    ExpertOpinion,
    Holding,
    InvestmentMemory,
    MarketSnapshot,
    PaperTrade,
    PortfolioSnapshot,
    RecommendationRecord,
    ReviewRecord,
    Signal,
)
from aegis.models.market_snapshot import IndexSummary


def test_market_snapshot_data_gap_example():
    """Reproduces the DATA_GAP example from Master Spec §8.1."""
    snap = MarketSnapshot(
        snapshot_id="mkt_20260703_US_pre_market",
        date="2026-07-03",
        session="pre_market",
        market="US",
        index_summary=IndexSummary(primary_index="SPX", primary_index_change_pct=None),
        trend_state="unknown",
        liquidity_state="unknown",
        sentiment_state="unknown",
        sector_rotation=[],
        risk_level="unknown",
        summary="DATA_GAP: US market data unavailable from configured provider.",
        data_quality=DataQuality(status="partial", missing_fields=["index_change_pct"]),
        created_at="2026-07-03T07:31:00-07:00",
    )
    assert snap.data_quality.status == "partial"
    assert snap.index_summary.primary_index_change_pct is None


def test_holding_crcl_example():
    """Reproduces the CRCL example from Master Spec §8.2 — must be readable
    without asking the user again."""
    holding = Holding(
        holding_id="hold_US_CRCL_20260701",
        symbol="CRCL",
        name="Circle Internet Group",
        market="US",
        shares=254,
        avg_cost=109.157,
        currency="USD",
        entry_date=None,
        current_price=None,
        market_value=None,
        unrealized_pnl=None,
        unrealized_pnl_pct=None,
        linked_recommendation_id=None,
        status="open",
        notes="Initial real holding from Project Aegis handoff.",
    )
    assert holding.symbol == "CRCL"
    assert holding.shares == 254
    assert holding.avg_cost == 109.157


def test_candidate_minimal():
    cand = Candidate(
        candidate_id="cand_20260703_US_CRCL",
        symbol="CRCL",
        market="US",
        source="holding_forced",
        filter_reason=["always_include: current holding"],
        liquidity_ok=True,
        data_quality=DataQuality(status="complete", missing_fields=[]),
        created_at="2026-07-03T07:31:00-07:00",
    )
    assert cand.liquidity_ok is True


def test_signal_unknown_evidence_on_missing_data():
    """A signal must degrade to evidence_strength='unknown', not crash and
    not fabricate a value, when data is missing (Master Spec §8.4)."""
    sig = Signal(
        signal_id="sig_20260703_US_CRCL_trend",
        signal_name="ma_alignment",
        signal_type="trend",
        symbol="CRCL",
        market="US",
        date="2026-07-03",
        value=None,
        interpretation="Insufficient price history to compute MA alignment.",
        evidence_strength="unknown",
        data_source="tushare",
    )
    assert sig.evidence_strength == "unknown"
    assert sig.value is None


def test_expert_opinion_records_missing_data():
    opinion = ExpertOpinion(
        opinion_id="opn_20260703_US_CRCL_trend",
        recommendation_id="rec_20260703_US_CRCL",
        expert_name="TrendAgent",
        stance="neutral",
        confidence=0.4,
        evidence=[],
        risks=["insufficient price history"],
        missing_data=["ma_alignment"],
        summary="Not enough history to form a trend view.",
        created_at="2026-07-03T07:31:00-07:00",
    )
    assert "ma_alignment" in opinion.missing_data


def test_recommendation_action_requires_invalidation_conditions():
    """Master Spec §8.6 acceptance: Action must have a non-empty
    invalidation_conditions list."""
    base_kwargs = dict(
        recommendation_id="rec_20260703_US_CRCL",
        date="2026-07-03",
        session="pre_market",
        symbol="CRCL",
        market="US",
        status="Action",
        action_label="hold",
        market_snapshot_id="mkt_20260703_US_pre_market",
        candidate_id="cand_20260703_US_CRCL",
        confidence=0.7,
        decision_summary="test",
        lifecycle_status="open",
        created_at="2026-07-03T07:31:00-07:00",
        updated_at="2026-07-03T07:31:00-07:00",
    )

    with pytest.raises(ValidationError):
        RecommendationRecord(**base_kwargs, invalidation_conditions=[])

    # Should succeed once a real invalidation condition is present.
    rec = RecommendationRecord(**base_kwargs, invalidation_conditions=["breaks below MA60"])
    assert rec.status == "Action"


def test_decision_record_veto_blocks_action():
    """Master Spec §5.5 / §8.7 acceptance: risk veto must block Action."""
    with pytest.raises(ValidationError):
        DecisionRecord(
            decision_id="dec_20260703_US_CRCL",
            recommendation_id="rec_20260703_US_CRCL",
            final_status="Action",
            final_action="hold",
            support_count=5,
            oppose_count=0,
            neutral_count=1,
            veto_count=1,
            risk_veto_triggered=True,
            confidence=0.2,
            decision_reason="test",
            invalidation_conditions=["breaks below MA60"],
            created_at="2026-07-03T07:31:00-07:00",
        )

    # Same facts but veto not triggered -> Action is fine.
    dec = DecisionRecord(
        decision_id="dec_20260703_US_CRCL",
        recommendation_id="rec_20260703_US_CRCL",
        final_status="Action",
        final_action="hold",
        support_count=5,
        oppose_count=0,
        neutral_count=1,
        veto_count=0,
        risk_veto_triggered=False,
        confidence=0.7,
        decision_reason="test",
        invalidation_conditions=["breaks below MA60"],
        created_at="2026-07-03T07:31:00-07:00",
    )
    assert dec.final_status == "Action"


def test_paper_trade_requires_real_entry_price():
    """Master Spec §16.1: no fabricated entry_price. Pydantic enforces the
    field is required; this test documents that expectation."""
    with pytest.raises(ValidationError):
        PaperTrade(
            paper_trade_id="ptr_1",
            recommendation_id="rec_20260703_US_CRCL",
            symbol="CRCL",
            market="US",
            direction="long",
            entry_date="2026-07-03",
            # entry_price intentionally omitted
            virtual_position_size=10000,
            status="open",
            created_at="2026-07-03T07:31:00-07:00",
            updated_at="2026-07-03T07:31:00-07:00",
        )


def test_review_record_evaluates_decision_quality_not_only_return():
    review = ReviewRecord(
        review_id="rev_1",
        recommendation_id="rec_20260703_US_CRCL",
        review_date="2026-07-10",
        horizon="5d",
        outcome="mixed",
        actual_return=-0.02,
        decision_quality="good_decision",
        failure_reason="Market-wide drawdown, thesis intact.",
        expert_contribution={"TrendAgent": "support"},
        lessons=["Don't confuse a bad week with a bad decision."],
        created_at="2026-07-10T07:00:00-07:00",
    )
    assert review.decision_quality == "good_decision"
    assert review.actual_return == -0.02


def test_portfolio_snapshot_and_memory_minimal():
    snap = PortfolioSnapshot(
        snapshot_id="pf_20260703",
        date="2026-07-03",
        total_cost=27725.878,
        market_allocation={"US": 1.0},
        sector_allocation={"fintech": 1.0},
        risk_level="unknown",
        summary="Single holding (CRCL), no market data connected yet.",
    )
    assert snap.total_cost == pytest.approx(254 * 109.157)

    memory = InvestmentMemory(
        memory_id="mem_1",
        date="2026-07-03",
        source_type="handoff",
        lesson_type="process",
        lesson="Phase 0 skeleton created before any real data pipeline.",
        tags=["phase0"],
        confidence=1.0,
        created_at="2026-07-03T07:31:00-07:00",
    )
    assert "phase0" in memory.tags
