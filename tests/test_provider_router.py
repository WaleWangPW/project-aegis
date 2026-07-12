"""P1B.1 tests for aegis/data/provider_router.py.

Fake provider objects only — no real Tushare/yfinance/network calls,
same convention as every other provider test in this repo.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from aegis.data.gaps import DataGapRegistry
from aegis.data.provider_router import ProviderRouter
from aegis.data.providers import ProviderError, ProviderNotConfiguredError, ProviderUnsupportedError
from aegis.data.symbol_mapping import SymbolMapper
from aegis.market.service import MarketDataService

_ROUTING_CONFIG = {
    "routing": {
        "daily_bars": {"A": "tushare", "H": "yahoo_finance", "US": "yahoo_finance"},
        "index_bars": {"A": "tushare", "H": "yahoo_finance", "US": "yahoo_finance"},
        "stock_basic": {"A": "tushare", "H": "not_configured", "US": "not_configured"},
        "sector_classification": {"A": "tushare", "H": "unsupported", "US": "unsupported"},
    },
    "symbol_mapping": {
        "yahoo_finance": {
            "H": {"symbols": {"00700.HK": "0700.HK"}, "indexes": {"HSI.HI": "^HSI"}},
            "US": {"symbols": {"CRCL": "CRCL"}, "indexes": {"SPX": "^GSPC"}},
        }
    },
}


def _bars(tag: str) -> pd.DataFrame:
    return pd.DataFrame({"trade_date": ["20260601"], "close": [10.0], "vol": [1000], "tag": [tag]})


class _RecordingProvider:
    """Records every symbol it was actually called with, so tests can
    assert that symbol mapping happened before the call reached here."""

    def __init__(self, tag: str, bars: pd.DataFrame | None = None, raise_error: bool = False):
        self.tag = tag
        self.calls: list[tuple] = []
        self._bars = bars if bars is not None else _bars(tag)
        self._raise_error = raise_error

    def get_daily_bars(self, symbol, market, start, end):
        self.calls.append(("daily_bars", symbol, market, start, end))
        if self._raise_error:
            raise ProviderError(f"simulated failure in {self.tag}")
        return self._bars.copy()

    def get_index_bars(self, index_code, market, start, end):
        self.calls.append(("index_bars", index_code, market, start, end))
        return self._bars.copy()

    def get_stock_basic(self, market):
        self.calls.append(("stock_basic", market))
        return self._bars.copy()


@pytest.fixture
def router() -> ProviderRouter:
    tushare = _RecordingProvider("tushare")
    yahoo = _RecordingProvider("yahoo_finance")
    return ProviderRouter(
        providers={"tushare": tushare, "yahoo_finance": yahoo},
        routing_config=_ROUTING_CONFIG,
    )


def test_a_share_daily_bars_route_to_tushare(router: ProviderRouter):
    tushare = router._providers["tushare"]
    yahoo = router._providers["yahoo_finance"]

    df = router.get_daily_bars("000001.SZ", "A", "2026-06-01", "2026-06-30")

    assert not df.empty
    assert tushare.calls == [("daily_bars", "000001.SZ", "A", "2026-06-01", "2026-06-30")]
    assert yahoo.calls == []


def test_h_and_us_daily_bars_route_to_secondary_provider_with_symbol_mapping(router: ProviderRouter):
    yahoo = router._providers["yahoo_finance"]

    router.get_daily_bars("00700.HK", "H", "2026-06-01", "2026-06-30")
    router.get_daily_bars("CRCL", "US", "2026-06-01", "2026-06-30")

    # The secondary provider must receive the *mapped* symbol, not
    # Aegis's own internal code — "00700.HK" -> "0700.HK" for H, while
    # "CRCL" stays "CRCL" for US (explicit identity mapping).
    assert ("daily_bars", "0700.HK", "H", "2026-06-01", "2026-06-30") in yahoo.calls
    assert ("daily_bars", "CRCL", "US", "2026-06-01", "2026-06-30") in yahoo.calls


def test_h_index_bars_route_to_secondary_provider_with_index_mapping(router: ProviderRouter):
    yahoo = router._providers["yahoo_finance"]
    router.get_index_bars("HSI.HI", "H", "2026-06-01", "2026-06-30")
    assert ("index_bars", "^HSI", "H", "2026-06-01", "2026-06-30") in yahoo.calls


def test_us_index_bars_route_to_secondary_provider_with_index_mapping(router: ProviderRouter):
    yahoo = router._providers["yahoo_finance"]
    router.get_index_bars("SPX", "US", "2026-06-01", "2026-06-30")
    assert ("index_bars", "^GSPC", "US", "2026-06-01", "2026-06-30") in yahoo.calls


def test_h_us_stock_basic_does_not_fall_back_to_a_share_stock_basic(router: ProviderRouter):
    tushare = router._providers["tushare"]

    # A股 stock_basic still works normally.
    a_df = router.get_stock_basic("A")
    assert not a_df.empty
    assert tushare.calls == [("stock_basic", "A")]

    # H/US must never silently reuse A股's stock_basic (the exact P1A.1
    # bug) — routing them to "not_configured" means the call is refused
    # structurally, before any provider (including tushare) is ever
    # touched again for these markets.
    with pytest.raises(ProviderNotConfiguredError):
        router.get_stock_basic("H")
    with pytest.raises(ProviderNotConfiguredError):
        router.get_stock_basic("US")

    # Confirm tushare was not called again for H/US.
    assert tushare.calls == [("stock_basic", "A")]


def test_route_marked_unsupported_raises_provider_unsupported_error(router: ProviderRouter):
    with pytest.raises(ProviderUnsupportedError):
        router.get_sector_classification("H")
    with pytest.raises(ProviderUnsupportedError):
        router.get_sector_classification("US")


def test_missing_route_raises_provider_not_configured_error(router: ProviderRouter):
    # "fundamentals" has no entry at all in _ROUTING_CONFIG's routing dict.
    with pytest.raises(ProviderNotConfiguredError):
        router.get_fundamentals("000001.SZ", "A", "2026-06-30")


def test_route_naming_unregistered_provider_raises_provider_error():
    router = ProviderRouter(
        providers={},  # no "tushare" instance registered
        routing_config={"routing": {"daily_bars": {"A": "tushare"}}},
    )
    with pytest.raises(ProviderError):
        router.get_daily_bars("000001.SZ", "A", "2026-06-01", "2026-06-30")


def test_route_table_lists_every_configured_pair(router: ProviderRouter):
    rows = router.route_table()
    assert {"data_type": "stock_basic", "market": "H", "provider": "not_configured"} in rows
    assert {"data_type": "daily_bars", "market": "A", "provider": "tushare"} in rows


def test_market_data_service_accepts_provider_router_and_records_data_gap(tmp_path: Path):
    tushare = _RecordingProvider("tushare")
    yahoo_failing = _RecordingProvider("yahoo_finance", raise_error=True)
    router = ProviderRouter(
        providers={"tushare": tushare, "yahoo_finance": yahoo_failing},
        routing_config=_ROUTING_CONFIG,
    )
    gaps = DataGapRegistry(tmp_path / "data_gaps.jsonl")
    service = MarketDataService(provider_router=router, cache=None, gaps=gaps)

    df = service.get_daily_bars_cached("00700.HK", "H", "2026-06-01", "2026-06-30")

    assert df.empty
    logged = gaps.list_gaps()
    assert any(g["market"] == "H" and g["data_type"] == "daily_bars" for g in logged)


def test_market_data_service_still_works_with_plain_provider(tmp_path: Path):
    # Existing (pre-P1B.1) call convention — provider=, no router — must
    # remain completely unaffected.
    tushare = _RecordingProvider("tushare")
    service = MarketDataService(provider=tushare, cache=None, gaps=None)
    df = service.get_daily_bars_cached("000001.SZ", "A", "2026-06-01", "2026-06-30")
    assert not df.empty


def test_market_data_service_requires_provider_or_router():
    with pytest.raises(ValueError):
        MarketDataService()


def test_symbol_mapper_can_be_injected_explicitly():
    tushare = _RecordingProvider("tushare")
    yahoo = _RecordingProvider("yahoo_finance")
    custom_mapper = SymbolMapper({"yahoo_finance": {"H": {"symbols": {"00700.HK": "OVERRIDE.HK"}}}})
    router = ProviderRouter(
        providers={"tushare": tushare, "yahoo_finance": yahoo},
        routing_config=_ROUTING_CONFIG,
        symbol_mapper=custom_mapper,
    )
    router.get_daily_bars("00700.HK", "H", "2026-06-01", "2026-06-30")
    assert ("daily_bars", "OVERRIDE.HK", "H", "2026-06-01", "2026-06-30") in yahoo.calls
