"""Phase 2 tests for MarketRegimeAnalyzer — Claude_Cowork_PHASE2_MARKET_UNIVERSE.md §8.1.

All data is synthetic/hand-built, no network, no real Tushare.
"""

from __future__ import annotations

import pandas as pd

from aegis.market.regime import MarketRegimeAnalyzer


def _bars(closes: list[float], vols: list[float]) -> pd.DataFrame:
    trade_dates = [f"202607{str(i + 1).zfill(2)}" for i in range(len(closes))]
    return pd.DataFrame({"trade_date": trade_dates, "close": closes, "vol": vols})


def test_uptrend_normal_liquidity_gives_low_or_medium_risk():
    closes = [100.0 + i for i in range(25)]  # monotonic increase
    vols = [1000.0] * 25  # latest == average -> "normal"
    df = _bars(closes, vols)

    analyzer = MarketRegimeAnalyzer()
    snap = analyzer.analyze_market(
        market="US", date="2026-07-03", session="pre_market", index_bars={"SPX": df}
    )

    assert snap.trend_state == "uptrend"
    assert snap.liquidity_state == "normal"
    assert snap.risk_level in ("low", "medium")
    assert snap.sentiment_state == "risk_on"


def test_downtrend_weak_liquidity_gives_high_risk():
    closes = [130.0 - i for i in range(25)]  # monotonic decrease
    vols = [1000.0] * 24 + [200.0]  # latest well below 0.8x average -> "weak"
    df = _bars(closes, vols)

    analyzer = MarketRegimeAnalyzer()
    snap = analyzer.analyze_market(
        market="A", date="2026-07-03", session="pre_market", index_bars={"000300.SH": df}
    )

    assert snap.trend_state == "downtrend"
    assert snap.liquidity_state == "weak"
    assert snap.risk_level == "high"
    assert snap.sentiment_state == "risk_off"


def test_missing_index_bars_gives_all_unknown_data_gap():
    analyzer = MarketRegimeAnalyzer()
    snap = analyzer.analyze_market(
        market="H", date="2026-07-03", session="pre_market", index_bars={}
    )

    assert snap.trend_state == "unknown"
    assert snap.liquidity_state == "unknown"
    assert snap.sentiment_state == "unknown"
    assert snap.risk_level == "unknown"
    assert snap.summary.startswith("DATA_GAP")
    assert snap.data_quality.status in ("partial", "unavailable", "missing")


def test_insufficient_bars_below_floor_is_unknown_no_crash():
    # Only 3 bars — below MIN_BARS_FOR_ANY_SIGNAL, must degrade gracefully.
    df = _bars([100.0, 101.0, 99.0], [1000.0, 1000.0, 1000.0])
    analyzer = MarketRegimeAnalyzer()

    snap = analyzer.analyze_market(
        market="US", date="2026-07-03", session="pre_market", index_bars={"SPX": df}
    )

    assert snap.trend_state == "unknown"
    assert snap.summary.startswith("DATA_GAP")


def test_insufficient_bars_partial_window_still_computes_but_marks_partial():
    # 10 bars: above the hard floor but below the full 20-day window —
    # spec allows "unknown or partial", we choose best-effort + partial.
    closes = [100.0 + i for i in range(10)]
    vols = [1000.0] * 10
    df = _bars(closes, vols)
    analyzer = MarketRegimeAnalyzer()

    snap = analyzer.analyze_market(
        market="US", date="2026-07-03", session="pre_market", index_bars={"SPX": df}
    )

    assert snap.trend_state != "unknown"
    assert snap.data_quality.status == "partial"
    assert "insufficient_bars_for_full_20d_window" in snap.data_quality.warnings
