#!/usr/bin/env python3
"""build_dashboard.py — Phase 5 §9.3.

Builds `data/dashboard/dashboard_data.json` from existing MarketSnapshot /
RecommendationRecord JSONL records plus `config/holdings.yaml`. Never
touches `dashboard/index.html`. Never writes a partial/invalid file — the
payload is fully validated before any write.

Usage:
    python scripts/build_dashboard.py --date 2026-07-04 --session pre_market
    python scripts/build_dashboard.py --date 2026-07-04 \
        --output data/dashboard/dashboard_data.json \
        --records-dir data/records \
        --holdings-config config/holdings.yaml
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pydantic import ValidationError  # noqa: E402

from aegis.dashboard.builder import DashboardBuilder  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]


def build_dashboard(
    *,
    date: str,
    session: str = "pre_market",
    records_dir: Path,
    holdings_config: Path,
    output_path: Path,
) -> Path:
    """Testable core logic behind the CLI. Raises on any failure — callers
    (the CLI `main()` here) are expected to catch and report a controlled
    error rather than let a partial/invalid file get written.
    """
    builder = DashboardBuilder(
        records_dir=records_dir, holdings_config_path=holdings_config, output_path=output_path
    )
    payload = builder.build(date=date, session=session)
    return builder.write_json(payload)


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Project Aegis Phase 5 dashboard JSON builder.")
    parser.add_argument("--date", required=True, help="YYYY-MM-DD")
    parser.add_argument("--session", default="pre_market")
    parser.add_argument("--output", default=str(REPO_ROOT / "data" / "dashboard" / "dashboard_data.json"))
    parser.add_argument("--records-dir", default=str(REPO_ROOT / "data" / "records"))
    parser.add_argument("--holdings-config", default=str(REPO_ROOT / "config" / "holdings.yaml"))
    args = parser.parse_args(argv)

    try:
        output_path = build_dashboard(
            date=args.date,
            session=args.session,
            records_dir=Path(args.records_dir),
            holdings_config=Path(args.holdings_config),
            output_path=Path(args.output),
        )
    except ValidationError as exc:
        print(f"Dashboard build failed: payload validation error:\n{exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # controlled, never a raw traceback; never prints secrets
        print(f"Dashboard build failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1

    print(str(output_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
