from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

import scripts.collect_a_share_dragon_tiger_research_samples as samples


def test_eligible_event_dates_keep_forward_window():
    dates = [f"202401{day:02d}" for day in range(1, 31)]

    selected = samples.eligible_event_dates(dates, lookback_dates=5, forward_days=20)

    assert selected == ["20240106", "20240107", "20240108", "20240109", "20240110"]


def test_build_samples_are_research_only_and_metadata_only():
    top_list = pd.DataFrame(
        [
            {
                "trade_date": "20240105",
                "ts_code": "002001.SZ",
                "name": "新和成",
                "net_amount": 1200.5,
                "pct_change": 8.2,
                "turnover_rate": 12.3,
                "reason": "日涨幅偏离值达7%",
            }
        ]
    )
    top_inst = pd.DataFrame(
        [
            {
                "trade_date": "20240105",
                "ts_code": "002001.SZ",
                "exalter": "机构专用",
                "net_buy": 88.0,
            }
        ]
    )

    result = samples.build_samples(
        [("20240105", top_list, top_inst)],
        {"002001.SZ": "新和成"},
        max_symbols=3,
        max_events_per_symbol=2,
    )

    assert len(result) == 1
    item = result[0]
    assert item["sample_source"] == "tushare_dragon_tiger_hot_money"
    assert item["research_sample_only"] is True
    assert item["user_facing_suggestion_allowed"] is False
    assert item["real_trade_allowed"] is False
    assert item["event_trade_dates"] == ["2024-01-05"]
    assert "reason" not in item["events"][0]
    assert item["events"][0]["reason_hash"]


def test_build_samples_filters_retired_or_st_names():
    top_list = pd.DataFrame(
        [
            {"trade_date": "20240105", "ts_code": "002001.SZ", "net_amount": 1},
            {"trade_date": "20240105", "ts_code": "002002.SZ", "net_amount": 1000},
            {"trade_date": "20240105", "ts_code": "002003.SZ", "net_amount": 1000},
        ]
    )
    top_inst = pd.DataFrame()

    result = samples.build_samples(
        [("20240105", top_list, top_inst)],
        {"002001.SZ": "新和成", "002002.SZ": "太安退", "002003.SZ": "*ST华闻"},
        max_symbols=10,
        max_events_per_symbol=2,
    )

    assert [item["ts_code"] for item in result] == ["002001.SZ"]


class _UnconfiguredAdapter:
    def is_configured(self) -> bool:
        return False


def test_dragon_tiger_cli_writes_blocked_report_without_secret(tmp_path: Path, capsys, monkeypatch):
    old_reports = samples.REPORTS
    old_processed = samples.PROCESSED
    old_daily = samples.DAILY_DIR
    old_stock_basic = samples.STOCK_BASIC
    old_out_json = samples.OUT_JSON
    old_out_md = samples.OUT_MD
    old_pass = samples.PASS_MARKER
    old_blocked = samples.BLOCKED_MARKER
    try:
        daily_dir = tmp_path / "daily"
        daily_dir.mkdir()
        for day in range(1, 31):
            (daily_dir / f"202401{day:02d}.json").write_text("{}", encoding="utf-8")
        stock_basic = tmp_path / "stock_basic.json"
        stock_basic.write_text(json.dumps({"rows": []}), encoding="utf-8")
        monkeypatch.setattr(samples.TushareAdapter, "from_env", lambda: _UnconfiguredAdapter())
        samples.REPORTS = tmp_path / "reports"
        samples.PROCESSED = tmp_path / "processed"
        samples.DAILY_DIR = daily_dir
        samples.STOCK_BASIC = stock_basic
        samples.OUT_JSON = samples.REPORTS / "a_share_dragon_tiger_research_samples_latest.json"
        samples.OUT_MD = samples.REPORTS / "a_share_dragon_tiger_research_samples_latest.md"
        samples.PASS_MARKER = samples.REPORTS / "A_SHARE_DRAGON_TIGER_RESEARCH_SAMPLES_PASS.marker"
        samples.BLOCKED_MARKER = samples.REPORTS / "A_SHARE_DRAGON_TIGER_RESEARCH_SAMPLES_BLOCKED.marker"
        exit_code = samples.main(["--run-id", "unit", "--lookback-dates", "5"])
        captured = capsys.readouterr()
    finally:
        samples.REPORTS = old_reports
        samples.PROCESSED = old_processed
        samples.DAILY_DIR = old_daily
        samples.STOCK_BASIC = old_stock_basic
        samples.OUT_JSON = old_out_json
        samples.OUT_MD = old_out_md
        samples.PASS_MARKER = old_pass
        samples.BLOCKED_MARKER = old_blocked

    assert exit_code == 2
    assert "BLOCKED_MISSING_TUSHARE_TOKEN" in captured.out
    assert "token=" not in captured.out.lower()
    assert "secret=" not in captured.out.lower()
    assert (tmp_path / "reports" / "A_SHARE_DRAGON_TIGER_RESEARCH_SAMPLES_BLOCKED.marker").exists()
