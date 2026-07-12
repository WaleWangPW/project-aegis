"""BaseSignal / SignalContext — Phase 3 §5.1.

Every signal takes the same shape of context and returns exactly one
`Signal`. Signals never raise, never fabricate a value, and always degrade
to `evidence_strength="unknown"` (plus a `DATA_GAP`-flavored interpretation)
when the data they need is missing — never a silent guess (Master Spec §4).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import pandas as pd

from aegis.models.candidate import Candidate
from aegis.models.common import DataQuality
from aegis.models.market_snapshot import MarketSnapshot
from aegis.models.signal import Signal


@dataclass
class SignalContext:
    date: str
    session: str
    symbol: str
    market: str
    bars: Optional[pd.DataFrame] = None
    index_bars: Optional[pd.DataFrame] = None
    sector_bars: Optional[pd.DataFrame] = None
    fundamentals: Optional[dict] = None
    candidate: Optional[Candidate] = None
    market_snapshot: Optional[MarketSnapshot] = None
    data_quality: Optional[DataQuality | dict] = None


class BaseSignal:
    name: str = "base_signal"
    signal_type: str = "trend"

    def compute(self, context: SignalContext) -> Signal:
        raise NotImplementedError

    def _signal_id(self, context: SignalContext) -> str:
        return f"sig_{context.date.replace('-', '')}_{context.market}_{context.symbol}_{self.name}"

    def _unknown(
        self,
        context: SignalContext,
        *,
        reason: str,
        data_source: str,
        lookback_window: Optional[str] = None,
    ) -> Signal:
        return Signal(
            signal_id=self._signal_id(context),
            signal_name=self.name,
            signal_type=self.signal_type,
            symbol=context.symbol,
            market=context.market,
            date=context.date,
            value=None,
            interpretation=f"DATA_GAP: {reason}",
            evidence_strength="unknown",
            data_source=data_source,
            lookback_window=lookback_window,
            valid_until=None,
        )

    def _signal(
        self,
        context: SignalContext,
        *,
        value,
        interpretation: str,
        evidence_strength: str,
        data_source: str,
        lookback_window: Optional[str] = None,
    ) -> Signal:
        return Signal(
            signal_id=self._signal_id(context),
            signal_name=self.name,
            signal_type=self.signal_type,
            symbol=context.symbol,
            market=context.market,
            date=context.date,
            value=value,
            interpretation=interpretation,
            evidence_strength=evidence_strength,
            data_source=data_source,
            lookback_window=lookback_window,
            valid_until=None,
        )


# Deterministic default order — used both by compute_signals_for_candidate
# and by anything that needs to iterate "the standard six".
def _default_signals() -> list[BaseSignal]:
    from aegis.signals.fundamental import FundamentalSignal
    from aegis.signals.relative_strength import RelativeStrengthSignal
    from aegis.signals.risk import RiskSignal
    from aegis.signals.sector import SectorSignal
    from aegis.signals.trend import TrendSignal
    from aegis.signals.volume import VolumeSignal

    return [
        TrendSignal(),
        VolumeSignal(),
        RelativeStrengthSignal(),
        SectorSignal(),
        FundamentalSignal(),
        RiskSignal(),
    ]


def compute_signals_for_candidate(
    context: SignalContext, signals: Optional[list[BaseSignal]] = None
) -> list[Signal]:
    """Runs the full default signal set (or a caller-supplied subset) against
    one candidate's context. Never raises — each signal is responsible for
    its own graceful degradation.
    """
    signals = signals if signals is not None else _default_signals()
    return [s.compute(context) for s in signals]
