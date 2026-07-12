"""Phase 2 tests for UniverseBuilder — PHASE2 doc §8.3.

All provider data is fake/mocked, no network, no real Tushare.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from aegis.data.gaps import DataGapRegistry
from aegis.data.providers import ProviderError
from aegis.models.holding import Holding
from aegis.universe.builder import UniverseBuilder


def _config() -> dict:
    return {
        "default": {"lookback_days": 120, "max_candidates_per_market": 30},
        "holdings": {"always_include": True},
        "markets": {
            "A": {"max_candidates": 50, "min_liquidity_amount": 50_000_000, "exclude_suspended": True, "exclude_st": True},
            "H": {"max_candidates": 30, "min_liquidity_amount": 20_000_000, "exclude_suspended": True, "exclude_st": False},
            "US": {"max_candidates": 30, "min_dollar_volume": 5_000_000, "exclude_suspended": True, "exclude_st": False},
        },
    }


def _crcl_holding() -> Holding:
    return Holding(
        holding_id="hold_US_CRCL_20260701",
        symbol="CRCL",
        name="Circle Internet Group",
        market="US",
        shares=254,
        avg_cost=109.157,
        currency="USD",
        entry_date="2026-07-01",
        status="open",
    )


class _StockBasicProvider:
    def __init__(self, df: pd.DataFrame, raise_error: bool = False):
        self.df = df
        self.raise_error = raise_error

    def get_stock_basic(self, market: str) -> pd.DataFrame:
        if self.raise_error:
            raise ProviderError(f"stock_basic not available for {market}")
        return self.df


def test_crcl_holding_always_included(tmp_path: Path):
    df = pd.DataFrame(
        [{"symbol": "OTHR", "name": "Other Co", "avg_dollar_volume": 10_000_000, "is_suspended": False, "is_st": False}]
    )
    provider = _StockBasicProvider(df)
    builder = UniverseBuilder(provider=provider, config=_config())

    candidates = builder.build_candidates(
        date="2026-07-03", session="pre_market", markets=["US"], holdings=[_crcl_holding()], market_snapshots=[]
    )

    crcl = [c for c in candidates if c.symbol == "CRCL"]
    assert len(crcl) == 1
    assert crcl[0].source == "holding"
    assert "current_real_holding" in crcl[0].filter_reason
    assert "must_analyze_holdings" in crcl[0].filter_reason


def test_low_liquidity_non_holding_is_filtered_out(tmp_path: Path):
    df = pd.DataFrame(
        [
            {"symbol": "AAA", "avg_dollar_volume": 10_000_000, "is_suspended": False, "is_st": False},
            {"symbol": "BBB", "avg_dollar_volume": 100_000, "is_suspended": False, "is_st": False},
        ]
    )
    provider = _StockBasicProvider(df)
    builder = UniverseBuilder(provider=provider, config=_config())

    candidates = builder.build_candidates(
        date="2026-07-03", session="pre_market", markets=["US"], holdings=[], market_snapshots=[]
    )

    symbols = {c.symbol for c in candidates}
    assert "AAA" in symbols
    assert "BBB" not in symbols


def test_candidate_count_respects_market_max(tmp_path: Path):
    rows = [
        {"symbol": f"SYM{i}", "avg_dollar_volume": 10_000_000, "is_suspended": False, "is_st": False}
        for i in range(5)
    ]
    df = pd.DataFrame(rows)
    provider = _StockBasicProvider(df)
    cfg = _config()
    cfg["markets"]["US"]["max_candidates"] = 2
    builder = UniverseBuilder(provider=provider, config=cfg)

    candidates = builder.build_candidates(
        date="2026-07-03", session="pre_market", markets=["US"], holdings=[], market_snapshots=[]
    )

    assert len(candidates) == 2


def test_missing_market_data_produces_data_gap_and_no_fake_candidates(tmp_path: Path):
    provider = _StockBasicProvider(pd.DataFrame(), raise_error=True)
    gaps = DataGapRegistry(tmp_path / "data_gaps.jsonl")
    builder = UniverseBuilder(provider=provider, config=_config(), gaps=gaps)

    candidates = builder.build_candidates(
        date="2026-07-03", session="pre_market", markets=["US"], holdings=[_crcl_holding()], market_snapshots=[]
    )

    assert len(candidates) == 1
    assert candidates[0].symbol == "CRCL"
    assert candidates[0].data_quality.status == "partial"
    assert gaps.list_gaps()  # a gap was recorded, nothing was fabricated


def test_a_and_h_markets_use_separate_liquidity_thresholds(tmp_path: Path):
    # 30M CNY turnover: passes H's 20M threshold, fails A's 50M threshold.
    row = pd.DataFrame([{"symbol": "MID", "avg_turnover_amount": 30_000_000, "is_suspended": False, "is_st": False}])
    cfg = _config()

    a_builder = UniverseBuilder(provider=_StockBasicProvider(row), config=cfg)
    a_candidates = a_builder.build_candidates(
        date="2026-07-03", session="pre_market", markets=["A"], holdings=[], market_snapshots=[]
    )
    assert "MID" not in {c.symbol for c in a_candidates}

    h_builder = UniverseBuilder(provider=_StockBasicProvider(row), config=cfg)
    h_candidates = h_builder.build_candidates(
        date="2026-07-03", session="pre_market", markets=["H"], holdings=[], market_snapshots=[]
    )
    assert "MID" in {c.symbol for c in h_candidates}


def test_candidate_has_non_empty_filter_reason(tmp_path: Path):
    df = pd.DataFrame([{"symbol": "AAA", "avg_dollar_volume": 10_000_000, "is_suspended": False, "is_st": False}])
    provider = _StockBasicProvider(df)
    builder = UniverseBuilder(provider=provider, config=_config())

    candidates = builder.build_candidates(
        date="2026-07-03", session="pre_market", markets=["US"], holdings=[_crcl_holding()], market_snapshots=[]
    )

    for c in candidates:
        assert len(c.filter_reason) > 0
