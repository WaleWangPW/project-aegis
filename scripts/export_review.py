#!/usr/bin/env python3
"""export_review.py — Phase 6 §5.8.

Reads existing `ReviewRecord`s (never re-computes/re-reviews) and writes a
plain factual report — no marketing language, no fabricated results, honest
`inconclusive`/data-gap counts included.

Usage:
    python scripts/export_review.py --start 2026-07-01 --end 2026-07-31 --format md
    python scripts/export_review.py --start 2026-07-01 --end 2026-07-31 --format json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

# Allow running this file directly without having installed the package.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aegis.paper.repository import PaperTradeRepository  # noqa: E402
from aegis.recommendation.repository import RecommendationRepository  # noqa: E402
from aegis.review.repository import ReviewRepository  # noqa: E402
from aegis.review.service import ReviewService  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]


def build_report(
    *,
    start: str,
    end: str,
    records_dir: Path,
) -> dict:
    """Testable core logic. Returns a plain dict — the CLI serializes it as
    md/json. Never fabricates a number: every field either comes straight
    from `ReviewService.compute_metrics` (which itself only reads existing
    `ReviewRecord`s) or is an explicit zero/"no reviews yet" honest state.
    """
    review_repository = ReviewRepository(records_dir)
    paper_repository = PaperTradeRepository(records_dir)
    recommendation_repository = RecommendationRepository(records_dir)
    review_service = ReviewService(
        review_repository=review_repository,
        paper_repository=paper_repository,
        recommendation_repository=recommendation_repository,
        records_dir=records_dir,
    )

    metrics = review_service.compute_metrics(start_date=start, end_date=end)
    reviews = [
        r
        for r in review_repository.list_all()
        if start <= r.review_date <= end
    ]
    inconclusive_count = sum(1 for r in reviews if r.outcome == "pending")
    lessons = [lesson for r in reviews for lesson in r.lessons]

    return {
        "start": start,
        "end": end,
        "total_reviewed": len(reviews),
        "action_success_rate": metrics["action_success_rate"],
        "average_return": metrics["average_return"],
        "max_drawdown": metrics["max_drawdown"],
        "win_loss_count": metrics["win_loss_count"],
        "market_breakdown": metrics["market_breakdown"],
        "sector_breakdown": metrics["sector_breakdown"],
        "inconclusive_count": inconclusive_count,
        "lessons": lessons,
    }


def _format_optional(value: Optional[float]) -> str:
    if value is None:
        return "DATA_GAP: 无可用数据"
    return f"{value:.4f}"


def render_markdown(report: dict) -> str:
    lines = [
        f"# Project Aegis Review 报告 ({report['start']} ~ {report['end']})",
        "",
        f"- 复盘记录总数: {report['total_reviewed']}",
        f"- Action 成功率: {_format_optional(report['action_success_rate'])}",
        f"- 平均收益: {_format_optional(report['average_return'])}",
        f"- 最大回撤: {_format_optional(report['max_drawdown'])}",
        f"- 数据不足/inconclusive 数: {report['inconclusive_count']}",
        "",
        "## 胜负统计",
        "",
    ]
    win_loss = report["win_loss_count"]
    for key in ("win", "loss", "mixed", "pending"):
        lines.append(f"- {key}: {win_loss.get(key, 0)}")

    lines.append("")
    lines.append("## 市场分布")
    lines.append("")
    if report["market_breakdown"]:
        for market, stats in report["market_breakdown"].items():
            lines.append(
                f"- {market}: count={stats['count']}, success_rate={_format_optional(stats['success_rate'])}, "
                f"average_return={_format_optional(stats['average_return'])}"
            )
    else:
        lines.append("- DATA_GAP: 本区间无复盘记录")

    lines.append("")
    lines.append("## 行业分布")
    lines.append("")
    if report["sector_breakdown"]:
        for sector, stats in report["sector_breakdown"].items():
            lines.append(
                f"- {sector}: count={stats['count']}, success_rate={_format_optional(stats['success_rate'])}, "
                f"average_return={_format_optional(stats['average_return'])}"
            )
    else:
        lines.append("- DATA_GAP: 本区间无复盘记录")

    lines.append("")
    lines.append("## 值得记录的教训")
    lines.append("")
    if report["lessons"]:
        for lesson in report["lessons"]:
            lines.append(f"- {lesson}")
    else:
        lines.append("- 尚无可提炼的教训（本区间复盘记录为空，或均未产生 lessons）。")

    lines.append("")
    return "\n".join(lines)


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Project Aegis Phase 6 review report exporter.")
    parser.add_argument("--start", required=True, help="YYYY-MM-DD")
    parser.add_argument("--end", required=True, help="YYYY-MM-DD")
    parser.add_argument("--format", choices=["md", "json"], default="md")
    parser.add_argument("--records-dir", default=str(REPO_ROOT / "data" / "records"))
    parser.add_argument("--output-dir", default=str(REPO_ROOT / "data" / "processed"))
    args = parser.parse_args(argv)

    try:
        report = build_report(start=args.start, end=args.end, records_dir=Path(args.records_dir))
    except Exception as exc:  # noqa: BLE001 - controlled, never a raw traceback; never prints secrets
        print(f"Review export failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = f"reviews_{args.start.replace('-', '')}_{args.end.replace('-', '')}"

    if args.format == "json":
        output_path = output_dir / f"{stem}.json"
        output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    else:
        output_path = output_dir / f"{stem}.md"
        output_path.write_text(render_markdown(report), encoding="utf-8")

    print(str(output_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
