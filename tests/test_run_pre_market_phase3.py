"""Phase 3 tests for scripts/run_pre_market.py — PHASE3 doc §9.6.

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


def _uptrend_bars(n: int = 25) -> pd.DataFrame:
    closes = [100.0 + i for i in range(n)]
    vols = [1000.0] * n
    trade_dates = [f"202606{str(i + 1).zfill(2)}" for i in range(n)]
    return pd.DataFrame({"trade_date": trade_dates, "close": closes, "vol": vols})


class _FakeProvider:
    def __init__(self):
        self._bars = _uptrend_bars()
        self._stock_basic = pd.DataFrame(
            [{"symbol": "OTHR", "avg_dollar_volume": 10_000_000, "is_suspended": False, "is_st": False}]
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


def test_run_pre_market_generates_signals_and_expert_opinions(tmp_path: Path):
    _write_repo_config(tmp_path)
    result = rpm.run_pre_market(
        date="2026-07-03", markets=["A", "H", "US"], repo_root=tmp_path, provider=_FakeProvider()
    )

    assert len(result.signals) > 0
    assert len(result.expert_opinions) > 0
    # 7 opinions per candidate (one per enabled P0 agent).
    assert len(result.expert_opinions) == len(result.candidates) * 7


def test_run_pre_market_creates_no_review_artifacts(tmp_path: Path):
    # NOTE: "recommendations.jsonl"/"decisions.jsonl" were forbidden here in
    # Phase 3 (they didn't exist yet). Phase 4 legitimately added them to
    # the same script (see tests/test_run_pre_market_phase4.py) — they are
    # no longer "later phase" artifacts. Phase 5 legitimately added a real
    # data/dashboard/dashboard_data.json (see
    # tests/test_run_pre_market_dashboard_boundary.py). Phase 6 legitimately
    # added `data/records/paper_trades.jsonl` for Action recommendations
    # (see tests/test_run_pre_market_dashboard_boundary.py /
    # test_paper_trade_service.py) — this fixture's synthetic uptrend bars
    # do produce at least one Action-status recommendation, so
    # paper_trades.jsonl is no longer forbidden either. Only Review/Memory
    # remain forbidden (those are `scripts/run_close.py`'s job, not this
    # script's).
    _write_repo_config(tmp_path)
    rpm.run_pre_market(date="2026-07-03", markets=["A", "H", "US"], repo_root=tmp_path, provider=_FakeProvider())

    records_dir = tmp_path / "data" / "records"
    assert not (records_dir / "reviews.jsonl").exists()
    assert not (records_dir / "memory.jsonl").exists()
    dashboard_dir = tmp_path / "data" / "dashboard"
    assert not (dashboard_dir / "reviews.json").exists()

    # Phase 3's own artifacts should still exist.
    assert (records_dir / "signals.jsonl").exists()
    assert (records_dir / "expert_opinions.jsonl").exists()
    processed_dir = tmp_path / "data" / "processed" / "2026-07-03"
    assert (processed_dir / "signals_pre_market.json").exists()
    assert (processed_dir / "expert_opinions_pre_market.json").exists()


def test_cli_prints_phase3_signal_and_opinion_counts(monkeypatch, capsys):
    # NOTE: the exact header/closing text changed in Phase 4 (see
    # tests/test_run_pre_market_phase4.py) — this test only re-verifies the
    # Phase 3 signals/expert_opinions counts still print correctly.
    fake_result = rpm.PreMarketResult(
        date="2026-07-03",
        markets=["A", "H", "US"],
        market_snapshots=[object()] * 4,
        candidates=[object()] * 2,
        forced_holdings=1,
        data_gaps=0,
        signals=[object()] * 12,
        expert_opinions=[object()] * 14,
    )
    monkeypatch.setattr(rpm, "run_pre_market", lambda **kwargs: fake_result)

    exit_code = rpm.main(["--date", "2026-07-03", "--markets", "A,H,US"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "signals: 12" in captured.out
    assert "expert_opinions: 14" in captured.out
    assert "recommendations: 0" in captured.out
