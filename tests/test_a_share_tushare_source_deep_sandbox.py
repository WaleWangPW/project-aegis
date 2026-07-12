from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

import scripts.evaluate_a_share_tushare_source_deep_sandbox as deep


class FakePro:
    def moneyflow(self, trade_date: str):
        return pd.DataFrame(
            [
                {
                    "ts_code": "603893.SH",
                    "trade_date": trade_date,
                    "net_mf_amount": 10.0,
                    "buy_lg_amount": 8.0,
                    "buy_elg_amount": 5.0,
                    "sell_lg_amount": 2.0,
                    "sell_elg_amount": 1.0,
                }
            ]
        )

    def top10_holders(self, ts_code: str, start_date: str, end_date: str):
        return pd.DataFrame(
            [
                {"ts_code": ts_code, "ann_date": "20230101", "end_date": "20221231", "hold_ratio": 35.0},
                {"ts_code": ts_code, "ann_date": "20230601", "end_date": "20230331", "hold_ratio": 36.0},
            ]
        )

    def top10_floatholders(self, ts_code: str, start_date: str, end_date: str):
        return pd.DataFrame(
            [
                {"ts_code": ts_code, "ann_date": "20230101", "end_date": "20221231", "hold_float_ratio": 20.0},
                {"ts_code": ts_code, "ann_date": "20230601", "end_date": "20230331", "hold_float_ratio": 21.0},
            ]
        )

    def stk_holdernumber(self, ts_code: str, start_date: str, end_date: str):
        return pd.DataFrame(
            [
                {"ts_code": ts_code, "ann_date": "20230101", "end_date": "20221231", "holder_num": 1000},
                {"ts_code": ts_code, "ann_date": "20230601", "end_date": "20230331", "holder_num": 900},
            ]
        )

    def daily_basic(self, trade_date: str):
        return pd.DataFrame([{"ts_code": "603893.SH", "trade_date": trade_date, "turnover_rate": 1.2, "pe_ttm": 60.0}])

    def stk_factor(self, trade_date: str):
        return pd.DataFrame([{"ts_code": "603893.SH", "trade_date": trade_date, "pct_change": 1.0, "rsi_6": 55.0}])

    def stk_rewards(self, ts_code: str):
        return pd.DataFrame([{"ts_code": ts_code, "ann_date": "20230601", "end_date": "20230331", "reward": 100.0, "hold_vol": 0}])

    def top_list(self, trade_date: str):
        return pd.DataFrame()

    def top_inst(self, trade_date: str):
        return pd.DataFrame()


class _UnconfiguredAdapter:
    def is_configured(self) -> bool:
        return False


def _queue() -> dict:
    return {
        "hypothesis_count": 2,
        "hypotheses": [
            {"hypothesis_id": "hyp_a_tushare_capital_flow_accumulation", "title": "Capital flow"},
            {"hypothesis_id": "hyp_a_tushare_dragon_tiger_seat_confirmation", "title": "Hot money"},
        ],
    }


def _cases_report() -> dict:
    return {
        "status": "PASS",
        "historical_cases": [
            {
                "case_id": "case_1",
                "symbol": "603893",
                "ts_code": "603893.SH",
                "market": "A",
                "entry_date": "2023-09-01",
                "raw_return": 0.05,
                "max_drawdown": -0.05,
                "case_result": "win",
            },
            {
                "case_id": "case_us",
                "symbol": "VRTX",
                "market": "US",
                "entry_date": "2023-09-01",
                "raw_return": -0.01,
                "max_drawdown": -0.02,
                "case_result": "loss",
            },
        ],
    }


def _coverage() -> dict:
    return {
        "status": "PASS",
        "items": [
            {
                "hypothesis_id": "hyp_a_tushare_capital_flow_accumulation",
                "feature_status": "READY_FOR_DEEP_SANDBOX",
                "min_endpoint_coverage": 1.0,
                "eligible_symbols": ["603893"],
            },
            {
                "hypothesis_id": "hyp_a_tushare_dragon_tiger_seat_confirmation",
                "feature_status": "FEATURE_GAPS",
                "min_endpoint_coverage": 0.0,
                "eligible_symbols": ["603893"],
            },
        ],
    }


def test_deep_sandbox_evaluates_only_ready_hypotheses_without_ranking():
    report = deep.build_report(_queue(), _cases_report(), _coverage(), FakePro(), run_id="unit", command="unit")

    assert report["status"] == "PASS"
    assert report["summary"]["evaluated_hypothesis_count"] == 1
    assert report["summary"]["blocked_feature_gap_count"] == 1
    assert report["summary"]["ranking_impact_allowed"] is False
    assert report["checks"]["raw_payload_saved"] is False
    assert report["safety"]["user_facing_suggestion_allowed"] is False
    item = report["items"][0]
    assert item["hypothesis_id"] == "hyp_a_tushare_capital_flow_accumulation"
    assert item["case_features"][0]["source_signal_pass"] is True
    assert item["case_features"][0]["feature_summary"]["net_flow_sign"] == 1
    assert "feature_hash" in item["case_features"][0]
    assert "net_mf_amount" not in json.dumps(item, ensure_ascii=False)


def test_deep_sandbox_cli_blocks_without_token(tmp_path: Path, capsys, monkeypatch):
    queue_json = tmp_path / "queue.json"
    cases_json = tmp_path / "cases.json"
    coverage_json = tmp_path / "coverage.json"
    queue_json.write_text(json.dumps(_queue(), ensure_ascii=False), encoding="utf-8")
    cases_json.write_text(json.dumps(_cases_report(), ensure_ascii=False), encoding="utf-8")
    coverage_json.write_text(json.dumps(_coverage(), ensure_ascii=False), encoding="utf-8")

    old_reports = deep.REPORTS
    old_processed = deep.PROCESSED
    old_out_json = deep.OUT_JSON
    old_out_md = deep.OUT_MD
    old_pass = deep.PASS_MARKER
    old_blocked = deep.BLOCKED_MARKER
    try:
        monkeypatch.setattr(deep.TushareAdapter, "from_env", lambda: _UnconfiguredAdapter())
        deep.REPORTS = tmp_path / "reports"
        deep.PROCESSED = tmp_path / "processed"
        deep.OUT_JSON = deep.REPORTS / "a_share_tushare_source_deep_sandbox_latest.json"
        deep.OUT_MD = deep.REPORTS / "a_share_tushare_source_deep_sandbox_latest.md"
        deep.PASS_MARKER = deep.REPORTS / "A_SHARE_TUSHARE_SOURCE_DEEP_SANDBOX_PASS.marker"
        deep.BLOCKED_MARKER = deep.REPORTS / "A_SHARE_TUSHARE_SOURCE_DEEP_SANDBOX_BLOCKED.marker"
        exit_code = deep.main(
            [
                "--queue-json",
                str(queue_json),
                "--cases-json",
                str(cases_json),
                "--feature-coverage-json",
                str(coverage_json),
                "--run-id",
                "unit",
            ]
        )
        captured = capsys.readouterr()
    finally:
        deep.REPORTS = old_reports
        deep.PROCESSED = old_processed
        deep.OUT_JSON = old_out_json
        deep.OUT_MD = old_out_md
        deep.PASS_MARKER = old_pass
        deep.BLOCKED_MARKER = old_blocked

    assert exit_code == 2
    assert "BLOCKED_MISSING_TUSHARE_TOKEN" in captured.out
    assert "token=" not in captured.out.lower()
    assert (tmp_path / "reports" / "A_SHARE_TUSHARE_SOURCE_DEEP_SANDBOX_BLOCKED.marker").exists()
