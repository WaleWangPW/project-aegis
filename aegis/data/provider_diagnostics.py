"""run_provider_diagnostics — P1A §2.1, hardened in P1A.1.

Exercises every P0 data category (A/H/US daily bars, index bars, stock
basic list, sector/industry classification, fundamentals, trading
calendar) against a `MarketDataProvider`-shaped object — real
`TushareAdapter` or a fake/mocked provider in tests, same duck-typed
convention as every other consumer in this codebase — and records one
honest `ProviderCheck` per category.

Status semantics (never fabricated) — see `aegis.data.coverage_report.CheckStatus`
for the full docstring of each value. Summary:
- "pass": the call succeeded and returned at least one row, and (after
  cross-market reconciliation) isn't suspected of reusing another
  market's data.
- "fail" / "permission_denied": the call raised `ProviderError` — a real
  provider failure. `permission_denied` is used when the error message
  itself looks entitlement/permission/quota related, so triage doesn't
  have to guess. Always recorded as a `DataGap` too.
- "skipped": the provider object doesn't implement this method at all
  (`AttributeError` degrade — same duck-typing convention used by
  `HistoricalDataProvider` in Phase 7).
- "not_configured": a required input (e.g. a per-market sample symbol)
  has no configured value, so the call was never attempted.
- "unknown_empty": the call succeeded but returned an empty result — this
  does NOT confirm coverage either way, so it is never reported as "pass".
  Recorded as an info-severity `DataGap`.
- "unsupported": (a) P1A.1 §1 hardening — a real, observed bug where a
  non-A股 market's check reported "pass" with the exact same row count as
  A股's check for the same data_type (e.g. `TushareAdapter.get_stock_basic`
  ignores its `market` argument and always returns the SSE/SZSE list);
  `reconcile_cross_market_checks` downgrades these from a naive "pass" to
  "unsupported". (b) P1B.1 — a `ProviderRouter` route explicitly marked
  `"unsupported"`, or a provider that raises `ProviderUnsupportedError`
  directly (e.g. `YahooFinanceAdapter.get_stock_basic`). Either way, a
  diagnostic bug or a known capability gap can never be misread as
  confirmed coverage.
- "not_configured" (P1B.1 addition to the pre-existing status): also now
  covers a `ProviderRouter` route with no configured provider for a
  `(market, data_type)` pair (`ProviderNotConfiguredError`) — structurally
  the same "never guess, always be explicit" rule as the pre-existing
  missing-sample-symbol case.

This module never turns provider availability into a recommendation and
never assumes coverage it hasn't actually observed.
"""

from __future__ import annotations

from typing import Any, Optional

import pandas as pd

from aegis.data.coverage_report import ProviderCheck
from aegis.data.gaps import DataGapRegistry
from aegis.data.providers import ProviderError, ProviderNotConfiguredError, ProviderUnsupportedError
from aegis.market.regime import DEFAULT_PRIMARY_INDEX
from aegis.utils.dates import lookback_range

DEFAULT_MARKETS = ["A", "H", "US"]

# Diagnostic-only sample symbols — never a recommendation, never a
# fabricated candidate. A/H use well-known liquid bellwethers; US uses the
# project's one real holding (CRCL) since that's the symbol whose real
# coverage actually matters to this user.
DEFAULT_SAMPLE_SYMBOLS = {"A": "000001.SZ", "H": "00700.HK", "US": "CRCL"}

_BARS_CHECK_NAME = {"A": "a_share_daily_bars", "H": "h_share_daily_bars", "US": "us_daily_bars"}

# P1A.1 §1: data_types where a non-A股 market reporting the exact same
# row count as A股 is treated as a suspected diagnostic bug (provider
# ignoring `market`) rather than confirmed coverage. Narrowly scoped to
# the case actually observed in the real report
# (`Claude_Cowork_P1A1_PROVIDER_COVERAGE_RECONCILIATION.md` §0) —
# `stock_basic` — rather than applied blanket to every data_type, since a
# legitimately healthy provider can coincidentally share exact bar counts
# across markets (e.g. two markets both returning N daily bars for the
# same lookback window) without that implying anything is wrong.
RECONCILED_DATA_TYPES = {"stock_basic"}

# Keywords that mean "the call failed for a permission/entitlement/quota
# reason", not an anonymous error — checked case-insensitively against the
# raw exception message. Never inspects/logs the token itself.
_PERMISSION_KEYWORDS = (
    "permission",
    "not authorized",
    "unauthorized",
    "entitlement",
    "quota",
    "no access",
    "not entitled",
    "权限",
    "积分",
    "无权",
)


