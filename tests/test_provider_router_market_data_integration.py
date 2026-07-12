"""P1B.3 integration tests — MarketDataService consuming a real,
config-driven `ProviderRouter` (loaded from the actual
`config/providers.yaml`, with fake `tushare`/`yahoo_finance` provider
instances substituted in) rather than a hand-written routing dict.

This is what P1B.3 actually proves beyond P1B.1's router skeleton and
P1B.2's standalone live-validation CLI: that `MarketDataService` itself,
wired against the real production routing table, sends A股 requests to
Tushare, H/US requests to the `yahoo_finance` secondary route (confirmed
real via P1B.2's local live validation — see
`docs/P1B2_PROVIDER_ROUTER_LIVE_VALIDATION_RESULT.md`), keeps H/US
`stock_basic` structurally blocked, records an honest `DataGap` instead
of crashing on any route/provider failure, and never lets H/US Yahoo
results collide with A股 Tushare results in the cache.

Fake provider objects only — no real Tushare/yfinance/network calls.
"""

from __future__ import annotations

import inspect
from pathlib import Path

import pandas as pd
import pytest
import yaml

import aegis.data.provider_router as provider_router_module
import aegis.market.service as market_service_module
from aegis.data.cache import DataCache
from aegis.data.gaps import DataGapRegistry
from aegis.data.provider_router import ProviderRouter
from aegis.data.providers import ProviderError, ProviderNotConfiguredError
from aegis.market.service import MarketDataService

REPO_ROOT = Path(__file__).resolve().parents[1]
PROVIDERS_CONFIG_PATH = REPO_ROOT / "config" / "providers.yaml"


def _load_real_providers_config() -> dict:
    return yaml.safe_load(PROVIDERS_CONFIG_PATH.read_text(encoding="utf-8"))


def _bars(tag: str, n: int = 3) -> pd.DataFrame:
    return pd.DataFrame(
        {"trade_date": [f"2026060{i}" for i in range(1, n + 1)], "close": [10.0 + i for i in range(n)], "tag": [tag] * n}
    )


class _RecordingProvider:
    """Records every call it actually received, so tests can confirm
    which underlying provider a request was routed to and with which
    (already-mapped) symbol."""

    def __init__(self, tag: str, bars: pd.DataFrame | None = None, raise_error: Exception | None = None):
        self.tag = tag
        self.calls: list[tuple] = []
        self._bars = bars if bars is not None else _bars(tag)
        self._raise_error = raise_error

    def get_daily_bars(self, symbol, market, start, end):
        self.calls.append(("daily_bars", symbol, market, start, end))
        if self._raise_error:
            raise self._raise_error
        return self._bars.copy()

    def get_index_bars(self, index_code, market, start, end):
        self.calls.append(("index_bars", index_code, market, start, end))
        if self._raise_error:
            raise self._raise_error
        return self._bars.copy()

    def get_stock_basic(self, market):
        self.calls.append(("stock_basic", market))
        return self._bars.copy()


@pytest.fixture
def real_router():
    """A `ProviderRouter` built from the actual `config/providers.yaml`
    routing table, with fake `tushare`/`yahoo_finance` instances — proves
    MarketDataService honors the real production routing decisions, not
    just a test-only routing dict."""
    config = _load_real_providers_config()
    tushare = _RecordingProvider("tushare")
    yahoo = _RecordingProvider("yahoo_finance")
    router = ProviderRouter(providers={"tushare": tushare, "yahoo_finance": yahoo}, routing_config=config)
    return router, tushare, yahoo


# -- 1: A daily bars still use existing Tushare path --------------------


