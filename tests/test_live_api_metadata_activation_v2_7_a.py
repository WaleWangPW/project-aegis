from __future__ import annotations

import json
from pathlib import Path

import scripts.validate_v2_7_a_live_api_metadata_activation as validator
from aegis.external_sources.api_activation import assess_live_api_activation, build_api_activation_report


def _config(path: Path) -> None:
    validator._write_fixture_config(path)


def test_api_activation_reports_ready_without_storing_env_value(tmp_path: Path):
    config = tmp_path / "external_api_connectors.local.json"
    _config(config)

    report = build_api_activation_report(
        config_path=config,
        connector_id=validator.DEFAULT_CONNECTOR_ID,
        run_id="unit",
        env={"AEGIS_RESEARCH_API_KEY": "unit-secret-value"},
    )
    text = json.dumps(report, ensure_ascii=False)

    assert report["overall_status"] == "PASS"
    assert report["activation"]["activation_status"] == "ready_for_live_dry_run"
    assert report["activation"]["present_env_vars"] == ["AEGIS_RESEARCH_API_KEY"]
    assert "unit-secret-value" not in text
    assert report["safety"]["network_not_used"] if "network_not_used" in report["safety"] else report["network_used"] is False


def test_api_activation_blocks_missing_metadata_and_missing_env(tmp_path: Path):
    missing = assess_live_api_activation(
        config_path=tmp_path / "missing.json",
        connector_id=validator.DEFAULT_CONNECTOR_ID,
        env={},
    )
    assert missing["activation_status"] == "blocked_missing_metadata"

    config = tmp_path / "external_api_connectors.local.json"
    _config(config)
    missing_env = assess_live_api_activation(
        config_path=config,
        connector_id=validator.DEFAULT_CONNECTOR_ID,
        env={},
    )
    assert missing_env["activation_status"] == "blocked_missing_env_vars"
    assert missing_env["missing_env_vars"] == ["AEGIS_RESEARCH_API_KEY"]


def test_v2_7_a_acceptance_writes_reports_and_real_status(tmp_path: Path):
    report = validator.run_acceptance(
        output_root=tmp_path / "processed",
        reports_dir=tmp_path / "reports",
        run_id="v2_7_a_test",
        command="test command",
        real_config_path=tmp_path / "missing-local.json",
    )

    assert report["overall_status"] == "PASS"
    assert report["checks"]["fixture_ready_for_live_dry_run"] is True
    assert report["checks"]["fixture_missing_env_is_blocked"] is True
    assert report["real_user_activation_status"] == "blocked_missing_metadata"
    assert report["network_used"] is False
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()


def test_v2_7_a_cli_exits_zero_and_prints_no_secret_values(tmp_path: Path, capsys):
    exit_code = validator.main(
        [
            "--output-root",
            str(tmp_path / "processed"),
            "--reports-dir",
            str(tmp_path / "reports"),
            "--run-id",
            "v2_7_a_cli",
            "--real-config-path",
            str(tmp_path / "missing-local.json"),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "PASS" in captured.out
    assert "fixture-value-not-persisted" not in captured.out
    assert "secret" not in captured.out.lower()
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()
