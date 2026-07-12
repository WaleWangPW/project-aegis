from __future__ import annotations

import json
from pathlib import Path

from aegis.external_sources.api_metadata_intake import assess_api_metadata_intake
import scripts.validate_v2_10_b_real_api_metadata_intake as validator


def _gitignore(path: Path) -> Path:
    target = path / ".gitignore"
    target.write_text("config/external_api_connectors.local.json\n", encoding="utf-8")
    return target


def _local_config(path: Path, *, base_url: str = "https://api.example.test/v1") -> Path:
    target = path / "external_api_connectors.local.json"
    target.write_text(
        json.dumps(
            {
                "schema_version": "external_api_connectors.local.test",
                "connectors": [
                    {
                        "connector_id": "api_user_candidate_refresh_approved_env",
                        "name": "User Candidate API",
                        "provider_type": "user_provided_research_api",
                        "markets": ["A", "H", "US"],
                        "base_url": base_url,
                        "auth_method": "env_var",
                        "required_env_vars": ["AEGIS_CANDIDATE_REFRESH_API_KEY"],
                        "license_status": "approved",
                        "retention_policy": "summary_only",
                        "allowed_purposes": ["candidate_refresh", "strategy_research_ingestion"],
                        "can_connect": True,
                        "candidate_payload_schema": {
                            "items_path": "items",
                            "symbol_field": "symbol",
                            "market_field": "market",
                            "name_field": "name",
                            "score_field": "score",
                            "status_field": "status",
                            "allowed_markets": ["A", "H", "US"],
                            "max_items_per_market": 50,
                            "freshness_policy": "same_day_or_latest_available",
                            "candidate_summary_only": True,
                        },
                    }
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return target


def test_v2_10_b_missing_metadata_is_pass_but_not_ready(tmp_path: Path):
    intake = assess_api_metadata_intake(
        local_config_path=tmp_path / "missing.json",
        gitignore_path=_gitignore(tmp_path),
        env={},
    )

    assert intake["intake_status"] == "blocked_missing_metadata"
    assert intake["selected_connector"] is None
    assert intake["raw_config_stored"] is False


def test_v2_10_b_present_metadata_blocks_missing_env_without_secret_values(tmp_path: Path):
    config = _local_config(tmp_path)
    intake = assess_api_metadata_intake(
        local_config_path=config,
        gitignore_path=_gitignore(tmp_path),
        env={},
    )
    text = json.dumps(intake, ensure_ascii=False)

    assert intake["intake_status"] == "blocked_missing_env_vars"
    assert intake["missing_env_vars"] == ["AEGIS_CANDIDATE_REFRESH_API_KEY"]
    assert "api.example.test/v1" not in text
    assert intake["selected_connector"]["base_url_host"] == "api.example.test"
    assert intake["raw_config_stored"] is False


def test_v2_10_b_ready_when_metadata_and_env_are_present(tmp_path: Path):
    config = _local_config(tmp_path)
    intake = assess_api_metadata_intake(
        local_config_path=config,
        gitignore_path=_gitignore(tmp_path),
        env={"AEGIS_CANDIDATE_REFRESH_API_KEY": "unit-secret-value"},
    )
    text = json.dumps(intake, ensure_ascii=False)

    assert intake["intake_status"] == "ready_for_live_readiness_check"
    assert intake["present_env_vars"] == ["AEGIS_CANDIDATE_REFRESH_API_KEY"]
    assert "unit-secret-value" not in text
    assert intake["selected_connector"]["can_run_live_readiness"] is True


def test_v2_10_b_secret_like_local_config_is_blocked(tmp_path: Path):
    config = _local_config(tmp_path, base_url="https://api.example.test/v1?api_key=SHOULD_NOT_EXIST")
    intake = assess_api_metadata_intake(
        local_config_path=config,
        gitignore_path=_gitignore(tmp_path),
        env={},
    )

    assert intake["intake_status"] == "blocked_secret_like_material"
    assert intake["secret_like_material_detected"] is True


def test_v2_10_b_validator_writes_report_and_marker(tmp_path: Path):
    report = validator.run_acceptance(
        output_root=tmp_path / "processed",
        reports_dir=tmp_path / "reports",
        run_id="v2_10_b_test",
        command="test command",
        local_config_path=tmp_path / "missing.json",
        gitignore_path=_gitignore(tmp_path),
        env={},
    )

    assert report["overall_status"] == "PASS"
    assert report["summary"]["intake_status"] == "blocked_missing_metadata"
    assert report["safety"]["network_not_used"] is True
    assert report["safety"]["no_broker_api"] is True
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()
