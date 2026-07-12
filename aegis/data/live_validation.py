"""validate_real_data — P1A §2.1 orchestration layer.

Ties together: token-presence check (never printing the token) -> a
cheap connectivity probe (mirrors `check_tushare.py`'s own "safe, small
Basic provider check") -> per-market/per-category checks via
`aegis.data.provider_diagnostics.run_checks_for_market` -> a
`ProviderCoverageReport`.

Never fabricates a passing report when the token/network isn't actually
available:

- No `TUSHARE_TOKEN` -> an honest report with `token_present=False`,
  `network_available=False`, zero checks attempted, and a note in
  `summary.critical_gaps` explaining why. This is the expected shape in
  this Cowork sandbox, which has no outbound network — see
  `docs/HANDOFF.md`'s `TODO_FOR_USER` note for the real-token command to
  run locally.
- Token present but the connectivity probe itself fails -> an honest
  report with `token_present=True`, `network_available=False`, and every
  requested check reported as `"skipped"` (never individually retried
  with a wall of duplicate network errors).
- Token present and the probe succeeds -> real per-category checks via
  `run_checks_for_market`.

A `provider` can always be injected directly (same convention as every
other script in this project) — when it is, `network_available` is
assumed true and the connectivity probe is skipped entirely, since an
injected provider (real or fake) is a deliberate test/CI substitution for
"we already know how to reach this provider."
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Optional

from dotenv import load_dotenv

from aegis.data.coverage_report import CoverageSummary, ProviderCheck, ProviderCoverageReport, summarize_checks
from aegis.data.gaps import DataGapRegistry
from aegis.data.provider_diagnostics import DEFAULT_MARKETS, reconcile_cross_market_checks, run_checks_for_market
from aegis.data.providers import ProviderError
from aegis.data.tushare_adapter import TushareAdapter

_PROBE_MARKET = "A"


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def generate_run_id() -> str:
    return f"provider_diag_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"


def check_token_present(env: Optional[dict] = None) -> bool:
    """True iff a `TUSHARE_TOKEN` string is present. Never returns or logs
    the value itself. `env` overrides `os.environ` for testing (same
    pattern as `scripts/check_tushare.py::check_tushare_config`)."""
    if env is None:
        load_dotenv()
        return bool(os.environ.get("TUSHARE_TOKEN"))
    return bool(env.get("TUSHARE_TOKEN"))


def _probe_network(provider: Any) -> tuple[bool, Optional[str]]:
    """A single, cheap connectivity check — a 2-day trading-calendar
    window for market A, same minimal-payload pattern
    `check_tushare_config` already uses. Returns (network_available,
    warning)."""
    try:
        provider.get_trading_calendar(market=_PROBE_MARKET, start="20260101", end="20260102")
    except ProviderError as exc:
        return False, str(exc)
    except AttributeError as exc:
        return False, f"provider does not implement get_trading_calendar: {exc}"
    return True, None


def _empty_report(*, run_id: str, token_present: bool, network_available: bool, reason: str) -> ProviderCoverageReport:
    return ProviderCoverageReport(
        run_id=run_id,
        created_at=_now_iso(),
        provider="tushare",
        token_present=token_present,
        network_available=network_available,
        checks=[],
        summary=CoverageSummary(critical_gaps=[reason]),
    )


def _all_skipped_report(
    *, run_id: str, markets: list[str], token_present: bool, network_available: bool, reason: str
) -> ProviderCoverageReport:
    checks = [
        ProviderCheck(check_name=f"{market.lower()}_connectivity", market=market, data_type="connectivity", status="skipped", warning=reason)
        for market in markets
    ]
    return ProviderCoverageReport(
        run_id=run_id,
        created_at=_now_iso(),
        provider="tushare",
        token_present=token_present,
        network_available=network_available,
        checks=checks,
        summary=summarize_checks(checks),
    )


def validate_real_data(
    *,
    markets: Optional[list[str]] = None,
    date: Optional[str] = None,
    provider: Any = None,
    env: Optional[dict] = None,
    gaps: Optional[DataGapRegistry] = None,
    run_id: Optional[str] = None,
) -> ProviderCoverageReport:
    """Testable core behind `scripts/validate_real_data.py`. `provider` is
    injectable for tests (fake providers only in this repo's own test
    suite — never a real network call from `pytest`)."""
    markets = markets if markets is not None else DEFAULT_MARKETS
    date = date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    run_id = run_id or generate_run_id()

    token_present = check_token_present(env)

    if provider is not None:
        # A caller explicitly injected a provider (real or fake) — treat
        # this as "we already know how to reach it," same convention as
        # every other script in this project. Skip the connectivity probe.
        network_available = True
    else:
        if not token_present:
            return _empty_report(
                run_id=run_id,
                token_present=False,
                network_available=False,
                reason="TUSHARE_TOKEN missing — no checks attempted",
            )
        provider = TushareAdapter.from_env()
        network_available, probe_warning = _probe_network(provider)
        if not network_available:
            return _all_skipped_report(
                run_id=run_id,
                markets=markets,
                token_present=True,
                network_available=False,
                reason=f"connectivity probe failed — no real checks attempted: {probe_warning}",
            )

    checks: list[ProviderCheck] = []
    for market in markets:
        checks.extend(run_checks_for_market(provider=provider, market=market, date=date, gaps=gaps))

    # P1A.1 §1: reconcile suspected cross-market diagnostic duplicates
    # (e.g. H/US `stock_basic` silently reusing A股's result) before
    # summarizing — never let a diagnostic bug read as confirmed coverage.
    checks = reconcile_cross_market_checks(checks, date=date, gaps=gaps)

    return ProviderCoverageReport(
        run_id=run_id,
        created_at=_now_iso(),
        provider="tushare",
        token_present=token_present,
        network_available=network_available,
        checks=checks,
        summary=summarize_checks(checks),
    )
