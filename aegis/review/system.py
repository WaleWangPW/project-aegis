"""V1.5 Review System reporting.

Builds weekly/monthly review reports from existing records. This module does
not recompute recommendations, mutate strategy, or create trades. It only reads
ReviewRecord, RecommendationRecord, PaperTrade, and InvestmentMemory JSONL
records and turns them into an auditable report.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal, Optional

from aegis.memory.repository import MemoryRepository
from aegis.paper.repository import PaperTradeRepository
from aegis.recommendation.repository import RecommendationRepository
from aegis.review.repository import ReviewRepository
from aegis.review.service import ReviewService

Period = Literal["weekly", "monthly"]


def _format_case(review, rec) -> dict:
    return {
        "review_id": review.review_id,
        "recommendation_id": review.recommendation_id,
        "symbol": rec.symbol if rec else None,
        "market": rec.market if rec else None,
        "sector": rec.sector if rec else None,
        "horizon": review.horizon,
        "outcome": review.outcome,
        "actual_return": review.actual_return,
        "decision_quality": review.decision_quality,
        "success_reason": review.success_reason,
        "failure_reason": review.failure_reason,
        "lessons": review.lessons,
    }


def _memory_reference(memory, rec) -> dict:
    return {
        "memory_id": memory.memory_id,
        "date": memory.date,
        "linked_recommendation_id": memory.linked_recommendation_id,
        "symbol": rec.symbol if rec else None,
        "market": rec.market if rec else None,
        "sector": rec.sector if rec else None,
        "lesson_type": memory.lesson_type,
        "lesson": memory.lesson,
        "tags": memory.tags,
        "confidence": memory.confidence,
    }


def build_review_system_report(
    *,
    records_dir: str | Path,
    start: str,
    end: str,
    period: Period,
    memory_limit: int = 20,
) -> dict:
    records_path = Path(records_dir)
    review_repository = ReviewRepository(records_path)
    paper_repository = PaperTradeRepository(records_path)
    recommendation_repository = RecommendationRepository(records_path)
    memory_repository = MemoryRepository(records_path)

    review_service = ReviewService(
        review_repository=review_repository,
        paper_repository=paper_repository,
        recommendation_repository=recommendation_repository,
        records_dir=records_path,
    )

    reviews = [r for r in review_repository.list_all() if start <= r.review_date <= end]
    recommendations = {r.recommendation_id: r for r in recommendation_repository.list_recommendations()}
    memories = [m for m in memory_repository.list_all() if start <= m.date <= end]
    metrics = review_service.compute_metrics(start_date=start, end_date=end)

    resolved_reviews = [r for r in reviews if r.actual_return is not None]
    best_cases = sorted(
        [r for r in resolved_reviews if r.actual_return is not None and r.actual_return > 0],
        key=lambda r: r.actual_return or 0,
        reverse=True,
    )[:5]
    failed_cases = sorted(
        [r for r in resolved_reviews if r.actual_return is not None and r.actual_return < 0],
        key=lambda r: r.actual_return or 0,
    )[:5]

    error_attribution = []
    for review in reviews:
        if review.outcome not in ("failure", "mixed") and review.decision_quality != "poor_decision":
            continue
        rec = recommendations.get(review.recommendation_id)
        error_attribution.append(
            {
                "review_id": review.review_id,
                "recommendation_id": review.recommendation_id,
                "symbol": rec.symbol if rec else None,
                "market": rec.market if rec else None,
                "actual_return": review.actual_return,
                "decision_quality": review.decision_quality,
                "failure_reason": review.failure_reason,
                "risks": rec.risks if rec else [],
                "oppose_reasons": rec.oppose_reasons if rec else [],
                "expert_contribution": review.expert_contribution,
                "lessons": review.lessons,
            }
        )

    memory_references = [
        _memory_reference(memory, recommendations.get(memory.linked_recommendation_id))
        for memory in memories[:memory_limit]
    ]

    return {
        "period": period,
        "start": start,
        "end": end,
        "review_count": len(reviews),
        "metrics": metrics,
        "best_cases": [_format_case(r, recommendations.get(r.recommendation_id)) for r in best_cases],
        "failed_cases": [_format_case(r, recommendations.get(r.recommendation_id)) for r in failed_cases],
        "error_attribution": error_attribution,
        "memory_reuse": {
            "available_references": memory_references,
            "reference_count": len(memory_references),
            "rule": "Reuse prior InvestmentMemory as explicit reference material; never mutate strategy automatically.",
        },
        "safety": {
            "read_only_records": True,
            "no_real_trade": True,
            "no_broker_api": True,
            "no_webhook": True,
            "no_strategy_mutation": True,
        },
    }


def render_review_system_markdown(report: dict) -> str:
    lines = [
        f"# Project Aegis {report['period'].title()} Review System",
        "",
        f"- Period: `{report['start']} -> {report['end']}`",
        f"- Reviews: `{report['review_count']}`",
        f"- Action success rate: `{report['metrics']['action_success_rate']}`",
        f"- Average return: `{report['metrics']['average_return']}`",
        f"- Max drawdown: `{report['metrics']['max_drawdown']}`",
        f"- Memory references: `{report['memory_reuse']['reference_count']}`",
        "",
        "## Best Cases",
        "",
    ]
    if report["best_cases"]:
        for case in report["best_cases"]:
            lines.append(f"- `{case['symbol']}` return=`{case['actual_return']}` quality=`{case['decision_quality']}`")
    else:
        lines.append("- DATA_GAP: no successful resolved review in this period")

    lines.extend(["", "## Failed Cases", ""])
    if report["failed_cases"]:
        for case in report["failed_cases"]:
            lines.append(f"- `{case['symbol']}` return=`{case['actual_return']}` reason={case['failure_reason']}")
    else:
        lines.append("- DATA_GAP: no failed resolved review in this period")

    lines.extend(["", "## Error Attribution", ""])
    if report["error_attribution"]:
        for item in report["error_attribution"]:
            lines.append(
                f"- `{item['symbol']}` quality=`{item['decision_quality']}` "
                f"risks={item['risks']} reason={item['failure_reason']}"
            )
    else:
        lines.append("- No failures or poor decisions to attribute in this period")

    lines.extend(["", "## Investment Memory References", ""])
    if report["memory_reuse"]["available_references"]:
        for item in report["memory_reuse"]["available_references"]:
            lines.append(f"- `{item['memory_id']}` `{item['symbol']}` {item['lesson']}")
    else:
        lines.append("- DATA_GAP: no InvestmentMemory references available")

    lines.append("")
    return "\n".join(lines)
