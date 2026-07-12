"""Phase 1 tests for DataGapRegistry (Phase 1 spec §5.3)."""

from __future__ import annotations

from pathlib import Path

import pytest

from aegis.data.gaps import DataGapRegistry


def test_record_gap_appends_jsonl_and_has_gap_id(tmp_path: Path):
    registry = DataGapRegistry(tmp_path / "records" / "data_gaps.jsonl")
    gap = registry.record_gap(
        date="2026-07-03",
        market="US",
        symbol="CRCL",
        provider="tushare",
        data_type="daily_bars",
        severity="warning",
        message="US daily bars unavailable from configured Tushare environment.",
        consumer_impact=["TrendAgent", "TimingAgent", "RiskAgent"],
    )
    assert gap["gap_id"] == "gap_20260703_US_CRCL_daily_bars"
    assert "created_at" in gap


def test_severity_preserved_and_list_gaps_reads_back(tmp_path: Path):
    registry = DataGapRegistry(tmp_path / "records" / "data_gaps.jsonl")
    registry.record_gap(
        date="2026-07-03", market="H", symbol=None, provider="tushare",
        data_type="stock_basic", severity="error", message="H market stock_basic call failed.",
    )
    gaps = registry.list_gaps()
    assert len(gaps) == 1
    assert gaps[0]["severity"] == "error"
    assert gaps[0]["market"] == "H"


def test_invalid_severity_rejected(tmp_path: Path):
    registry = DataGapRegistry(tmp_path / "records" / "data_gaps.jsonl")
    with pytest.raises(ValueError):
        registry.record_gap(
            date="2026-07-03", market="A", symbol=None, provider="tushare",
            data_type="daily_bars", severity="catastrophic", message="bad severity",
        )
