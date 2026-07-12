from __future__ import annotations

import json
from pathlib import Path

import scripts.validate_v2_1_c_suggestion_gate as validator
from aegis.strategy.suggestion_gate import build_suggestion_drafts, build_suggestion_gate_report


def test_suggestion_gate_allows_passed_strategy_and_blocks_failed_or_vetoed():
    sandbox_report = validator._fixture_sandbox_report()
    opportunities = validator._fixture_opportunities()

    drafts = build_suggestion_drafts(
        opportunities,
        sandbox_report,
        created_at="2026-07-11T00:00:00+08:00",
    )
    by_id = {draft.opportunity_id: draft for draft in drafts}

    assert by_id["opp_a_defensive_001"].action == "paper_entry_candidate"
    assert by_id["opp_a_defensive_001"].simulation_only is True
    assert by_id["opp_a_defensive_001"].user_must_execute_externally is True

    assert by_id["opp_us_raw_momentum_001"].action == "blocked"
    assert "strategy_sandbox_not_passed" in by_id["opp_us_raw_momentum_001"].blocked_by

    assert by_id["opp_a_risk_veto_001"].action == "blocked"
    assert "risk_veto_triggered" in by_id["opp_a_risk_veto_001"].blocked_by


def test_suggestion_gate_report_keeps_real_trading_forbidden():
    report = build_suggestion_gate_report(
        validator._fixture_opportunities(),
        validator._fixture_sandbox_report(),
        run_id="v2_1_c_unit",
        command="unit test",
    )

    assert report["overall_status"] == "PASS"
    assert report["summary"]["allowed_count"] == 1
    assert report["summary"]["blocked_count"] == 2
    assert report["safety"]["manual_external_execution_only"] is True
    assert report["safety"]["no_real_trade"] is True
    assert report["production_records_written"] is False


def test_v2_1_c_acceptance_writes_marker_hashes_and_reports(tmp_path: Path):
    report = validator.run_acceptance(
        output_root=tmp_path / "processed",
        reports_dir=tmp_path / "reports",
        run_id="v2_1_c_test",
        command="test command",
    )

    assert report["overall_status"] == "PASS"
    assert report["checks"]["at_least_one_allowed_draft"] is True
    assert report["checks"]["sandbox_failed_strategy_blocked"] is True
    assert report["checks"]["risk_veto_blocked"] is True
    assert report["checks"]["manual_execution_only"] is True
    assert report["production_records_written"] is False
    assert report["hashes"]["suggestions_json"]
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()
    payload = json.loads((tmp_path / "reports" / validator.REPORT_JSON).read_text(encoding="utf-8"))
    assert payload["summary"]["allowed_count"] == 1


def test_v2_1_c_cli_exits_zero_and_prints_no_secrets(tmp_path: Path, capsys):
    exit_code = validator.main(
        [
            "--output-root",
            str(tmp_path / "processed"),
            "--reports-dir",
            str(tmp_path / "reports"),
            "--run-id",
            "v2_1_c_cli",
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "PASS" in captured.out
    assert "token" not in captured.out.lower()
    assert "secret" not in captured.out.lower()
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()
