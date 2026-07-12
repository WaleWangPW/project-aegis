from __future__ import annotations

import json
from pathlib import Path

from aegis.strategy.h_us_current_simulation_brief import (
    build_h_us_current_simulation_brief,
    render_h_us_current_simulation_brief_markdown,
)
import scripts.validate_v2_12_f_h_us_current_simulation_brief as validator


def _gate_report() -> dict:
    return {
        "overall_status": "PASS",
        "acceptance_target": "V2.12-E H-US Suggestion Gate Refresh From Sandbox Evidence",
        "network_used": False,
        "production_records_written": False,
        "dashboard_contract_changed": False,
        "summary": {
            "allowed_count": 2,
            "blocked_count": 0,
            "user_facing_simulation_brief_allowed": True,
        },
        "suggestions": [
            {
                "suggestion_id": "sug_h",
                "strategy_id": "strategy_h_cache_readiness_multifactor_probe",
                "symbol": "H_API_SANDBOX_PAPER_BASKET",
                "market": "H",
                "action": "paper_entry_candidate",
                "simulation_only": True,
                "user_must_execute_externally": True,
                "reasons": [
                    "h_us_sandbox_status=PASS",
                    "sample_count=1",
                    "win_rate=1.0000",
                    "average_return=0.1130",
                    "max_drawdown=-0.0112",
                    "historical_symbols=00700.HK",
                ],
                "risk_warnings": [
                    "Preliminary H/US API-backed sandbox sample only; sample size is too small.",
                    "Manual external execution only.",
                    "No live price, position size, trading webhook, broker execution, or order is produced.",
                ],
                "evidence_refs": ["v2_12_c_normalized_cache:h_00700:hash"],
                "blocked_by": [],
            },
            {
                "suggestion_id": "sug_us",
                "strategy_id": "strategy_us_cache_readiness_multifactor_probe",
                "symbol": "US_API_SANDBOX_PAPER_BASKET",
                "market": "US",
                "action": "paper_entry_candidate",
                "simulation_only": True,
                "user_must_execute_externally": True,
                "reasons": [
                    "h_us_sandbox_status=PASS",
                    "sample_count=2",
                    "win_rate=1.0000",
                    "average_return=0.0365",
                    "max_drawdown=-0.0181",
                    "historical_symbols=AAPL.US",
                ],
                "risk_warnings": [
                    "Preliminary H/US API-backed sandbox sample only; sample size is too small.",
                    "Manual external execution only.",
                    "No live price, position size, trading webhook, broker execution, or order is produced.",
                ],
                "evidence_refs": ["v2_12_c_normalized_cache:us_aapl:hash"],
                "blocked_by": [],
            },
        ],
    }


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def test_v2_12_f_builds_user_readable_h_us_brief():
    brief = build_h_us_current_simulation_brief(
        _gate_report(),
        run_id="v2_12_f_unit",
        generated_at="2026-07-12T00:00:00+08:00",
    )

    assert brief["overall_status"] == "PASS"
    assert brief["summary"]["candidate_count"] == 2
    assert brief["summary"]["candidate_markets"] == ["H", "US"]
    assert brief["checks"]["has_h_us_simulation_candidates"] is True
    assert brief["checks"]["sample_size_warning_visible"] is True
    assert brief["checks"]["manual_external_execution_only"] is True
    assert all(item["brief_status"] == "simulation_candidate" for item in brief["items"])
    assert all(item["no_order_placement"] is True for item in brief["items"])
    assert "simulation-only" in brief["current_answer"]["usable_suggestions_status"]


def test_v2_12_f_markdown_is_chinese_and_boundary_explicit():
    brief = build_h_us_current_simulation_brief(_gate_report(), run_id="v2_12_f_unit")

    md = render_h_us_current_simulation_brief_markdown(brief)

    assert "Project Aegis H/US 当前模拟建议简报" in md
    assert "H_API_SANDBOX_PAPER_BASKET" in md
    assert "US_API_SANDBOX_PAPER_BASKET" in md
    assert "不含实时价格" in md
    assert "不接券商" in md
    assert "不下单" in md


def test_v2_12_f_fails_if_source_does_not_allow_user_facing_brief():
    source = _gate_report()
    source["summary"]["user_facing_simulation_brief_allowed"] = False

    brief = build_h_us_current_simulation_brief(source, run_id="v2_12_f_unit_fail")

    assert brief["overall_status"] == "FAIL"
    assert brief["checks"]["source_allows_user_facing_simulation_brief"] is False


def test_v2_12_f_validator_writes_brief_marker_and_preserves_records(tmp_path: Path):
    source_json = tmp_path / "v2_12_e.json"
    marker = tmp_path / "v2_12_e.marker"
    _write_json(source_json, _gate_report())
    marker.write_text("exit_code=0\n", encoding="utf-8")
    record = tmp_path / "records" / "recommendations.jsonl"
    record.parent.mkdir()
    record.write_text("existing\n", encoding="utf-8")

    report = validator.run_acceptance(
        output_root=tmp_path / "processed",
        reports_dir=tmp_path / "reports",
        run_id="v2_12_f_test",
        command="test command",
        source_v2_12_e_report_json=source_json,
        source_v2_12_e_pass_marker=marker,
        record_paths={"recommendations_jsonl": record},
    )

    assert report["overall_status"] == "PASS"
    assert report["checks"]["brief_json_written"] is True
    assert report["checks"]["brief_md_written"] is True
    assert report["checks"]["production_record_files_unchanged"] is True
    assert report["hashes"]["brief_json"]
    assert record.read_text(encoding="utf-8") == "existing\n"
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()


def test_v2_12_f_cli_exits_zero_and_prints_no_secret_values(tmp_path: Path, capsys):
    source_json = tmp_path / "v2_12_e.json"
    marker = tmp_path / "v2_12_e.marker"
    _write_json(source_json, _gate_report())
    marker.write_text("exit_code=0\n", encoding="utf-8")

    exit_code = validator.main(
        [
            "--output-root",
            str(tmp_path / "processed"),
            "--reports-dir",
            str(tmp_path / "reports"),
            "--run-id",
            "v2_12_f_cli",
            "--source-v2-12-e-report-json",
            str(source_json),
            "--source-v2-12-e-pass-marker",
            str(marker),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "PASS" in captured.out
    assert "token" not in captured.out.lower()
    assert "secret" not in captured.out.lower()
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()