def _run_call(fn) -> tuple[Optional[pd.DataFrame], Optional[Exception], str]:
    """Returns (df, error, kind) where kind is one of
    "ok"/"provider_error"/"missing_method"/"not_configured"/"unsupported".

    `ProviderNotConfiguredError`/`ProviderUnsupportedError` (P1B.1,
    raised by `ProviderRouter` or a provider like `YahooFinanceAdapter`)
    are checked *before* the generic `ProviderError` branch — both are
    `ProviderError` subclasses, but they mean something more specific
    ("no route decided yet" / "known, deliberate capability gap") than a
    plain unexpected provider failure, and must not be classified as a
    generic `fail`/`permission_denied`.
    """
    try:
        df = fn()
    except ProviderNotConfiguredError as exc:
        return None, exc, "not_configured"
    except ProviderUnsupportedError as exc:
        return None, exc, "unsupported"
    except ProviderError as exc:
        return None, exc, "provider_error"
    except AttributeError as exc:
        return None, exc, "missing_method"
    return df, None, "ok"


def _looks_permission_related(error: Exception) -> bool:
    message = str(error).lower()
    return any(keyword.lower() in message for keyword in _PERMISSION_KEYWORDS)


def _check(
    *,
    check_name: str,
    market: Optional[str],
    data_type: str,
    sample_symbol: Optional[str],
    fn,
    date: str,
    gaps: Optional[DataGapRegistry],
    sample_symbol_required: bool = False,
) -> ProviderCheck:
    if sample_symbol_required and not sample_symbol:
        return ProviderCheck(
            check_name=check_name,
            market=market,
            data_type=data_type,
            status="not_configured",
            sample_symbol=sample_symbol,
            warning=f"no sample symbol configured for market {market!r} — check not attempted",
        )

    df, error, kind = _run_call(fn)

    if kind == "missing_method":
        return ProviderCheck(
            check_name=check_name,
            market=market,
            data_type=data_type,
            status="skipped",
            sample_symbol=sample_symbol,
            warning=f"provider does not implement this call: {error}",
        )

    if kind == "not_configured":
        return ProviderCheck(
            check_name=check_name,
            market=market,
            data_type=data_type,
            status="not_configured",
            sample_symbol=sample_symbol,
            warning=str(error),
        )

    if kind == "unsupported":
        gap_id = None
        if gaps is not None:
            gap = gaps.record_gap(
                date=date,
                market=market,
                symbol=sample_symbol,
                provider="provider_diagnostics",
                data_type=data_type,
                severity="info",
                message=f"{check_name}: {error}",
            )
            gap_id = gap["gap_id"]
        return ProviderCheck(
            check_name=check_name,
            market=market,
            data_type=data_type,
            status="unsupported",
            sample_symbol=sample_symbol,
            rows_returned=0,
            warning=str(error),
            data_gap_id=gap_id,
        )

    if kind == "provider_error":
        status = "permission_denied" if _looks_permission_related(error) else "fail"
        gap_id = None
        if gaps is not None:
            gap = gaps.record_gap(
                date=date,
                market=market,
                symbol=sample_symbol,
                provider="provider_diagnostics",
                data_type=data_type,
                severity="warning",
                message=f"{check_name} failed ({status}): {error}",
            )
            gap_id = gap["gap_id"]
        return ProviderCheck(
            check_name=check_name,
            market=market,
            data_type=data_type,
            status=status,
            sample_symbol=sample_symbol,
            rows_returned=0,
            warning=str(error),
            data_gap_id=gap_id,
        )

    # kind == "ok"
    row_count = 0 if df is None else len(df)
    if row_count == 0:
        gap_id = None
        if gaps is not None:
            gap = gaps.record_gap(
                date=date,
                market=market,
                symbol=sample_symbol,
                provider="provider_diagnostics",
                data_type=data_type,
                severity="info",
                message=f"{check_name} returned an empty result — coverage not confirmed either way.",
            )
            gap_id = gap["gap_id"]
        return ProviderCheck(
            check_name=check_name,
            market=market,
            data_type=data_type,
            status="unknown_empty",
            sample_symbol=sample_symbol,
            rows_returned=0,
            warning="empty result — coverage not confirmed",
            data_gap_id=gap_id,
        )

    return ProviderCheck(
        check_name=check_name,
        market=market,
        data_type=data_type,
        status="pass",
        sample_symbol=sample_symbol,
        rows_returned=row_count,
    )


