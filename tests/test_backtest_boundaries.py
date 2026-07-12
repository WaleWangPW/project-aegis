"""Phase 7 boundary tests — PHASE7 doc §9.6/§14.

Guards the hard constraints that must hold regardless of how Phase 7 was
implemented: dashboard/index.html byte-identical, no broker/real-trading
module introduced, no composite/weighted scoring introduced, and the
backtest engine never writes to data/records/ (live records untouched).
"""

from __future__ import annotations

import importlib
import inspect
import pkgutil
from pathlib import Path

import pandas as pd

import aegis.backtest as backtest_pkg
from aegis.backtest.time_travel import TimeTravelEngine

REPO_ROOT = Path(__file__).resolve().parents[1]

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

UNIVERSE_YAML = """
default:
  lookback_days: 120
  max_candidates_per_market: 30
holdings:
  always_include: true
markets:
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


def _bars(n: int = 40) -> pd.DataFrame:
    closes = [100.0 + i for i in range(n)]
    vols = [1000.0] * n
    dates = [f"202606{str(i + 1).zfill(2)}" for i in range(min(n, 30))]
    while len(dates) < n:
        dates.append(f"202607{str(len(dates) - 29).zfill(2)}")
    return pd.DataFrame({"trade_date": dates, "close": closes, "vol": vols})


class _FakeProvider:
    def __init__(self):
        self._bars = _bars()

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


def _write_repo_config(root: Path) -> None:
    config_dir = root / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "holdings.yaml").write_text(HOLDINGS_YAML, encoding="utf-8")
    (config_dir / "universe.yaml").write_text(UNIVERSE_YAML, encoding="utf-8")
    (config_dir / "experts.yaml").write_text(EXPERTS_YAML, encoding="utf-8")
    (config_dir / "decision_rules.yaml").write_text(DECISION_RULES_YAML, encoding="utf-8")


def test_dashboard_index_html_unchanged():
    repo_html = REPO_ROOT / "dashboard" / "index.html"
    vault_html = REPO_ROOT.parent / "dashboard" / "index.html"
    assert repo_html.exists()
    assert repo_html.read_bytes() == vault_html.read_bytes()


def test_no_broker_or_real_trading_module_introduced():
    # Phase 7 must never introduce a real-broker/order-execution module —
    # only decision-support artifacts (BacktestResult/MetricsReport/etc).
    forbidden_module_name_fragments = ("broker", "order_execution", "live_trade", "real_trade")
    for _, module_name, _ in pkgutil.walk_packages(backtest_pkg.__path__, prefix="aegis.backtest."):
        lowered = module_name.lower()
        for fragment in forbidden_module_name_fragments:
            assert fragment not in lowered, f"forbidden module name fragment {fragment!r} found in {module_name}"


def test_no_composite_or_weighted_scoring_introduced():
    # ADR-002: no evidence-weighted/composite score anywhere in the
    # backtest package — DecisionEngine's evidence-voting + Risk veto is
    # reused unchanged, never replaced with a weighted score.
    forbidden_terms = ("composite_score", "weighted_score", "overall_score")
    for _, module_name, _ in pkgutil.walk_packages(backtest_pkg.__path__, prefix="aegis.backtest."):
        module = importlib.import_module(module_name)
        function_names = [name.lower() for name, obj in inspect.getmembers(module, inspect.isfunction)]
        for term in forbidden_terms:
            assert not any(term in name for name in function_names), f"{term!r} found in {module_name}"


def test_backtest_engine_never_writes_to_live_records_directory(tmp_path: Path):
    _write_repo_config(tmp_path)
    engine = TimeTravelEngine(
        base_provider=_FakeProvider(), data_dir=str(tmp_path / "data"), repo_root=str(tmp_path)
    )
    engine.run_range(start_date="2026-06-29", end_date="2026-06-30", session="close", markets=["US"])

    records_dir = tmp_path / "data" / "records"
    for filename in (
        "paper_trades.jsonl",
        "reviews.jsonl",
        "investment_memory.jsonl",
        "recommendations.jsonl",
        "decisions.jsonl",
        "data_gaps.jsonl",
    ):
        assert not (records_dir / filename).exists(), f"backtest must never create {filename} under data/records/"


def test_backtest_output_confined_to_processed_backtests_directory(tmp_path: Path):
    _write_repo_config(tmp_path)
    engine = TimeTravelEngine(
        base_provider=_FakeProvider(), data_dir=str(tmp_path / "data"), repo_root=str(tmp_path)
    )
    run_id = "bt_boundary_test"
    engine.run_date(freeze_date="2026-06-30", session="close", markets=["US"], run_id=run_id)

    output_dir = tmp_path / "data" / "processed" / "backtests" / run_id
    assert output_dir.exists()
    # Nothing should exist directly under data/ besides the processed/ tree.
    top_level_entries = {p.name for p in (tmp_path / "data").iterdir()}
    assert top_level_entries == {"processed"}
