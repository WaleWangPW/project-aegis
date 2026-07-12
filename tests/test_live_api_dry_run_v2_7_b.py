from __future__ import annotations

import json
from pathlib import Path

import scripts.validate_v2_7_b_live_api_dry_run as validator
from aegis.external_sources.live_api_dry_run import build_live_api_dry_run_report


def test_live_api_dry_run_runs_only_after_activation_ready(tmp_path: Path):
    config = tmp_path / "external_api_connectors.local.json"
    validator._write_fixture_config(config)

    report = build_live_api_dry_run_report(
        config_path=config,
        connector_id=validator.DEFAULT_CONNECTOR_ID,
        endpoint_path="/candidate-refresh",
        output_root=tmp_path / "runs",
        run_id="ready",
        query={"market": "A,H,US", "purpose": "candidate_refresh"},
        env={"AEGIS_RESEARCH_API_KEY": validator._FIXTURE_SECRET},
        fetch_fn=validator._fixture_fetch,
    )
    text = Path(report["report_json"]).read_text(encoding="utf-8")

    assert report["overall_status"] == "PASS"
    assert report["activation"]["activation_status"] == "ready_for_live_dry_run"
    assert report["live_dry_run_status"] == "completed"
    assert report["api_fetch_item_json"]
    assert report["summary"]["auth_env_vars_used"] == ["AEGIS_RESEARCH_API_KEY"]
    assert validator._FIXTURE_SECRET not in text
    assert "A,H,US" not in text
    assert report["checks"]["raw_bytes_not_stored"] is True
    assert report["checks"]["request_headers_not_stored"] is True


def test_live_api_dry_run_blocks_missing_metadata_without_fetch(tmp_path: Path):
    called = False

    def should_not_fetch(url, headers, timeout):  # pragma: no cover - proves no fetch if called
        nonlocal called
        called = True
        return 200, "application/json", b"{}"

    report = build_live_api_dry_run_report(
        config_path=tmp_path / "missing.json",
        connector_id=validator.DEFAULT_CONNECTOR_ID,
        endpoint_path="/candidate-refresh",
        output_root=tmp_path / "runs",
        run_id="missing",
        env={"AEGIS_RESEARCH_API_KEY": validator._FIXTURE_SECRET},
        fetch_fn=should_not_fetch,
    )

    assert report["overall_status"] == "BLOCKED"
    assert report["activation"]["activation_status"] == "blocked_missing_metadata"
    assert report["api_fetch_item_json"] is None
    assert called is False
    assert report["checks"]["blocked_run_does_not_fetch"] is True


def test_live_api_dry_run_blocks_missing_env_without_fetch(tmp_path: Path):
    config = tmp_path / "external_api_connectors.local.json"
    validator._write_fixture_config(config)

    report = build_live_api_dry_run_report(
        config_path=config,
        connector_id=validator.DEFAULT_CONNECTOR_ID,
        endpoint_path="/candidate-refresh",
        output_root=tmp_path / "runs",
        run_id="missing_env",
        env={},
        fetch_fn=validator._fixture_fetch,
    )

    assert report["overall_status"] == "BLOCKED"
    assert report["activation"]["activation_status"] == "blocked_missing_env_vars"
    assert report["api_fetch_item_json"] is None
    assert report["network_used"] is False


def test_v2_7_b_acceptance_writes_reports_and_records_real_status(tmp_path: Path):
    report = validator.run_acceptance(
        output_root=tmp_path / "processed",
        reports_dir=tmp_path / "reports",
        run_id="v2_7_b_test",
        command="test command",
        real_config_path=tmp_path / "missing-local.json",
    )
    report_text = (tmp_path / "reports" / validator.REPORT_JSON).read_text(encoding="utf-8")

    assert report["overall_status"] == "PASS"
    assert report["checks"]["fixture_live_dry_run_completed"] is True
    assert report["checks"]["real_user_status_recorded"] is True
    assert report["real_user_live_dry_run_status"] == "blocked_missing_metadata"
    assert report["production_records_written"] is False
    assert validator._FIXTURE_SECRET not in report_text
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()


def test_v2_7_b_cli_exits_zero_and_prints_no_secret_values(tmp_path: Path, capsys):
    exit_code = validator.main(
        [
            "--output-root",
            str(tmp_path / "processed"),
            "--reports-dir",
            str(tmp_path / "reports"),
            "--run-id",
            "v2_7_b_cli",
            "--real-config-path",
            str(tmp_path / "missing-local.json"),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "PASS" in captured.out
    assert validator._FIXTURE_SECRET not in captured.out
    assert "secret" not in captured.out.lower()
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()
