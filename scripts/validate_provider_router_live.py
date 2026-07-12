#!/usr/bin/env python3
"""validate_provider_router_live.py — P1B.2.

CLI wrapper around `aegis.data.provider_router_live_validation.run_live_validation`.
Validates **only** `ProviderRouter`'s H/US secondary (`yahoo_finance`)
route — never constructs a `TushareAdapter`, never reads `.env` or
`os.environ`, never requires `TUSHARE_TOKEN`. Writes a report even when
the `yfinance` dependency or network is unavailable; never crashes.

Usage:
    python scripts/validate_provider_router_live.py
    python scripts/validate_provider_router_live.py --start 2026-06-01 --end 2026-07-03
    python scripts/validate_provider_router_live.py --markets H,US
    python scripts/validate_provider_router_live.py --output data/processed/provider_router/provider_router_live_report.json
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Optional

# Allow running this file directly without having installed the package.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aegis.data.provider_router_live_validation import (  # noqa: E402
    DEFAULT_OUTPUT,
    DEFAULT_PROVIDERS_CONFIG,
    default_date_window,
    run_live_validation,
    write_report,
)

VALID_MARKETS = {"H", "US"}
_BARS_DATA_TYPES = {"daily_bars", "index_bars"}


class ValidateProviderRouterLiveArgumentError(ValueError):
    """A controlled, expected CLI input error — never a raw traceback."""


def _validate_markets(markets: list[str]) -> None:
    if not markets:
        raise ValidateProviderRouterLiveArgumentError("--markets must name at least one market.")
    unknown = [m for m in markets if m not in VALID_MARKETS]
    if unknown:
        raise ValidateProviderRouterLiveArgumentError(
            f"Unknown market(s) {unknown} — this CLI validates only ProviderRouter's H/US "
            f"secondary route; valid markets are {sorted(VALID_MARKETS)}. A股/Tushare is out "
            "of scope for this script (see docs/P1B2_PROVIDER_ROUTER_LIVE_VALIDATION_RESULT.md)."
        )


def load_providers_config(config_path: str | Path) -> dict:
    import yaml

    path = Path(config_path)
    if not path.exists():
        raise ValidateProviderRouterLiveArgumentError(f"Config file not found: {path}")
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def run_validate_provider_router_live(
    *,
    markets: list[str],
    output_path: str | Path,
    config_path: str | Path = DEFAULT_PROVIDERS_CONFIG,
    router: Any = None,
) -> dict[str, Any]:
    """Testable core behind the CLI. `router` is injectable for tests
    (fake `yahoo_finance` adapter only — never a real network call from
    pytest)."""
    _validate_markets(markets)
    providers_config = None if router is not None else load_providers_config(config_path)
    report = run_live_validation(markets=markets, providers_config=providers_config, router=router)
    write_report(report, output_path)
    return report


def _print_summary(report: dict[str, Any], output_path: str) -> None:
    print(f"Provider router live validation run_id: {report['run_id']}")
    print(f"network_attempted: {report['network_attempted']}")
    print(f"Checks: {len(report['checks'])}")
    for check in report["checks"]:
        mapped = f" -> {check['mapped_symbol']}" if check.get("mapped_symbol") else ""
        rows = f" rows={check['rows_returned']}" if check.get("rows_returned") is not None else ""
        print(
            f"  [{check['status']}] {check['check_name']} "
            f"({check['market']}/{check['data_type']} via {check['provider']}) "
            f"sample={check.get('sample_symbol')}{mapped}{rows}"
        )
    s = report["summary"]
    print(
        f"pass={s['pass_count']} fail={s['fail_count']} unknown={s['unknown_count']} "
        f"skipped={s['skipped_count']} not_configured={s['not_configured_count']} "
        f"dependency_missing={s['dependency_missing_count']} "
        f"network_unavailable={s['network_unavailable_count']} unsupported={s['unsupported_count']}"
    )
    print(f"Output: {output_path}")


def main(argv: Optional[list[str]] = None) -> int:
    default_start, default_end = default_date_window()
    parser = argparse.ArgumentParser(
        description="Project Aegis P1B.2 ProviderRouter H/US secondary-provider live validation "
        "(yahoo_finance only — never Tushare, never .env/token)."
    )
    parser.add_argument("--start", default=default_start, help="YYYY-MM-DD (currently informational; "
                        "the underlying router/adapter use a fixed recent window)")
    parser.add_argument("--end", default=default_end, help="YYYY-MM-DD")
    parser.add_argument("--markets", default="H,US", help="Comma-separated, e.g. H,US")
    parser.add_argument("--config", default=str(DEFAULT_PROVIDERS_CONFIG))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args(argv)

    markets = [m.strip().upper() for m in args.markets.split(",") if m.strip()]

    try:
        report = run_validate_provider_router_live(
            markets=markets, output_path=args.output, config_path=args.config,
        )
    except ValidateProviderRouterLiveArgumentError as exc:
        print(f"validate_provider_router_live argument error: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001 - controlled, never a raw traceback; never prints secrets
        print(f"validate_provider_router_live failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1

    _print_summary(report, args.output)

    bars_checks = [c for c in report["checks"] if c["data_type"] in _BARS_DATA_TYPES]
    any_pass = any(c["status"] == "pass" for c in bars_checks)
    return 0 if any_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
