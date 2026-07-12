"""TrendSignal — Phase 3 §5.2 (trend.py row): MA20 vs MA60, recent return,
basic trend direction. Missing/insufficient bars => unknown, never a guess.
"""

from __future__ import annotations

from aegis.signals._bars import moving_average, recent_return, sorted_closes
from aegis.signals.base import BaseSignal, SignalContext
from aegis.models.signal import Signal

MIN_BARS = 20
FULL_MA60_WINDOW = 60
RECENT_RETURN_LOOKBACK = 5


class TrendSignal(BaseSignal):
    name = "trend_ma_alignment"
    signal_type = "trend"

    def compute(self, context: SignalContext) -> Signal:
        df = sorted_closes(context.bars)
        if df is None or len(df) < MIN_BARS:
            return self._unknown(
                context,
                reason="Insufficient price bars to compute MA20/MA60 trend (need >= 20).",
                data_source="tushare",
                lookback_window="60d",
            )

        ma20 = moving_average(df, 20)
        ma60 = moving_average(df, FULL_MA60_WINDOW)
        ret = recent_return(df, RECENT_RETURN_LOOKBACK)
        latest_close = float(df["close"].iloc[-1])

        if latest_close > ma20 and ret is not None and ret > 0:
            direction = "uptrend"
        elif latest_close < ma20 and ret is not None and ret < 0:
            direction = "downtrend"
        else:
            direction = "sideways"

        has_full_ma60_window = len(df) >= FULL_MA60_WINDOW
        alignment_agrees = (
            (direction == "uptrend" and ma20 >= ma60)
            or (direction == "downtrend" and ma20 <= ma60)
            or direction == "sideways"
        )

        if has_full_ma60_window and alignment_agrees:
            evidence_strength = "strong"
        elif has_full_ma60_window or alignment_agrees:
            evidence_strength = "moderate"
        else:
            evidence_strength = "weak"

        value = {"ma20": ma20, "ma60": ma60, "recent_return": ret, "direction": direction}
        ret_pct = f"{ret:+.2%}" if ret is not None else "n/a"
        interpretation = (
            f"MA20={ma20:.4f}, MA60={ma60:.4f}, recent {RECENT_RETURN_LOOKBACK}d return={ret_pct} -> {direction}."
        )
        return self._signal(
            context,
            value=value,
            interpretation=interpretation,
            evidence_strength=evidence_strength,
            data_source="tushare",
            lookback_window="60d",
        )
