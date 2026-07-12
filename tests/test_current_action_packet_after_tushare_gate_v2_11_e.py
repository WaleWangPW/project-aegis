from __future__ import annotations

import json
from pathlib import Path

from aegis.paper.action_packet_after_tushare_gate import (
    build_action_packet_after_tushare_gate,
    render_action_packet_after_tushare_gate_markdown,
)
import scripts.validate_v2_11_e_current_action_packet_after_tushare_gate as validator


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
                "strategy_id": "strategy_a_low_vol_dividend_defensive",
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
                "strategy_id": "strategy_h_low_vol_dividend",
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
                "strategy_id": "strategy_us_value_quality_momentum",
                "candidate_score": 0.76,
                "source_mode": "approved_fixture_not_live_market_data",
                "why": ["sandbox_status=PASS"],
                "risk_warnings": ["No live price."],
                "evidence_ref_count": 3,
            },
        ],
        "blocked_paths": [
            {
                "symbol": "A_VALUE_QUALITY_PAPER_BASKET",
                "market": "A",
                "strategy_id": "strategy_a_value_quality_multifactor",
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


def _tushare_gate() -> dict:
    return {
        "overall_status": "PASS",
        "acceptance_target": "V2.11-D Tushare-Backed A-Share Suggestion Gate Refresh",
        "network_used": False,
        "production_records_written": False,
        "dashboard_contract_changed": False,
        "summary": {"allowed_count": 0, "blocked_count": 2},
        "suggestions": [
            {
                "suggestion_id": "sug_a_low",
                "strategy_id": "strategy_a_low_vol_dividend_defensive",
                "symbol": "STRATEGY_A_LOW_VOL_DIVIDEND_DEFENSIVE_TUSHARE_SANDBOX_BASKET",
                "market": "A",
                "action": "blocked",
                "blocked_by": ["strategy_sandbox_not_passed"],
                "reasons": ["tushare_sandbox_status=FAIL"],
                "risk_warnings": ["No live price, position size, broker execution, webhook, or order is produced."],
                "evidence_refs": ["v2_11_c.json", "v2_11_c.marker"],
                "simulation_only": True,
            },
            {
                "suggestion_id": "sug_a_value",
                "strategy_id": "strategy_a_value_quality_multifactor",
                "symbol": "STRATEGY_A_VALUE_QUALITY_MULTIFACTOR_TUSHARE_SANDBOX_BASKET",
                "market": "A",
                "action": "blocked",
                "blocked_by": ["strategy_sandbox_not_passed"],
                "reasons": ["tushare_sandbox_status=FAIL"],
                "risk_warnings": ["No live price, position size, broker execution, webhook, or order is produced."],
                "evidence_refs": ["v2_11_c.json", "v2_11_c.marker"],
                "simulation_only": True,
            },
        ],
    }


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def test_v2_11_e_removes_blocked_a_share_focus_and_keeps_h_us_focus():
    packet = build_action_packet_after_tushare_gate(
        current_brief=_current_brief(),
        api_backed_brief=_api_backed_brief(),
        tushare_gate_report=_tushare_gate(),
        run_id="unit",
        generated_at="2026-07-11T00:00:00+08:00",
    )

    focus_symbols = {item["symbol"] for item in packet["today_focus"]}
    blocked_strategy_ids = {item["strategy_id"] for item in packet["do_not_use"]}

    assert packet["overall_status"] == "PASS"
    assert "600519.SH" not in focus_symbols
    assert {"00700.HK", "MSFT"}.issubset(focus_symbols)
    assert "strategy_a_low_vol_dividend_defensive" in blocked_strategy_ids
    assert packet["summary"]["removed_focus_count"] == 1
    assert packet["checks"]["blocked_a_strategies_removed_from_focus"] is True
    assert packet["checks"]["non_a_focus_still_visible"] is True
    assert packet["safety"]["tushare_blocked_a_share_strategies_not_in_focus"] is True


def test_v2_11_e_markdown_keeps_do_not_use_visible():
    packet = build_action_packet_after_tushare_gate(
        current_brief=_current_brief(),
        api_backed_brief=_api_backed_brief(),
        tushare_gate_report=_tushare_gate(),
        run_id="unit",
    )
    md = render_action_packet_after_tushare_gate_markdown(packet)

    assert "Project Aegis Simulation Action Packet" in md
    assert "Do Not Use" in md
    assert "STRATEGY_A_LOW_VOL_DIVIDEND_DEFENSIVE_TUSHARE_SANDBOX_BASKET" in md
    assert "600519.SH" not in "\n".join(line for line in md.splitlines() if line.startswith("###"))


def test_v2_11_e_validator_writes_packet_without_record_mutation(tmp_path: Path):
    current = tmp_path / "current.json"
    api = tmp_path / "api.json"
    gate = tmp_path / "gate.json"
    _write_json(current, _current_brief())
    _write_json(api, _api_backed_brief())
    _write_json(gate, _tushare_gate())
    record_path = tmp_path / "records" / "paper_trades.jsonl"
    record_path.parent.mkdir()
    record_path.write_text("existing\n", encoding="utf-8")

    report = validator.run_acceptance(
        output_root=tmp_path / "processed",
        reports_dir=tmp_path / "reports",
        run_id="v2_11_e_test",
        command="test command",
        current_brief_json=current,
        api_backed_brief_json=api,
        tushare_gate_json=gate,
        record_paths={"paper_trades_jsonl": record_path},
    )

    assert report["overall_status"] == "PASS"
    assert report["checks"]["packet_json_written"] is True
    assert report["checks"]["production_record_files_unchanged"] is True
    assert record_path.read_text(encoding="utf-8") == "existing\n"
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()


def test_v2_11_e_cli_exits_zero_and_prints_no_secret_values(tmp_path: Path, capsys):
    current = tmp_path / "current.json"
    api = tmp_path / "api.json"
    gate = tmp_path / "gate.json"
    _write_json(current, _current_brief())
    _write_json(api, _api_backed_brief())
    _write_json(gate, _tushare_gate())

    exit_code = validator.main(
        [
            "--output-root",
            str(tmp_path / "processed"),
            "--reports-dir",
            str(tmp_path / "reports"),
            "--run-id",
            "v2_11_e_cli",
            "--current-brief-json",
            str(current),
            "--api-backed-brief-json",
            str(api),
            "--tushare-gate-json",
            str(gate),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "PASS" in captured.out
    assert "token" not in captured.out.lower()
    assert "secret" not in captured.out.lower()
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()
