"""Phase 4 tests for scripts/run_pre_market.py — PHASE4 doc §11.6.

Fake provider only, isolated tmp_path repo root, no real Tushare/network.
"""

from __future__ import annotations

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


def test_pipeline_calls_decision_and_recommendation_steps_after_experts(tmp_path: Path):
    _write_repo_config(tmp_path)
    result = rpm.run_pre_market(
        date="2026-07-03", markets=["A", "H", "US"], repo_root=tmp_path, provider=_FakeProvider()
    )

    assert len(result.decisions) == len(result.candidates)
    assert len(result.recommendations) == len(result.candidates)
    # One decision/recommendation per candidate, built from that candidate's 7 opinions.
    for status in (r.status for r in result.recommendations):
        assert status in ("Watch", "Ready", "Action", "Exit")


def test_script_does_not_create_paper_trade_dashboard_side_effects(tmp_path: Path):
    # NOTE: this test originally asserted the script did NOT build a
    # dashboard at all (true in Phase 4, before Dashboard JSON existed).
    # Phase 5 legitimately added dashboard building to this same script
    # (see tests/test_run_pre_market_dashboard_boundary.py for that
    # coverage) — the
    # thing this test still needs to guard is narrower: no Paper Trade
    # artifacts should ever end up under data/dashboard/.
    _write_repo_config(tmp_path)
    rpm.run_pre_market(date="2026-07-03", markets=["A", "H", "US"], repo_root=tmp_path, provider=_FakeProvider())

    dashboard_dir = tmp_path / "data" / "dashboard"
    assert not (dashboard_dir / "paper_trades.json").exists()


def test_script_does_not_create_review_or_memory_records(tmp_path: Path):
    # NOTE: originally also asserted `paper_trades.jsonl` did not exist
    # (true in Phase 4). Phase 6 legitimately added real PaperTrade creation
    # to this same script for Action recommendations (see
    # tests/test_run_pre_market_dashboard_boundary.py /
    # test_paper_trade_service.py) — this fixture's synthetic uptrend bars
    # do produce an Action-status recommendation, so `paper_trades.jsonl`
    # is no longer forbidden. Review/Memory generation remains
    # `scripts/run_close.py`'s job, so those two stay forbidden here.
    _write_repo_config(tmp_path)
    rpm.run_pre_market(date="2026-07-03", markets=["A", "H", "US"], repo_root=tmp_path, provider=_FakeProvider())

    records_dir = tmp_path / "data" / "records"
    assert not (records_dir / "reviews.jsonl").exists()
    assert not (records_dir / "investment_memory.jsonl").exists()
    assert not (records_dir / "memory.jsonl").exists()

    # Phase 4's own artifacts should exist.
    assert (records_dir / "decisions.jsonl").exists()
    assert (records_dir / "recommendations.jsonl").exists()


def test_script_handles_empty_candidates_cleanly(tmp_path: Path):
    _write_repo_config(tmp_path)
    # Empty markets list -> UniverseBuilder produces zero candidates.
    result = rpm.run_pre_market(date="2026-07-03", markets=[], repo_root=tmp_path, provider=_FakeProvider())

    assert result.candidates == []
    assert result.decisions == []
    assert result.recommendations == []

    # Printing the summary over an empty result must not raise.
    rpm._print_summary(result)


def test_cli_prints_decision_and_recommendation_counts(monkeypatch, capsys):
    # NOTE: header/closing text changed again in Phase 5 (dashboard building
    # is now real — see tests/test_run_pre_market_dashboard_boundary.py).
    # This test only re-verifies the Phase 4 decisions/recommendations
    # counts still print.
    fake_result = rpm.PreMarketResult(
        date="2026-07-03",
        markets=["A", "H", "US"],
        market_snapshots=[object()] * 4,
        candidates=[object()] * 2,
        forced_holdings=1,
        data_gaps=0,
        signals=[object()] * 12,
        expert_opinions=[object()] * 14,
        decisions=[object()] * 2,
        recommendations=[],
    )
    monkeypatch.setattr(rpm, "run_pre_market", lambda **kwargs: fake_result)

    exit_code = rpm.main(["--date", "2026-07-03", "--markets", "A,H,US"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "decisions: 2" in captured.out
    assert "recommendations: 0" in captured.out
