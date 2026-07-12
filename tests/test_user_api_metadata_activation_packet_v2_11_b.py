from __future__ import annotations

import json
from pathlib import Path

from aegis.external_sources.api_metadata_activation_packet import (
    build_api_metadata_activation_packet,
    contains_secret_like_material,
    render_api_metadata_activation_packet_markdown,
)
import scripts.validate_v2_11_b_user_api_metadata_activation_packet as validator


def _template() -> dict:
    return {
        "schema_version": "unit",
        "connectors": [
            {
                "connector_id": "api_user_candidate_refresh_approved_env",
                "name": "Candidate API",
                "provider_type": "user_provided_research_api",
                "markets": ["A", "H", "US"],
                "base_url": "https://api.example.test/v1",
                "auth_method": "env_var",
                "required_env_vars": ["AEGIS_CANDIDATE_REFRESH_API_KEY"],
                "license_status": "approved",
                "retention_policy": "summary_only",
                "allowed_purposes": ["candidate_refresh", "strategy_research_ingestion"],
                "can_connect": True,
                "endpoint_path": "/candidate-refresh",
                "request_query_template": {"markets": "A,H,US"},
                "candidate_payload_schema": {
                    "items_path": "items",
                    "symbol_field": "symbol",
                    "market_field": "market",
                    "name_field": "name",
                    "score_field": "score",
                    "status_field": "status",
                    "allowed_markets": ["A", "H", "US"],
                    "max_items_per_market": 50,
                    "candidate_summary_only": True,
                },
            }
        ],
    }


def _intake_report(status: str = "blocked_missing_metadata") -> dict:
    return {
        "overall_status": "PASS",
        "summary": {
            "intake_status": status,
            "blocked_by": ["missing_connector_metadata"],
            "connector_id": "api_user_candidate_refresh_approved_env",
            "required_env_vars": [],
            "present_env_vars": [],
            "missing_env_vars": [],
        },
    }


def _tushare_probe() -> dict:
    return {
        "provider": "tushare",
        "token_present": True,
        "network_available": True,
        "summary": {"pass_count": 4, "unknown_count": 2},
        "checks": [
            {"market": "A", "data_type": "daily_bars", "status": "pass"},
            {"market": "A", "data_type": "index_bars", "status": "pass"},
            {"market": "A", "data_type": "stock_basic", "status": "pass"},
            {"market": "A", "data_type": "trading_calendar", "status": "pass"},
            {"market": "A", "data_type": "sector_classification", "status": "unknown_empty"},
            {"market": "A", "data_type": "fundamentals", "status": "unknown_empty"},
        ],
    }


def test_v2_11_b_builds_safe_user_activation_packet():
    packet = build_api_metadata_activation_packet(
        template_payload=_template(),
        metadata_intake_report=_intake_report(),
        tushare_probe_report=_tushare_probe(),
        run_id="unit",
        connector_id="api_user_candidate_refresh_approved_env",
        generated_at="2026-07-11T00:00:00+08:00",
    )
    text = json.dumps(packet, ensure_ascii=False)

    assert packet["overall_status"] == "PASS"
    assert packet["summary"]["current_intake_status"] == "blocked_missing_metadata"
    assert packet["summary"]["required_env_vars"] == ["AEGIS_CANDIDATE_REFRESH_API_KEY"]
    assert packet["summary"]["tushare_status"] == "a_share_core_ready"
    assert packet["tushare_first"]["a_share_core_ready"] is True
    assert packet["checks"]["raw_config_not_stored"] is True
    assert packet["checks"]["env_values_not_stored"] is True
    assert "unit-secret-value" not in text
    assert "api.example.test/v1" not in text
    assert packet["safe_template_summary"]["base_url_host_example"] == "api.example.test"


def test_v2_11_b_secret_like_template_is_not_pass():
    template = _template()
    template["connectors"][0]["notes"] = "api_key=SHOULD_NOT_BE_HERE"
    packet = build_api_metadata_activation_packet(
        template_payload=template,
        metadata_intake_report=_intake_report(),
        tushare_probe_report=_tushare_probe(),
        run_id="unit",
        connector_id="api_user_candidate_refresh_approved_env",
    )

    assert contains_secret_like_material(template) is True
    assert packet["overall_status"] == "FAIL"
    assert packet["checks"]["template_secret_like_material_absent"] is False


def test_v2_11_b_markdown_lists_user_steps_and_forbidden_values():
    packet = build_api_metadata_activation_packet(
        template_payload=_template(),
        metadata_intake_report=_intake_report(),
        tushare_probe_report=_tushare_probe(),
        run_id="unit",
        connector_id="api_user_candidate_refresh_approved_env",
    )
    md = render_api_metadata_activation_packet_markdown(packet)

    assert "Fill These Non-Secret Metadata Fields" in md
    assert "required_env_vars" in md
    assert "Never Put These In Files Or Chat" in md
    assert "bearer token" in md
    assert "No API key values stored" in md


def test_v2_11_b_validator_writes_packet_and_marker(tmp_path: Path):
    template = tmp_path / "template.json"
    intake = tmp_path / "intake.json"
    tushare = tmp_path / "tushare.json"
    template.write_text(json.dumps(_template(), ensure_ascii=False), encoding="utf-8")
    intake.write_text(json.dumps(_intake_report(), ensure_ascii=False), encoding="utf-8")
    tushare.write_text(json.dumps(_tushare_probe(), ensure_ascii=False), encoding="utf-8")

    report = validator.run_acceptance(
        output_root=tmp_path / "processed",
        reports_dir=tmp_path / "reports",
        run_id="v2_11_b_test",
        command="test command",
        template_json=template,
        metadata_intake_report_json=intake,
        tushare_probe_report_json=tushare,
    )

    assert report["overall_status"] == "PASS"
    assert report["checks"]["packet_json_written"] is True
    assert report["checks"]["template_hash_only"] is True
    assert report["checks"]["tushare_probe_report_exists"] is True
    assert report["safety"]["no_broker_api"] is True
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()


def test_v2_11_b_cli_exits_zero(tmp_path: Path, capsys):
    template = tmp_path / "template.json"
    intake = tmp_path / "intake.json"
    tushare = tmp_path / "tushare.json"
    template.write_text(json.dumps(_template(), ensure_ascii=False), encoding="utf-8")
    intake.write_text(json.dumps(_intake_report(), ensure_ascii=False), encoding="utf-8")
    tushare.write_text(json.dumps(_tushare_probe(), ensure_ascii=False), encoding="utf-8")

    exit_code = validator.main(
        [
            "--output-root",
            str(tmp_path / "processed"),
            "--reports-dir",
            str(tmp_path / "reports"),
            "--run-id",
            "v2_11_b_cli",
            "--template-json",
            str(template),
            "--metadata-intake-report-json",
            str(intake),
            "--tushare-probe-report-json",
            str(tushare),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "PASS" in captured.out
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()
