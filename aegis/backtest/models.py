"""BacktestResult / MetricsReport — Phase 7 §5.4-5.5.

Date convention: plain "YYYY-MM-DD" strings throughout (never
`datetime.date`/`datetime.datetime`), consistent with every other model in
this codebase (see `aegis/backtest/frozen_context.py`'s docstring for the
same reasoning). No `aegis/models/backtest.py` was needed — these two
models are backtest-only (never consumed by the live pipeline, Dashboard,
or any Phase 0-6 model), so they live alongside the rest of
`aegis/backtest/` per the PHASE7 doc's own "models.py (allowed if no
existing backtest model file exists)" option.

Storage: `data/processed/backtests/<run_id>/backtest_results.jsonl` (one
`BacktestResult` per freeze_date, one JSON object per line) and
`metrics_report.json`/`metrics_report.md` — never `data/records/`.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class BacktestResult(BaseModel):
    run_id: str
    freeze_date: str
    session: str
    markets: list[str]
    market_snapshot_ids: list[str] = Field(default_factory=list)
    candidate_count: int = 0
    recommendation_ids: list[str] = Field(default_factory=list)
    recommendations: list[dict] = Field(default_factory=list)
    forward_returns: dict[str, dict] = Field(default_factory=dict)
    data_gaps: list[dict] = Field(default_factory=list)
    no_future_data_violations: int = 0
    created_at: str


class MetricsReport(BaseModel):
    run_id: str
    start_date: str
    end_date: str
    trading_days_run: int
    total_recommendations: int
    action_count: int = 0
    ready_count: int = 0
    watch_count: int = 0
    exit_count: int = 0
    action_success_rate_5d: Optional[float] = None
    action_success_rate_10d: Optional[float] = None
    action_success_rate_20d: Optional[float] = None
    action_success_rate_40d: Optional[float] = None
    average_return_by_horizon: dict[str, Optional[float]] = Field(default_factory=dict)
    max_drawdown_summary: dict = Field(default_factory=dict)
    market_breakdown: dict = Field(default_factory=dict)
    sector_breakdown: dict = Field(default_factory=dict)
    data_gap_count: int = 0
    no_future_data_violations: int = 0
    summary: str
    created_at: str
