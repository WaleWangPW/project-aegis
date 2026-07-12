"""Phase 2 tests for MarketSnapshotService — PHASE2 doc §8.2.

Uses a fake provider (no real Tushare/network) wired through the existing
Phase 1 MarketDataService, exactly like tests/test_market_data_service.py.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from aegis.data.cache import DataCache
from aegis.data.gaps import DataGapRegistry
from aegis.data.providers import ProviderError
from aegis.market.regime import MarketSnapshotService
from aegis.market.service import MarketDataService

PRIMARY = {"A": "000300.SH", "H": "HSI.HI", "US": "SPX"}


def _uptrend_bars(n: int = 25) -> pd.DataFrame:
    closes = [100.0 + i for i in range(n)]
    vols = [1000.0] * n
    trade_dates = [f"202606{str(i + 1).zfill(2)}" for i in range(n)]
    return pd.DataFrame({"trade_date": trade_dates, "close": closes, "vol": vols})


class _FakeProvider:
    """get_index_bars keyed by index_code; missing/empty by default."""

    def __init__(self, bars_by_index: dict[str, pd.DataFrame], raise_for: set[str] | None = None):
        self.bars_by_index = bars_by_index
        self.raise_for = raise_for or set()

    def get_index_bars(self, index_code, market, start, end):
        if index_code in self.raise_for:
            raise ProviderError(f"{market} not covered by current Tushare plan")
        return self.bars_by_index.get(index_code, pd.DataFrame())

    def get_daily_bars(self, symbol, market, start, end):
        return pd.DataFrame()


def _build_service(provider, gaps_path: Path) -> MarketSnapshotService:
    gaps = DataGapRegistry(gaps_path)
    mds = MarketDataService(provider=provider, cache=None, gaps=gaps)
    return MarketSnapshotService(market_data_service=mds, gaps=gaps, primary_index_by_market=PRIMARY)


def test_creates_a_h_us_snapshots_with_fake_index_data(tmp_path: Path):
    bars = _uptrend_bars()
    provider = _FakeProvider({"000300.SH": bars, "HSI.HI": bars, "SPX": bars})
    service = _build_service(provider, tmp_path / "data_gaps.jsonl")

    snapshots = service.build_snapshots(date="2026-07-03", session="pre_market", markets=["A", "H", "US"])

    by_market = {s.market: s for s in snapshots}
    assert set(by_market) == {"A", "H", "US", "GLOBAL"}
    for m in ("A", "H", "US"):
        assert by_market[m].trend_state == "uptrend"
        assert by_market[m].data_quality.status == "complete"


def test_records_data_gap_when_provider_returns_empty(tmp_path: Path):
    bars = _uptrend_bars()
    # H's index has no bars at all.
    provider = _FakeProvider({"000300.SH": bars, "SPX": bars})
    gaps_path = tmp_path / "data_gaps.jsonl"
    service = _build_service(provider, gaps_path)

    snapshots = service.build_snapshots(date="2026-07-03", session="pre_market", markets=["A", "H", "US"])

    by_market = {s.market: s for s in snapshots}
    assert by_market["H"].trend_state == "unknown"
    assert by_market["H"].summary.startswith("DATA_GAP")

    gaps = DataGapRegistry(gaps_path)
    recorded = gaps.list_gaps()
    assert any(g["market"] == "H" for g in recorded)


def test_global_snapshot_is_aggregate_of_available_markets(tmp_path: Path):
    bars = _uptrend_bars()
    provider = _FakeProvider({"000300.SH": bars, "HSI.HI": bars, "SPX": bars})
    service = _build_service(provider, tmp_path / "data_gaps.jsonl")

    snapshots = service.build_snapshots(date="2026-07-03", session="pre_market", markets=["A", "H", "US"])
    global_snap = snapshots[-1]

    assert global_snap.market == "GLOBAL"
    assert global_snap.trend_state == "uptrend"  # mode of three matching uptrends
    assert "A:" in global_snap.summary and "H:" in global_snap.summary and "US:" in global_snap.summary


def test_provider_exceptions_do_not_raise_to_caller(tmp_path: Path):
    bars = _uptrend_bars()
    provider = _FakeProvider({"000300.SH": bars, "SPX": bars}, raise_for={"HSI.HI"})
    service = _build_service(provider, tmp_path / "data_gaps.jsonl")

    snapshots = service.build_snapshots(date="2026-07-03", session="pre_market", markets=["A", "H", "US"])

    by_market = {s.market: s for s in snapshots}
    assert by_market["H"].trend_state == "unknown"
    assert by_market["H"].summary.startswith("DATA_GAP")
    assert by_market["A"].trend_state == "uptrend"
