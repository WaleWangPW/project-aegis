"""Phase 1 tests for MarketDataService — not one of the 5 explicitly named
test files in Phase 1 spec §5, but the module itself (§4.7) is in scope
and acceptance item 8 ("missing H/US Tushare coverage recorded as
DataGap") is specifically about this service, so it gets its own tests.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from aegis.data.cache import DataCache
from aegis.data.gaps import DataGapRegistry
from aegis.data.providers import ProviderError
from aegis.market.service import MarketDataService


class _EmptyProvider:
    def get_daily_bars(self, symbol, market, start, end):
        return pd.DataFrame()

    def get_index_bars(self, index_code, market, start, end):
        return pd.DataFrame()


class _FailingProvider:
    def get_daily_bars(self, symbol, market, start, end):
        raise ProviderError("US market not covered by current Tushare plan")

    def get_index_bars(self, index_code, market, start, end):
        raise ProviderError("index not covered")


class _WorkingProvider:
    def __init__(self, df):
        self._df = df

    def get_daily_bars(self, symbol, market, start, end):
        return self._df

    def get_index_bars(self, index_code, market, start, end):
        return self._df


def test_empty_result_records_data_gap(tmp_path: Path):
    gaps = DataGapRegistry(tmp_path / "data_gaps.jsonl")
    service = MarketDataService(provider=_EmptyProvider(), cache=None, gaps=gaps)
    df = service.get_daily_bars_cached("CRCL", "US", "20260601", "20260701")
    assert df.empty
    recorded = gaps.list_gaps()
    assert len(recorded) == 1
    assert recorded[0]["symbol"] == "CRCL"
    assert recorded[0]["market"] == "US"


def test_provider_error_records_data_gap_not_crash(tmp_path: Path):
    gaps = DataGapRegistry(tmp_path / "data_gaps.jsonl")
    service = MarketDataService(provider=_FailingProvider(), cache=None, gaps=gaps)
    df = service.get_daily_bars_cached("CRCL", "US", "20260601", "20260701")
    assert df.empty
    recorded = gaps.list_gaps()
    assert len(recorded) == 1
    assert "not covered" in recorded[0]["message"]


def test_successful_result_is_cached_and_reused(tmp_path: Path):
    df = pd.DataFrame({"trade_date": ["20260701"], "close": [109.5]})
    provider = _WorkingProvider(df)
    cache = DataCache(tmp_path / "cache")
    service = MarketDataService(provider=provider, cache=cache, gaps=None)

    first = service.get_daily_bars_cached("CRCL", "US", "20260601", "20260701")
    assert not first.empty
    assert cache.exists("US", "daily_bars", "CRCL_20260601_20260701")

    # Second call should be served from cache; swap provider to prove it.
    service.provider = _FailingProvider()
    second = service.get_daily_bars_cached("CRCL", "US", "20260601", "20260701")
    assert not second.empty
    assert list(second["close"]) == [109.5]


def test_get_latest_close_returns_float(tmp_path: Path):
    df = pd.DataFrame({"trade_date": ["20260701"], "close": [109.5]})
    service = MarketDataService(provider=_WorkingProvider(df), cache=None, gaps=None)
    price = service.get_latest_close("CRCL", "US", as_of="20260701")
    assert price == 109.5


def test_get_latest_close_returns_none_on_empty(tmp_path: Path):
    gaps = DataGapRegistry(tmp_path / "data_gaps.jsonl")
    service = MarketDataService(provider=_EmptyProvider(), cache=None, gaps=gaps)
    price = service.get_latest_close("CRCL", "US", as_of="20260701")
    assert price is None


def test_data_gap_includes_consumer_impact_and_generic_provider_label_for_plain_provider(tmp_path: Path):
    # P1B.3: a plain (non-router) provider has no `route_name_for`, so
    # the gap's `provider` field falls back to the generic label — but
    # `consumer_impact` and the error type are still always populated.
    gaps = DataGapRegistry(tmp_path / "data_gaps.jsonl")
    service = MarketDataService(provider=_FailingProvider(), cache=None, gaps=gaps)
    df = service.get_daily_bars_cached("CRCL", "US", "20260601", "20260701")
    assert df.empty
    recorded = gaps.list_gaps()
    assert len(recorded) == 1
    gap = recorded[0]
    assert gap["provider"] == "market_data_service"
    assert gap["consumer_impact"]
    assert "ProviderError" in gap["message"]


def test_data_gap_on_empty_result_also_includes_consumer_impact(tmp_path: Path):
    gaps = DataGapRegistry(tmp_path / "data_gaps.jsonl")
    service = MarketDataService(provider=_EmptyProvider(), cache=None, gaps=gaps)
    df = service.get_index_bars_cached("SPX", "US", "20260601", "20260701")
    assert df.empty
    recorded = gaps.list_gaps()
    assert len(recorded) == 1
    assert recorded[0]["consumer_impact"]
