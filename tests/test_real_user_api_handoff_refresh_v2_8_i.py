from __future__ import annotations

import json
from pathlib import Path

import pytest

import scripts.validate_v2_8_i_real_user_api_handoff_refresh as validator


def test_v2_8_i_refresh_doc_defines_candidate_refresh_boundary():
    text = validator.REFRESH_DOC.read_text(encoding="utf-8")

    for term in [
        "candidate_payload_schema",
        "items_path",
        "symbol_field",
        "market_field",
        "max_items_per_market",
    ]:
        assert term in text
    for term in ["Broker credentials", "Trading webhook URLs", "Automatic order placement"]:
        assert term in text
    assert "manual" in text.lower()


def test_v2_8_i_user_template_is_non_secret_candidate_refresh_metadata():
    payload = validator._load_template()
    connectors = payload["connectors"]
    connector = connectors[0]

    assert len(connectors) == 1
    assert validator._connector_has_required_fields(connector)
    assert validator._candidate_schema_ok(connector)
    assert validator._purposes_are_safe(connector)
    assert connector["allowed_purposes"] == ["candidate_refresh", "strategy_research_ingestion"]
    assert connector["required_env_vars"] == ["AEGIS_CANDIDATE_REFRESH_API_KEY"]
    assert not validator._template_has_secret_values(payload)
    assert connector["provider_type"] != "broker_api"


def test_v2_8_i_secret_like_url_material_is_rejected_by_helper():
    payload = validator._load_template()
    payload["connectors"][0]["base_url"] = "https://example.invalid/v1?api_key=SHOULD_NOT_EXIST"

    assert validator._template_has_secret_values(payload)


def test_v2_8_i_forbidden_purposes_are_rejected_by_helper():
    connector = {
        "allowed_purposes": ["candidate_refresh", "order_placement"],
    }

    assert validator._purposes_are_safe(connector) is False


def test_v2_8_i_acceptance_writes_reports_and_marker(tmp_path: Path):
    report = validator.run_acceptance(
        output_root=tmp_path / "processed",
        reports_dir=tmp_path / "reports",
        run_id="v2_8_i_test",
        command="test command",
    )

    assert report["overall_status"] == "PASS"
    assert report["checks"]["template_candidate_schema_ok"] is True
    assert report["checks"]["no_secret_values_in_template"] is True
    assert report["checks"]["no_broker_or_webhook"] is True
    assert report["safety"]["requires_historical_sandbox"] is True
    assert report["safety"]["requires_suggestion_gate"] is True
    assert report["production_records_written"] is False
    assert report["dashboard_contract_changed"] is False
    assert report["hashes"]["user_template"]
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()

    payload = json.loads((tmp_path / "reports" / validator.REPORT_JSON).read_text(encoding="utf-8"))
    assert payload["summary"]["next_target"] == "V2.8-J Real User API Candidate Refresh Dry Run After Local Metadata"


def test_v2_8_i_cli_exits_zero_and_prints_no_secret_values(tmp_path: Path, capsys):
    exit_code = validator.main(
        [
            "--output-root",
            str(tmp_path / "processed"),
            "--reports-dir",
            str(tmp_path / "reports"),
            "--run-id",
            "v2_8_i_cli",
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "PASS" in captured.out
    assert "sk-" not in captured.out.lower()
    assert "bearer " not in captured.out.lower()
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()


def test_v2_8_i_acceptance_fails_when_template_has_secret_like_material(monkeypatch, tmp_path: Path):
    payload = validator._load_template()
    payload["connectors"][0]["base_url"] = "https://example.invalid/v1?token=SHOULD_NOT_EXIST"
    template = tmp_path / "bad-template.json"
    template.write_text(json.dumps(payload), encoding="utf-8")

    monkeypatch.setattr(validator, "USER_TEMPLATE", template)

    with pytest.raises(RuntimeError, match="template_parses_existing_policy_model"):
        validator.run_acceptance(
            output_root=tmp_path / "processed",
            reports_dir=tmp_path / "reports",
            run_id="v2_8_i_bad_template",
            command="test command",
        )