def run_checks_for_market(
    *,
    provider: Any,
    market: str,
    date: str,
    sample_symbol: Optional[str] = None,
    gaps: Optional[DataGapRegistry] = None,
    lookback_days: int = 30,
) -> list[ProviderCheck]:
    """Runs every P0 data category's check for one market. Pure/testable —
    takes any duck-typed provider, real or fake."""
    sample_symbol = sample_symbol or DEFAULT_SAMPLE_SYMBOLS.get(market)
    start, end = lookback_range(date, lookback_days)
    index_code = DEFAULT_PRIMARY_INDEX.get(market)

    checks: list[ProviderCheck] = []

    checks.append(
        _check(
            check_name=_BARS_CHECK_NAME.get(market, f"{market.lower()}_daily_bars"),
            market=market,
            data_type="daily_bars",
            sample_symbol=sample_symbol,
            fn=lambda: provider.get_daily_bars(sample_symbol, market, start, end),
            date=date,
            gaps=gaps,
            sample_symbol_required=True,
        )
    )

    if index_code:
        checks.append(
            _check(
                check_name=f"{market.lower()}_index_bars",
                market=market,
                data_type="index_bars",
                sample_symbol=index_code,
                fn=lambda: provider.get_index_bars(index_code, market, start, end),
                date=date,
                gaps=gaps,
            )
        )

    checks.append(
        _check(
            check_name=f"{market.lower()}_stock_basic",
            market=market,
            data_type="stock_basic",
            sample_symbol=None,
            fn=lambda: provider.get_stock_basic(market),
            date=date,
            gaps=gaps,
        )
    )

    checks.append(
        _check(
            check_name=f"{market.lower()}_sector_classification",
            market=market,
            data_type="sector_classification",
            sample_symbol=None,
            fn=lambda: provider.get_sector_classification(market),
            date=date,
            gaps=gaps,
        )
    )

    checks.append(
        _check(
            check_name=f"{market.lower()}_fundamentals",
            market=market,
            data_type="fundamentals",
            sample_symbol=sample_symbol,
            fn=lambda: provider.get_fundamentals(sample_symbol, market, date),
            date=date,
            gaps=gaps,
            sample_symbol_required=True,
        )
    )

    checks.append(
        _check(
            check_name=f"{market.lower()}_trading_calendar",
            market=market,
            data_type="trading_calendar",
            sample_symbol=None,
            fn=lambda: provider.get_trading_calendar(market, start, end),
            date=date,
            gaps=gaps,
        )
    )

    return checks


def reconcile_cross_market_checks(
    checks: list[ProviderCheck],
    *,
    date: str,
    gaps: Optional[DataGapRegistry] = None,
) -> list[ProviderCheck]:
    """P1A.1 §1/§3.1: cross-market reconciliation hardening.

    A single per-market check can't tell whether a "pass" is really that
    market's own data — it only knows the call didn't error and returned
    rows. The real report in
    `Claude_Cowork_P1A1_PROVIDER_COVERAGE_RECONCILIATION.md` §0 showed
    `h_stock_basic`/`us_stock_basic` both reporting `pass` with exactly
    5534 rows — identical to A股's `stock_basic` count — which is strong
    evidence `TushareAdapter.get_stock_basic` ignores its `market`
    argument and always returns the SSE/SZSE list, not real H/US
    universes.

    This function looks across all markets checked in one run: for every
    `data_type` in `RECONCILED_DATA_TYPES`, if market A股's check passed
    and some other market's check for the same data_type also reports
    "pass" with the exact same `rows_returned`, that other market's check
    is downgraded to "unsupported" — a suspected diagnostic duplicate,
    never confirmed real coverage. A股's own check is left untouched
    (it is the reference/first-confirmed market, not the one under
    suspicion). Every downgrade is also recorded as a `DataGap` so it is
    never silently hidden.

    Markets outside the reconciled set, or data_types not in
    `RECONCILED_DATA_TYPES`, pass through completely unchanged.
    """
    by_type: dict[str, dict[Optional[str], ProviderCheck]] = {}
    for check in checks:
        by_type.setdefault(check.data_type, {})[check.market] = check

    reconciled = list(checks)
    for data_type in RECONCILED_DATA_TYPES:
        markets_for_type = by_type.get(data_type, {})
        reference = markets_for_type.get("A")
        if reference is None or reference.status != "pass" or not reference.rows_returned:
            continue
        for market, check in markets_for_type.items():
            if market == "A" or check.status != "pass":
                continue
            if check.rows_returned != reference.rows_returned:
                continue
            gap_id = check.data_gap_id
            if gaps is not None:
                gap = gaps.record_gap(
                    date=date,
                    market=market,
                    symbol=check.sample_symbol,
                    provider="provider_diagnostics",
                    data_type=data_type,
                    severity="warning",
                    message=(
                        f"{check.check_name} returned the same row count "
                        f"({check.rows_returned}) as A股's {reference.check_name} — "
                        f"suspected reuse of A股 universe data, not confirmed as "
                        f"real {market} coverage."
                    ),
                )
                gap_id = gap["gap_id"]
            idx = reconciled.index(check)
            reconciled[idx] = check.model_copy(
                update={
                    "status": "unsupported",
                    "warning": (
                        f"suspected diagnostic duplication: same row count as A股 "
                        f"({check.rows_returned}) — provider may be ignoring the "
                        f"market parameter; not confirmed as real {market} coverage"
                    ),
                    "data_gap_id": gap_id,
                }
            )
    return reconciled

    return checks