def test_a_daily_and_index_bars_still_route_to_tushare(real_router, tmp_path: Path):
    router, tushare, yahoo = real_router
    service = MarketDataService(provider_router=router, cache=None, gaps=None)

    daily = service.get_daily_bars_cached("000001.SZ", "A", "2026-06-01", "2026-06-30")
    index = service.get_index_bars_cached("SH000001", "A", "2026-06-01", "2026-06-30")

    assert not daily.empty
    assert not index.empty
    assert ("daily_bars", "000001.SZ", "A", "2026-06-01", "2026-06-30") in tushare.calls
    assert ("index_bars", "SH000001", "A", "2026-06-01", "2026-06-30") in tushare.calls
    assert yahoo.calls == []


# -- 2/3: H daily/index bars route through ProviderRouter/Yahoo --------


def test_h_daily_bars_route_through_provider_router_to_yahoo(real_router):
    router, tushare, yahoo = real_router
    service = MarketDataService(provider_router=router, cache=None, gaps=None)

    df = service.get_daily_bars_cached("00700.HK", "H", "2026-06-01", "2026-06-30")

    assert not df.empty
    assert tushare.calls == []
    # The router must map the internal symbol before yahoo ever sees it.
    assert ("daily_bars", "0700.HK", "H", "2026-06-01", "2026-06-30") in yahoo.calls


def test_h_index_bars_route_through_provider_router_to_yahoo(real_router):
    router, tushare, yahoo = real_router
    service = MarketDataService(provider_router=router, cache=None, gaps=None)

    df = service.get_index_bars_cached("HSI.HI", "H", "2026-06-01", "2026-06-30")

    assert not df.empty
    assert tushare.calls == []
    assert ("index_bars", "^HSI", "H", "2026-06-01", "2026-06-30") in yahoo.calls


# -- 4/5: US daily/index bars (incl. CRCL) route through Yahoo ---------


def test_us_daily_bars_including_crcl_route_through_provider_router_to_yahoo(real_router):
    router, tushare, yahoo = real_router
    service = MarketDataService(provider_router=router, cache=None, gaps=None)

    # CRCL is exercised here as an ordinary US sample symbol, exactly
    # like any other holding — no CRCL-specific branch exists anywhere
    # in MarketDataService or ProviderRouter.
    df = service.get_daily_bars_cached("CRCL", "US", "2026-06-01", "2026-06-30")

    assert not df.empty
    assert tushare.calls == []
    assert ("daily_bars", "CRCL", "US", "2026-06-01", "2026-06-30") in yahoo.calls


def test_us_index_bars_route_through_provider_router_to_yahoo(real_router):
    router, tushare, yahoo = real_router
    service = MarketDataService(provider_router=router, cache=None, gaps=None)

    df = service.get_index_bars_cached("SPX", "US", "2026-06-01", "2026-06-30")

    assert not df.empty
    assert tushare.calls == []
    assert ("index_bars", "^GSPC", "US", "2026-06-01", "2026-06-30") in yahoo.calls


# -- 6: H/US stock_basic remains not_configured, never false-passes ----


def test_h_and_us_stock_basic_remain_not_configured_in_real_config(real_router):
    router, tushare, yahoo = real_router
    with pytest.raises(ProviderNotConfiguredError):
        router.get_stock_basic("H")
    with pytest.raises(ProviderNotConfiguredError):
        router.get_stock_basic("US")
    # Confirm this was never satisfied by silently falling back to
    # tushare's A股 stock_basic (the exact P1A.1 bug).
    assert tushare.calls == []


# -- 7: dependency/network errors become DataGap, not crashes ----------


def test_yahoo_provider_error_becomes_data_gap_not_crash(real_router, tmp_path: Path):
    router, tushare, yahoo = real_router
    yahoo._raise_error = ProviderError("yfinance client/package is not available in this environment")
    gaps = DataGapRegistry(tmp_path / "data_gaps.jsonl")
    service = MarketDataService(provider_router=router, cache=None, gaps=gaps)

    df = service.get_daily_bars_cached("CRCL", "US", "2026-06-01", "2026-06-30")

    assert df.empty
    recorded = gaps.list_gaps()
    assert len(recorded) == 1
    gap = recorded[0]
    assert gap["market"] == "US"
    assert gap["symbol"] == "CRCL"
    assert gap["data_type"] == "daily_bars"
    # The gap must name the actual failing route, not a generic label —
    # and must not hide the error type/status.
    assert gap["provider"] == "yahoo_finance"
    assert "ProviderError" in gap["message"]
    assert "yahoo_finance" in gap["message"]
    assert gap["consumer_impact"]


