"""P1B.1 tests for aegis/data/yahoo_finance_adapter.py.

Fake `yfinance`-shaped client only — no real network/package call from
pytest, same convention as `tests/test_tushare_adapter.py` (if present)
and every other provider test in this repo.
"""

from __future__ import annotations

import re

import pandas as pd
import pytest

import aegis.data.yahoo_finance_adapter as yahoo_finance_adapter_module
from aegis.data.providers import ProviderError, ProviderUnsupportedError
from aegis.data.yahoo_finance_adapter import SOURCE_LABEL, YahooFinanceAdapter


class _FakeYfClient:
    """Mimics `yfinance.download(...)`'s shape: a Date-indexed DataFrame
    with Open/High/Low/Close/Volume columns. Also records the exact
    `start`/`end` values it received, so tests can confirm what actually
    reaches the (simulated) real `yfinance` call."""

    def __init__(self, frame: pd.DataFrame | None = None, raise_error: bool = False):
        self._frame = frame
        self._raise_error = raise_error
        self.calls: list[tuple] = []

    def download(self, symbol, start=None, end=None, progress=None):
        self.calls.append((symbol, start, end))
        if self._raise_error:
            raise RuntimeError("simulated yfinance network failure")
        if self._frame is None:
            return pd.DataFrame()
        return self._frame.copy()


def _sample_yf_frame() -> pd.DataFrame:
    idx = pd.to_datetime(["2026-06-01", "2026-06-02"])
    return pd.DataFrame(
        {"Open": [10.0, 10.5], "High": [10.2, 10.8], "Low": [9.8, 10.3], "Close": [10.1, 10.6], "Volume": [1000, 1200]},
        index=idx,
    ).rename_axis("Date")


def test_get_daily_bars_normalizes_fake_yfinance_data():
    adapter = YahooFinanceAdapter(client=_FakeYfClient(_sample_yf_frame()))
    df = adapter.get_daily_bars("0700.HK", "H", "2026-06-01", "2026-06-02")

    assert not df.empty
    assert list(df["trade_date"]) == ["20260601", "20260602"]
    assert list(df["close"]) == [10.1, 10.6]
    assert list(df["open"]) == [10.0, 10.5]
    assert list(df["vol"]) == [1000, 1200]
    assert (df["source"] == SOURCE_LABEL).all()


def test_get_index_bars_normalizes_fake_yfinance_data():
    adapter = YahooFinanceAdapter(client=_FakeYfClient(_sample_yf_frame()))
    df = adapter.get_index_bars("^HSI", "H", "2026-06-01", "2026-06-02")

    assert not df.empty
    assert (df["source"] == SOURCE_LABEL).all()
    assert "trade_date" in df.columns


def test_empty_provider_result_returns_empty_dataframe_not_fake_bars():
    adapter = YahooFinanceAdapter(client=_FakeYfClient(pd.DataFrame()))
    df = adapter.get_daily_bars("CRCL", "US", "2026-06-01", "2026-06-02")

    assert isinstance(df, pd.DataFrame)
    assert df.empty


def test_provider_exception_becomes_controlled_provider_error():
    adapter = YahooFinanceAdapter(client=_FakeYfClient(raise_error=True))
    with pytest.raises(ProviderError):
        adapter.get_daily_bars("CRCL", "US", "2026-06-01", "2026-06-02")


def test_no_client_configured_raises_provider_error(monkeypatch):
    # `YahooFinanceAdapter(client=None)` falls back to the module-level
    # `yf` (the real `yfinance` package, if installed) — same lazy-import
    # convention `TushareAdapter` uses for `tushare`. This test's intent
    # is "no client/package available at all", so the module-level `yf`
    # must be forced to `None` here rather than relying on whether the
    # real `yfinance` package happens to be installed in whatever
    # environment `pytest` runs in (P1B.2 QA fix: this test previously
    # depended on ambient environment state and failed wherever
    # `yfinance` is actually installed, e.g. a real local machine running
    # live validation — see docs/P1B2_PROVIDER_ROUTER_LIVE_VALIDATION_RESULT.md).
    monkeypatch.setattr(yahoo_finance_adapter_module, "yf", None)
    adapter = YahooFinanceAdapter(client=None)
    with pytest.raises(ProviderError):
        adapter.get_daily_bars("CRCL", "US", "2026-06-01", "2026-06-02")
    assert adapter.is_configured() is False


# -- P1B.4 local smoke failure triage: compact-date normalization ------
#
# Root cause: real `yfinance` parses string start/end via a strict
# `datetime.strptime(dt, "%Y-%m-%d")` internally (see
# `yfinance.utils._parse_user_dt`); a compact "YYYYMMDD" string (the
# Tushare-oriented convention `aegis.utils.dates.lookback_range`
# produces, which `MarketSnapshotService`/`scripts/run_market_snapshot_smoke.py`
# both use) fails that strict parse. `yfinance`'s own `_download_one`
# swallows the resulting `ValueError` and substitutes an empty result
# instead of raising — so this bug was never visible as a crash, only as
# zero rows. These tests use a fake client that behaves like the real
# one would if given a malformed date (only responds with real data for
# the exact string it expects) to actually catch a regression here.


