"""P1B.2 tests for aegis/data/provider_router_live_validation.py.

Fake `yahoo_finance`-shaped adapter only — no real network/package call
from pytest, same convention as every other provider test in this repo
(tests/test_provider_router.py, tests/test_yahoo_finance_adapter.py).
"""

from __future__ import annotations

import inspect

import pandas as pd
import pytest

from aegis.data import provider_router_live_validation as live
from aegis.data.provider_router import ProviderRouter
from aegis.data.providers import ProviderError

_ROUTING_CONFIG = {
    "routing": {
        "daily_bars": {"H": "yahoo_finance", "US": "yahoo_finance"},
        "index_bars": {"H": "yahoo_finance", "US": "yahoo_finance"},
        "stock_basic": {"H": "not_configured", "US": "not_configured"},
    },
    "symbol_mapping": {
        "yahoo_finance": {
            "H": {"symbols": {"00700.HK": "0700.HK"}, "indexes": {"HSI.HI": "^HSI"}},
            "US": {"symbols": {"CRCL": "CRCL"}, "indexes": {"SPX": "^GSPC"}},
        }
    },
}


def _bars(n: int = 3) -> pd.DataFrame:
    return pd.DataFrame({"trade_date": [f"2026060{i}" for i in range(1, n + 1)], "close": [10.0] * n})


class _FakeYahooAdapter:
    """Mimics `YahooFinanceAdapter`'s duck-typed shape, with fully
    controllable behavior per test — never touches real yfinance/network."""

    def __init__(self, configured: bool = True, daily_result=None, index_result=None, raise_error: Exception | None = None):
        self._configured = configured
        self._daily_result = daily_result if daily_result is not None else _bars()
        self._index_result = index_result if index_result is not None else _bars()
        self._raise_error = raise_error
        self.calls: list[tuple] = []

    def is_configured(self) -> bool:
        return self._configured

    def get_daily_bars(self, symbol, market, start, end):
        self.calls.append(("daily_bars", symbol, market, start, end))
        if self._raise_error:
            raise self._raise_error
        return self._daily_result.copy()

    def get_index_bars(self, index_code, market, start, end):
        self.calls.append(("index_bars", index_code, market, start, end))
        if self._raise_error:
            raise self._raise_error
        return self._index_result.copy()

    def get_stock_basic(self, market):
        raise ProviderError("should never be called for H/US in this config")


def _router(adapter: _FakeYahooAdapter) -> ProviderRouter:
    return ProviderRouter(providers={"yahoo_finance": adapter}, routing_config=_ROUTING_CONFIG)


# -- 1/2/3/4: pass cases ----------------------------------------------


def test_h_daily_bars_pass_through_router_secondary_provider():
    adapter = _FakeYahooAdapter(daily_result=_bars(5))
    report = live.run_live_validation(markets=["H"], router=_router(adapter))
    check = next(c for c in report["checks"] if c["check_name"] == "h_daily_bars")
    assert check["status"] == "pass"
    assert check["rows_returned"] == 5
    assert check["sample_symbol"] == "00700.HK"
    assert check["mapped_symbol"] == "0700.HK"
    # The adapter must receive the *mapped* symbol, never Aegis's own
    # internal code — confirms ProviderRouter's mapping ran first.
    assert adapter.calls[0][0] == "daily_bars"
    assert adapter.calls[0][1] == "0700.HK"
    assert adapter.calls[0][2] == "H"


def test_h_index_bars_pass_through_router_secondary_provider():
    adapter = _FakeYahooAdapter(index_result=_bars(4))
    report = live.run_live_validation(markets=["H"], router=_router(adapter))
    check = next(c for c in report["checks"] if c["check_name"] == "h_index_bars")
    assert check["status"] == "pass"
    assert check["rows_returned"] == 4
    assert check["mapped_symbol"] == "^HSI"


def test_us_crcl_daily_bars_pass_through_router_secondary_provider():
    adapter = _FakeYahooAdapter(daily_result=_bars(21))
    report = live.run_live_validation(markets=["US"], router=_router(adapter))
    check = next(c for c in report["checks"] if c["check_name"] == "us_daily_bars")
    assert check["status"] == "pass"
    assert check["sample_symbol"] == "CRCL"
    assert check["mapped_symbol"] == "CRCL"
    assert check["rows_returned"] == 21


def test_us_index_bars_pass_through_router_secondary_provider():
    adapter = _FakeYahooAdapter(index_result=_bars(2))
    report = live.run_live_validation(markets=["US"], router=_router(adapter))
    check = next(c for c in report["checks"] if c["check_name"] == "us_index_bars")
    assert check["status"] == "pass"
    assert check["mapped_symbol"] == "^GSPC"


