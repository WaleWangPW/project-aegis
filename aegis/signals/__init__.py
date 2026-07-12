"""Signal Library — Phase 3 §5.

Deterministic, rule-based Signal computation. No LLM, no composite score.
Each `BaseSignal` subclass computes exactly one `Signal` from a
`SignalContext`; `compute_signals_for_candidate` runs the full default set.
"""

from .base import BaseSignal, SignalContext, compute_signals_for_candidate
from .fundamental import FundamentalSignal
from .relative_strength import RelativeStrengthSignal
from .risk import RiskSignal
from .sector import SectorSignal
from .trend import TrendSignal
from .volume import VolumeSignal

__all__ = [
    "BaseSignal",
    "SignalContext",
    "compute_signals_for_candidate",
    "TrendSignal",
    "VolumeSignal",
    "RelativeStrengthSignal",
    "SectorSignal",
    "FundamentalSignal",
    "RiskSignal",
]
