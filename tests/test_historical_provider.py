"""Phase 7 tests for HistoricalDataProvider — PHASE7 doc §5.2/§9.2."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from aegis.backtest.frozen_context import FrozenContext
from aegis.backtest.historical_provider import HistoricalDataProvider
from aegis.data.gaps import DataGapRegistry


class _FakeProvider:
    def __init__(self, bars: pd.DataFrame, fundamentals: pd.DataFrame | None = None):
        self._bars = bars
        self._fundamentals = fundamentals if fundamentals is not None else pd.DataFrame([{"pe_ratio": 18.4}])

    def get_daily_bars(self, symbol, market, start, end):
        return self._bars[(self._bars["trade_date"] >= start) & (self._bars["trade_date"] <= end)]

    def get_index_bars(self, index_code, market, start, end):
        return self._bars[(self._bars["trade_date"] >= start) & (self._bars["trade_date"] <= end)]

    def get_stock_basic(self, market):
        return pd.DataFrame([{"symbol": "CRCL"}])

    def get_fundamentals(self, symbol, market, as_of):
        return self._fundamentals


def _bars() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "trade_date": ["20260101", "20260102", "20260103"],
            "close": [10.0, 11.0, 30.0],
            "vol": [1000.0, 1000.0, 1000.0],
        }
    )


def _provider(tmp_path: Path, freeze_date="2026-01-02", **fake_kwargs) -> HistoricalDataProvider:
    ctx = FrozenContext(freeze_date=freeze_date, session="close", markets=["US"])
    gaps = DataGapRegistry(tmp_path / "data_gaps.jsonl")
    return HistoricalDataProvider(_FakeProvider(_bars(), **fake_kwargs), ctx, gaps=gaps)


def test_caps_decision_stage_daily_bars_to_freeze_date(tmp_path: Path):
    provider = _provider(tmp_path)
    df = provider.get_daily_bars("CRCL", "US", "20260101", "20260105")  # requested end beyond freeze_date
    assert df["trade_date"].astype(str).max() == "20260102"
    assert provider.violations == 1


def test_caps_decision_stage_index_bars_to_freeze_date(tmp_path: Path):
    provider = _provider(tmp_path)
    df = provider.get_index_bars("000300.SH", "A", "20260101", "20260105")
    assert df["trade_date"].astype(str).max() == "20260102"
    assert provider.violations == 1


def test_fundamentals_pass_through_via_as_of_capped_to_freeze_date(tmp_path: Path):
    provider = _provider(tmp_path)
    # as_of requested beyond freeze_date -> capped, and flagged as a violation.
    df = provider.get_fundamentals("CRCL", "US", "2026-01-05")
    assert not df.empty
    assert provider.violations == 1


def test_fundamentals_within_freeze_date_is_not_a_violation(tmp_path: Path):
    provider = _provider(tmp_path)
    df = provider.get_fundamentals("CRCL", "US", "2026-01-02")
    assert not df.empty
    assert provider.violations == 0


def test_missing_sector_classification_logs_data_gap(tmp_path: Path):
    gaps_path = tmp_path / "data_gaps.jsonl"
    ctx = FrozenContext(freeze_date="2026-01-02", session="close", markets=["US"])
    gaps = DataGapRegistry(gaps_path)
    # _FakeProvider above has no get_sector_classification method at all —
    # duck-typed AttributeError degrade path.
    provider = HistoricalDataProvider(_FakeProvider(_bars()), ctx, gaps=gaps)

    df = provider.get_sector_classification("US")

    assert df.empty
    logged = gaps.list_gaps()
    assert any(g["data_type"] == "sector_classification" for g in logged)


def test_stock_basic_logs_honest_data_gap_note(tmp_path: Path):
    gaps_path = tmp_path / "data_gaps.jsonl"
    ctx = FrozenContext(freeze_date="2026-01-02", session="close", markets=["US"])
    gaps = DataGapRegistry(gaps_path)
    provider = HistoricalDataProvider(_FakeProvider(_bars()), ctx, gaps=gaps)

    df = provider.get_stock_basic("US")

    assert not df.empty
    logged = gaps.list_gaps()
    assert any(g["data_type"] == "stock_basic" for g in logged)


def test_access_log_is_inspectable(tmp_path: Path):
    provider = _provider(tmp_path)
    provider.get_daily_bars("CRCL", "US", "20260101", "20260102")
    provider.get_index_bars("000300.SH", "A", "20260101", "20260102")

    assert len(provider.data_access_log) == 2
    assert {entry["data_type"] for entry in provider.data_access_log} == {"daily_bars", "index_bars"}
    assert all(entry["violation"] is False for entry in provider.data_access_log)
