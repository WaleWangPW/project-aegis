"""Phase 5 boundary tests for scripts/run_pre_market.py — PHASE5 doc §10.4.

Confirms the pre-market pipeline now builds the Dashboard JSON after
recommendations, and confirms it still does NOT create PaperTrade, Review,
or Investment Memory artifacts, and never touches dashboard/index.html.

Fake provider only, isolated tmp_path repo root, no real Tushare/network —
same pattern as tests/test_run_pre_market_phase4.py.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

import scripts.run_pre_market as rpm

HOLDINGS_YAML = """
holdings:
  - holding_id: hold_US_CRCL_20260701
    symbol: CRCL
    name: Circle Internet Group
    market: US
    shares: 254
    avg_cost: 109.157
    currency: USD
    entry_date: "2026-07-01"
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


def _uptrend_bars(n: int = 25) -> pd.DataFrame:
    closes = [100.0 + i for i in range(n)]
    vols = [1000.0] * n
    trade_dates = [f"202606{str(i + 1).zfill(2)}" for i in range(n)]
    return pd.DataFrame({"trade_date": trade_dates, "close": closes, "vol": vols})


class _FakeProvider:
    def __init__(self, stock_basic: pd.DataFrame | None = None):
        self._bars = _uptrend_bars()
        self._stock_basic = (
            stock_basic
            if stock_basic is not None
            else pd.DataFrame([{"symbol": "OTHR", "avg_dollar_volume": 10_000_000, "is_suspended": False, "is_st": False}])
        )

    def get_index_bars(self, index_code, market, start, end):
        return self._bars

    def get_daily_bars(self, symbol, market, start, end):
        return self._bars

    def get_stock_basic(self, market):
        return self._stock_basic

    def get_fundamentals(self, symbol, market, as_of):
        return pd.DataFrame([{"pe_ratio": 18.4, "risk_flags": []}])


def _write_repo_config(root: Path) -> None:
    config_dir = root / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "holdings.yaml").write_text(HOLDINGS_YAML, encoding="utf-8")
    (config_dir / "universe.yaml").write_text(UNIVERSE_YAML, encoding="utf-8")
    (config_dir / "experts.yaml").write_text(EXPERTS_YAML, encoding="utf-8")
    (config_dir / "decision_rules.yaml").write_text(DECISION_RULES_YAML, encoding="utf-8")


def test_pipeline_generates_dashboard_json_after_recommendations(tmp_path: Path):
    _write_repo_config(tmp_path)
    result = rpm.run_pre_market(
        date="2026-07-03", markets=["A", "H", "US"], repo_root=tmp_path, provider=_FakeProvider()
    )

    assert result.dashboard_error is None
    assert result.dashboard_path is not None
    assert result.dashboard_path.exists()
    payload = json.loads(result.dashboard_path.read_text(encoding="utf-8"))
    assert payload["date"] == "2026-07-03"
    # Dashboard must be built from the recommendations already computed.
    assert len(result.recommendations) > 0


def test_script_does_not_create_review_or_memory_records(tmp_path: Path):
    # NOTE: originally also asserted `paper_trades.jsonl` did not exist
    # (true when this file was written, in Phase 5). Phase 6 legitimately
    # added real PaperTrade creation to this same script for Action
    # recommendations (see test_paper_trade_service.py /
    # test_run_close.py for the dedicated Phase 6 coverage) — this fixture
    # produces at least one Action-status recommendation, so
    # `paper_trades.jsonl` is expected to exist now. Review/Memory
    # generation remains `scripts/run_close.py`'s job, so those stay
    # forbidden here.
    _write_repo_config(tmp_path)
    rpm.run_pre_market(date="2026-07-03", markets=["A", "H", "US"], repo_root=tmp_path, provider=_FakeProvider())

    records_dir = tmp_path / "data" / "records"
    assert not (records_dir / "reviews.jsonl").exists()
    assert not (records_dir / "investment_memory.jsonl").exists()
    assert not (records_dir / "memory.jsonl").exists()

    dashboard_dir = tmp_path / "data" / "dashboard"
    assert not (dashboard_dir / "paper_trades.json").exists()
    assert not (dashboard_dir / "reviews.json").exists()


def test_script_does_not_modify_dashboard_index_html(tmp_path: Path):
    # There is no dashboard/index.html under the isolated tmp_path repo root
    # at all in this test (Phase 5 backend never creates or writes to it),
    # so the pipeline running end-to-end here is itself proof no such file
    # gets created as a side effect of the dashboard build step.
    _write_repo_config(tmp_path)
    rpm.run_pre_market(date="2026-07-03", markets=["A", "H", "US"], repo_root=tmp_path, provider=_FakeProvider())

    assert not (tmp_path / "dashboard" / "index.html").exists()


def test_summary_reports_dashboard_build_path(tmp_path: Path, capsys):
    # NOTE: closing text changed again in Phase 6 (the pre-market script now
    # also attempts PaperTrade creation and points at run_close.py for the
    # rest of the loop — see test_run_close.py for that coverage).
    _write_repo_config(tmp_path)
    result = rpm.run_pre_market(
        date="2026-07-03", markets=["A", "H", "US"], repo_root=tmp_path, provider=_FakeProvider()
    )
    rpm._print_summary(result)
    captured = capsys.readouterr()

    assert "dashboard_build:" in captured.out
    assert "FAILED" not in captured.out
    assert "Phase 6 pre-market step complete." in captured.out
