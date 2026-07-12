"""Time Travel Backtest — Phase 7.

Historical replay of the exact same deterministic Phase 2-4 pipeline
(MarketSnapshot -> Universe -> Signals -> ExpertCommittee -> DecisionEngine
-> RecommendationRecord), with a strict point-in-time data boundary so no
future data can leak into a decision made "as of" some past `freeze_date`.

Never places a real order, never talks to a broker, never creates live
PaperTrade/Review/Memory records — all backtest output is isolated under
`data/processed/backtests/<run_id>/`, never `data/records/`.
"""

from __future__ import annotations

from aegis.backtest.frozen_context import FrozenContext, FutureDataAccessError
from aegis.backtest.historical_provider import HistoricalDataProvider
from aegis.backtest.models import BacktestResult, MetricsReport
from aegis.backtest.time_travel import TimeTravelEngine

__all__ = [
    "FrozenContext",
    "FutureDataAccessError",
    "HistoricalDataProvider",
    "BacktestResult",
    "MetricsReport",
    "TimeTravelEngine",
]
