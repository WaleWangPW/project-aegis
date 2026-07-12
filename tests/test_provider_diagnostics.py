"""P1A tests for aegis/data/live_validation.py + provider_diagnostics.py.

Fake provider / fake env dict only, no real Tushare/network — same
convention as every prior phase's tests.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from aegis.data.gaps import DataGapRegistry
from aegis.data.live_validation import validate_real_data
from aegis.data.providers import ProviderError


def _bars() -> pd.DataFrame:
    return pd.DataFrame({"trade_date": ["20260601", "20260602"], "close": [10.0, 11.0], "vol": [1000.0, 1000.0]})


_STOCK_BASIC_SIZES = {"A": 40, "H": 25, "US": 60}


class _FullySupportedFakeProvider:
    """Every method returns non-empty data for every market — a fully
    "healthy" provider, used to test the success-report shape.

    `get_stock_basic` intentionally returns a *different* row count per
    market (real per-market universes are naturally different sizes) so
    this fixture represents genuinely distinct H/US coverage rather than
    the diagnostic-bug pattern (`_StockBasicReusesAShareProvider` below)
    that P1A.1's cross-market reconciliation exists to catch."""

    def get_daily_bars(self, symbol, market, start, end):
        return _bars()

    def get_index_bars(self, index_code, market, start, end):
        return _bars()

    def get_stock_basic(self, market):
        n = _STOCK_BASIC_SIZES.get(market, 10)
        return pd.DataFrame([{"symbol": f"{market}-{i}"} for i in range(n)])

    def get_sector_classification(self, market):
        return pd.DataFrame([{"index_code": "801010.SI", "index_name": "Fake Sector"}])

    def get_fundamentals(self, symbol, market, as_of):
        return pd.DataFrame([{"pe_ratio": 18.4}])

    def get_trading_calendar(self, market, start, end):
        return pd.DataFrame({"cal_date": ["20260601", "20260602"], "is_open": [1, 1]})


class _AFailsDailyBarsProvider(_FullySupportedFakeProvider):
    def get_daily_bars(self, symbol, market, start, end):
        if market == "A":
            raise ProviderError("simulated upstream failure for A-share daily bars")
        return super().get_daily_bars(symbol, market, start, end)


class _PermissionDeniedDailyBarsProvider(_FullySupportedFakeProvider):
    def get_daily_bars(self, symbol, market, start, end):
        if market == "H":
            raise ProviderError("抱歉，您没有该接口权限 (permission denied for this endpoint)")
        return super().get_daily_bars(symbol, market, start, end)


class _StockBasicReusesAShareProvider(_FullySupportedFakeProvider):
    """Reproduces the exact real-world bug from
    `Claude_Cowork_P1A1_PROVIDER_COVERAGE_RECONCILIATION.md` §0: H/US
    `stock_basic` silently returns the same rows as A股 regardless of
    `market` — a provider abstraction bug, not real H/US coverage."""

    def get_stock_basic(self, market):
        # Same content for every market, ignoring `market` entirely.
        return pd.DataFrame([{"symbol": f"A-{i}"} for i in range(_STOCK_BASIC_SIZES["A"])])


class _MissingSampleSymbolProvider(_FullySupportedFakeProvider):
    """A healthy provider used together with `DEFAULT_SAMPLE_SYMBOLS`
    intentionally lacking an entry for one market, to exercise the
    "not_configured" status."""


def test_provider_diagnostics_missing_token_does_not_print_secret(capsys):
    report = validate_real_data(env={}, markets=["A", "H", "US"])
    captured = capsys.readouterr()

    # The library layer never prints anything itself — printing is the
    # CLI's job — so there is nothing to leak here regardless.
    assert captured.out == ""
    assert captured.err == ""
    assert report.token_present is False
    assert report.network_available is False
    assert report.checks == []
    assert report.summary.critical_gaps  # honest note that no checks were attempted


def test_provider_diagnostics_success_report_shape():
    provider = _FullySupportedFakeProvider()
    report = validate_real_data(
        env={"TUSHARE_TOKEN": "fake-token"}, provider=provider, markets=["A", "H", "US"], date="2026-07-04"
    )

    assert report.token_present is True
    assert report.network_available is True
    assert report.provider == "tushare"
    assert report.checks, "expected at least one check per market/category"
    assert all(
        c.status
        in ("pass", "fail", "skipped", "unknown_empty", "unsupported", "permission_denied", "not_configured")
        for c in report.checks
    )
    # A fully-supported fake provider with non-empty, per-market-distinct
    # results everywhere should produce zero fail/skipped/unknown_empty/
    # unsupported/permission_denied/not_configured checks.
    assert report.summary.fail_count == 0
    assert report.summary.skipped_count == 0
    assert report.summary.unknown_count == 0
    assert report.summary.unsupported_count == 0
    assert report.summary.permission_denied_count == 0
    assert report.summary.not_configured_count == 0
    assert report.summary.pass_count == len(report.checks)
    # Schema fields present on every check.
    check = report.checks[0]
    assert check.check_name
    assert check.data_type
    assert check.rows_returned is not None and check.rows_returned > 0
    # required categories exist somewhere in the check list
    check_names = {c.check_name for c in report.checks}
    assert "a_share_daily_bars" in check_names
    assert "h_share_daily_bars" in check_names
    assert "us_daily_bars" in check_names


