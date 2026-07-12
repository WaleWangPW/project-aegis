from __future__ import annotations

import json
from pathlib import Path

import scripts.run_api_research_dry_run as dry_runner
import scripts.validate_v2_3_b_real_user_api_dry_run as validator
from aegis.external_sources.api_config import get_api_connector_spec


def test_load_fixture_user_config_and_run_dry_run(tmp_path: Path):
    config_path = tmp_path / "external_api_connectors.local.fixture.json"
    validator._write_fixture_user_config(config_path)

    spec = get_api_connector_spec(config_path, "api_fixture_real_user_research")
    assert spec.required_env_vars == ["AEGIS_RESEARCH_API_KEY"]

    report = dry_runner.run_dry_run(
        config_path=config_path,
        connector_id="api_fixture_real_user_research",
        endpoint_path="/strategy-notes",
        query={"market": "A"},
        output_root=tmp_path / "runs",
        run_id="unit_dry_run",
        fetch_fn=validator._fixture_fetch,
        env={"AEGIS_RESEARCH_API_KEY": validator._FIXTURE_SECRET},
    )
    payload = Path(report["report_json"]).read_text(encoding="utf-8")
    persisted = json.loads(payload)

    assert report["overall_status"] == "PASS"
    assert report["summary"]["auth_env_vars_used"] == ["AEGIS_RESEARCH_API_KEY"]
    assert validator._FIXTURE_SECRET not in payload
    assert report["safety"]["raw_bytes_not_stored"] is True
    assert report["safety"]["request_headers_not_stored"] is True
    assert "report_json" not in persisted["hashes"]


def test_real_user_config_missing_is_reported_as_blocked():
    reason = validator._real_config_blocked_reason()
    assert reason
    assert "external_api_connectors.local.json" in reason


def test_v2_3_b_acceptance_writes_marker_hashes_and_reports(tmp_path: Path):
    report = validator.run_acceptance(
        output_root=tmp_path / "processed",
        reports_dir=tmp_path / "reports",
        run_id="v2_3_b_test",
        command="test command",
    )

    assert report["overall_status"] == "PASS"
    assert report["checks"]["fixture_dry_run_passed"] is True
    assert report["checks"]["secret_value_not_serialized"] is True
    assert report["checks"]["real_user_config_missing_is_blocked"] is True
    assert report["production_records_written"] is False
    assert report["hashes"]["fixture_dry_run_report"]
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()
    payload = json.loads((tmp_path / "reports" / validator.REPORT_JSON).read_text(encoding="utf-8"))
    assert payload["summary"]["next_target"] == "V2.3-C Live API Dry Run After User Provides Metadata"


def test_v2_3_b_cli_exits_zero_and_prints_no_secret_values(tmp_path: Path, capsys):
    exit_code = validator.main(
        [
            "--output-root",
            str(tmp_path / "processed"),
            "--reports-dir",
            str(tmp_path / "reports"),
            "--run-id",
            "v2_3_b_cli",
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "PASS" in captured.out
    assert validator._FIXTURE_SECRET not in captured.out
    assert "secret" not in captured.out.lower()
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()
