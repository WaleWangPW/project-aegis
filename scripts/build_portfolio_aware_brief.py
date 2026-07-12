#!/usr/bin/env python3
"""Build a read-only portfolio-aware recommendation brief."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aegis.models.recommendation import RecommendationRecord  # noqa: E402
from aegis.portfolio.aware_brief import (  # noqa: E402
    build_portfolio_aware_brief,
    render_portfolio_aware_brief_markdown,
)
from aegis.recommendation.repository import RecommendationRepository  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RECORDS_DIR = ROOT / "data" / "records"
DEFAULT_OUTPUT_DIR = ROOT / "data" / "reports"


def _load_recommendations(records_dir: Path, date: str, session: str) -> list[RecommendationRecord]:
    return [
        rec
        for rec in RecommendationRepository(records_dir).list_recommendations()
        if rec.date == date and rec.session == session
    ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build a portfolio-aware daily brief.")
    parser.add_argument("--date", required=True)
    parser.add_argument("--session", default="pre_market")
    parser.add_argument("--portfolio-report", required=True)
    parser.add_argument("--records-dir", default=str(DEFAULT_RECORDS_DIR))
    parser.add_argument("--planned-position-value", type=float, default=1000.0)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--format", choices=["json", "md"], default="json")
    args = parser.parse_args(argv)

    portfolio_report = json.loads(Path(args.portfolio_report).read_text(encoding="utf-8"))
    recommendations = _load_recommendations(Path(args.records_dir), args.date, args.session)
    report = build_portfolio_aware_brief(
        recommendations=recommendations,
        portfolio_report=portfolio_report,
        planned_position_value=args.planned_position_value,
    )
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    suffix = "json" if args.format == "json" else "md"
    output_path = output_dir / f"portfolio_aware_brief_{args.date}_{args.session}.{suffix}"
    if args.format == "json":
        output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    else:
        output_path.write_text(render_portfolio_aware_brief_markdown(report), encoding="utf-8")
    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