def test_provider_diagnostics_failure_records_data_gap(tmp_path: Path):
    gaps = DataGapRegistry(tmp_path / "data_gaps.jsonl")
    provider = _AFailsDailyBarsProvider()

    report = validate_real_data(
        env={"TUSHARE_TOKEN": "fake-token"},
        provider=provider,
        markets=["A"],
        date="2026-07-04",
        gaps=gaps,
    )

    failed = [c for c in report.checks if c.status == "fail"]
    assert failed, "expected the A-share daily bars check to fail"
    assert failed[0].check_name == "a_share_daily_bars"
    assert failed[0].data_gap_id is not None
    assert report.summary.fail_count == 1
    assert "a_share_daily_bars" in report.summary.critical_gaps

    logged_gaps = gaps.list_gaps()
    assert any(g["data_type"] == "daily_bars" and g["market"] == "A" for g in logged_gaps)


def test_provider_diagnostics_permission_denied_is_distinguished_from_generic_fail(tmp_path: Path):
    """P1A.1 §1: a `ProviderError` whose message looks entitlement/quota
    related must be reported as the more specific `permission_denied`
    status, not a generic `fail` — so triage doesn't have to re-read raw
    error strings to know it's a permissions problem, not a random
    failure."""
    gaps = DataGapRegistry(tmp_path / "data_gaps.jsonl")
    provider = _PermissionDeniedDailyBarsProvider()

    report = validate_real_data(
        env={"TUSHARE_TOKEN": "fake-token"},
        provider=provider,
        markets=["A", "H"],
        date="2026-07-05",
        gaps=gaps,
    )

    denied = [c for c in report.checks if c.check_name == "h_share_daily_bars"]
    assert len(denied) == 1
    assert denied[0].status == "permission_denied"
    assert denied[0].data_gap_id is not None
    assert report.summary.permission_denied_count == 1
    assert report.summary.fail_count == 0
    # Still surfaced as a critical gap — a permission problem is just as
    # actionable as a generic failure, never quietly downgraded.
    assert "h_share_daily_bars" in report.summary.critical_gaps


def test_provider_diagnostics_flags_stock_basic_reusing_a_share_data(tmp_path: Path):
    """P1A.1 §1/§3: reproduces the real observed bug
    (`Claude_Cowork_P1A1_PROVIDER_COVERAGE_RECONCILIATION.md` §0) —
    h_stock_basic/us_stock_basic returning the exact same row count as
    A股. These must be downgraded from a naive "pass" to "unsupported",
    never misread as confirmed H/US coverage. A股's own stock_basic check
    stays "pass" since it is the reference market."""
    gaps = DataGapRegistry(tmp_path / "data_gaps.jsonl")
    provider = _StockBasicReusesAShareProvider()

    report = validate_real_data(
        env={"TUSHARE_TOKEN": "fake-token"},
        provider=provider,
        markets=["A", "H", "US"],
        date="2026-07-05",
        gaps=gaps,
    )

    by_name = {c.check_name: c for c in report.checks}
    assert by_name["a_stock_basic"].status == "pass"
    assert by_name["h_stock_basic"].status == "unsupported"
    assert by_name["us_stock_basic"].status == "unsupported"
    assert by_name["h_stock_basic"].data_gap_id is not None
    assert by_name["us_stock_basic"].data_gap_id is not None
    assert report.summary.unsupported_count == 2
    # An "unsupported" diagnostic-bug finding is not the same severity as
    # an unexplained "fail"/"permission_denied" — it's excluded from
    # critical_gaps, but still fully recorded via DataGap (never hidden).
    assert "h_stock_basic" not in report.summary.critical_gaps
    assert "us_stock_basic" not in report.summary.critical_gaps

    logged_gaps = gaps.list_gaps()
    assert any(g["market"] == "H" and g["data_type"] == "stock_basic" for g in logged_gaps)
    assert any(g["market"] == "US" and g["data_type"] == "stock_basic" for g in logged_gaps)

    # Daily bars (not in RECONCILED_DATA_TYPES) are untouched even though
    # this same fake provider's bars fixture also returns identical
    # content across markets — reconciliation is narrowly scoped to
    # stock_basic, matching the specific bug actually observed, not a
    # blanket "same row count anywhere is suspicious" rule.
    assert by_name["a_share_daily_bars"].status == "pass"
    assert by_name["h_share_daily_bars"].status == "pass"
    assert by_name["us_daily_bars"].status == "pass"


def test_provider_diagnostics_missing_sample_symbol_is_not_configured():
    """P1A.1 §1: a market with no configured sample symbol (not in
    `DEFAULT_SAMPLE_SYMBOLS`, and none explicitly passed) must never
    silently attempt — and possibly falsely pass/fail — a symbol-keyed
    check. It should be reported as `not_configured` without ever calling
    the provider for that check."""
    from aegis.data.provider_diagnostics import run_checks_for_market

    provider = _MissingSampleSymbolProvider()
    # "XX" is deliberately not a key in DEFAULT_SAMPLE_SYMBOLS, simulating
    # a market added without a configured diagnostic sample symbol.
    checks = run_checks_for_market(provider=provider, market="XX", date="2026-07-05")

    by_name = {c.check_name: c for c in checks}
    assert by_name["xx_daily_bars"].status == "not_configured"
    assert by_name["xx_fundamentals"].status == "not_configured"
    # Categories that don't need a sample symbol are unaffected.
    assert by_name["xx_stock_basic"].status == "pass"
