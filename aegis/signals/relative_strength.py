"""RelativeStrengthSignal — Phase 3 §5.2: candidate recent return vs index
recent return. Missing index => unknown.
"""

from __future__ import annotations

from aegis.signals._bars import recent_return, sorted_closes
from aegis.signals.base import BaseSignal, SignalContext
from aegis.models.signal import Signal

RECENT_RETURN_LOOKBACK = 5


class RelativeStrengthSignal(BaseSignal):
    name = "relative_strength_vs_index"
    signal_type = "relative_strength"

    def compute(self, context: SignalContext) -> Signal:
        sym_df = sorted_closes(context.bars)
        if sym_df is None or len(sym_df) < 2:
            return self._unknown(
                context,
                reason="Insufficient candidate bars to compute relative strength.",
                data_source="tushare",
                lookback_window="5d",
            )

        idx_df = sorted_closes(context.index_bars)
        if idx_df is None or len(idx_df) < 2:
            return self._unknown(
                context,
                reason="Missing index bars for relative-strength comparison.",
                data_source="tushare",
                lookback_window="5d",
            )

        sym_ret = recent_return(sym_df, RECENT_RETURN_LOOKBACK)
        idx_ret = recent_return(idx_df, RECENT_RETURN_LOOKBACK)
        if sym_ret is None or idx_ret is None:
            return self._unknown(
                context,
                reason="Could not compute a recent return for the candidate or the index.",
                data_source="tushare",
                lookback_window="5d",
            )

        relative_strength = sym_ret - idx_ret
        if relative_strength > 0:
            state = "outperforming"
        elif relative_strength < 0:
            state = "underperforming"
        else:
            state = "in_line"

        evidence_strength = "moderate" if len(sym_df) >= 20 and len(idx_df) >= 20 else "weak"
        value = {
            "symbol_return": sym_ret,
            "index_return": idx_ret,
            "relative_strength": relative_strength,
            "state": state,
        }
        interpretation = (
            f"Candidate {RECENT_RETURN_LOOKBACK}d return={sym_ret:+.2%} vs index {idx_ret:+.2%} "
            f"-> {state} (relative={relative_strength:+.2%})."
        )
        return self._signal(
            context,
            value=value,
            interpretation=interpretation,
            evidence_strength=evidence_strength,
            data_source="tushare",
            lookback_window="5d",
        )
