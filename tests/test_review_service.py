"""Phase 6 tests for ReviewService — PHASE6 doc §5.4/§7.2.

Fixture data only (RecommendationRecord/DecisionRecord/PaperTrade/
ExpertOpinion), tmp_path-isolated repositories, no real Tushare/network.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from aegis.models.decision import DecisionRecord
from aegis.models.paper_trade import PaperTrade
from aegis.models.recommendation import RecommendationRecord
from aegis.paper.repository import PaperTradeRepository
from aegis.recommendation.repository import RecommendationRepository
from aegis.review.repository import ReviewRepository
from aegis.review.service import ReviewService
from aegis.utils.jsonl import append_jsonl


def _now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def _recommendation(
    *,
    rec_id="rec_20260701_pre_market_US_AAA",
    symbol="AAA",
    market="US",
    support_reasons=None,
    invalidation_conditions=None,
) -> RecommendationRecord:
    return RecommendationRecord(
        recommendation_id=rec_id,
        date="2026-07-01",
        session="pre_market",
        symbol=symbol,
        market=market,
        sector="Fintech",
        status="Action",
        action_label="prepare_entry_plan",
        market_snapshot_id="mkt_20260701_US_pre_market",
        candidate_id=f"cand_20260701_{market}_{symbol}",
        expert_opinions=["opn_1", "opn_2"],
        support_reasons=support_reasons if support_reasons is not None else ["TrendAgent support: fixture (source_opinion_id=opn_1)"],
        oppose_reasons=[],
        risks=[],
        invalidation_conditions=invalidation_conditions if invalidation_conditions is not None else ["fixture invalidation"],
        confidence=0.7,
        decision_summary="fixture decision summary",
        lifecycle_status="open",
        created_at=_now(),
        updated_at=_now(),
    )


def _decision(rec_id: str, risk_veto_triggered: bool = False) -> DecisionRecord:
    return DecisionRecord(
        decision_id=f"dec_{rec_id}",
        recommendation_id=rec_id,
        final_status="Action",
        final_action="prepare_entry_plan",
        support_count=3,
        oppose_count=0,
        neutral_count=1,
        veto_count=1 if risk_veto_triggered else 0,
        risk_veto_triggered=risk_veto_triggered,
        confidence=0.7,
        decision_reason="fixture",
        invalidation_conditions=["fixture invalidation"],
        created_at=_now(),
    )


def _trade(
    *,
    rec_id="rec_20260701_pre_market_US_AAA",
    symbol="AAA",
    market="US",
    return_5d=None,
    status="open",
) -> PaperTrade:
    return PaperTrade(
        paper_trade_id=f"ptr_{rec_id}",
        recommendation_id=rec_id,
        symbol=symbol,
        market=market,
        direction="long",
        entry_date="2026-07-01",
        entry_price=100.0,
        virtual_position_size=1.0,
        status=status,
        return_5d=return_5d,
        updated_at=_now(),
        created_at=_now(),
    )


def _setup(tmp_path: Path):
    records_dir = tmp_path / "records"
    recommendation_repository = RecommendationRepository(records_dir)
    paper_repository = PaperTradeRepository(records_dir)
    review_repository = ReviewRepository(records_dir)
    service = ReviewService(
        review_repository=review_repository,
        paper_repository=paper_repository,
        recommendation_repository=recommendation_repository,
        records_dir=records_dir,
    )
    return service, recommendation_repository, paper_repository, review_repository, records_dir


def test_due_review_generated_from_paper_trade(tmp_path: Path):
    service, rec_repo, paper_repo, review_repo, _ = _setup(tmp_path)
    rec = _recommendation()
    rec_repo.append_recommendation(rec)
    rec_repo.append_decision(_decision(rec.recommendation_id))
    paper_repo.append(_trade(return_5d=0.05))

    generated = service.generate_due_reviews(date="2026-07-06")

    assert len(generated) == 1
    assert generated[0].horizon == "5d"
    assert generated[0].recommendation_id == rec.recommendation_id
    assert review_repo.list_all() == generated


def test_duplicate_review_for_same_recommendation_and_horizon_not_created(tmp_path: Path):
    service, rec_repo, paper_repo, review_repo, _ = _setup(tmp_path)
    rec = _recommendation()
    rec_repo.append_recommendation(rec)
    rec_repo.append_decision(_decision(rec.recommendation_id))
    paper_repo.append(_trade(return_5d=0.05))

    first_batch = service.generate_due_reviews(date="2026-07-06")
    second_batch = service.generate_due_reviews(date="2026-07-06")

    assert len(first_batch) == 1
    assert len(second_batch) == 0  # already exists for (recommendation_id, "5d")
    assert len(review_repo.list_all()) == 1


def test_incomplete_trade_produces_pending_inconclusive_review(tmp_path: Path):
    service, rec_repo, paper_repo, review_repo, _ = _setup(tmp_path)
    rec = _recommendation()
    rec_repo.append_recommendation(rec)
    rec_repo.append_decision(_decision(rec.recommendation_id))

    # review_recommendation called directly for a horizon that has no data yet.
    review = service.review_recommendation(rec, "10d")

    assert review.outcome == "pending"  # stands in for "inconclusive"
    assert review.decision_quality == "unclear"  # stands in for "unknown"


def test_decision_quality_not_purely_equal_to_return(tmp_path: Path):
    service, rec_repo, paper_repo, review_repo, _ = _setup(tmp_path)

    # Solid process (support + invalidation conditions, no veto) but a loss:
    # should be "reasonable_decision", NOT "poor_decision" just because return < 0.
    rec_good_process = _recommendation(rec_id="rec_good_process")
    rec_repo.append_recommendation(rec_good_process)
    rec_repo.append_decision(_decision(rec_good_process.recommendation_id))
    paper_repo.append(_trade(rec_id=rec_good_process.recommendation_id, return_5d=-0.05))
    review_loss = service.review_recommendation(rec_good_process, "5d")
    assert review_loss.actual_return == -0.05
    assert review_loss.decision_quality == "reasonable_decision"

    # Thin process (no support_reasons — invalidation_conditions must stay
    # non-empty here since RecommendationRecord itself forbids an "Action"
    # status with an empty invalidation_conditions list) with a gain:
    # should NOT automatically be "good_decision".
    rec_thin = _recommendation(rec_id="rec_thin_process", support_reasons=[])
    rec_repo.append_recommendation(rec_thin)
    rec_repo.append_decision(_decision(rec_thin.recommendation_id))
    paper_repo.append(_trade(rec_id=rec_thin.recommendation_id, symbol="BBB", return_5d=0.05))
    review_gain_thin = service.review_recommendation(rec_thin, "5d")
    assert review_gain_thin.actual_return == 0.05
    assert review_gain_thin.decision_quality == "reasonable_decision"
    assert review_gain_thin.decision_quality != "good_decision"


def test_review_metrics_compute_action_success_rate_and_average_return(tmp_path: Path):
    service, rec_repo, paper_repo, review_repo, _ = _setup(tmp_path)
    rec_a = _recommendation(rec_id="rec_a", symbol="AAA")
    rec_b = _recommendation(rec_id="rec_b", symbol="BBB")
    rec_repo.append_recommendation(rec_a)
    rec_repo.append_recommendation(rec_b)
    rec_repo.append_decision(_decision(rec_a.recommendation_id))
    rec_repo.append_decision(_decision(rec_b.recommendation_id))
    paper_repo.append(_trade(rec_id=rec_a.recommendation_id, symbol="AAA", return_5d=0.10))
    paper_repo.append(_trade(rec_id=rec_b.recommendation_id, symbol="BBB", return_5d=-0.02))

    service.generate_due_reviews(date="2026-07-06")
    metrics = service.compute_metrics()

    assert metrics["review_count"] == 2
    assert round(metrics["action_success_rate"], 4) == 0.5
    assert round(metrics["average_return"], 4) == round((0.10 - 0.02) / 2, 4)


def test_expert_contribution_handles_missing_opinion_data_honestly(tmp_path: Path):
    service, rec_repo, paper_repo, review_repo, records_dir = _setup(tmp_path)
    rec = _recommendation()
    rec_repo.append_recommendation(rec)
    rec_repo.append_decision(_decision(rec.recommendation_id))
    paper_repo.append(_trade(return_5d=0.05))
    # Deliberately never write expert_opinions.jsonl.

    review = service.review_recommendation(rec, "5d")

    assert "status" in review.expert_contribution
    assert "DATA_GAP" in review.expert_contribution["status"]


def test_expert_contribution_reads_real_opinions_when_available(tmp_path: Path):
    service, rec_repo, paper_repo, review_repo, records_dir = _setup(tmp_path)
    rec = _recommendation()
    rec_repo.append_recommendation(rec)
    rec_repo.append_decision(_decision(rec.recommendation_id))
    paper_repo.append(_trade(return_5d=0.05))
    append_jsonl(
        records_dir / "expert_opinions.jsonl",
        {
            "opinion_id": "opn_1",
            "recommendation_id": rec.recommendation_id,
            "expert_name": "TrendAgent",
            "stance": "support",
            "confidence": 0.7,
            "evidence": [],
            "risks": [],
            "missing_data": [],
            "summary": "fixture",
            "created_at": _now(),
        },
    )

    review = service.review_recommendation(rec, "5d")

    assert review.expert_contribution.get("TrendAgent") == "support"


def test_empty_lessons_when_return_not_yet_resolved(tmp_path: Path):
    service, rec_repo, paper_repo, review_repo, _ = _setup(tmp_path)
    rec = _recommendation()
    rec_repo.append_recommendation(rec)
    rec_repo.append_decision(_decision(rec.recommendation_id))

    review = service.review_recommendation(rec, "10d")
    assert review.lessons == []
