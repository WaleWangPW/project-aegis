"""Phase 4 tests for RecommendationRepository — PHASE4 doc §11.5."""

from __future__ import annotations

from pathlib import Path

from aegis.models.decision import DecisionRecord
from aegis.models.recommendation import RecommendationRecord
from aegis.recommendation.repository import RecommendationRepository


def _decision(decision_id="dec_1") -> DecisionRecord:
    return DecisionRecord(
        decision_id=decision_id,
        recommendation_id="rec_1",
        final_status="Ready",
        final_action="prepare_entry_plan",
        support_count=2,
        oppose_count=0,
        neutral_count=5,
        veto_count=0,
        risk_veto_triggered=False,
        confidence=0.6,
        decision_reason="fixture",
        invalidation_conditions=["fixture invalidation"],
        created_at="2026-07-03T07:31:00-07:00",
    )


def _recommendation(recommendation_id="rec_1") -> RecommendationRecord:
    return RecommendationRecord(
        recommendation_id=recommendation_id,
        date="2026-07-03",
        session="pre_market",
        symbol="AAA",
        market="US",
        status="Ready",
        action_label="prepare_entry_plan",
        market_snapshot_id="mkt_20260703_US_pre_market",
        candidate_id="cand_20260703_US_AAA",
        expert_opinions=["opn_1"],
        support_reasons=["fixture support"],
        oppose_reasons=[],
        risks=[],
        invalidation_conditions=["fixture invalidation"],
        confidence=0.6,
        decision_summary="fixture",
        paper_trade_id=None,
        review_id=None,
        lifecycle_status="open",
        created_at="2026-07-03T07:31:00-07:00",
        updated_at="2026-07-03T07:31:00-07:00",
    )


def test_decisions_and_recommendations_append_to_jsonl(tmp_path: Path):
    repo = RecommendationRepository(tmp_path / "records")
    repo.append_decision(_decision())
    repo.append_recommendation(_recommendation())

    assert (tmp_path / "records" / "decisions.jsonl").exists()
    assert (tmp_path / "records" / "recommendations.jsonl").exists()


def test_parent_directories_are_created(tmp_path: Path):
    nested = tmp_path / "a" / "b" / "c"
    repo = RecommendationRepository(nested)
    repo.append_decision(_decision())
    assert (nested / "decisions.jsonl").exists()


def test_records_can_be_read_back(tmp_path: Path):
    repo = RecommendationRepository(tmp_path / "records")
    repo.append_decision(_decision("dec_1"))
    repo.append_decision(_decision("dec_2"))
    repo.append_recommendation(_recommendation("rec_1"))

    decisions = repo.list_decisions()
    recommendations = repo.list_recommendations()

    assert {d.decision_id for d in decisions} == {"dec_1", "dec_2"}
    assert all(isinstance(d, DecisionRecord) for d in decisions)
    assert len(recommendations) == 1
    assert isinstance(recommendations[0], RecommendationRecord)


def test_repository_requires_no_database_just_files(tmp_path: Path):
    records_dir = tmp_path / "records"
    repo = RecommendationRepository(records_dir)
    # Reading before anything is written should not error or require setup.
    assert repo.list_decisions() == []
    assert repo.list_recommendations() == []
    repo.append_recommendation(_recommendation())
    assert len(repo.list_recommendations()) == 1
