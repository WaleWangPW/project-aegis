from __future__ import annotations

import json
from pathlib import Path

import scripts.evaluate_a_share_tushare_source_hypotheses as evaluator


def _queue() -> dict:
    return {
        "hypothesis_count": 2,
        "hypotheses": [
            {
                "hypothesis_id": "hyp_a_tushare_capital_flow_accumulation",
                "title": "Capital flow",
                "strategy_families": ["capital_flow", "momentum", "risk_overlay"],
                "source_research_ids": ["tushare_probe:moneyflow"],
            },
            {
                "hypothesis_id": "hyp_a_tushare_governance_reward_alignment",
                "title": "Governance",
                "strategy_families": ["governance", "quality", "risk_overlay"],
                "source_research_ids": ["tushare_probe:stk_rewards"],
            },
        ],
    }


def _cases() -> dict:
    return {
        "status": "PASS",
        "summary": {"a_share_case_count": 8},
        "candidate_results": [
            {
                "symbol": "603893",
                "market": "A",
                "matched_strategy_ids": ["a_share_short_momentum", "growth_breakout"],
                "summary": {
                    "case_count": 4,
                    "win_rate": 0.75,
                    "average_return": 0.04,
                    "average_max_drawdown": -0.05,
                    "best_return": 0.1,
                    "worst_return": -0.02,
                },
            },
            {
                "symbol": "300059",
                "market": "A",
                "matched_strategy_ids": ["qvm"],
                "summary": {
                    "case_count": 4,
                    "win_rate": 0.25,
                    "average_return": -0.03,
                    "average_max_drawdown": -0.08,
                    "best_return": 0.05,
                    "worst_return": -0.1,
                },
            },
            {
                "symbol": "VRTX",
                "market": "US",
                "matched_strategy_ids": ["growth_breakout"],
                "summary": {"case_count": 4, "win_rate": 1.0, "average_return": 0.2},
            },
        ],
    }


def test_source_hypothesis_evaluation_is_proxy_only_and_per_hypothesis():
    report = evaluator.build_report(_queue(), _cases(), run_id="unit", command="unit")

    assert report["status"] == "PASS"
    assert report["summary"]["hypothesis_count"] == 2
    assert report["checks"]["all_hypotheses_evaluated"] is True
    assert report["checks"]["feature_history_limitation_explicit"] is True
    assert report["safety"]["requires_deep_source_specific_sandbox_before_ranking"] is True
    assert report["items"][0]["eligible_symbols"] == ["603893"]
    assert report["items"][0]["disposition"] == "needs_more_a_share_cases"
    assert report["items"][1]["eligible_symbols"] == ["300059"]
    assert report["items"][1]["disposition"] == "proxy_fail"
    assert all(item["user_facing_suggestion_allowed"] is False for item in report["items"])


def test_source_hypothesis_evaluation_cli_writes_reports_without_secret(tmp_path: Path, capsys):
    queue_json = tmp_path / "queue.json"
    cases_json = tmp_path / "cases.json"
    queue_json.write_text(json.dumps(_queue(), ensure_ascii=False), encoding="utf-8")
    cases_json.write_text(json.dumps(_cases(), ensure_ascii=False), encoding="utf-8")

    old_reports = evaluator.REPORTS
    old_processed = evaluator.PROCESSED
    old_out_json = evaluator.OUT_JSON
    old_out_md = evaluator.OUT_MD
    old_pass = evaluator.PASS_MARKER
    old_fail = evaluator.FAIL_MARKER
    try:
        evaluator.REPORTS = tmp_path / "reports"
        evaluator.PROCESSED = tmp_path / "processed"
        evaluator.OUT_JSON = evaluator.REPORTS / "a_share_tushare_source_hypothesis_evaluation_latest.json"
        evaluator.OUT_MD = evaluator.REPORTS / "a_share_tushare_source_hypothesis_evaluation_latest.md"
        evaluator.PASS_MARKER = evaluator.REPORTS / "A_SHARE_TUSHARE_SOURCE_HYPOTHESIS_EVALUATION_PASS.marker"
        evaluator.FAIL_MARKER = evaluator.REPORTS / "A_SHARE_TUSHARE_SOURCE_HYPOTHESIS_EVALUATION_FAIL.marker"
        exit_code = evaluator.main(["--queue-json", str(queue_json), "--cases-json", str(cases_json), "--run-id", "unit"])
        captured = capsys.readouterr()
    finally:
        evaluator.REPORTS = old_reports
        evaluator.PROCESSED = old_processed
        evaluator.OUT_JSON = old_out_json
        evaluator.OUT_MD = old_out_md
        evaluator.PASS_MARKER = old_pass
        evaluator.FAIL_MARKER = old_fail

    assert exit_code == 0
    assert "PASS" in captured.out
    assert "secret" not in captured.out.lower()
    assert "token" not in captured.out.lower()
    assert (tmp_path / "reports" / "A_SHARE_TUSHARE_SOURCE_HYPOTHESIS_EVALUATION_PASS.marker").exists()
