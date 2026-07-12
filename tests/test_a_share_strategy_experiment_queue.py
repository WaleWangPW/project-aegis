from __future__ import annotations

import json
from pathlib import Path

import scripts.build_a_share_strategy_experiment_queue as queue


def _probe() -> dict:
    return {
        "modules": [
            {"module_id": "capital_flow", "endpoint": "moneyflow", "status": "EMPTY"},
            {"module_id": "factor_base", "endpoint": "stk_factor", "status": "EMPTY"},
            {"module_id": "factor_base", "endpoint": "daily_basic", "status": "EMPTY"},
        ]
    }


def _dragon() -> dict:
    return {"summary": {"sample_count": 24, "event_count": 72}}


def _cases() -> dict:
    return {"summary": {"a_share_case_count": 76, "a_share_dragon_tiger_research_sample_case_count": 36}}


def _feature() -> dict:
    return {
        "summary": {"ready_for_deep_sandbox_count": 3},
        "items": [
            {
                "hypothesis_id": "hyp_a_tushare_holder_concentration_improvement",
                "eligible_case_count": 76,
                "min_endpoint_coverage": 0.55,
                "endpoint_results": [{"endpoint": "stk_holdernumber", "covered_case_count": 42}],
            }
        ],
    }


def _deep() -> dict:
    return {
        "items": [
            {
                "hypothesis_id": "hyp_a_tushare_institutional_ownership_stability",
                "disposition": "DEEP_SANDBOX_FAIL",
                "reasons": ["source_signal_win_rate_below_threshold"],
                "metrics": {
                    "source_signal_case_count": 30,
                    "source_signal_win_rate": 0.2,
                    "source_signal_average_return": -0.08,
                    "source_signal_max_drawdown": -0.49,
                },
            },
            {
                "hypothesis_id": "hyp_a_tushare_governance_reward_alignment",
                "disposition": "DEEP_SANDBOX_FAIL",
                "reasons": ["source_signal_average_return_below_threshold"],
                "metrics": {
                    "source_signal_case_count": 40,
                    "source_signal_win_rate": 0.275,
                    "source_signal_average_return": -0.06,
                    "source_signal_max_drawdown": -0.49,
                },
            },
        ]
    }


def _refined() -> dict:
    return {"summary": {"refined_sandbox_blocked_count": 5}}


def _tuned() -> dict:
    return {"summary": {"tuned_experiment_count": 4, "tuned_pass_candidate_count": 0, "tuned_fail_count": 4}}


def _ranking_gate() -> dict:
    return {"summary": {"ranking_gate_approved_count": 0}}


def _diagnostics() -> dict:
    return {
        "summary": {"rankable_strategy_count": 0, "priority_action_count": 2},
        "priority_actions": [{"hypothesis_id": "x", "recommended_action": "tighten_signal_definition"}],
    }


def test_experiment_queue_converts_failures_into_stock_agent_tasks():
    report = queue.build_report(
        _probe(),
        _dragon(),
        _cases(),
        _feature(),
        _deep(),
        _refined(),
        _tuned(),
        _ranking_gate(),
        _diagnostics(),
        run_id="unit",
        command="unit",
    )

    assert report["status"] == "PASS"
    assert report["summary"]["experiment_count"] >= 6
    assert report["summary"]["ready_experiment_count"] >= 4
    assert report["summary"]["blocked_experiment_count"] >= 2
    assert report["summary"]["ranking_impact_allowed"] is False
    assert report["safety"]["no_order_placement"] is True
    assert any(item["experiment_id"] == "exp_a_dragon_tiger_event_signal_split" for item in report["experiments"])
    assert any(item["experiment_id"] == "exp_a_signal_tuning_result_review" for item in report["experiments"])
    assert any(item["status"] == "BLOCKED_NEEDS_PROBE_IMPLEMENTATION" for item in report["experiments"])


def test_experiment_queue_cli_writes_marker_without_secret(tmp_path: Path, capsys):
    files = {
        "probe": _probe(),
        "dragon": _dragon(),
        "cases": _cases(),
        "feature": _feature(),
        "deep": _deep(),
        "refined": _refined(),
        "tuned": _tuned(),
        "ranking": _ranking_gate(),
        "diagnostics": _diagnostics(),
    }
    paths = {}
    for name, payload in files.items():
        path = tmp_path / f"{name}.json"
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        paths[name] = path

    old_reports = queue.REPORTS
    old_processed = queue.PROCESSED
    old_out_json = queue.OUT_JSON
    old_out_md = queue.OUT_MD
    old_marker = queue.PASS_MARKER
    try:
        queue.REPORTS = tmp_path / "reports"
        queue.PROCESSED = tmp_path / "processed"
        queue.OUT_JSON = queue.REPORTS / "a_share_strategy_experiment_queue_latest.json"
        queue.OUT_MD = queue.REPORTS / "a_share_strategy_experiment_queue_latest.md"
        queue.PASS_MARKER = queue.REPORTS / "A_SHARE_STRATEGY_EXPERIMENT_QUEUE_PASS.marker"
        exit_code = queue.main(
            [
                "--source-probe-json",
                str(paths["probe"]),
                "--dragon-tiger-json",
                str(paths["dragon"]),
                "--cases-json",
                str(paths["cases"]),
                "--feature-json",
                str(paths["feature"]),
                "--deep-json",
                str(paths["deep"]),
                "--refined-json",
                str(paths["refined"]),
                "--tuned-json",
                str(paths["tuned"]),
                "--ranking-gate-json",
                str(paths["ranking"]),
                "--diagnostics-json",
                str(paths["diagnostics"]),
                "--run-id",
                "unit",
            ]
        )
        captured = capsys.readouterr()
    finally:
        queue.REPORTS = old_reports
        queue.PROCESSED = old_processed
        queue.OUT_JSON = old_out_json
        queue.OUT_MD = old_out_md
        queue.PASS_MARKER = old_marker

    assert exit_code == 0
    assert "PASS" in captured.out
    assert "token=" not in captured.out.lower()
    assert "secret=" not in captured.out.lower()
    assert (tmp_path / "reports" / "A_SHARE_STRATEGY_EXPERIMENT_QUEUE_PASS.marker").exists()
