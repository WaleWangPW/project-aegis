#!/usr/bin/env python3
"""check_provider_router.py — P1B.1 §7.

Prints the `ProviderRouter` route table (from `config/providers.yaml`),
validates every configured symbol/index-code mapping, and reports package
availability (`tushare`, `yfinance`) — all **without** attempting any
live network call and **without** ever reading or printing a token value.

P1B.1 does not need to prove live H/US coverage from inside this Cowork
sandbox (see `docs/P1B1_PROVIDER_ROUTER_RESULT.md`), so every
`(market, data_type)` route is reported with status `"skipped"` and an
explicit reason rather than attempting a real provider call — this
script is a **config + wiring** sanity check, not a live data validator
(that remains `scripts/validate_real_data.py`'s job).

Usage:
    python scripts/check_provider_router.py
    python scripts/check_provider_router.py --config config/providers.yaml
    python scripts/check_provider_router.py --output data/processed/provider_diagnostics/provider_router_report.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Optional

import yaml

# Allow running this file directly without having installed the package.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aegis.data.symbol_mapping import SymbolMapper, SymbolMappingError  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = REPO_ROOT / "config" / "providers.yaml"
DEFAULT_OUTPUT = REPO_ROOT / "data" / "processed" / "provider_diagnostics" / "provider_router_report.json"

_LIVE_CHECK_SKIP_REASON = (
    "live provider checks intentionally not attempted — P1B.1 is a "
    "config + routing skeleton round only (see docs/P1B1_PROVIDER_ROUTER_RESULT.md); "
    "run scripts/validate_real_data.py locally with a real token/network "
    "for actual live coverage."
)


class ProviderRouterCheckError(ValueError):
    """A controlled, expected CLI input error — never a raw traceback."""


def load_routing_config(config_path: str | Path) -> dict:
    path = Path(config_path)
    if not path.exists():
        raise ProviderRouterCheckError(f"Config file not found: {path}")
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _package_installed(module_name: str) -> bool:
    try:
        __import__(module_name)
    except ImportError:
        return False
    return True


def build_route_checks(routing: dict) -> list[dict[str, Any]]:
    """One entry per configured `(data_type, market)` pair — never a live
    call, just a report of what's configured and an honest reason for
    why it wasn't exercised live this round."""
    checks: list[dict[str, Any]] = []
    for data_type, by_market in routing.items():
        for market, provider_name in by_market.items():
            if provider_name in ("not_configured", "unsupported"):
                status = provider_name
                reason = f"route explicitly marked {provider_name!r} in config/providers.yaml"
            else:
                status = "skipped"
                reason = _LIVE_CHECK_SKIP_REASON
            checks.append(
                {
                    "data_type": data_type,
                    "market": market,
                    "provider": provider_name,
                    "status": status,
                    "reason": reason,
                }
            )
    return checks


def build_mapping_checks(symbol_mapping_cfg: dict) -> list[dict[str, Any]]:
    """Validates every configured symbol_mapping entry actually resolves
    to the value the config claims — pure config validation, no network,
    no provider instantiation."""
    mapper = SymbolMapper(symbol_mapping_cfg)
    checks: list[dict[str, Any]] = []
    for provider_name, by_market in symbol_mapping_cfg.items():
        for market, tables in (by_market or {}).items():
            for kind, resolver in (("symbols", mapper.map_symbol), ("indexes", mapper.map_index)):
                for internal_code, expected in (tables.get(kind) or {}).items():
                    try:
                        resolved = resolver(provider_name, market, internal_code)
                        status = "ok" if resolved == expected else "mismatch"
                    except SymbolMappingError as exc:
                        resolved = None
                        status = "error"
                        expected = f"{expected} (error: {exc})"
                    checks.append(
                        {
                            "provider": provider_name,
                            "market": market,
                            "kind": kind,
                            "internal_code": internal_code,
                            "expected": expected,
                            "resolved": resolved,
                            "status": status,
                        }
                    )
    return checks


def build_report(config: dict) -> dict[str, Any]:
    routing = config.get("routing", {})
    symbol_mapping_cfg = config.get("symbol_mapping", {})

    route_checks = build_route_checks(routing)
    mapping_checks = build_mapping_checks(symbol_mapping_cfg)

    return {
        "route_table": [
            {"data_type": c["data_type"], "market": c["market"], "provider": c["provider"]} for c in route_checks
        ],
        "route_checks": route_checks,
        "mapping_checks": mapping_checks,
        "package_availability": {
            "tushare": _package_installed("tushare"),
            "yfinance": _package_installed("yfinance"),
        },
        "note": _LIVE_CHECK_SKIP_REASON,
    }


def run_check_provider_router(
    *,
    config_path: str | Path = DEFAULT_CONFIG,
    output_path: Optional[str | Path] = None,
) -> dict[str, Any]:
    """Testable core behind the CLI."""
    config = load_routing_config(config_path)
    report = build_report(config)
    if output_path is not None:
        out_path = Path(output_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def _print_report(report: dict[str, Any]) -> None:
    print("Route table:")
    for row in report["route_table"]:
        print(f"  {row['data_type']:<24} {row['market']:<4} -> {row['provider']}")
    print()
    print("Symbol/index mapping checks:")
    if not report["mapping_checks"]:
        print("  (none configured)")
    for row in report["mapping_checks"]:
        print(
            f"  [{row['status']}] {row['provider']}/{row['market']}/{row['kind']}: "
            f"{row['internal_code']} -> {row['resolved']} (expected {row['expected']})"
        )
    print()
    print(f"tushare package installed: {report['package_availability']['tushare']}")
    print(f"yfinance package installed: {report['package_availability']['yfinance']}")
    print()
    print(report["note"])


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Project Aegis P1B.1 ProviderRouter config + routing sanity check.")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG), help="Path to config/providers.yaml")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args(argv)

    try:
        report = run_check_provider_router(config_path=args.config, output_path=args.output)
    except ProviderRouterCheckError as exc:
        print(f"check_provider_router argument error: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001 - controlled, never a raw traceback; never prints secrets
        print(f"check_provider_router failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1

    _print_report(report)
    print(f"Output: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