class _StrictDateFakeYfClient:
    """Only returns real data if `start`/`end` are exactly the dashed
    `"YYYY-MM-DD"` format the real `yfinance` package requires — anything
    else (e.g. an un-normalized compact `"YYYYMMDD"` string) gets an empty
    result, exactly mirroring how the real package actually behaves."""

    _DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

    def __init__(self, frame: pd.DataFrame):
        self._frame = frame
        self.calls: list[tuple] = []

    def download(self, symbol, start=None, end=None, progress=None):
        self.calls.append((symbol, start, end))
        if not (self._DATE_RE.match(start or "") and self._DATE_RE.match(end or "")):
            return pd.DataFrame()
        return self._frame.copy()


def test_get_daily_bars_normalizes_compact_dates_before_calling_client():
    client = _StrictDateFakeYfClient(_sample_yf_frame())
    adapter = YahooFinanceAdapter(client=client)

    df = adapter.get_daily_bars("0700.HK", "H", "20260601", "20260602")

    assert not df.empty
    assert client.calls[-1] == ("0700.HK", "2026-06-01", "2026-06-02")


def test_get_index_bars_normalizes_compact_dates_before_calling_client():
    client = _StrictDateFakeYfClient(_sample_yf_frame())
    adapter = YahooFinanceAdapter(client=client)

    df = adapter.get_index_bars("^HSI", "H", "20260601", "20260602")

    assert not df.empty
    assert client.calls[-1] == ("^HSI", "2026-06-01", "2026-06-02")


def test_already_dashed_dates_pass_through_unchanged():
    client = _StrictDateFakeYfClient(_sample_yf_frame())
    adapter = YahooFinanceAdapter(client=client)

    df = adapter.get_daily_bars("CRCL", "US", "2026-06-01", "2026-06-02")

    assert not df.empty
    assert client.calls[-1] == ("CRCL", "2026-06-01", "2026-06-02")


# -- P1B.4.1 smoke consistency fix: MultiIndex-columned yfinance shape --
#
# Root cause of the P1B.4.1 bug: real `yfinance` (recent versions) can
# return MultiIndex columns from `.download()` even for a single symbol
# (top level = field name, second level = ticker). Before this fix,
# `_normalize_ohlcv`'s alias matching (`str(col).strip().lower()`) never
# matched a tuple column key, so the returned frame kept its original row
# count but had zero usable OHLCV columns — `len(df) > 0` while
# `df.empty` was `True` (a DataFrame with rows but no columns is empty)
# and `"close" not in df.columns`. That is exactly what let a smoke
# report's naive `len(df) > 0` check say "pass" while
# `MarketSnapshotService`/`MarketRegimeAnalyzer` (which correctly check
# `df.empty` and `"close" in df.columns`) said "No index bars available".


def _multiindex_yf_frame() -> pd.DataFrame:
    idx = pd.to_datetime(["2026-06-01", "2026-06-02", "2026-06-03"])
    frame = pd.DataFrame(
        {
            "Open": [10.0, 10.5, 10.7], "High": [10.2, 10.8, 11.0], "Low": [9.8, 10.3, 10.4],
            "Close": [10.1, 10.6, 10.9], "Volume": [1000, 1200, 1300],
        },
        index=idx,
    ).rename_axis("Date")
    frame.columns = pd.MultiIndex.from_product([frame.columns, ["TICKER"]])
    return frame


def test_multiindex_columned_response_still_normalizes_to_usable_ohlcv_columns():
    adapter = YahooFinanceAdapter(client=_FakeYfClient(_multiindex_yf_frame()))
    df = adapter.get_index_bars("^HSI", "H", "2026-06-01", "2026-06-03")

    assert not df.empty
    assert "close" in df.columns
    assert list(df["close"]) == [10.1, 10.6, 10.9]
    assert list(df["trade_date"]) == ["20260601", "20260602", "20260603"]
    assert (df["source"] == SOURCE_LABEL).all()
    assert len(df) == 3


def test_multiindex_columned_response_also_normalizes_for_daily_bars():
    adapter = YahooFinanceAdapter(client=_FakeYfClient(_multiindex_yf_frame()))
    df = adapter.get_daily_bars("0700.HK", "H", "2026-06-01", "2026-06-03")

    assert not df.empty
    assert "close" in df.columns
    assert len(df) == 3


def test_flat_columns_are_unaffected_by_multiindex_flattening_logic():
    """Regression guard: the ordinary flat-column shape (already covered
    by every other test in this file) must produce byte-identical
    results to before this fix — the MultiIndex handling is additive."""
    adapter = YahooFinanceAdapter(client=_FakeYfClient(_sample_yf_frame()))
    df = adapter.get_daily_bars("0700.HK", "H", "2026-06-01", "2026-06-02")
    assert list(df["close"]) == [10.1, 10.6]


def test_stock_basic_is_explicitly_unsupported():
    adapter = YahooFinanceAdapter(client=_FakeYfClient())
    with pytest.raises(ProviderUnsupportedError):
        adapter.get_stock_basic("US")


def test_fundamentals_sector_and_calendar_are_explicitly_unsupported():
    adapter = YahooFinanceAdapter(client=_FakeYfClient())
    with pytest.raises(ProviderUnsupportedError):
        adapter.get_fundamentals("CRCL", "US", "2026-06-01")
    with pytest.raises(ProviderUnsupportedError):
        adapter.get_sector_classification("US")
    with pytest.raises(ProviderUnsupportedError):
        adapter.get_trading_calendar("US", "2026-06-01", "2026-06-02")
