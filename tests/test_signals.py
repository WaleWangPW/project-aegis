"""Phase 3 tests for the Signal Library — PHASE3 doc §9.1.

All bars/fundamentals are synthetic, no network, no real Tushare.
"""

from __future__ import annotations

import pandas as pd

from aegis.models.candidate import Candidate
from aegis.models.common import DataQuality
from aegis.signals.base import SignalContext
from aegis.signals.relative_strength import RelativeStrengthSignal
from aegis.signals.risk import RiskSignal
from aegis.signals.trend import TrendSignal
from aegis.signals.volume import VolumeSignal


def _bars(closes: list[float], vols: list[float]) -> pd.DataFrame:
    trade_dates = [f"202606{str(i + 1).zfill(2)}" for i in range(len(closes))]
    return pd.DataFrame({"trade_date": trade_dates, "close": closes, "vol": vols})


def _candidate(symbol="AAA", market="US", liquidity_ok=True) -> Candidate:
    return Candidate(
        candidate_id=f"cand_20260703_{market}_{symbol}",
        symbol=symbol,
        market=market,
        source="universe_builder",
        filter_reason=["liquidity_ok"],
        liquidity_ok=liquidity_ok,
        data_quality=DataQuality(status="complete"),
        created_at="2026-07-03T07:31:00-07:00",
    )


def _context(**overrides) -> SignalContext:
    base = dict(date="2026-07-03", session="pre_market", symbol="AAA", market="US")
    base.update(overrides)
    return SignalContext(**base)


def test_trend_signal_returns_uptrend_on_rising_valid_bars():
    closes = [100.0 + i for i in range(25)]
    vols = [1000.0] * 25
    context = _context(bars=_bars(closes, vols), candidate=_candidate())

    signal = TrendSignal().compute(context)

    assert signal.evidence_strength != "unknown"
    assert signal.value["direction"] == "uptrend"
    assert "uptrend" in signal.interpretation


def test_volume_signal_detects_expansion():
    closes = [100.0 + i for i in range(25)]
    vols = [1000.0] * 24 + [2000.0]  # latest well above 1.2x average
    context = _context(bars=_bars(closes, vols), candidate=_candidate())

    signal = VolumeSignal().compute(context)

    assert signal.evidence_strength != "unknown"
    assert signal.value["state"] == "expansion"


def test_relative_strength_compares_candidate_vs_index():
    sym_closes = [100.0 + 2 * i for i in range(10)]  # strong rally
    idx_closes = [100.0 + 0.5 * i for i in range(10)]  # flat-ish index
    vols = [1000.0] * 10
    context = _context(bars=_bars(sym_closes, vols), index_bars=_bars(idx_closes, vols), candidate=_candidate())

    signal = RelativeStrengthSignal().compute(context)

    assert signal.evidence_strength != "unknown"
    assert signal.value["state"] == "outperforming"
    assert signal.value["symbol_return"] > signal.value["index_return"]


def test_risk_signal_detects_drawdown_and_volatility():
    # Sharp, volatile drop -> both volatility and drawdown flags.
    closes = [100.0, 105.0, 95.0, 110.0, 90.0, 70.0, 65.0, 60.0, 58.0, 55.0]
    vols = [1000.0] * len(closes)
    context = _context(bars=_bars(closes, vols), candidate=_candidate())

    signal = RiskSignal().compute(context)

    assert signal.evidence_strength in ("moderate", "strong")
    assert signal.value["flags"]  # at least one risk flag detected


def test_signal_ids_are_deterministic():
    closes = [100.0 + i for i in range(25)]
    vols = [1000.0] * 25
    context = _context(bars=_bars(closes, vols), candidate=_candidate())

    sig_a = TrendSignal().compute(context)
    sig_b = TrendSignal().compute(context)

    assert sig_a.signal_id == sig_b.signal_id
    assert sig_a.signal_id == "sig_20260703_US_AAA_trend_ma_alignment"
