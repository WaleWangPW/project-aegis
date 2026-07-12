from __future__ import annotations

import json
from pathlib import Path

import scripts.analyze_a_share_tushare_strategy_diagnostics as diagnostics


def _proxy() -> dict:
    return {"status": "PASS", "summary": {"proxy_pass_count": 0, "proxy_fail_count": 2}}


def _feature() -> dict:
    return {
        "status": "PASS",
        "summary": {"ready_for_deep_sandbox_count": 1, "feature_gap_count": 1},
        "items": [
            {
                "hypothesis_id": "hyp_a_tushare_dragon_tiger_seat_confirmation",
                "title": "Dragon tiger",
                "feature_status": "FEATURE_GAPS",
                "required_endpoints": ["top_list", "top_inst"],
                "eligible_symbols": ["603893", "300059"],
            },
            {
                "hypothesis_id": "hyp_a_tushare_capital_flow_accumulation",
                "title": "Capital flow",
                "feature_status": "READY_FOR_DEEP_SANDBOX",
                "required_endpoints": ["moneyflow"],
                "eligible_symbols": ["603893", "300059"],
            },
        ],
    }


def _deep() -> dict:
    return {
        "status": "PASS",
        "summary": {"deep_sandbox_pass_candidate_count": 0, "deep_sandbox_fail_count": 1},
        "items": [
            {
                "hypothesis_id": "hyp_a_tushare_capital_flow_accumulation",
                "title": "Capital flow",
                "required_endpoints": ["moneyflow"],
                "disposition": "DEEP_SANDBOX_FAIL",
                "reasons": [
                    "source_signal_win_rate_below_threshold",
                    "source_signal_average_return_below_threshold",
                    "source_signal_drawdown_breached",
                ],
                "metrics": {
                    "eligible_case_count": 40,
                    "source_signal_case_count": 9,
                    "source_signal_rate": 0.225,
                    "source_signal_win_rate": 0.33,
                    "source_signal_average_return": -0.11,
                    "source_signal_max_drawdown": -0.49,
                },
            }
        ],
    }


def _cases() -> dict:
    return {"status": "PASS", "summary": {"a_share_case_count": 40}}


def test_strategy_diagnostics_separates_feature_gaps_from_failed_signals():
    report = diagnostics.build_report(_proxy(), _feature(), _deep(), _cases())

    assert report["status"] == "PASS"
    assert report["summary"]["rankable_strategy_count"] == 0
    assert report["summary"]["ranking_impact_allowed"] is False
    assert report["feature_gap_actions"][0]["hypothesis_id"] == "hyp_a_tushare_dragon_tiger_seat_confirmation"
    assert report["feature_gap_actions"][0]["recommended_action"] == "collect_endpoint_history"
    assert report["deep_diagnostics"][0]["recommended_action"] == "add_risk_veto_before_retest"
    assert report["deep_diagnostics"][0]["ranking_gate_allowed"] is False
    assert report["checks"]["no_network_used"] is True
    assert report["safety"]["no_order_placement"] is True


def test_strategy_diagnostics_cli_writes_report_without_secret(tmp_path: Path, capsys):
    proxy = tmp_path / "proxy.json"
    feature = tmp_path / "feature.json"
    deep = tmp_path / "deep.json"
    cases = tmp_path / "cases.json"
    proxy.write_text(json.dumps(_proxy(), ensure_ascii=False), encoding="utf-8")
    feature.write_text(json.dumps(_feature(), ensure_ascii=False), encoding="utf-8")
    deep.write_text(json.dumps(_deep(), ensure_ascii=False), encoding="utf-8")
    cases.write_text(json.dumps(_cases(), ensure_ascii=False), encoding="utf-8")

    old_reports = diagnostics.REPORTS
    old_processed = diagnostics.PROCESSED
    old_out_json = diagnostics.OUT_JSON
    old_out_md = diagnostics.OUT_MD
    old_marker = diagnostics.PASS_MARKER
    try:
        diagnostics.REPORTS = tmp_path / "reports"
        diagnostics.PROCESSED = tmp_path / "processed"
        diagnostics.OUT_JSON = diagnostics.REPORTS / "a_share_tushare_strategy_diagnostics_latest.json"
        diagnostics.OUT_MD = diagnostics.REPORTS / "a_share_tushare_strategy_diagnostics_latest.md"
        diagnostics.PASS_MARKER = diagnostics.REPORTS / "A_SHARE_TUSHARE_STRATEGY_DIAGNOSTICS_PASS.marker"
        exit_code = diagnostics.main(
            [
                "--proxy-json",
                str(proxy),
                "--feature-json",
                str(feature),
                "--deep-json",
                str(deep),
                "--cases-json",
                str(cases),
                "--run-id",
                "unit",
            ]
        )
        captured = capsys.readouterr()
    finally:
        diagnostics.REPORTS = old_reports
        diagnostics.PROCESSED = old_processed
        diagnostics.OUT_JSON = old_out_json
        diagnostics.OUT_MD = old_out_md
        diagnostics.PASS_MARKER = old_marker

    assert exit_code == 0
    assert "PASS" in captured.out
    assert "token=" not in captured.out.lower()
    assert "secret=" not in captured.out.lower()
    assert (tmp_path / "reports" / "A_SHARE_TUSHARE_STRATEGY_DIAGNOSTICS_PASS.marker").exists()