# -- 5: empty result becomes unknown, not pass -------------------------


def test_empty_result_becomes_unknown_not_pass():
    adapter = _FakeYahooAdapter(daily_result=pd.DataFrame())
    report = live.run_live_validation(markets=["US"], router=_router(adapter))
    check = next(c for c in report["checks"] if c["check_name"] == "us_daily_bars")
    assert check["status"] == "unknown"
    assert check["status"] != "pass"
    assert check["rows_returned"] == 0
    assert check["warning"]


# -- 6: missing dependency becomes dependency_missing, not crash -------


def test_missing_dependency_becomes_dependency_missing_not_crash():
    adapter = _FakeYahooAdapter(configured=False)
    report = live.run_live_validation(markets=["H", "US"], router=_router(adapter))
    bars_checks = [c for c in report["checks"] if c["data_type"] in ("daily_bars", "index_bars")]
    assert bars_checks  # sanity
    for check in bars_checks:
        assert check["status"] == "dependency_missing"
    assert adapter.calls == []  # never actually attempted a call
    assert report["network_attempted"] is False


# -- 7: network error becomes network_unavailable, not crash -----------


def test_network_error_becomes_network_unavailable_not_crash():
    adapter = _FakeYahooAdapter(raise_error=ProviderError("Connection timed out while reaching Yahoo Finance"))
    report = live.run_live_validation(markets=["US"], router=_router(adapter))
    check = next(c for c in report["checks"] if c["check_name"] == "us_daily_bars")
    assert check["status"] == "network_unavailable"
    assert check["error_type"] == "ProviderError"


def test_unrecognized_provider_error_becomes_fail_not_crash():
    adapter = _FakeYahooAdapter(raise_error=ProviderError("upstream returned HTTP 500"))
    report = live.run_live_validation(markets=["US"], router=_router(adapter))
    check = next(c for c in report["checks"] if c["check_name"] == "us_daily_bars")
    assert check["status"] == "fail"


# -- 8: H/US stock_basic remains not_configured/unsupported, never pass -


def test_stock_basic_remains_not_configured_never_false_passes():
    adapter = _FakeYahooAdapter()
    report = live.run_live_validation(markets=["H", "US"], router=_router(adapter))
    for market in ("h", "us"):
        check = next(c for c in report["checks"] if c["check_name"] == f"{market}_stock_basic")
        assert check["status"] in ("not_configured", "unsupported")
        assert check["status"] != "pass"


def test_stock_basic_unsupported_route_reports_unsupported():
    adapter = _FakeYahooAdapter()
    config = {
        "routing": {
            "daily_bars": {"H": "yahoo_finance"},
            "index_bars": {"H": "yahoo_finance"},
            "stock_basic": {"H": "unsupported"},
        },
        "symbol_mapping": _ROUTING_CONFIG["symbol_mapping"],
    }
    router = ProviderRouter(providers={"yahoo_finance": adapter}, routing_config=config)
    report = live.run_live_validation(markets=["H"], router=router)
    check = next(c for c in report["checks"] if c["check_name"] == "h_stock_basic")
    assert check["status"] == "unsupported"


# -- report shape / summary ---------------------------------------------


def test_report_has_required_top_level_shape():
    adapter = _FakeYahooAdapter()
    report = live.run_live_validation(markets=["H", "US"], router=_router(adapter))
    assert set(["run_id", "created_at", "network_attempted", "checks", "summary"]) <= set(report.keys())
    for status_key in (
        "pass_count", "fail_count", "unknown_count", "skipped_count",
        "not_configured_count", "dependency_missing_count",
        "network_unavailable_count", "unsupported_count",
    ):
        assert status_key in report["summary"]
    total = sum(report["summary"].values())
    assert total == len(report["checks"])
    for check in report["checks"]:
        assert check["status"] in live.ACCEPTED_STATUSES


def test_module_never_touches_dotenv_or_tushare_token():
    """P1B.2 requirement: must not read .env, must not call Tushare, must
    not require TUSHARE_TOKEN. Verified structurally against the actual
    module source (checking for real usage, not doc-comment mentions of
    the rule itself), not just against this test's own mocks."""
    source = inspect.getsource(live)
    assert "import dotenv" not in source
    assert "load_dotenv(" not in source
    assert "os.environ" not in source.replace("`os.environ`", "")
    assert "os.getenv(" not in source
    assert "TUSHARE_TOKEN" not in source.replace("`TUSHARE_TOKEN`", "")
    assert "TushareAdapter(" not in source
    assert "import TushareAdapter" not in source
    assert "tushare_adapter" not in source