def test_a_share_provider_error_labels_gap_with_tushare_route(real_router, tmp_path: Path):
    router, tushare, yahoo = real_router
    tushare._raise_error = ProviderError("simulated Tushare outage")
    gaps = DataGapRegistry(tmp_path / "data_gaps.jsonl")
    service = MarketDataService(provider_router=router, cache=None, gaps=gaps)

    df = service.get_daily_bars_cached("000001.SZ", "A", "2026-06-01", "2026-06-30")

    assert df.empty
    recorded = gaps.list_gaps()
    assert len(recorded) == 1
    assert recorded[0]["provider"] == "tushare"


def test_missing_route_returns_empty_and_records_not_configured_gap_not_crash(tmp_path: Path):
    # A deliberately incomplete routing config — H has no daily_bars
    # entry at all (distinct from the "not_configured" sentinel) — to
    # prove MarketDataService degrades honestly rather than crashing,
    # independent of what config/providers.yaml currently contains.
    config = {
        "routing": {
            "daily_bars": {"A": "tushare"},  # H/US intentionally absent
            "index_bars": {"A": "tushare", "H": "yahoo_finance", "US": "yahoo_finance"},
        },
        "symbol_mapping": {"yahoo_finance": {"H": {"indexes": {"HSI.HI": "^HSI"}}, "US": {"indexes": {"SPX": "^GSPC"}}}},
    }
    tushare = _RecordingProvider("tushare")
    yahoo = _RecordingProvider("yahoo_finance")
    router = ProviderRouter(providers={"tushare": tushare, "yahoo_finance": yahoo}, routing_config=config)
    gaps = DataGapRegistry(tmp_path / "data_gaps.jsonl")
    service = MarketDataService(provider_router=router, cache=None, gaps=gaps)

    df = service.get_daily_bars_cached("00700.HK", "H", "2026-06-01", "2026-06-30")

    assert df.empty
    assert yahoo.calls == []
    assert tushare.calls == []  # never silently retried through the A-share provider either
    recorded = gaps.list_gaps()
    assert len(recorded) == 1
    gap = recorded[0]
    # No route is configured at all for H/daily_bars in this deliberately
    # incomplete config (distinct from the explicit "not_configured"
    # sentinel) — `route_name_for` honestly returns nothing to label it
    # with, so the gap falls back to the generic label, but the error
    # type/status is still visible in the message, never hidden.
    assert gap["provider"] == "market_data_service"
    assert "ProviderNotConfiguredError" in gap["message"]


# -- 8: cache keys separate A/H/US ---------------------------------------


