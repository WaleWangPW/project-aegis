"""Phase 1 tests for scripts/check_tushare.py (Phase 1 spec §5.5).

Tests call the testable `check_tushare_config()` function directly (as the
spec suggests) rather than shelling out to the CLI, and inject a fake
adapter so no real network call happens.
"""

from __future__ import annotations

from aegis.data.providers import ProviderError
from scripts.check_tushare import check_tushare_config


class _OkAdapter:
    def get_trading_calendar(self, market, start, end):
        return {"ok": True}


class _FailingAdapter:
    def get_trading_calendar(self, market, start, end):
        raise ProviderError("simulated upstream failure")


def test_missing_token_returns_non_zero_safe_output():
    result = check_tushare_config(env={})
    assert result.ok is False
    assert "missing" in result.message
    assert "TUSHARE_TOKEN" in result.message


def test_token_is_never_printed_in_message():
    result = check_tushare_config(env={"TUSHARE_TOKEN": "super-secret-value"}, adapter=_OkAdapter())
    assert "super-secret-value" not in result.message


def test_mocked_successful_adapter_returns_ok():
    result = check_tushare_config(env={"TUSHARE_TOKEN": "fake-token"}, adapter=_OkAdapter())
    assert result.ok is True
    assert "OK" in result.message


def test_mocked_failure_reports_failure_and_does_not_crash():
    result = check_tushare_config(env={"TUSHARE_TOKEN": "fake-token"}, adapter=_FailingAdapter())
    assert result.ok is False
    assert "FAILED" in result.message
