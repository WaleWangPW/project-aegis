"""Phase 6 tests for aegis/review/metrics.py — PHASE6 doc §5.4/§7.2.5."""

from __future__ import annotations

from aegis.models.review import ReviewRecord
from aegis.review.metrics import (
    compute_action_success_rate,
    compute_average_return,
    compute_breakdown_by_key,
    compute_max_drawdown_summary,
    compute_win_loss_count,
)


def _review(*, rec_id="rec_1", outcome="success", actual_return=0.05, max_drawdown=-0.02) -> ReviewRecord:
    return ReviewRecord(
        review_id=f"rev_{rec_id}_5d",
        recommendation_id=rec_id,
        review_date="2026-07-10",
        horizon="5d",
        outcome=outcome,
        actual_return=actual_return,
        max_drawdown=max_drawdown,
        decision_quality="good_decision" if outcome == "success" else "poor_decision",
        expert_contribution={"TrendAgent": "support"},
        lessons=[],
        created_at="2026-07-10T00:00:00+00:00",
    )


def test_compute_action_success_rate_basic():
    reviews = [_review(outcome="success"), _review(outcome="failure"), _review(outcome="success")]
    assert round(compute_action_success_rate(reviews), 4) == round(2 / 3, 4)


def test_compute_action_success_rate_excludes_pending():
    reviews = [_review(outcome="success"), _review(outcome="pending", actual_return=None)]
    assert compute_action_success_rate(reviews) == 1.0


def test_compute_action_success_rate_all_pending_returns_none():
    reviews = [_review(outcome="pending", actual_return=None)]
    assert compute_action_success_rate(reviews) is None


def test_compute_action_success_rate_empty_returns_none():
    assert compute_action_success_rate([]) is None


def test_compute_average_return():
    reviews = [_review(actual_return=0.10), _review(actual_return=-0.02)]
    assert round(compute_average_return(reviews), 4) == 0.04


def test_compute_average_return_ignores_none():
    reviews = [_review(actual_return=0.10), _review(outcome="pending", actual_return=None)]
    assert compute_average_return(reviews) == 0.10


def test_compute_average_return_empty_returns_none():
    assert compute_average_return([]) is None


def test_compute_max_drawdown_summary_picks_worst():
    reviews = [_review(max_drawdown=-0.02), _review(max_drawdown=-0.15)]
    assert compute_max_drawdown_summary(reviews) == -0.15


def test_compute_win_loss_count():
    reviews = [
        _review(outcome="success"),
        _review(outcome="failure"),
        _review(outcome="mixed"),
        _review(outcome="pending", actual_return=None),
    ]
    counts = compute_win_loss_count(reviews)
    assert counts == {"win": 1, "loss": 1, "mixed": 1, "pending": 1}


def test_compute_breakdown_by_key_groups_correctly():
    reviews = [
        _review(rec_id="rec_A", outcome="success"),
        _review(rec_id="rec_B", outcome="failure"),
    ]
    key_by_review = {"rec_A": "US", "rec_B": "A"}
    breakdown = compute_breakdown_by_key(reviews, key_by_review)
    assert breakdown["US"]["count"] == 1
    assert breakdown["A"]["count"] == 1
    assert breakdown["US"]["success_rate"] == 1.0
    assert breakdown["A"]["success_rate"] == 0.0


def test_compute_breakdown_by_key_unknown_key_falls_back():
    reviews = [_review(rec_id="rec_missing")]
    breakdown = compute_breakdown_by_key(reviews, {})
    assert "未知" in breakdown
