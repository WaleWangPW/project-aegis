from __future__ import annotations

import json
from pathlib import Path

from aegis.external_sources.api_candidate_live_dry_run import run_api_candidate_live_dry_run
import scripts.validate_v2_10_c_real_api_candidate_refresh_live_dry_run as validator


FIXTURE_SECRET = "unit-secret-value-must-not-serialize"


def _gitignore(path: Path) -> Path:
    target = path / ".gitignore"
    target.write_text("config/external_api_connectors.local.json\n", encoding="utf-8")
    return target


def _suggestions(path: Path) -> Path:
    target = path / "suggestions.json"
    target.write_text(
        json.dumps(
            [
                {
                    "suggestion_id": "sug_a",
                    "strategy_id": "strategy_a_low_vol_dividend_defensive",
                    "market": "A",
                    "action": "paper_entry_candidate",
                    "evidence_refs": ["sandbox.json"],
                    "blocked_by": [],
                },
                {
                    "suggestion_id": "sug_h",
                    "strategy_id": "strategy_h_low_vol_dividend",
                    "market": "H",
                    "action": "paper_entry_candidate",
                    "evidence_refs": ["sandbox.json"],
                    "blocked_by": [],
                },
                {
                    "suggestion_id": "sug_us",
                    "strategy_id": "strategy_us_value_quality_momentum",
                    "market": "US",
                    "action": "paper_entry_candidate",
                    "evidence_refs": ["sandbox.json"],
                    "blocked_by": [],
                },
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return target


def _local_config(path: Path) -> Path:
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
                        "base_url": "https://api.example.test/v1",
                        "auth_method": "env_var",
                        "required_env_vars": ["AEGIS_CANDIDATE_REFRESH_API_KEY"],
                        "license_status": "approved",
                        "retention_policy": "summary_only",
                        "allowed_purposes": ["candidate_refresh", "strategy_research_ingestion"],
                        "can_connect": True,
                        "endpoint_path": "/candidate-refresh",
                        "request_query_template": {"markets": "A,H,US", "purpose": "candidate_refresh"},
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


def _fixture_fetch(url: str, headers: dict, timeout: int):
    assert "markets=A%2CH%2CUS" in url
    assert FIXTURE_SECRET in headers.get("Authorization", "")
    assert timeout > 0
    payload = {
        "items": [
            {"symbol": "600036.SH", "market": "A", "name": "招商银行", "score": 0.86, "status": "Watch"},
            {"symbol": "00700.HK", "market": "H", "name": "Tencent Holdings", "score": 0.83, "status": "Watch"},
            {"symbol": "MSFT", "market": "US", "name": "Microsoft", "score": 0.78, "status": "Watch"},
        ]
    }
    return 200, "application/json", json.dumps(payload, ensure_ascii=False).encode("utf-8")


def test_v2_10_c_missing_metadata_does_not_fetch(tmp_path: Path):
    report = run_api_candidate_live_dry_run(
        local_config_path=tmp_path / "missing.json",
        gitignore_path=_gitignore(tmp_path),
        suggestion_drafts_json=_suggestions(tmp_path),
        output_dir=tmp_path / "run",
        run_id="missing",
        env={},
        fetch_fn=lambda *_args: (_ for _ in ()).throw(AssertionError("fetch must not run")),
    )

    assert report["overall_status"] == "PASS"
    assert report["dry_run_status"] == "blocked_missing_metadata"
    assert report["network_used"] is False
    assert report["api_fetch_item_json"] is None
    assert report["checks"]["blocked_path_does_not_fetch"] is True


def test_v2_10_c_ready_metadata_binds_a_h_us_without_serializing_secret_or_query(tmp_path: Path):
    report = run_api_candidate_live_dry_run(
        local_config_path=_local_config(tmp_path),
        gitignore_path=_gitignore(tmp_path),
        suggestion_drafts_json=_suggestions(tmp_path),
        output_dir=tmp_path / "run",
        run_id="ready",
        env={"AEGIS_CANDIDATE_REFRESH_API_KEY": FIXTURE_SECRET},
        fetch_fn=_fixture_fetch,
    )
    text = json.dumps(report, ensure_ascii=False)

    assert report["overall_status"] == "PASS"
    assert report["dry_run_status"] == "completed"
    assert set(report["refresh_summary"]["bound_markets"]) == {"A", "H", "US"}
    assert Path(report["api_fetch_item_json"]).exists()
    assert Path(report["api_candidate_source_registry_json"]).exists()
    assert Path(report["api_candidate_bindings_json"]).exists()
    assert FIXTURE_SECRET not in text
    assert "A,H,US" not in text
    assert report["safety"]["raw_payload_not_stored"] is True
    assert report["safety"]["no_broker_api"] is True


def test_v2_10_c_validator_writes_blocked_report_and_marker(tmp_path: Path):
    report = validator.run_acceptance(
        output_root=tmp_path / "processed",
        reports_dir=tmp_path / "reports",
        run_id="v2_10_c_test",
        command="test command",
        local_config_path=tmp_path / "missing.json",
        gitignore_path=_gitignore(tmp_path),
        suggestion_drafts_json=_suggestions(tmp_path),
        env={},
    )

    assert report["overall_status"] == "PASS"
    assert report["dry_run_status"] == "blocked_missing_metadata"
    assert report["safety"]["activation_gate_before_fetch"] is True
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()
