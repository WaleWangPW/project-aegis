"""Phase 7 tests for scripts/run_backtest.py — PHASE7 doc §7/§9.5.

Fake provider only, isolated tmp_path repo root + data dir, no real
Tushare/network — same convention as every prior phase's CLI tests.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

import scripts.run_backtest as rb

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


def _bars(n: int = 45) -> pd.DataFrame:
    closes = [100.0 + i for i in range(n)]
    vols = [1000.0] * n
    dates = []
    month, day = 6, 1
    for _ in range(n):
        dates.append(f"2026{str(month).zfill(2)}{str(day).zfill(2)}")
        day += 1
        if day > 30:
            day = 1
            month += 1
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


def test_validate_date_range_rejects_end_before_start():
    with pytest.raises(rb.BacktestArgumentError):
        rb._validate_date_range("2026-07-01", "2026-06-01")


def test_validate_date_range_rejects_malformed_dates():
    with pytest.raises(rb.BacktestArgumentError):
        rb._validate_date_range("2026/07/01", "2026-07-05")


def test_validate_date_range_accepts_valid_range():
    rb._validate_date_range("2026-06-01", "2026-06-05")  # must not raise


def test_validate_markets_rejects_empty_list():
    with pytest.raises(rb.BacktestArgumentError):
        rb._validate_markets([])


def test_validate_markets_rejects_unknown_market():
    with pytest.raises(rb.BacktestArgumentError):
        rb._validate_markets(["A", "XX"])


def test_validate_markets_accepts_known_markets():
    rb._validate_markets(["A", "H", "US"])  # must not raise


def test_run_backtest_writes_expected_output_files(tmp_path: Path):
    _write_repo_config(tmp_path)
    data_dir = tmp_path / "data"

    run_id, results, report, output_dir = rb.run_backtest(
        start="2026-06-29",
        end="2026-06-30",
        markets=["US"],
        data_dir=data_dir,
        repo_root=tmp_path,
        base_provider=_FakeProvider(),
        run_id="bt_cli_test",
    )

    assert run_id == "bt_cli_test"
    assert len(results) == 2
    assert (output_dir / "backtest_results.jsonl").exists()
    assert (output_dir / "metrics_report.json").exists()
    assert (output_dir / "metrics_report.md").exists()
    assert (output_dir / "data_access_log.jsonl").exists()


def test_run_backtest_never_writes_to_live_records_dir(tmp_path: Path):
    _write_repo_config(tmp_path)
    data_dir = tmp_path / "data"

    rb.run_backtest(
        start="2026-06-30",
        end="2026-06-30",
        markets=["US"],
        data_dir=data_dir,
        repo_root=tmp_path,
        base_provider=_FakeProvider(),
        run_id="bt_cli_isolation",
    )

    records_dir = data_dir / "records"
    for filename in ("paper_trades.jsonl", "reviews.jsonl", "recommendations.jsonl", "decisions.jsonl"):
        assert not (records_dir / filename).exists()


def test_cli_main_exits_zero_and_does_not_print_secrets(tmp_path: Path, monkeypatch, capsys):
    _write_repo_config(tmp_path)
    data_dir = tmp_path / "data"

    monkeypatch.setenv("TUSHARE_TOKEN", "totally-fake-secret-token-should-not-print")
    original_run_backtest = rb.run_backtest
    monkeypatch.setattr(
        rb,
        "run_backtest",
        lambda **kwargs: original_run_backtest(
            start=kwargs["start"],
            end=kwargs["end"],
            markets=kwargs["markets"],
            session=kwargs["session"],
            data_dir=data_dir,
            repo_root=tmp_path,
            base_provider=_FakeProvider(),
        ),
    )

    exit_code = rb.main(["--start", "2026-06-30", "--end", "2026-06-30", "--markets", "US", "--data-dir", str(data_dir)])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "totally-fake-secret-token-should-not-print" not in captured.out
    assert "totally-fake-secret-token-should-not-print" not in captured.err
    assert "No future data violations: 0" in captured.out


def test_cli_main_reports_bad_argument_without_traceback(capsys):
    exit_code = rb.main(["--start", "2026-07-05", "--end", "2026-06-01", "--markets", "US"])
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "Backtest argument error" in captured.err
    assert "Traceback" not in captured.err
