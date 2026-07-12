from __future__ import annotations

import json
from pathlib import Path

import scripts.plan_a_share_strategy_sample_expansion as plan


def _ranking_gate() -> dict:
    return {
        "status": "PASS",
        "items": [
            {
                "refined_strategy_id": "refined_a_moneyflow_holder_concentration",
                "label": "主力资金 + 筹码集中",
                "ranking_gate_disposition": "RANKING_GATE_BLOCKED",
                "ranking_gate_blockers": [
                    "ranking_gate_case_count_below_threshold",
                    "ranking_gate_unique_symbol_count_below_threshold",
                    "ranking_gate_single_symbol_concentration_too_high",
                    "ranking_gate_entry_month_coverage_below_threshold",
                ],
                "observations": {
                    "case_count": 3,
                    "unique_symbol_count": 2,
                    "entry_month_count": 2,
                    "max_single_symbol_case_share": 2 / 3,
                },
            }
        ],
    }


def _dragon_tiger() -> dict:
    return {
        "summary": {
            "sample_count": 12,
            "event_count": 24,
            "queried_trade_date_count": 45,
            "eligible_cache_date_start": "2024-04-26",
            "eligible_cache_date_end": "2024-07-03",
        }
    }


def _historical_cases() -> dict:
    return {"summary": {"a_share_dragon_tiger_research_sample_case_count": 22}}


def test_expansion_plan_turns_gate_blockers_into_stock_agent_tasks():
    report = plan.build_report(_ranking_gate(), _dragon_tiger(), _historical_cases(), run_id="unit", command="unit")

    assert report["status"] == "PASS"
    assert report["summary"]["expansion_task_count"] == 1
    assert report["summary"]["next_lookback_dates"] == 90
    assert report["summary"]["next_max_symbols"] == 24
    assert report["summary"]["network_used"] is False
    assert report["summary"]["ranking_impact_allowed"] is False
    task = report["tasks"][0]
    assert "--lookback-dates 90" in task["recommended_collect_command"]
    assert "--max-symbols 24" in task["recommended_collect_command"]
    assert {item["task"] for item in task["shortfalls"]} == {
        "increase_case_count",
        "increase_unique_symbol_coverage",
        "reduce_single_symbol_concentration",
        "increase_entry_month_coverage",
    }
    assert task["user_facing_suggestion_allowed"] is False


def test_expansion_plan_cli_writes_outputs_without_network(tmp_path: Path, capsys, monkeypatch):
    ranking_gate = tmp_path / "ranking_gate.json"
    dragon_tiger = tmp_path / "dragon_tiger.json"
    historical_cases = tmp_path / "historical_cases.json"
    ranking_gate.write_text(json.dumps(_ranking_gate(), ensure_ascii=False), encoding="utf-8")
    dragon_tiger.write_text(json.dumps(_dragon_tiger(), ensure_ascii=False), encoding="utf-8")
    historical_cases.write_text(json.dumps(_historical_cases(), ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(plan, "daily_cache_dates", lambda: [f"202401{day:02d}" for day in range(1, 32)] + [f"202402{day:02d}" for day in range(1, 29)] + [f"202403{day:02d}" for day in range(1, 32)] + [f"202404{day:02d}" for day in range(1, 31)])

    old_reports = plan.REPORTS
    old_processed = plan.PROCESSED
    old_out_json = plan.OUT_JSON
    old_out_md = plan.OUT_MD
    old_pass = plan.PASS_MARKER
    old_blocked = plan.BLOCKED_MARKER
    try:
        plan.REPORTS = tmp_path / "reports"
        plan.PROCESSED = tmp_path / "processed"
        plan.OUT_JSON = plan.REPORTS / "a_share_strategy_sample_expansion_plan_latest.json"
        plan.OUT_MD = plan.REPORTS / "a_share_strategy_sample_expansion_plan_latest.md"
        plan.PASS_MARKER = plan.REPORTS / "A_SHARE_STRATEGY_SAMPLE_EXPANSION_PLAN_PASS.marker"
        plan.BLOCKED_MARKER = plan.REPORTS / "A_SHARE_STRATEGY_SAMPLE_EXPANSION_PLAN_BLOCKED.marker"
        exit_code = plan.main(
            [
                "--ranking-gate-json",
                str(ranking_gate),
                "--dragon-tiger-json",
                str(dragon_tiger),
                "--historical-cases-json",
                str(historical_cases),
                "--run-id",
                "unit",
            ]
        )
        captured = capsys.readouterr()
    finally:
        plan.REPORTS = old_reports
        plan.PROCESSED = old_processed
        plan.OUT_JSON = old_out_json
        plan.OUT_MD = old_out_md
        plan.PASS_MARKER = old_pass
        plan.BLOCKED_MARKER = old_blocked

    assert exit_code == 0
    assert "PASS" in captured.out
    payload = json.loads((tmp_path / "reports" / "a_share_strategy_sample_expansion_plan_latest.json").read_text())
    assert payload["checks"]["network_not_used"] is True
    assert payload["summary"]["expansion_task_count"] == 1
    assert (tmp_path / "reports" / "A_SHARE_STRATEGY_SAMPLE_EXPANSION_PLAN_PASS.marker").exists()
