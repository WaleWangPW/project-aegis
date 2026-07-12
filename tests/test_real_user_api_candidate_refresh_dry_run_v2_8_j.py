from __future__ import annotations

import json
from pathlib import Path

import scripts.validate_v2_8_j_real_user_api_candidate_refresh_dry_run as validator


def _suggestions() -> list[dict]:
    return [
        {
            "suggestion_id": "sug_research_hyp_a_low_vol_dividend_defensive",
            "strategy_id": "strategy_a_low_vol_dividend_defensive",
            "market": "A",
            "action": "paper_entry_candidate",
            "evidence_refs": ["v2_8_e_report.json"],
            "blocked_by": [],
        },
        {
            "suggestion_id": "sug_research_hyp_h_low_vol_dividend",
            "strategy_id": "strategy_h_low_vol_dividend",
            "market": "H",
            "action": "paper_entry_candidate",
            "evidence_refs": ["v2_8_e_report.json"],
            "blocked_by": [],
        },
        {
            "suggestion_id": "sug_research_hyp_us_value_quality_momentum",
            "strategy_id": "strategy_us_value_quality_momentum",
            "market": "US",
            "action": "paper_entry_candidate",
            "evidence_refs": ["v2_8_e_report.json"],
            "blocked_by": [],
        },
    ]


def test_v2_8_j_candidate_refresh_dry_run_blocks_missing_metadata_without_fetch(tmp_path: Path):
    suggestions_json = tmp_path / "suggestions.json"
    suggestions_json.write_text(json.dumps(_suggestions(), ensure_ascii=False), encoding="utf-8")

    report = validator._run_candidate_refresh_dry_run(
        config_path=tmp_path / "missing-local.json",
        connector_id=validator.DEFAULT_CONNECTOR_ID,
        endpoint_path=validator.DEFAULT_ENDPOINT_PATH,
        query={"markets": "A,H,US", "purpose": "candidate_refresh"},
        output_root=tmp_path / "runs",
        run_id="missing",
        suggestion_drafts_json=suggestions_json,
        env={validator.DEFAULT_ENV_VAR: validator._FIXTURE_SECRET},
        fetch_fn=lambda *_args: (_ for _ in ()).throw(AssertionError("fetch must not run")),
    )

    assert report["overall_status"] == "BLOCKED"
    assert report["dry_run_status"] == "blocked_missing_metadata"
    assert report["api_fetch_item_json"] is None
    assert report["safety"]["activation_gate_before_fetch"] is True


def test_v2_8_j_candidate_refresh_dry_run_fixture_binds_a_h_us(tmp_path: Path):
    suggestions_json = tmp_path / "suggestions.json"
    suggestions_json.write_text(json.dumps(_suggestions(), ensure_ascii=False), encoding="utf-8")
    config = tmp_path / "external_api_connectors.local.fixture.json"
    validator._write_fixture_config(config)

    report = validator._run_candidate_refresh_dry_run(
        config_path=config,
        connector_id=validator.DEFAULT_CONNECTOR_ID,
        endpoint_path=validator.DEFAULT_ENDPOINT_PATH,
        query={"markets": "A,H,US", "purpose": "candidate_refresh"},
        output_root=tmp_path / "runs",
        run_id="fixture",
        suggestion_drafts_json=suggestions_json,
        env={validator.DEFAULT_ENV_VAR: validator._FIXTURE_SECRET},
        fetch_fn=validator._fixture_fetch,
    )
    report_text = json.dumps(report, ensure_ascii=False)

    assert report["overall_status"] == "PASS"
    assert set(report["refresh_summary"]["bound_markets"]) == {"A", "H", "US"}
    assert report["refresh_summary"]["bound_count"] == 3
    assert validator._FIXTURE_SECRET not in report_text
    assert "A,H,US" not in report_text
    assert Path(report["api_candidate_source_registry_json"]).exists()
    assert Path(report["api_candidate_bindings_json"]).exists()


def test_v2_8_j_acceptance_writes_blocked_real_user_status_and_no_secret(tmp_path: Path):
    suggestions_json = tmp_path / "suggestions.json"
    suggestions_json.write_text(json.dumps(_suggestions(), ensure_ascii=False), encoding="utf-8")

    report = validator.run_acceptance(
        output_root=tmp_path / "processed",
        reports_dir=tmp_path / "reports",
        run_id="v2_8_j_test",
        command="test command",
        real_config_path=tmp_path / "missing-local.json",
        suggestion_drafts_json=suggestions_json,
    )
    report_text = (tmp_path / "reports" / validator.REPORT_JSON).read_text(encoding="utf-8")

    assert report["overall_status"] == "PASS"
    assert report["checks"]["fixture_dry_run_completed"] is True
    assert report["checks"]["fixture_a_h_us_bound"] is True
    assert report["real_user_dry_run_status"] == "blocked_missing_metadata"
    assert report["production_records_written"] is False
    assert report["dashboard_contract_changed"] is False
    assert validator._FIXTURE_SECRET not in report_text
    assert "A,H,US" not in report_text
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()


def test_v2_8_j_cli_exits_zero_and_prints_no_secret_values(tmp_path: Path, capsys):
    suggestions_json = tmp_path / "suggestions.json"
    suggestions_json.write_text(json.dumps(_suggestions(), ensure_ascii=False), encoding="utf-8")

    exit_code = validator.main(
        [
            "--output-root",
            str(tmp_path / "processed"),
            "--reports-dir",
            str(tmp_path / "reports"),
            "--run-id",
            "v2_8_j_cli",
            "--real-config-path",
            str(tmp_path / "missing-local.json"),
            "--suggestion-drafts-json",
            str(suggestions_json),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "PASS" in captured.out
    assert validator._FIXTURE_SECRET not in captured.out
    assert "secret" not in captured.out.lower()
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()