def test_cache_keys_separate_markets_and_never_collide(real_router, tmp_path: Path):
    router, tushare, yahoo = real_router
    cache = DataCache(tmp_path / "cache")
    service = MarketDataService(provider_router=router, cache=cache, gaps=None)

    # Same US-identity symbol string used across A/US (Tushare has no
    # mapping table so passes any code through unchanged; US defaults to
    # identity too), plus a real configured H symbol — must land in three
    # distinct cache locations and never let H/US Yahoo data overwrite (or
    # be served as) A股 Tushare data.
    a_df = service.get_daily_bars_cached("SAME_CODE", "A", "2026-06-01", "2026-06-30")
    h_df = service.get_daily_bars_cached("00700.HK", "H", "2026-06-01", "2026-06-30")
    us_df = service.get_daily_bars_cached("SAME_CODE", "US", "2026-06-01", "2026-06-30")

    assert cache.exists("A", "daily_bars", "SAME_CODE_2026-06-01_2026-06-30")
    assert cache.exists("H", "daily_bars", "00700.HK_2026-06-01_2026-06-30")
    assert cache.exists("US", "daily_bars", "SAME_CODE_2026-06-01_2026-06-30")
    assert cache.get_path("A", "daily_bars", "SAME_CODE_2026-06-01_2026-06-30") != cache.get_path(
        "US", "daily_bars", "SAME_CODE_2026-06-01_2026-06-30"
    )

    # Each was actually served by its own route (H/US via yahoo, tagged
    # distinctly in the fake bars), never by another market's route.
    assert list(a_df["tag"])[0] == "tushare"
    assert list(h_df["tag"])[0] == "yahoo_finance"
    assert list(us_df["tag"])[0] == "yahoo_finance"

    # Swap yahoo out for a failing provider and confirm the now-cached
    # A股 result is untouched and still served from cache — proves the
    # A-market cache entry was never at risk of being overwritten by a
    # H/US Yahoo response sharing the same symbol string.
    router._providers["yahoo_finance"] = _RecordingProvider("yahoo_finance", raise_error=ProviderError("down"))
    a_again = service.get_daily_bars_cached("SAME_CODE", "A", "2026-06-01", "2026-06-30")
    assert list(a_again["tag"])[0] == "tushare"


# -- 9: get_latest_close() works for H/US when route returns bars -------


def test_get_latest_close_works_for_h_and_us_via_provider_router(real_router):
    router, tushare, yahoo = real_router
    df = pd.DataFrame({"trade_date": ["20260630"], "close": [123.45]})
    yahoo._bars = df
    service = MarketDataService(provider_router=router, cache=None, gaps=None)

    h_price = service.get_latest_close("00700.HK", "H", as_of="2026-06-30")
    us_price = service.get_latest_close("CRCL", "US", as_of="2026-06-30")

    assert h_price == 123.45
    assert us_price == 123.45
    assert tushare.calls == []


def test_get_latest_close_returns_none_and_records_gap_when_yahoo_route_fails(real_router, tmp_path: Path):
    router, tushare, yahoo = real_router
    yahoo._raise_error = ProviderError("yfinance client/package is not available in this environment")
    gaps = DataGapRegistry(tmp_path / "data_gaps.jsonl")
    service = MarketDataService(provider_router=router, cache=None, gaps=gaps)

    price = service.get_latest_close("00700.HK", "H", as_of="2026-06-30")

    assert price is None
    recorded = gaps.list_gaps()
    assert len(recorded) == 1
    assert recorded[0]["market"] == "H"
    assert recorded[0]["provider"] == "yahoo_finance"


# -- 10: missing H/US route returns None/empty honestly (real config's --
#    stock_basic path, via the router directly, since MarketDataService
#    itself has no stock_basic method) -------------------------------


def test_stock_basic_not_configured_never_silently_produces_data(real_router):
    router, tushare, yahoo = real_router
    with pytest.raises(ProviderNotConfiguredError):
        router.get_stock_basic("H")
    assert yahoo.calls == []
    assert tushare.calls == []


# -- 12: no token read/printed -------------------------------------------


def test_market_service_and_router_never_touch_dotenv_or_tushare_token():
    for module in (market_service_module, provider_router_module):
        source = inspect.getsource(module)
        assert "import dotenv" not in source
        assert "load_dotenv(" not in source
        assert "os.environ" not in source
        assert "os.getenv(" not in source
        assert "TUSHARE_TOKEN" not in source
        # A docstring may *mention* TushareAdapter as an example of what a
        # caller could construct (P1B.1's convention) — that's fine; what
        # must never happen is this module importing or instantiating it
        # directly, which would mean it decided to talk to Tushare itself.
        assert "import TushareAdapter" not in source
        assert "from aegis.data.tushare_adapter" not in source
