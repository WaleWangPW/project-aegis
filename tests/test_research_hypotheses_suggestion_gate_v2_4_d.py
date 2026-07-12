from __future__ import annotations

import json
from pathlib import Path

import scripts.validate_v2_4_c_historical_sandbox_research_hypotheses as v2_4_c
import scripts.validate_v2_4_d_research_hypotheses_suggestion_gate as validator
from aegis.strategy.hypothesis_suggestion import (
    build_hypothesis_suggestion_gate_report,
    build_hypothesis_suggestion_opportunities,
)


def _v2_4_c_fixture(tmp_path: Path) -> tuple[Path, Path, dict]:
    report = v2_4_c.run_acceptance(
        output_root=tmp_path / "v2_4_c_processed",
        reports_dir=tmp_path / "v2_4_c_reports",
        run_id="v2_4_c_for_v2_4_d",
        command="unit test v2.4-c",
    )
    return Path(report["source_hypothesis_queue_json"]), Path(report["hypothesis_sandbox_report_json"]), report


def test_hypothesis_suggestion_opportunities_cover_all_sandbox_results(tmp_path: Path):
    hypothesis_queue_json, sandbox_report_json, _ = _v2_4_c_fixture(tmp_path)
    hypotheses = validator._load_hypotheses(hypothesis_queue_json)
    sandbox_report = validator._load_json(sandbox_report_json)

    opportunities = build_hypothesis_suggestion_opportunities(
        hypotheses,
        sandbox_report,
        evidence_refs=["data/reports/v2_4_c_historical_sandbox_research_hypotheses_latest.json"],
    )

    assert len(opportunities) == 6
    assert {item.market for item in opportunities} == {"A", "H", "US"}
    assert all(item.evidence_refs for item in opportunities)
    assert all("PAPER_BASKET" in item.symbol for item in opportunities)


def test_hypothesis_suggestion_gate_allows_only_sandbox_passes(tmp_path: Path):
    hypothesis_queue_json, sandbox_report_json, sandbox_acceptance = _v2_4_c_fixture(tmp_path)
    hypotheses = validator._load_hypotheses(hypothesis_queue_json)
    sandbox_report = validator._load_json(sandbox_report_json)

    report = build_hypothesis_suggestion_gate_report(
        hypotheses,
        sandbox_report,
        run_id="v2_4_d_unit",
        evidence_refs=["data/reports/v2_4_c_historical_sandbox_research_hypotheses_latest.json"],
        command="unit test",
    )

    assert report["overall_status"] == "PASS"
    assert report["acceptance_target"] == "V2.4-D Research Hypotheses To Suggestion Gate Drafts"
    assert report["summary"]["allowed_count"] == sandbox_acceptance["summary"]["pass_count"]
    assert report["summary"]["blocked_count"] == sandbox_acceptance["summary"]["fail_count"]
    assert all(item["simulation_only"] for item in report["suggestions"])
    assert all(item["user_must_execute_externally"] for item in report["suggestions"])
    assert all(
        "strategy_sandbox_not_passed" in item["blocked_by"]
        for item in report["suggestions"]
        if item["action"] == "blocked"
    )
    assert report["safety"]["suggestion_drafts_not_orders"] is True
    assert report["production_records_written"] is False


def test_v2_4_d_acceptance_writes_reports_hashes_and_keeps_boundaries(tmp_path: Path):
    hypothesis_queue_json, sandbox_report_json, _ = _v2_4_c_fixture(tmp_path)

    report = validator.run_acceptance(
        output_root=tmp_path / "processed",
        reports_dir=tmp_path / "reports",
        run_id="v2_4_d_test",
        command="test command",
        hypothesis_queue_json=hypothesis_queue_json,
        sandbox_report_json=sandbox_report_json,
    )

    assert report["overall_status"] == "PASS"
    assert report["checks"]["allowed_count_matches_sandbox_pass"] is True
    assert report["checks"]["blocked_count_matches_sandbox_fail"] is True
    assert report["checks"]["blocked_failed_sandbox_hypotheses"] is True
    assert report["checks"]["manual_external_execution_only"] is True
    assert report["checks"]["no_real_trade_or_broker"] is True
    assert report["production_records_written"] is False
    assert report["dashboard_contract_changed"] is False
    assert report["hashes"]["suggestions_json"]
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()

    payload = json.loads((tmp_path / "reports" / validator.REPORT_JSON).read_text(encoding="utf-8"))
    assert payload["summary"]["allowed_count"] == 3
    assert payload["summary"]["blocked_count"] == 3


def test_v2_4_d_cli_exits_zero_and_prints_no_secret_values(tmp_path: Path, capsys):
    hypothesis_queue_json, sandbox_report_json, _ = _v2_4_c_fixture(tmp_path)

    exit_code = validator.main(
        [
            "--output-root",
            str(tmp_path / "processed"),
            "--reports-dir",
            str(tmp_path / "reports"),
            "--run-id",
            "v2_4_d_cli",
            "--hypothesis-queue-json",
            str(hypothesis_queue_json),
            "--sandbox-report-json",
            str(sandbox_report_json),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "PASS" in captured.out
    assert "token" not in captured.out.lower()
    assert "secret" not in captured.out.lower()
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()

