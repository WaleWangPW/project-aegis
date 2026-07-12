#!/usr/bin/env python3
"""check_tushare.py — Master Spec §21 / Phase 1 §4.8.

Verifies Tushare configuration and connectivity WITHOUT ever printing the
token. Exits 0 on success, non-zero on any failure (missing token, missing
package, or a provider call failing).

Usage:
    python scripts/check_tushare.py
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

# Allow running this file directly (`python scripts/check_tushare.py`)
# without having installed the package first.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aegis.data.providers import ProviderError  # noqa: E402
from aegis.data.tushare_adapter import TushareAdapter  # noqa: E402


@dataclass
class CheckResult:
    ok: bool
    message: str


def check_tushare_config(env: Optional[dict] = None, adapter: Optional[TushareAdapter] = None) -> CheckResult:
    """Testable core logic behind the CLI.

    `env`: overrides os.environ for testing. If None, loads the real
    environment plus a local `.env` file (never overwrites `.env` — only
    reads it).
    `adapter`: injectable for tests so no real network call is made; if
    None, a real TushareAdapter is constructed from the resolved token.
    """
    if env is None:
        load_dotenv()
        token = os.environ.get("TUSHARE_TOKEN") or None
    else:
        token = env.get("TUSHARE_TOKEN") or None

    if not token:
        return CheckResult(
            ok=False,
            message=(
                "TUSHARE_TOKEN: missing\n"
                "Set TUSHARE_TOKEN in .env or environment. Token value was not printed."
            ),
        )

    tushare_adapter = adapter if adapter is not None else TushareAdapter(token=token)

    try:
        # Minimal, safe call: a two-day trading-calendar window. No symbol
        # subscription level required, small payload, cheap to repeat.
        tushare_adapter.get_trading_calendar(market="A", start="20260101", end="20260102")
    except ProviderError as exc:
        return CheckResult(
            ok=False,
            message=f"TUSHARE_TOKEN: configured\nTushareAdapter: initialized\nBasic provider check: FAILED ({exc})",
        )

    return CheckResult(
        ok=True,
        message="TUSHARE_TOKEN: configured\nTushareAdapter: initialized\nBasic provider check: OK",
    )


def main() -> int:
    result = check_tushare_config()
    print(result.message)
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
