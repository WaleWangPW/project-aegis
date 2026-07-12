"""Review pure metric functions — Phase 6 §5.4.

Pure, dependency-free aggregation helpers over a list of `ReviewRecord`s.
Composed by `ReviewService.compute_metrics`. No Sharpe/Sortino/annualized
metrics (out of scope per PHASE6 doc, same as `aegis/paper/metrics.py`).
"""

from __future__ import annotations

from typing import Optional, Sequence

from aegis.models.review import ReviewRecord


def compute_action_success_rate(reviews: Sequence[ReviewRecord]) -> Optional[float]:
    """Fraction of reviews with `outcome == "success"`, counted only over
    reviews that actually reached a real outcome (excludes "pending" —
    there is nothing to divide by if every review is still inconclusive)."""
    resolved = [r for r in reviews if r.outcome in ("success", "failure", "mixed")]
    if not resolved:
        return None
    successes = sum(1 for r in resolved if r.outcome == "success")
    return successes / len(resolved)


def compute_average_return(reviews: Sequence[ReviewRecord]) -> Optional[float]:
    returns = [r.actual_return for r in reviews if r.actual_return is not None]
    if not returns:
        return None
    return sum(returns) / len(returns)


def compute_max_drawdown_summary(reviews: Sequence[ReviewRecord]) -> Optional[float]:
    """Worst (most negative) `max_drawdown` seen across all reviews."""
    drawdowns = [r.max_drawdown for r in reviews if r.max_drawdown is not None]
    if not drawdowns:
        return None
    return min(drawdowns)


def compute_win_loss_count(reviews: Sequence[ReviewRecord]) -> dict[str, int]:
    counts = {"win": 0, "loss": 0, "mixed": 0, "pending": 0}
    for r in reviews:
        if r.outcome == "success":
            counts["win"] += 1
        elif r.outcome == "failure":
            counts["loss"] += 1
        elif r.outcome == "mixed":
            counts["mixed"] += 1
        else:
            counts["pending"] += 1
    return counts


def compute_breakdown_by_key(reviews: Sequence[ReviewRecord], key_by_review: dict[str, str]) -> dict[str, dict]:
    """Group reviews by an external key (market or sector, looked up by
    `recommendation_id` since `ReviewRecord` itself does not carry
    market/sector) and report a per-group win rate + average return."""
    groups: dict[str, list[ReviewRecord]] = {}
    for review in reviews:
        group_key = key_by_review.get(review.recommendation_id, "未知")
        groups.setdefault(group_key, []).append(review)

    breakdown: dict[str, dict] = {}
    for group_key, group_reviews in groups.items():
        breakdown[group_key] = {
            "count": len(group_reviews),
            "success_rate": compute_action_success_rate(group_reviews),
            "average_return": compute_average_return(group_reviews),
        }
    return breakdown
