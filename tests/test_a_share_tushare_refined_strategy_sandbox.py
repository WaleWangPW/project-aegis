from __future__ import annotations

import json
from pathlib import Path

import scripts.evaluate_a_share_tushare_refined_strategy_sandbox as refined


def _case(case_id: str, symbol: str, passed: bool, raw_return: float, max_drawdown: float) -> dict:
    return {
        "case_id": case_id,
        "symbol": symbol,
        "entry_date": "2024-01-02",
        "source_signal_pass": passed,
        "feature_hash": f"hash-{case_id}",
        "raw_return": raw_return,
        "max_drawdown": max_drawdown,
        "case_result": "win" if raw_return > 0 else "loss",
    }


def _deep_report() -> dict:
    return {
        "status": "PASS",
        "items": [
            {
                "hypothesis_id": "hyp_a_tushare_capital_flow_accumulation",
                "case_features": [
                    _case("case_1", "600150", True, 0.06, -0.04),
                    _case("case_2", "603863", True, 0.13, -0.14),
                    _case("case_3", "603863", True, -0.01, -0.08),
                    _case("case_4", "002709", True, -0.20, -0.21),
                ],
            },
            {
                "hypothesis_id": "hyp_a_tushare_holder_concentration_improvement",
                "case_features": [
                    _case("case_1", "600150", True, 0.06, -0.04),
                    _case("case_2", "603863", True, 0.13, -0.14),
                    _case("case_3", "603863", True, -0.01, -0.08),
                    _case("case_4", "002709", False, -0.20, -0.21),
                ],
            },
            {
                "hypothesis_id": "hyp_a_tushare_factor_liquidity_quality_overlay",
                "case_features": [
                    _case("case_1", "600150", True, 0.06, -0.04),
                    _case("case_2", "603863", False, 0.13, -0.14),
                    _case("case_3", "603863", False, -0.01, -0.08),
                    _case("case_4", "002709", True, -0.20, -0.21),
                ],
            },
            {
                "hypothesis_id": "hyp_a_tushare_institutional_ownership_stability",
                "case_features": [
                    _case("case_1", "600150", True, 0.06, -0.04),
                    _case("case_2", "603863", True, 0.13, -0.14),
                ],
            },
        ],
    }


def test_refined_sandbox_finds_moneyflow_holder_pass_candidate():
    report = refined.build_report(_deep_report(), run_id="unit", command="unit")

    assert report["status"] == "PASS"
    assert report["summary"]["network_used"] is False
    assert report["summary"]["ranking_impact_allowed"] is False
    assert report["summary"]["user_facing_suggestion_allowed"] is False
    assert report["summary"]["refined_sandbox_pass_candidate_count"] >= 1

    item = next(x for x in report["items"] if x["refined_strategy_id"] == "refined_a_moneyflow_holder_concentration")
    assert item["disposition"] == "REFINED_SANDBOX_PASS_CANDIDATE"
    assert item["metrics"]["refined_signal_case_count"] == 3
    assert item["metrics"]["refined_signal_win_rate"] == 2 / 3
    assert item["ranking_impact_allowed"] is False
    assert item["user_facing_suggestion_allowed"] is False
    assert item["real_trade_allowed"] is False
    assert "feature_hashes" in item["case_features"][0]


def test_refined_sandbox_cli_writes_outputs_without_network(tmp_path: Path, capsys, monkeypatch):
    deep_json = tmp_path / "deep.json"
    deep_json.write_text(json.dumps(_deep_report(), ensure_ascii=False), encoding="utf-8")

    old_reports = refined.REPORTS
    old_processed = refined.PROCESSED
    old_out_json = refined.OUT_JSON
    old_out_md = refined.OUT_MD
    old_pass = refined.PASS_MARKER
    old_blocked = refined.BLOCKED_MARKER
    try:
        refined.REPORTS = tmp_path / "reports"
        refined.PROCESSED = tmp_path / "processed"
        refined.OUT_JSON = refined.REPORTS / "a_share_tushare_refined_strategy_sandbox_latest.json"
        refined.OUT_MD = refined.REPORTS / "a_share_tushare_refined_strategy_sandbox_latest.md"
        refined.PASS_MARKER = refined.REPORTS / "A_SHARE_TUSHARE_REFINED_STRATEGY_SANDBOX_PASS.marker"
        refined.BLOCKED_MARKER = refined.REPORTS / "A_SHARE_TUSHARE_REFINED_STRATEGY_SANDBOX_BLOCKED.marker"
        exit_code = refined.main(["--deep-json", str(deep_json), "--run-id", "unit"])
        captured = capsys.readouterr()
    finally:
        refined.REPORTS = old_reports
        refined.PROCESSED = old_processed
        refined.OUT_JSON = old_out_json
        refined.OUT_MD = old_out_md
        refined.PASS_MARKER = old_pass
        refined.BLOCKED_MARKER = old_blocked

    assert exit_code == 0
    assert "PASS" in captured.out
    assert "token=" not in captured.out.lower()
    payload = json.loads((tmp_path / "reports" / "a_share_tushare_refined_strategy_sandbox_latest.json").read_text())
    assert payload["summary"]["network_used"] is False
    assert payload["checks"]["network_not_used"] is True
    assert (tmp_path / "reports" / "A_SHARE_TUSHARE_REFINED_STRATEGY_SANDBOX_PASS.marker").exists()
