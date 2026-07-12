from __future__ import annotations

import json
from pathlib import Path

import scripts.review_a_share_refined_strategy_ranking_gate as gate


def _case(case_id: str, symbol: str, entry_date: str, raw_return: float, max_drawdown: float) -> dict:
    return {
        "case_id": case_id,
        "symbol": symbol,
        "entry_date": entry_date,
        "raw_return": raw_return,
        "max_drawdown": max_drawdown,
    }


def _refined_item(cases: list[dict]) -> dict:
    return {
        "refined_strategy_id": "refined_a_moneyflow_holder_concentration",
        "label": "主力资金 + 筹码集中",
        "disposition": "REFINED_SANDBOX_PASS_CANDIDATE",
        "metrics": {
            "refined_signal_case_count": len(cases),
            "refined_signal_win_rate": sum(1 for case in cases if case["raw_return"] > 0) / len(cases),
            "refined_signal_average_return": sum(case["raw_return"] for case in cases) / len(cases),
            "refined_signal_max_drawdown": min(case["max_drawdown"] for case in cases),
        },
        "case_features": cases,
    }


def test_ranking_gate_blocks_small_concentrated_refined_candidate():
    refined_report = {
        "status": "PASS",
        "items": [
            _refined_item(
                [
                    _case("aegis_case_600150_stock_selection_workbench_2", "600150", "2023-12-12", 0.01, -0.03),
                    _case("aegis_case_603863_tushare_dragon_tiger_hot_money_1", "603863", "2024-06-24", 0.13, -0.14),
                    _case("aegis_case_603863_tushare_dragon_tiger_hot_money_2", "603863", "2024-06-26", -0.01, -0.14),
                ]
            )
        ],
    }
    report = gate.build_report(refined_report, run_id="unit", command="unit")

    assert report["status"] == "PASS"
    assert report["summary"]["ranking_gate_reviewed_count"] == 1
    assert report["summary"]["ranking_gate_approved_count"] == 0
    assert report["summary"]["ranking_impact_allowed"] is False
    item = report["items"][0]
    assert item["ranking_gate_disposition"] == "RANKING_GATE_BLOCKED"
    assert "ranking_gate_case_count_below_threshold" in item["ranking_gate_blockers"]
    assert "ranking_gate_unique_symbol_count_below_threshold" in item["ranking_gate_blockers"]
    assert "ranking_gate_single_symbol_concentration_too_high" in item["ranking_gate_blockers"]
    assert item["user_facing_suggestion_allowed"] is False
    assert item["real_trade_allowed"] is False


def test_ranking_gate_can_approve_broad_simulation_sort_candidate():
    cases = [
        _case("aegis_case_000001_stock_selection_workbench_1", "000001", "2024-01-02", 0.05, -0.05),
        _case("aegis_case_000002_stock_selection_workbench_1", "000002", "2024-02-02", 0.04, -0.06),
        _case("aegis_case_000003_stock_selection_workbench_1", "000003", "2024-03-02", 0.03, -0.07),
        _case("aegis_case_000004_stock_selection_workbench_1", "000004", "2024-04-02", 0.05, -0.08),
        _case("aegis_case_000005_stock_selection_workbench_1", "000005", "2024-05-02", 0.04, -0.05),
        _case("aegis_case_000006_stock_selection_workbench_1", "000006", "2024-06-02", -0.01, -0.09),
    ]
    report = gate.build_report({"status": "PASS", "items": [_refined_item(cases)]}, run_id="unit", command="unit")

    assert report["summary"]["ranking_gate_approved_count"] == 1
    assert report["summary"]["ranking_impact_allowed"] is True
    assert report["items"][0]["ranking_gate_disposition"] == "RANKING_GATE_APPROVED_FOR_SIMULATION_SORT"
    assert report["items"][0]["user_facing_suggestion_allowed"] is False
    assert report["items"][0]["real_trade_allowed"] is False


def test_ranking_gate_cli_writes_outputs_without_network(tmp_path: Path, capsys):
    refined_json = tmp_path / "refined.json"
    refined_json.write_text(
        json.dumps(
            {
                "status": "PASS",
                "items": [
                    _refined_item(
                        [
                            _case("aegis_case_600150_stock_selection_workbench_2", "600150", "2023-12-12", 0.01, -0.03),
                            _case("aegis_case_603863_tushare_dragon_tiger_hot_money_1", "603863", "2024-06-24", 0.13, -0.14),
                            _case("aegis_case_603863_tushare_dragon_tiger_hot_money_2", "603863", "2024-06-26", -0.01, -0.14),
                        ]
                    )
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    old_reports = gate.REPORTS
    old_processed = gate.PROCESSED
    old_out_json = gate.OUT_JSON
    old_out_md = gate.OUT_MD
    old_pass = gate.PASS_MARKER
    old_blocked = gate.BLOCKED_MARKER
    try:
        gate.REPORTS = tmp_path / "reports"
        gate.PROCESSED = tmp_path / "processed"
        gate.OUT_JSON = gate.REPORTS / "a_share_refined_strategy_ranking_gate_latest.json"
        gate.OUT_MD = gate.REPORTS / "a_share_refined_strategy_ranking_gate_latest.md"
        gate.PASS_MARKER = gate.REPORTS / "A_SHARE_REFINED_STRATEGY_RANKING_GATE_PASS.marker"
        gate.BLOCKED_MARKER = gate.REPORTS / "A_SHARE_REFINED_STRATEGY_RANKING_GATE_BLOCKED.marker"
        exit_code = gate.main(["--refined-json", str(refined_json), "--run-id", "unit"])
        captured = capsys.readouterr()
    finally:
        gate.REPORTS = old_reports
        gate.PROCESSED = old_processed
        gate.OUT_JSON = old_out_json
        gate.OUT_MD = old_out_md
        gate.PASS_MARKER = old_pass
        gate.BLOCKED_MARKER = old_blocked

    assert exit_code == 0
    assert "PASS" in captured.out
    payload = json.loads((tmp_path / "reports" / "a_share_refined_strategy_ranking_gate_latest.json").read_text())
    assert payload["summary"]["network_used"] is False
    assert payload["checks"]["network_not_used"] is True
    assert payload["summary"]["ranking_gate_approved_count"] == 0
    assert (tmp_path / "reports" / "A_SHARE_REFINED_STRATEGY_RANKING_GATE_PASS.marker").exists()
