#!/usr/bin/env python3
"""validate_real_data.py — P1A §5.1.

CLI wrapper around `aegis.data.live_validation.validate_real_data`. Never
prints a token; never fabricates a passing report when the token/network
isn't actually available.

Usage:
    python scripts/validate_real_data.py
    python scripts/validate_real_data.py --markets A,H,US
    python scripts/validate_real_data.py --output data/processed/provider_diagnostics/provider_coverage_report.json
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional

# Allow running this file directly without having installed the package.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aegis.data.coverage_report import ProviderCoverageReport  # noqa: E402
from aegis.data.live_validation import validate_real_data  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = REPO_ROOT / "data" / "processed" / "provider_diagnostics" / "provider_coverage_report.json"
VALID_MARKETS = {"A", "H", "US"}


class ValidateRealDataArgumentError(ValueError):
    """A controlled, expected CLI input error — never a raw traceback."""


def _validate_markets(markets: list[str]) -> None:
    if not markets:
        raise ValidateRealDataArgumentError("--markets must name at least one market.")
    unknown = [m for m in markets if m not in VALID_MARKETS]
    if unknown:
        raise ValidateRealDataArgumentError(f"Unknown market(s) {unknown} — valid markets are {sorted(VALID_MARKETS)}.")


def run_validate_real_data(
    *,
    markets: list[str],
    date: Optional[str] = None,
    output_path: str | Path,
    env: Optional[dict] = None,
    provider=None,
) -> ProviderCoverageReport:
    """Testable core behind the CLI."""
    _validate_markets(markets)
    report = validate_real_data(markets=markets, date=date, provider=provider, env=env)
    report.write_json(output_path)
    return report


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Project Aegis P1A real Tushare provider-coverage diagnostics.")
    parser.add_argument("--markets", default="A,H,US", help="Comma-separated, e.g. A,H,US")
    parser.add_argument("--date", default=None, help="YYYY-MM-DD (default: today, UTC)")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args(argv)

    markets = [m.strip() for m in args.markets.split(",") if m.strip()]

    try:
        report = run_validate_real_data(markets=markets, date=args.date, output_path=args.output)
    except ValidateRealDataArgumentError as exc:
        print(f"validate_real_data argument error: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001 - controlled, never a raw traceback; never prints secrets
        print(f"validate_real_data failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1

    print(f"Provider diagnostics run_id: {report.run_id}")
    print(f"Token present: {report.token_present}")
    print(f"Network available: {report.network_available}")
    print(f"Checks: {len(report.checks)}")
    print(
        f"Pass={report.summary.pass_count} Fail={report.summary.fail_count} "
        f"Skipped={report.summary.skipped_count} Unknown={report.summary.unknown_count}"
    )
    if report.summary.critical_gaps:
        print(f"Critical gaps: {report.summary.critical_gaps}")
    print(f"Output: {args.output}")

    if not report.token_present:
        print(
            "TUSHARE_TOKEN missing — set it in .env or the environment to run a real check. "
            "Token value was not printed.",
            file=sys.stderr,
        )
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
