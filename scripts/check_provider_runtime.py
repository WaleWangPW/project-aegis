#!/usr/bin/env python3
"""check_provider_runtime.py — P1D.4 Provider runtime dependency check.

Reports whether the Python environment running this script has the packages
required for the H/US Yahoo Finance ProviderRouter route, and whether the
ProviderRouter itself can be instantiated.

Checks performed (all without any live network call, token read, or
.env access):
  1. Python executable and version
  2. Whether `yfinance` is importable (and its version)
  3. Whether `YahooFinanceAdapter.is_configured()` returns True
  4. Whether `ProviderRouter` instantiates with the H/US Yahoo route

Exits with code 0 if H/US provider runtime is fully available.
Exits with code 1 if `yfinance` is not importable (runtime missing).
Exits with code 2 on any unexpected error.

Note: "available" means importable — it does NOT guarantee live network
reachability. Network health is validated separately by
`scripts/validate_provider_router_live.py`.

Usage:
    python scripts/check_provider_runtime.py
    python scripts/check_provider_runtime.py --json
    python scripts/check_provider_runtime.py --json --output /tmp/runtime.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

# Allow running this file directly without installing the package.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

REPO_ROOT = Path(__file__).resolve().parents[1]


def _check_yfinance() -> dict[str, Any]:
    """Try importing yfinance; return a status dict. Never reads .env."""
    try:
        import yfinance as yf  # noqa: PLC0415
        version = getattr(yf, "__version__", "unknown")
        return {"importable": True, "version": version, "error": None}
    except ImportError as exc:
        return {"importable": False, "version": None, "error": str(exc)}


def _check_adapter() -> dict[str, Any]:
    """Instantiate YahooFinanceAdapter and call is_configured().
    Returns a status dict. No live network call, no token read."""
    try:
        from aegis.data.yahoo_finance_adapter import YahooFinanceAdapter  # noqa: PLC0415
        adapter = YahooFinanceAdapter()
        configured = adapter.is_configured()
        return {"instantiated": True, "is_configured": configured, "error": None}
    except Exception as exc:  # noqa: BLE001
        return {"instantiated": False, "is_configured": False, "error": str(exc)}


def _check_provider_router() -> dict[str, Any]:
    """Instantiate ProviderRouter with the H/US Yahoo route from config/providers.yaml.
    No live network call, no token read."""
    try:
        import yaml  # noqa: PLC0415
        from aegis.data.provider_router import ProviderRouter  # noqa: PLC0415
        from aegis.data.yahoo_finance_adapter import YahooFinanceAdapter  # noqa: PLC0415

        providers_config_path = REPO_ROOT / "config" / "providers.yaml"
        routing_config: dict = {}
        if providers_config_path.exists():
            with providers_config_path.open(encoding="utf-8") as fh:
                routing_config = yaml.safe_load(fh) or {}

        adapter = YahooFinanceAdapter()
        router = ProviderRouter(
            providers={"yahoo_finance": adapter},
            routing_config=routing_config,
        )
        # provider_for raises ProviderNotConfiguredError if route missing; success = route exists
        provider = router.provider_for("US", "daily_bars")
        return {
            "instantiated": True,
            "us_daily_route_resolved": provider is not None,
            "error": None,
        }
    except Exception as exc:  # noqa: BLE001
        return {"instantiated": False, "us_daily_route_resolved": False, "error": str(exc)}


def run_check() -> dict[str, Any]:
    """Run all runtime checks and return a summary dict."""
    yf_check = _check_yfinance()
    adapter_check = _check_adapter()
    router_check = _check_provider_router()

    overall_ok = (
        yf_check["importable"]
        and adapter_check["is_configured"]
        and router_check["instantiated"]
    )

    return {
        "python_executable": sys.executable,
        "python_version": sys.version.split()[0],
        "yfinance": yf_check,
        "yahoo_finance_adapter": adapter_check,
        "provider_router_h_us": router_check,
        "overall_status": "ok" if overall_ok else "unavailable",
        "notes": (
            "yfinance importable; H/US ProviderRouter route is ready. "
            "Network reachability is NOT tested here — run "
            "scripts/validate_provider_router_live.py for live validation."
            if overall_ok
            else "H/US Yahoo Finance runtime is NOT fully available. "
            "Install yfinance: pip install 'yfinance>=0.2.40' "
            "(it is listed in pyproject.toml main dependencies — "
            "run: pip install -e . )"
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Check P1D.4 provider runtime dependency (yfinance + ProviderRouter). "
            "No live network call. No .env read. No token printed."
        )
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print result as JSON (default: human-readable).",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Optional path to write JSON result file.",
    )
    args = parser.parse_args(argv)

    result = run_check()

    if args.json or args.output:
        text = json.dumps(result, indent=2)
        print(text)
        if args.output:
            out = Path(args.output)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(text, encoding="utf-8")
    else:
        status_icon = "✓" if result["overall_status"] == "ok" else "✗"
        print(f"Provider runtime check {status_icon}")
        print(f"  Python:             {result['python_executable']} ({result['python_version']})")
        yf = result["yfinance"]
        if yf["importable"]:
            print(f"  yfinance:           importable, version={yf['version']}")
        else:
            print(f"  yfinance:           NOT importable — {yf['error']}")
        adp = result["yahoo_finance_adapter"]
        print(f"  YahooFinanceAdapter: is_configured={adp['is_configured']}")
        rtr = result["provider_router_h_us"]
        print(f"  ProviderRouter H/US: instantiated={rtr['instantiated']}, us_daily_resolved={rtr['us_daily_route_resolved']}")
        print(f"  Overall status:     {result['overall_status']}")
        print(f"  Notes:              {result['notes']}")

    return 0 if result["overall_status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
