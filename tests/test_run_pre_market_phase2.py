"""Phase 2 tests for scripts/run_pre_market.py — PHASE2 doc §8.4.

Fake provider only, isolated tmp_path repo root, no real Tushare/network,
no writes to the real repo's data/ directory.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import yaml

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


def _uptrend_bars(n: int = 25) -> pd.DataFrame:
    closes = [100.0 + i for i in range(n)]
    vols = [1000.0] * n
    trade_dates = [f"202606{str(i + 1).zfill(2)}" for i in range(n)]
    return pd.DataFrame({"trade_date": trade_dates, "close": closes, "vol": vols})


class _FakeProvider:
    def __init__(self):
        bars = _uptrend_bars()
        self._index_bars = {"000300.SH": bars, "HSI.HI": bars, "SPX": bars}
        self._stock_basic = pd.DataFrame(
            [{"symbol": "OTHR", "avg_dollar_volume": 10_000_000, "is_suspended": False, "is_st": False}]
        )

    def get_index_bars(self, index_code, market, start, end):
        return self._index_bars.get(index_code, pd.DataFrame())

    def get_daily_bars(self, symbol, market, start, end):
        return pd.DataFrame()

    def get_stock_basic(self, market):
        return self._stock_basic


def _write_repo_config(root: Path) -> None:
    config_dir = root / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "holdings.yaml").write_text(HOLDINGS_YAML, encoding="utf-8")
    (config_dir / "universe.yaml").write_text(UNIVERSE_YAML, encoding="utf-8")


def test_run_pre_market_end_to_end_with_fake_provider(tmp_path: Path):
    _write_repo_config(tmp_path)
    provider = _FakeProvider()

    result = rpm.run_pre_market(
        date="2026-07-03", markets=["A", "H", "US"], repo_root=tmp_path, provider=provider
    )

    assert result.forced_holdings == 1
    assert any(c.symbol == "CRCL" for c in result.candidates)
    assert len(result.market_snapshots) == 4  # A, H, US, GLOBAL

    data_dir = tmp_path / "data"
    assert (data_dir / "processed" / "2026-07-03" / "market_snapshots_pre_market.json").exists()
    assert (data_dir / "processed" / "2026-07-03" / "candidates_pre_market.json").exists()
    assert (data_dir / "records" / "market_snapshots.jsonl").exists()
    assert (data_dir / "records" / "candidates.jsonl").exists()

    candidates_json = json.loads((data_dir / "processed" / "2026-07-03" / "candidates_pre_market.json").read_text())
    assert any(c["symbol"] == "CRCL" for c in candidates_json)


def test_run_pre_market_creates_no_later_phase_artifacts(tmp_path: Path):
    # NOTE: "expert_opinions.jsonl"/"signals.jsonl" were forbidden here in
    # Phase 2, then "recommendations.jsonl"/"decisions.jsonl" were forbidden
    # through Phase 3. Phase 3 and Phase 4 each legitimately added their own
    # artifacts to this same script (see test_run_pre_market_phase3.py /
    # test_run_pre_market_phase4.py) — none of those are "later phase"
    # artifacts anymore. Phase 5 legitimately added a real
    # data/dashboard/dashboard_data.json (see
    # tests/test_run_pre_market_dashboard_boundary.py), so "the whole
    # data/dashboard directory must not exist" is no longer true — only
    # PaperTrade/Review remain forbidden, at both the records and dashboard
    # layers.
    _write_repo_config(tmp_path)
    rpm.run_pre_market(date="2026-07-03", markets=["A", "H", "US"], repo_root=tmp_path, provider=_FakeProvider())

    records_dir = tmp_path / "data" / "records"
    for forbidden in ("paper_trades.jsonl", "reviews.jsonl"):
        assert not (records_dir / forbidden).exists()
    dashboard_dir = tmp_path / "data" / "dashboard"
    assert not (dashboard_dir / "paper_trades.json").exists()
    assert not (dashboard_dir / "reviews.json").exists()


def test_cli_prints_expected_summary_and_no_recommendations_line(monkeypatch, capsys):
    # NOTE: scripts/run_pre_market.py is the same script later phases
    # extended (per each phase doc's "modify only if necessary" — the
    # header/summary legitimately changed from "Phase 2" -> "Phase 3" ->
    # "Phase 4" -> "Phase 5" -> "Phase 6" plus new fields each time; see
    # test_run_pre_market_phase3.py / test_run_pre_market_phase4.py /
    # test_run_pre_market_dashboard_boundary.py / test_run_close.py for the
    # phase-specific assertions). This test only re-verifies the Phase 2
    # fields (market_snapshots/candidates/forced_holdings/data_gaps) still
    # print.
    fake_result = rpm.PreMarketResult(
        date="2026-07-03",
        markets=["A", "H", "US"],
        market_snapshots=[object()] * 4,
        candidates=[object()] * 3,
        forced_holdings=1,
        data_gaps=2,
    )
    monkeypatch.setattr(rpm, "run_pre_market", lambda **kwargs: fake_result)

    exit_code = rpm.main(["--date", "2026-07-03", "--markets", "A,H,US"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Project Aegis pre-market Phase 6" in captured.out
    assert "market_snapshots: 4" in captured.out
    assert "candidates: 3" in captured.out
    assert "forced_holdings: 1" in captured.out
    assert "data_gaps: 2" in captured.out
    assert "recommendations: 0" in captured.out
