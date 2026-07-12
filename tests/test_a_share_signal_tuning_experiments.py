from __future__ import annotations

import json
from pathlib import Path

import scripts.evaluate_a_share_signal_tuning_experiments as tuned


def _case(case_id: str, hypothesis_id: str, *, signal: bool, raw_return: float, drawdown: float, summary: dict) -> dict:
    return {
        "case_id": case_id,
        "symbol": "603893",
        "entry_date": "2023-09-01",
        "source_signal_pass": signal,
        "feature_reasons": [hypothesis_id],
        "feature_summary": summary,
        "covered_endpoints": ["derived"],
        "feature_hash": f"hash_{hypothesis_id}_{case_id}",
        "raw_return": raw_return,
        "max_drawdown": drawdown,
        "case_result": "win" if raw_return > 0 else "loss",
    }


def _deep_report() -> dict:
    return {
        "status": "PASS",
        "items": [
            {
                "hypothesis_id": "hyp_a_tushare_capital_flow_accumulation",
                "case_features": [
                    _case("case_1", "moneyflow", signal=True, raw_return=0.08, drawdown=-0.05, summary={"net_flow_sign": 1, "large_order_net_sign": 1}),
                    _case("case_2", "moneyflow", signal=True, raw_return=-0.03, drawdown=-0.12, summary={"net_flow_sign": 1, "large_order_net_sign": 1}),
                ],
            },
            {
                "hypothesis_id": "hyp_a_tushare_factor_liquidity_quality_overlay",
                "case_features": [
                    _case("case_1", "factor", signal=True, raw_return=0.08, drawdown=-0.05, summary={"turnover_bucket": "liquid", "valuation_bucket": "not_extreme", "overheat_flag": False}),
                    _case("case_2", "factor", signal=False, raw_return=-0.03, drawdown=-0.12, summary={"turnover_bucket": "liquid", "valuation_bucket": "not_extreme", "overheat_flag": True}),
                ],
            },
            {
                "hypothesis_id": "hyp_a_tushare_holder_concentration_improvement",
                "case_features": [
                    _case("case_1", "holder", signal=True, raw_return=0.08, drawdown=-0.05, summary={"holder_num_delta_sign": 1}),
                    _case("case_2", "holder", signal=True, raw_return=-0.03, drawdown=-0.12, summary={"holder_num_delta_sign": 0}),
                ],
            },
            {
                "hypothesis_id": "hyp_a_tushare_institutional_ownership_stability",
                "case_features": [
                    _case("case_1", "institution", signal=True, raw_return=0.08, drawdown=-0.05, summary={"top10_hold_ratio_delta_sign": 1, "top10_float_ratio_delta_sign": 1}),
                    _case("case_2", "institution", signal=True, raw_return=-0.03, drawdown=-0.12, summary={"top10_hold_ratio_delta_sign": 1, "top10_float_ratio_delta_sign": -1}),
                ],
            },
            {
                "hypothesis_id": "hyp_a_tushare_governance_reward_alignment",
                "case_features": [
                    _case("case_1", "governance", signal=True, raw_return=0.08, drawdown=-0.05, summary={"reward_row_count": 1}),
                    _case("case_2", "governance", signal=True, raw_return=-0.03, drawdown=-0.12, summary={"reward_row_count": 1}),
                ],
            },
        ],
    }


def test_signal_tuning_experiments_use_derived_features_without_ranking():
    report = tuned.build_report(_deep_report(), run_id="unit", command="unit")

    assert report["status"] == "PASS"
    assert report["summary"]["tuned_experiment_count"] == 4
    assert report["summary"]["ranking_impact_allowed"] is False
    assert report["safety"]["no_order_placement"] is True
    moneyflow = next(item for item in report["items"] if item["experiment_id"] == "tuned_a_moneyflow_factor_veto")
    assert moneyflow["metrics"]["tuned_signal_case_count"] == 1
    assert moneyflow["metrics"]["tuned_signal_entry_month_count"] == 1
    assert "entry_month_coverage_too_narrow_for_ranking" in moneyflow["coverage_warnings"]
    governance = next(item for item in report["items"] if item["experiment_id"] == "tuned_a_governance_veto_only")
    assert "veto_or_diagnostic_only_not_rankable" in governance["reasons"]
    assert "net_mf_amount" not in json.dumps(report, ensure_ascii=False)


def test_signal_tuning_cli_writes_marker(tmp_path: Path, capsys):
    deep_json = tmp_path / "deep.json"
    deep_json.write_text(json.dumps(_deep_report(), ensure_ascii=False), encoding="utf-8")

    old_reports = tuned.REPORTS
    old_processed = tuned.PROCESSED
    old_out_json = tuned.OUT_JSON
    old_out_md = tuned.OUT_MD
    old_pass = tuned.PASS_MARKER
    old_blocked = tuned.BLOCKED_MARKER
    try:
        tuned.REPORTS = tmp_path / "reports"
        tuned.PROCESSED = tmp_path / "processed"
        tuned.OUT_JSON = tuned.REPORTS / "a_share_signal_tuning_experiments_latest.json"
        tuned.OUT_MD = tuned.REPORTS / "a_share_signal_tuning_experiments_latest.md"
        tuned.PASS_MARKER = tuned.REPORTS / "A_SHARE_SIGNAL_TUNING_EXPERIMENTS_PASS.marker"
        tuned.BLOCKED_MARKER = tuned.REPORTS / "A_SHARE_SIGNAL_TUNING_EXPERIMENTS_BLOCKED.marker"
        exit_code = tuned.main(["--deep-json", str(deep_json), "--run-id", "unit"])
        captured = capsys.readouterr()
    finally:
        tuned.REPORTS = old_reports
        tuned.PROCESSED = old_processed
        tuned.OUT_JSON = old_out_json
        tuned.OUT_MD = old_out_md
        tuned.PASS_MARKER = old_pass
        tuned.BLOCKED_MARKER = old_blocked

    assert exit_code == 0
    assert "PASS" in captured.out
    assert "token=" not in captured.out.lower()
    assert (tmp_path / "reports" / "A_SHARE_SIGNAL_TUNING_EXPERIMENTS_PASS.marker").exists()
