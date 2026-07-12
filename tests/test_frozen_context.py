"""Phase 7 tests for FrozenContext — PHASE7 doc §5.1/§9.1."""

from __future__ import annotations

import pandas as pd
import pytest

from aegis.backtest.frozen_context import FrozenContext
from aegis.backtest.historical_provider import HistoricalDataProvider


class _FakeProvider:
    def __init__(self, bars: pd.DataFrame):
        self._bars = bars

    def get_daily_bars(self, symbol, market, start, end):
        return self._bars[(self._bars["trade_date"] >= start) & (self._bars["trade_date"] <= end)]


def _bars() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "trade_date": ["20260101", "20260102", "20260103"],
            "close": [10.0, 11.0, 30.0],  # 2026-01-03 is a future spike
            "vol": [1000.0, 1000.0, 1000.0],
        }
    )


def test_frozen_context_defaults_to_decision_stage():
    ctx = FrozenContext(freeze_date="2026-01-02", session="close", markets=["US"])
    assert ctx.stage == "decision"
    assert ctx.is_decision_stage()
    assert not ctx.is_evaluation_stage()


def test_frozen_context_rejects_invalid_stage():
    with pytest.raises(ValueError):
        FrozenContext(freeze_date="2026-01-02", session="close", markets=["US"], stage="something_else")


def test_allowed_data_max_date_matches_freeze_date():
    ctx = FrozenContext(freeze_date="2026-01-02", session="close", markets=["US"])
    assert ctx.allowed_data_max_date == "2026-01-02"


def test_as_evaluation_stage_returns_new_instance_without_mutating_original():
    decision_ctx = FrozenContext(freeze_date="2026-01-02", session="close", markets=["US"])
    evaluation_ctx = decision_ctx.as_evaluation_stage()

    assert decision_ctx.stage == "decision"  # original untouched
    assert evaluation_ctx.stage == "evaluation"
    assert evaluation_ctx.freeze_date == decision_ctx.freeze_date


def test_data_date_equal_to_freeze_date_is_allowed(tmp_path):
    ctx = FrozenContext(freeze_date="2026-01-02", session="close", markets=["US"])
    provider = HistoricalDataProvider(_FakeProvider(_bars()), ctx)

    df = provider.get_daily_bars("CRCL", "US", "20260101", "20260102")

    assert not df.empty
    assert df["trade_date"].astype(str).max() == "20260102"
    assert provider.violations == 0


def test_data_date_after_freeze_date_is_blocked_in_decision_stage(tmp_path):
    ctx = FrozenContext(freeze_date="2026-01-02", session="close", markets=["US"])
    provider = HistoricalDataProvider(_FakeProvider(_bars()), ctx)

    df = provider.get_daily_bars("CRCL", "US", "20260101", "20260103")

    served_dates = set(df["trade_date"].astype(str))
    assert "20260103" not in served_dates
    assert provider.violations >= 1  # requested_end (20260103) was beyond freeze_date


def test_explicit_evaluation_stage_allows_future_reads(tmp_path):
    decision_ctx = FrozenContext(freeze_date="2026-01-02", session="close", markets=["US"])
    provider = HistoricalDataProvider(_FakeProvider(_bars()), decision_ctx)
    provider.enter_evaluation_stage()

    df = provider.get_future_bars_for_evaluation("CRCL", "US", "20260101", "20260103")

    served_dates = set(df["trade_date"].astype(str))
    assert "20260103" in served_dates  # future spike IS visible now, evaluation-only


def test_access_log_records_useful_violation_information(tmp_path):
    ctx = FrozenContext(freeze_date="2026-01-02", session="close", markets=["US"])
    provider = HistoricalDataProvider(_FakeProvider(_bars()), ctx)

    provider.get_daily_bars("CRCL", "US", "20260101", "20260103")

    assert len(provider.data_access_log) == 1
    entry = provider.data_access_log[0]
    assert entry["stage"] == "decision"
    assert entry["symbol"] == "CRCL"
    assert entry["data_type"] == "daily_bars"
    assert entry["requested_end"] == "20260103"
    assert entry["violation"] is True
