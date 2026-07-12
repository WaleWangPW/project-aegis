"""Phase 3 tests for missing-data behavior in the Signal Library —
PHASE3 doc §9.2. No signal may raise or fabricate a value; missing data
must degrade to evidence_strength="unknown".
"""

from __future__ import annotations

import pandas as pd

from aegis.models.candidate import Candidate
from aegis.models.common import DataQuality
from aegis.signals.base import SignalContext, compute_signals_for_candidate
from aegis.signals.relative_strength import RelativeStrengthSignal
from aegis.signals.risk import RiskSignal
from aegis.signals.trend import TrendSignal
from aegis.signals.volume import VolumeSignal


def _candidate() -> Candidate:
    return Candidate(
        candidate_id="cand_20260703_US_AAA",
        symbol="AAA",
        market="US",
        source="universe_builder",
        filter_reason=["liquidity_ok"],
        liquidity_ok=True,
        data_quality=DataQuality(status="complete"),
        created_at="2026-07-03T07:31:00-07:00",
    )


def _context(**overrides) -> SignalContext:
    base = dict(date="2026-07-03", session="pre_market", symbol="AAA", market="US", candidate=_candidate())
    base.update(overrides)
    return SignalContext(**base)


def test_missing_bars_returns_unknown_no_crash():
    context = _context(bars=None)

    for cls in (TrendSignal, VolumeSignal, RiskSignal):
        signal = cls().compute(context)
        assert signal.evidence_strength == "unknown"
        assert signal.value is None
        assert signal.interpretation.startswith("DATA_GAP")


def test_missing_volume_column_returns_data_gap_interpretation():
    closes = [100.0 + i for i in range(25)]
    bars_no_vol = pd.DataFrame(
        {"trade_date": [f"202606{str(i + 1).zfill(2)}" for i in range(25)], "close": closes}
    )
    context = _context(bars=bars_no_vol)

    signal = VolumeSignal().compute(context)

    assert signal.evidence_strength == "unknown"
    assert "DATA_GAP" in signal.interpretation


def test_missing_index_bars_makes_relative_strength_unknown():
    closes = [100.0 + i for i in range(10)]
    vols = [1000.0] * 10
    bars = pd.DataFrame({"trade_date": [f"202606{str(i + 1).zfill(2)}" for i in range(10)], "close": closes, "vol": vols})
    context = _context(bars=bars, index_bars=None)

    signal = RelativeStrengthSignal().compute(context)

    assert signal.evidence_strength == "unknown"
    assert signal.interpretation.startswith("DATA_GAP")


def test_all_signals_unknown_on_fully_empty_context():
    context = _context(bars=None, index_bars=None, fundamentals=None)
    # Candidate has no sector set, so SectorSignal is also unknown.

    signals = compute_signals_for_candidate(context)

    assert len(signals) == 6
    for signal in signals:
        assert signal.evidence_strength == "unknown"
        assert signal.value is None
