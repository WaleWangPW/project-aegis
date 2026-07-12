from __future__ import annotations

import json
from pathlib import Path

from aegis.strategy.h_us_suggestion_gate_refresh import (
    build_h_us_suggestion_gate_report,
    build_h_us_suggestion_opportunities,
)
import scripts.validate_v2_12_e_h_us_suggestion_gate_refresh as validator


def _source_report() -> dict:
    return {
        "overall_status": "PASS",
        "acceptance_target": "V2.12-D H-US Historical Sandbox Candidate Refresh Dry Run",
        "production_records_written": False,
        "dashboard_contract_changed": False,
        "summary": {
            "candidate_count": 2,
            "historical_case_count": 3,
            "strategy_pass_count": 2,
            "strategy_fail_count": 0,
            "markets_with_cases": ["H", "US"],
            "preliminary_only": True,
            "user_facing_suggestion_allowed": False,
            "next_stage": "V2.12-E H-US Suggestion Gate Refresh From Sandbox Evidence",
        },
        "safety": {
            "preliminary_sample_only": True,
            "simulation_only": True,
            "suggestion_gate_required": True,
            "no_real_trade": True,
            "no_broker_api": True,
            "no_webhook": True,
        },
        "candidates": [
            {
                "strategy_id": "strategy_h_cache_readiness_multifactor_probe",
                "name": "H-share cache-readiness multifactor sandbox probe",
                "market": "H",
                "risk_controls": [
                    "manual_execution_only",
                    "sample_size_warning",
                    "suggestion_gate_required",
                ],
            },
            {
                "strategy_id": "strategy_us_cache_readiness_multifactor_probe",
                "name": "U.S. cache-readiness multifactor sandbox probe",
                "market": "US",
                "risk_controls": [
                    "manual_execution_only",
                    "sample_size_warning",
                    "suggestion_gate_required",
                ],
            },
        ],
        "historical_cases": [
            {
                "strategy_id": "strategy_h_cache_readiness_multifactor_probe",
                "symbol": "00700.HK",
                "evidence_ref": "v2_12_c_normalized_cache:h_00700_eodhd_daily_bars:hash",
            },
            {
                "strategy_id": "strategy_us_cache_readiness_multifactor_probe",
                "symbol": "AAPL.US",
                "evidence_ref": "v2_12_c_normalized_cache:us_aapl_eodhd_daily_bars:hash",
            },
            {
                "strategy_id": "strategy_us_cache_readiness_multifactor_probe",
                "symbol": "AAPL.US",
                "evidence_ref": "v2_12_c_normalized_cache:us_aapl_twelve_data_daily_bars:hash",
            },
        ],
        "results": [
            {
                "strategy_id": "strategy_h_cache_readiness_multifactor_probe",
                "status": "PASS",
                "metrics": {
                    "sample_count": 1,
                    "win_rate": 1.0,
                    "average_return": 0.11297071129707119,
                    "max_drawdown": -0.01115760111576014,
                    "failed_reasons": [],
                },
            },
            {
                "strategy_id": "strategy_us_cache_readiness_multifactor_probe",
                "status": "PASS",
                "metrics": {
                    "sample_count": 2,
                    "win_rate": 1.0,
                    "average_return": 0.036542036961483615,
                    "max_drawdown": -0.01810273140152252,
                    "failed_reasons": [],
                },
            },
        ],
    }


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def test_v2_12_e_builds_h_us_opportunities_from_sandbox_passes():
    opportunities = build_h_us_suggestion_opportunities(
        _source_report(),
        evidence_refs=["source-report.json", "pass.marker"],
    )

    assert len(opportunities) == 2
    assert {item.market for item in opportunities} == {"H", "US"}
    assert {item.symbol for item in opportunities} == {
        "H_API_SANDBOX_PAPER_BASKET",
        "US_API_SANDBOX_PAPER_BASKET",
    }
    assert all(item.evidence_refs for item in opportunities)
    assert all("sample size" in " ".join(item.risk_warnings).lower() for item in opportunities)


def test_v2_12_e_all_passing_h_us_strategies_become_simulation_only_drafts():
    report = build_h_us_suggestion_gate_report(
        _source_report(),
        run_id="v2_12_e_unit",
        evidence_refs=["source-report.json", "pass.marker"],
        command="unit test",
        generated_at="2026-07-12T00:00:00+08:00",
    )

    assert report["overall_status"] == "PASS"
    assert report["summary"]["allowed_count"] == 2
    assert report["summary"]["blocked_count"] == 0
    assert report["checks"]["allowed_suggestions_present"] is True
    assert report["checks"]["sample_size_warning_visible"] is True
    assert report["checks"]["cache_case_evidence_refs_present"] is True
    assert all(item["action"] == "paper_entry_candidate" for item in report["suggestions"])
    assert all(item["simulation_only"] for item in report["suggestions"])
    assert all(item["user_must_execute_externally"] for item in report["suggestions"])
    assert report["safety"]["no_order_placement"] is True
    assert report["safety"]["not_real_trade_advice"] is True


def test_v2_12_e_fails_if_source_was_not_preliminary_blocked_by_gate():
    source = _source_report()
    source["summary"]["user_facing_suggestion_allowed"] = True

    report = build_h_us_suggestion_gate_report(
        source,
        run_id="v2_12_e_unit_fail",
        evidence_refs=["source-report.json"],
    )

    assert report["overall_status"] == "FAIL"
    assert report["checks"]["source_user_facing_suggestion_was_blocked"] is False


def test_v2_12_e_validator_writes_reports_marker_and_hashes(tmp_path: Path):
    source_json = tmp_path / "v2_12_d.json"
    marker = tmp_path / "v2_12_d.marker"
    _write_json(source_json, _source_report())
    marker.write_text("exit_code=0\n", encoding="utf-8")

    report = validator.run_acceptance(
        output_root=tmp_path / "processed",
        reports_dir=tmp_path / "reports",
        run_id="v2_12_e_test",
        command="test command",
        source_v2_12_d_report_json=source_json,
        source_v2_12_d_pass_marker=marker,
    )

    assert report["overall_status"] == "PASS"
    assert report["summary"]["allowed_count"] == 2
    assert report["summary"]["blocked_count"] == 0
    assert report["checks"]["suggestions_json_written"] is True
    assert report["hashes"]["suggestions_json"]
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()


def test_v2_12_e_cli_exits_zero_and_prints_no_secret_values(tmp_path: Path, capsys):
    source_json = tmp_path / "v2_12_d.json"
    marker = tmp_path / "v2_12_d.marker"
    _write_json(source_json, _source_report())
    marker.write_text("exit_code=0\n", encoding="utf-8")

    exit_code = validator.main(
        [
            "--output-root",
            str(tmp_path / "processed"),
            "--reports-dir",
            str(tmp_path / "reports"),
            "--run-id",
            "v2_12_e_cli",
            "--source-v2-12-d-report-json",
            str(source_json),
            "--source-v2-12-d-pass-marker",
            str(marker),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "PASS" in captured.out
    assert "token" not in captured.out.lower()
    assert "secret" not in captured.out.lower()
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()
