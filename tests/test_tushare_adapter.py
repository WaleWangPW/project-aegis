"""Phase 1 tests for TushareAdapter (Phase 1 spec §5.1).

No real network calls. The underlying `pro` client is replaced with a fake
stub object so we control exactly what tushare "returns" without touching
the internet or a real token.
"""

from __future__ import annotations

import pandas as pd
import pytest

from aegis.data.providers import ProviderError
from aegis.data.tushare_adapter import TushareAdapter


class _FakePro:
    """Stands in for `tushare.pro_api(token)` — exposes the same method
    names TushareAdapter calls, fully offline."""

    def __init__(self, daily_df=None, raise_on_daily: Exception | None = None):
        self._daily_df = daily_df
        self._raise_on_daily = raise_on_daily

    def daily(self, ts_code, start_date, end_date):
        if self._raise_on_daily is not None:
            raise self._raise_on_daily
        return self._daily_df

    def index_daily(self, ts_code, start_date, end_date):
        return pd.DataFrame()

    def stock_basic(self, exchange, list_status):
        return pd.DataFrame()

    def index_classify(self, level, src):
        return pd.DataFrame()

    def fina_indicator(self, ts_code, period):
        return pd.DataFrame()

    def trade_cal(self, exchange, start_date, end_date):
        return pd.DataFrame({"cal_date": ["20260101", "20260102"], "is_open": [0, 1]})


def test_missing_token_is_not_configured():
    adapter = TushareAdapter(token=None)
    assert adapter.is_configured() is False


def test_token_present_is_configured_and_never_printed(capsys):
    adapter = TushareAdapter(token="super-secret-token-value")
    assert adapter.is_configured() is True
    captured = capsys.readouterr()
    assert "super-secret-token-value" not in captured.out
    assert "super-secret-token-value" not in captured.err
    assert "super-secret-token-value" not in repr(adapter)


def test_missing_token_raises_provider_error_on_data_call():
    adapter = TushareAdapter(token=None)
    with pytest.raises(ProviderError):
        adapter.get_daily_bars("CRCL", "US", "20260601", "20260701")


def test_adapter_returns_normalized_empty_dataframe_on_empty_result():
    adapter = TushareAdapter(token="fake-token")
    adapter._pro = _FakePro(daily_df=None)  # simulate tushare returning None
    df = adapter.get_daily_bars("CRCL", "US", "20260601", "20260701")
    assert isinstance(df, pd.DataFrame)
    assert df.empty


def test_adapter_handles_provider_exception_cleanly():
    adapter = TushareAdapter(token="fake-token")
    adapter._pro = _FakePro(raise_on_daily=RuntimeError("upstream 500"))
    with pytest.raises(ProviderError):
        adapter.get_daily_bars("CRCL", "US", "20260601", "20260701")


def test_adapter_returns_dataframe_when_pro_provides_data():
    adapter = TushareAdapter(token="fake-token")
    adapter._pro = _FakePro(daily_df=pd.DataFrame({"trade_date": ["20260701"], "close": [110.0]}))
    df = adapter.get_daily_bars("CRCL", "US", "20260601", "20260701")
    assert not df.empty
    assert df.iloc[0]["close"] == 110.0


def test_trading_calendar_via_fake_pro():
    adapter = TushareAdapter(token="fake-token")
    adapter._pro = _FakePro()
    df = adapter.get_trading_calendar(market="A", start="20260101", end="20260102")
    assert list(df["cal_date"]) == ["20260101", "20260102"]
