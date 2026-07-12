"""Phase 7 tests for TimeTravelEngine — PHASE7 doc §5.3/§9.3.

Fake provider only, isolated tmp_path repo root, no real Tushare/network —
same convention as every prior phase's tests.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from aegis.backtest.models import BacktestResult
from aegis.backtest.time_travel import TimeTravelEngine

HOLDINGS_YAML = """
holdings:
  - holding_id: hold_US_CRCL_20260601
    symbol: CRCL
    name: Circle Internet Group
    market: US
    shares: 100
    avg_cost: 100.0
    currency: USD
    entry_date: "2026-06-01"
    status: open
    notes: "test fixture"
"""

EMPTY_HOLDINGS_YAML = """
holdings: []
"""

UNIVERSE_YAML = """
default:
  lookback_days: 120
  max_candidates_per_market: 30
holdings:
  always_include: true
markets:
  A:
    max_candidates: 10
    min_liquidity_amount: 50000000
    exclude_suspended: true
    exclude_st: true
  H:
    max_candidates: 10
    min_liquidity_amount: 20000000
    exclude_suspended: true
    exclude_st: false
  US:
    max_candidates: 10
    min_dollar_volume: 5000000
    exclude_suspended: true
    exclude_st: false
"""

EXPERTS_YAML = """
experts:
  MarketRegimeAgent: {enabled: true}
  TrendAgent: {enabled: true}
  FundamentalAgent: {enabled: true, allow_missing_data: true}
  CapitalFlowAgent: {enabled: true}
  SectorAgent: {enabled: true}
  TimingAgent: {enabled: true}
  RiskAgent: {enabled: true, veto_enabled: true}
"""

DECISION_RULES_YAML = """
decision:
  action:
    min_support_count: 3
    min_confidence: 0.65
    require_invalidation_conditions: true
    require_risk_no_veto: true
    require_entry_price: true
  ready:
    min_support_count: 2
    min_confidence: 0.45
  downgrade:
    timing_oppose_max_status: Ready
    risk_veto_max_status: Watch
