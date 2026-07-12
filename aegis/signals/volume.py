"""VolumeSignal — Phase 3 §5.2 (volume.py row): latest volume vs 20d
average, volume expansion. Missing volume => unknown.
"""

from __future__ import annotations

import pandas as pd

from aegis.signals._bars import sorted_closes
from aegis.signals.base import BaseSignal, SignalContext
from aegis.models.signal import Signal

MIN_BARS = 5
FULL_WINDOW = 20


class VolumeSignal(BaseSignal):
    name = "volume_expansion"
    signal_type = "volume"

    def compute(self, context: SignalContext) -> Signal:
        df = sorted_closes(context.bars)
        if df is None or len(df) < MIN_BARS or "vol" not in df.columns:
            return self._unknown(
                context,
                reason="Insufficient bars or missing volume column.",
                data_source="tushare",
                lookback_window="20d",
            )

        window = min(len(df), FULL_WINDOW)
        recent = df.tail(window)
        vol_recent = recent["vol"].dropna()
        if vol_recent.empty:
            return self._unknown(
                context,
                reason="Volume column present but all recent values are missing.",
                data_source="tushare",
                lookback_window=f"{window}d",
            )

        latest_raw = recent["vol"].iloc[-1]
        if pd.isna(latest_raw):
            return self._unknown(
                context,
                reason="Latest volume value is missing.",
                data_source="tushare",
                lookback_window=f"{window}d",
            )

        latest_vol = float(latest_raw)
        avg_vol = float(vol_recent.mean())
        if avg_vol == 0:
            return self._unknown(
                context,
                reason="Average volume over the window is zero, cannot compare.",
                data_source="tushare",
                lookback_window=f"{window}d",
            )

        if latest_vol > 1.2 * avg_vol:
            state = "expansion"
        elif latest_vol < 0.8 * avg_vol:
            state = "contraction"
        else:
            state = "normal"

        full_window = len(df) >= FULL_WINDOW
        if state in ("expansion", "contraction") and full_window:
            evidence_strength = "strong"
        elif state in ("expansion", "contraction"):
            evidence_strength = "moderate"
        else:
            evidence_strength = "weak"

        value = {"latest_vol": latest_vol, "avg_vol": avg_vol, "state": state}
        interpretation = f"Latest volume {latest_vol:.0f} vs {window}d average {avg_vol:.0f} -> {state}."
        return self._signal(
            context,
            value=value,
            interpretation=interpretation,
            evidence_strength=evidence_strength,
            data_source="tushare",
            lookback_window=f"{window}d",
        )
