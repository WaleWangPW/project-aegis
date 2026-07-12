#!/usr/bin/env python3
"""Build a read-only V2.0-A portfolio snapshot report."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aegis.portfolio.holdings_loader import HoldingLoader  # noqa: E402
from aegis.portfolio.snapshot import (  # noqa: E402
    RiskBudget,
    build_portfolio_snapshot,
    render_portfolio_snapshot_markdown,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_HOLDINGS_PATH = ROOT / "config" / "holdings.yaml"
DEFAULT_OUTPUT_DIR = ROOT / "data" / "reports"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build a read-only portfolio snapshot.")
    parser.add_argument("--date", required=True)
    parser.add_argument("--holdings-path", default=str(DEFAULT_HOLDINGS_PATH))
    parser.add_argument("--cash", type=float, required=True)
    parser.add_argument("--max-exposure-pct", type=float, default=0.8)
    parser.add_argument("--max-single-position-pct", type=float, default=0.35)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--format", choices=["json", "md"], default="json")
    args = parser.parse_args(argv)

    holdings = HoldingLoader(args.holdings_path).load_holdings()
    report = build_portfolio_snapshot(
        holdings=holdings,
        date=args.date,
        cash=args.cash,
        risk_budget=RiskBudget(
            max_exposure_pct=args.max_exposure_pct,
            max_single_position_pct=args.max_single_position_pct,
        ),
    )
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    suffix = "json" if args.format == "json" else "md"
    output_path = output_dir / f"portfolio_snapshot_{args.date}.{suffix}"
    if args.format == "json":
        output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    else:
        output_path.write_text(render_portfolio_snapshot_markdown(report), encoding="utf-8")
    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
