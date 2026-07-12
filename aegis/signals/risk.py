"""RiskSignal — Phase 3 §5.2: volatility proxy, max drawdown proxy, invalid
bars, liquidity risk. Can create strong risk evidence when data shows it —
but missing/insufficient bars still degrade to unknown like every other
signal, never a fabricated risk read.
"""

from __future__ import annotations

from aegis.signals._bars import sorted_closes
from aegis.signals.base import BaseSignal, SignalContext
from aegis.models.signal import Signal

MIN_BARS = 5
FULL_WINDOW = 20
VOLATILITY_THRESHOLD = 0.03  # daily return std dev
DRAWDOWN_THRESHOLD = -0.20  # -20% peak-to-trough over the window


class RiskSignal(BaseSignal):
    name = "risk_volatility_drawdown"
    signal_type = "risk"

    def compute(self, context: SignalContext) -> Signal:
        df = sorted_closes(context.bars)
        if df is None or len(df) < MIN_BARS:
            return self._unknown(
                context,
                reason="Insufficient price bars to assess volatility/drawdown risk.",
                data_source="tushare",
                lookback_window="20d",
            )

        window = min(len(df), FULL_WINDOW)
        recent = df.tail(window).reset_index(drop=True)
        returns = recent["close"].pct_change().dropna()
        volatility = float(returns.std()) if not returns.empty else None
        running_max = recent["close"].cummax()
        drawdowns = (recent["close"] - running_max) / running_max
        max_drawdown = float(drawdowns.min()) if not drawdowns.empty else None

        flags: list[str] = []
        if volatility is not None and volatility > VOLATILITY_THRESHOLD:
            flags.append("high_volatility")
        if max_drawdown is not None and max_drawdown < DRAWDOWN_THRESHOLD:
            flags.append("severe_drawdown")

        candidate = context.candidate
        if candidate is not None and not candidate.liquidity_ok:
            flags.append("liquidity_risk")

        if len(flags) >= 2:
            evidence_strength = "strong"
        elif len(flags) == 1:
            evidence_strength = "moderate"
        else:
            evidence_strength = "weak"

        value = {"volatility": volatility, "max_drawdown": max_drawdown, "flags": flags}
        vol_pct = f"{volatility:.2%}" if volatility is not None else "n/a"
        dd_pct = f"{max_drawdown:.2%}" if max_drawdown is not None else "n/a"
        if flags:
            interpretation = f"Risk flags: {', '.join(flags)} (volatility={vol_pct}, max_drawdown={dd_pct})."
        else:
            interpretation = f"No elevated risk flags (volatility={vol_pct}, max_drawdown={dd_pct})."

        return self._signal(
            context,
            value=value,
            interpretation=interpretation,
            evidence_strength=evidence_strength,
            data_source="tushare",
            lookback_window=f"{window}d",
        )
