from __future__ import annotations

import json
from pathlib import Path

import scripts.validate_v2_3_a_api_configuration_handoff as validator
from aegis.external_sources.api_connector import evaluate_api_connector_registry


def test_api_configuration_handoff_doc_lists_metadata_and_forbidden_secrets():
    text = validator.HANDOFF_DOC.read_text(encoding="utf-8")

    for term in ["connector_id", "base_url", "required_env_vars", "license_status", "retention_policy"]:
        assert term in text
    for term in ["API key values", "Secret values", "Cookies", "Bearer tokens", "Passwords"]:
        assert term in text
    assert "actual values must stay outside the repo and Vault" in text


def test_example_api_config_parses_and_allows_only_safe_connectors():
    specs = validator._load_example_specs()
    registry = evaluate_api_connector_registry(specs)
    decisions = {item["connector_id"]: item for item in registry["decisions"]}

    assert len(specs) == 2
    assert decisions["api_sec_companyfacts"]["decision"] == "allow"
    assert decisions["api_user_research_approved_env"]["decision"] == "allow"
    assert decisions["api_user_research_approved_env"]["required_env_vars"] == ["AEGIS_RESEARCH_API_KEY"]
    assert registry["safety"]["no_secret_values_stored"] is True
    assert registry["safety"]["no_broker_api"] is True
    assert registry["safety"]["no_trading_webhook"] is True


def test_example_api_config_contains_no_secret_values():
    text = validator.EXAMPLE_CONFIG.read_text(encoding="utf-8")

    assert not validator._text_has_forbidden_secret_value(text)
    assert "sk-" not in text
    assert "bearer " not in text.lower()
    assert "cookie=" not in text.lower()


def test_v2_3_a_acceptance_writes_marker_hashes_and_reports(tmp_path: Path):
    report = validator.run_acceptance(
        output_root=tmp_path / "processed",
        reports_dir=tmp_path / "reports",
        run_id="v2_3_a_test",
        command="test command",
    )

    assert report["overall_status"] == "PASS"
    assert report["checks"]["handoff_doc_exists"] is True
    assert report["checks"]["example_config_exists"] is True
    assert report["checks"]["no_forbidden_secret_values_in_example"] is True
    assert report["checks"]["no_broker_or_webhook"] is True
    assert report["production_records_written"] is False
    assert report["hashes"]["handoff_doc"]
    assert report["hashes"]["example_config"]
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()
    payload = json.loads((tmp_path / "reports" / validator.REPORT_JSON).read_text(encoding="utf-8"))
    assert payload["summary"]["next_target"] == "V2.3-B Real User API Dry Run When Metadata Is Provided"


def test_v2_3_a_cli_exits_zero_and_prints_no_secret_values(tmp_path: Path, capsys):
    exit_code = validator.main(
        [
            "--output-root",
            str(tmp_path / "processed"),
            "--reports-dir",
            str(tmp_path / "reports"),
            "--run-id",
            "v2_3_a_cli",
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "PASS" in captured.out
    assert "secret" not in captured.out.lower()
    assert "sk-" not in captured.out.lower()
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()
