from __future__ import annotations

import json
from pathlib import Path

from aegis.paper.simulation_action_packet import (
    build_simulation_action_packet,
    render_simulation_action_packet_markdown,
)
import scripts.validate_v2_11_a_simulation_suggestion_action_packet as validator


def _current_brief() -> dict:
    return {
        "overall_status": "PASS",
        "network_used": False,
        "production_records_written": False,
        "dashboard_contract_changed": False,
        "summary": {
            "candidate_markets": ["A", "H", "US"],
            "real_user_api_status": "blocked_missing_metadata",
            "sandbox_pass_count": 3,
            "sandbox_fail_count": 3,
        },
        "top_candidates": [
            {
                "symbol": "600519.SH",
                "name": "贵州茅台",
                "market": "A",
                "strategy_id": "strategy_a",
                "candidate_score": 0.95,
                "source_mode": "approved_fixture_not_live_market_data",
                "why": ["sandbox_status=PASS"],
                "risk_warnings": ["No live price."],
                "evidence_ref_count": 3,
            },
            {
                "symbol": "00700.HK",
                "name": "Tencent",
                "market": "H",
                "strategy_id": "strategy_h",
                "candidate_score": 0.82,
                "source_mode": "approved_fixture_not_live_market_data",
                "why": ["sandbox_status=PASS"],
                "risk_warnings": ["No live price."],
                "evidence_ref_count": 3,
            },
            {
                "symbol": "MSFT",
                "name": "Microsoft",
                "market": "US",
                "strategy_id": "strategy_us",
                "candidate_score": 0.76,
                "source_mode": "approved_fixture_not_live_market_data",
                "why": ["sandbox_status=PASS"],
                "risk_warnings": ["No live price."],
                "evidence_ref_count": 3,
            },
        ],
        "blocked_paths": [
            {
                "symbol": "A_BLOCKED",
                "market": "A",
                "strategy_id": "strategy_a_blocked",
                "blocked_by": ["strategy_sandbox_not_passed"],
                "why": ["sandbox_status=FAIL"],
            },
            {
                "symbol": "H_BLOCKED",
                "market": "H",
                "strategy_id": "strategy_h_blocked",
                "blocked_by": ["strategy_sandbox_not_passed"],
                "why": ["sandbox_status=FAIL"],
            },
            {
                "symbol": "US_BLOCKED",
                "market": "US",
                "strategy_id": "strategy_us_blocked",
                "blocked_by": ["strategy_sandbox_not_passed"],
                "why": ["sandbox_status=FAIL"],
            },
        ],
        "review_memory_queue": [
            {
                "paper_trade_id": "ptr_600519",
                "review_id": "rev_600519",
                "outcome": "pending",
                "decision_quality": "unclear",
                "no_return_fabrication": True,
                "simulation_only": True,
            }
        ],
    }


def _api_backed_brief() -> dict:
    return {
        "overall_status": "PASS",
        "brief_status": "blocked_missing_real_api_artifacts",
        "network_used": False,
        "production_records_written": False,
        "dashboard_contract_changed": False,
    }


def test_v2_11_a_builds_daily_action_packet():
    packet = build_simulation_action_packet(
        current_brief=_current_brief(),
        api_backed_brief=_api_backed_brief(),
        run_id="unit",
        generated_at="2026-07-11T00:00:00+08:00",
    )

    assert packet["overall_status"] == "PASS"
    assert packet["acceptance_target"] == "V2.11-A Simulation Suggestion Action Packet"
    assert packet["summary"]["today_focus_count"] == 3
    assert packet["summary"]["blocked_count"] == 3
    assert packet["summary"]["api_backed_brief_status"] == "blocked_missing_real_api_artifacts"
    assert packet["checks"]["has_a_h_us_focus"] is True
    assert packet["checks"]["api_blocker_visible"] is True
    assert packet["checks"]["no_api_backed_claim_without_artifacts"] is True
    assert packet["safety"]["no_broker_api"] is True


def test_v2_11_a_markdown_is_user_readable_and_boundary_explicit():
    packet = build_simulation_action_packet(
        current_brief=_current_brief(),
        api_backed_brief=_api_backed_brief(),
        run_id="unit",
    )

    md = render_simulation_action_packet_markdown(packet)

    assert "Project Aegis Simulation Action Packet" in md
    assert "600519.SH" in md
    assert "Do Not Use" in md
    assert "不做真实交易" in md
    assert "不接 Broker API" in md


def test_v2_11_a_validator_writes_packet_without_records_mutation(tmp_path: Path):
    current = tmp_path / "current.json"
    api = tmp_path / "api.json"
    current.write_text(json.dumps(_current_brief(), ensure_ascii=False), encoding="utf-8")
    api.write_text(json.dumps(_api_backed_brief(), ensure_ascii=False), encoding="utf-8")
    record_path = tmp_path / "records" / "paper_trades.jsonl"
    record_path.parent.mkdir()
    record_path.write_text("existing\n", encoding="utf-8")

    report = validator.run_acceptance(
        output_root=tmp_path / "processed",
        reports_dir=tmp_path / "reports",
        run_id="v2_11_a_test",
        command="test command",
        current_brief_json=current,
        api_backed_brief_json=api,
        record_paths={"paper_trades_jsonl": record_path},
    )

    assert report["overall_status"] == "PASS"
    assert report["checks"]["packet_json_written"] is True
    assert report["checks"]["production_record_files_unchanged"] is True
    assert record_path.read_text(encoding="utf-8") == "existing\n"
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()


def test_v2_11_a_cli_exits_zero(tmp_path: Path, capsys):
    current = tmp_path / "current.json"
    api = tmp_path / "api.json"
    current.write_text(json.dumps(_current_brief(), ensure_ascii=False), encoding="utf-8")
    api.write_text(json.dumps(_api_backed_brief(), ensure_ascii=False), encoding="utf-8")

    exit_code = validator.main(
        [
            "--output-root",
            str(tmp_path / "processed"),
            "--reports-dir",
            str(tmp_path / "reports"),
            "--run-id",
            "v2_11_a_cli",
            "--current-brief-json",
            str(current),
            "--api-backed-brief-json",
            str(api),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "PASS" in captured.out
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()