"""


def _uptrend_bars(n: int = 40, start_month_day: int = 1) -> pd.DataFrame:
    closes = [100.0 + i for i in range(n)]
    vols = [1000.0] * n
    trade_dates = [f"202606{str(start_month_day + i).zfill(2)}" for i in range(n)] if start_month_day + n - 1 <= 30 else None
    if trade_dates is None:
        # Spill into July for longer ranges used by run_range tests.
        trade_dates = []
        month, day = 6, start_month_day
        for _ in range(n):
            trade_dates.append(f"2026{str(month).zfill(2)}{str(day).zfill(2)}")
            day += 1
            if day > 30:
                day = 1
                month += 1
    return pd.DataFrame({"trade_date": trade_dates, "close": closes, "vol": vols})


class _FakeProvider:
    def __init__(self, bars: pd.DataFrame | None = None):
        self._bars = bars if bars is not None else _uptrend_bars()

    def get_daily_bars(self, symbol, market, start, end):
        return self._bars[(self._bars["trade_date"] >= start) & (self._bars["trade_date"] <= end)]

    def get_index_bars(self, index_code, market, start, end):
        return self._bars[(self._bars["trade_date"] >= start) & (self._bars["trade_date"] <= end)]

    def get_stock_basic(self, market):
        return pd.DataFrame(
            [{"symbol": "OTHR", "avg_dollar_volume": 10_000_000, "is_suspended": False, "is_st": False}]
        )

    def get_fundamentals(self, symbol, market, as_of):
        return pd.DataFrame([{"pe_ratio": 18.4, "risk_flags": []}])


def _write_repo_config(root: Path, holdings_yaml: str = HOLDINGS_YAML) -> None:
    config_dir = root / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "holdings.yaml").write_text(holdings_yaml, encoding="utf-8")
    (config_dir / "universe.yaml").write_text(UNIVERSE_YAML, encoding="utf-8")
    (config_dir / "experts.yaml").write_text(EXPERTS_YAML, encoding="utf-8")
    (config_dir / "decision_rules.yaml").write_text(DECISION_RULES_YAML, encoding="utf-8")


def _engine(tmp_path: Path, bars: pd.DataFrame | None = None, holdings_yaml: str = HOLDINGS_YAML) -> TimeTravelEngine:
    _write_repo_config(tmp_path, holdings_yaml=holdings_yaml)
    return TimeTravelEngine(
        base_provider=_FakeProvider(bars),
        data_dir=str(tmp_path / "data"),
        repo_root=str(tmp_path),
    )


def test_run_date_produces_a_backtest_result_with_forward_returns(tmp_path: Path):
    engine = _engine(tmp_path)
    result = engine.run_date(freeze_date="2026-06-30", session="close", markets=["US"])

    assert isinstance(result, BacktestResult)
    assert result.freeze_date == "2026-06-30"
    assert result.candidate_count >= 1
    assert result.recommendations
    assert result.forward_returns  # simulate_future_returns runs automatically inside run_date


def test_run_date_output_isolated_under_backtests_directory_not_records(tmp_path: Path):
    engine = _engine(tmp_path)
    run_id = "bt_test_isolation"
    engine.run_date(freeze_date="2026-06-30", session="close", markets=["US"], run_id=run_id)

    backtests_dir = tmp_path / "data" / "processed" / "backtests" / run_id
    assert backtests_dir.exists()
    assert (backtests_dir / "data_gaps.jsonl").exists()

    live_records_dir = tmp_path / "data" / "records"
    # The live pipeline's own record files must never be created by the
    # backtest engine.
    for filename in ("paper_trades.jsonl", "reviews.jsonl", "recommendations.jsonl", "decisions.jsonl"):
        assert not (live_records_dir / filename).exists()


def test_run_range_iterates_multiple_freeze_dates_under_one_run_id(tmp_path: Path):
    engine = _engine(tmp_path, bars=_uptrend_bars(n=45, start_month_day=1))
    results = engine.run_range(start_date="2026-06-28", end_date="2026-06-30", session="close", markets=["US"])

    assert len(results) == 3
    run_ids = {r.run_id for r in results}
    assert len(run_ids) == 1  # same run_id shared across the whole range
    freeze_dates = [r.freeze_date for r in results]
    assert freeze_dates == ["2026-06-28", "2026-06-29", "2026-06-30"]


def test_run_date_handles_empty_candidates_without_crashing(tmp_path: Path):
    engine = _engine(tmp_path, holdings_yaml=EMPTY_HOLDINGS_YAML)
    # Empty markets -> UniverseBuilder produces zero candidates, same
    # pattern already proven safe by scripts/run_pre_market.py's own tests.
    result = engine.run_date(freeze_date="2026-06-30", session="close", markets=[])

    assert result.candidate_count == 0
    assert result.recommendations == []
    assert result.forward_returns == {}


def test_simulate_future_returns_is_independently_callable(tmp_path: Path):
    engine = _engine(tmp_path)
    result = engine.run_date(freeze_date="2026-06-30", session="close", markets=["US"])

    # Calling it again (idempotent, independently testable per doc §5.3)
    # must not raise and must return a result with the same recommendations.
    re_simulated = engine.simulate_future_returns(result)
    assert re_simulated.recommendation_ids == result.recommendation_ids


def test_build_metrics_report_from_run_range_results(tmp_path: Path):
    engine = _engine(tmp_path, bars=_uptrend_bars(n=45, start_month_day=1))
    results = engine.run_range(start_date="2026-06-29", end_date="2026-06-30", session="close", markets=["US"])
    report = engine.build_metrics_report(results)

    assert report.trading_days_run == 2
    assert report.start_date == "2026-06-29"
    assert report.end_date == "2026-06-30"
    assert report.total_recommendations >= 1
