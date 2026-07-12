from __future__ import annotations

import json
from pathlib import Path

import pytest

import scripts.validate_v2_2_a_external_api_research_ingestion as validator
from aegis.external_sources.api_connector import evaluate_api_connector_registry
from aegis.models.external_api import ExternalAPIConnectorSpec
from aegis.models.strategy_research import StrategyResearchRecord
from aegis.strategy.research_ingestion import build_strategy_research_corpus, write_strategy_research_corpus


def test_external_api_connector_policy_allows_approved_metadata_and_denies_trading():
    registry = evaluate_api_connector_registry(validator._fixture_connectors())
    decisions = {item["connector_id"]: item for item in registry["decisions"]}

    assert decisions["api_sec_companyfacts"]["decision"] == "allow"
    assert decisions["api_user_research_approved_env"]["decision"] == "allow"
    assert decisions["api_user_research_approved_env"]["required_env_vars"] == ["AEGIS_RESEARCH_API_KEY"]
    assert decisions["api_broker_forbidden"]["decision"] == "deny"
    assert decisions["api_trading_webhook_forbidden"]["decision"] == "deny"
    assert registry["safety"]["no_secret_values_stored"] is True
    assert registry["safety"]["no_broker_api"] is True
    assert registry["safety"]["no_trading_webhook"] is True


def test_external_api_connector_rejects_secret_in_base_url():
    with pytest.raises(ValueError):
        ExternalAPIConnectorSpec(
            connector_id="bad_secret_url",
            name="Bad Secret URL",
            provider_type="user_provided_research_api",
            markets=["US"],
            base_url="https://example.invalid/data?api_key=SHOULD_NOT_BE_HERE",
            auth_method="none",
            license_status="approved",
            retention_policy="summary_only",
            allowed_purposes=["strategy_research_ingestion"],
            can_connect=True,
        )


def test_strategy_research_ingestion_covers_markets_factors_and_hashes(tmp_path: Path):
    records = validator._fixture_research_records()
    output = tmp_path / "strategy_research_corpus.json"
    corpus = write_strategy_research_corpus(records, output)

    assert output.exists()
    assert corpus["record_count"] == 6
    assert all(corpus["market_coverage"].get(market, 0) > 0 for market in ["A", "H", "US"])
    assert all(
        corpus["strategy_family_coverage"].get(family, 0) > 0
        for family in ["value", "quality", "momentum", "low_volatility", "dividend", "multi_factor"]
    )
    assert len(corpus["record_hashes"]) == 6
    assert corpus["safety"]["raw_text_not_stored"] is True
    assert corpus["safety"]["no_real_trade"] is True


def test_strategy_research_record_rejects_raw_text_storage():
    with pytest.raises(ValueError):
        StrategyResearchRecord(
            research_id="bad_raw_text",
            title="Bad Raw Text",
            source_type="public_web",
            publisher="Example",
            url="https://example.invalid",
            markets=["US"],
            strategy_families=["value"],
            evidence_level="context_only",
            retention_policy="summary_only",
            summary="Should be rejected.",
            raw_text_stored=True,
        )


def test_v2_2_a_acceptance_writes_marker_hashes_and_reports(tmp_path: Path):
    report = validator.run_acceptance(
        output_root=tmp_path / "processed",
        reports_dir=tmp_path / "reports",
        run_id="v2_2_a_test",
        command="test command",
    )

    assert report["overall_status"] == "PASS"
    assert report["checks"]["official_api_allowed"] is True
    assert report["checks"]["user_api_env_only_allowed"] is True
    assert report["checks"]["broker_api_denied"] is True
    assert report["checks"]["trading_webhook_denied"] is True
    assert report["checks"]["research_covers_a_h_us"] is True
    assert report["checks"]["research_covers_core_factors"] is True
    assert report["production_records_written"] is False
    assert report["hashes"]["api_registry_json"]
    assert report["hashes"]["strategy_research_corpus_json"]
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()
    payload = json.loads((tmp_path / "reports" / validator.REPORT_JSON).read_text(encoding="utf-8"))
    assert payload["summary"]["next_target"] == "V2.2-B API-backed Research Fetch Dry Run"


def test_v2_2_a_cli_exits_zero_and_prints_no_secrets(tmp_path: Path, capsys):
    exit_code = validator.main(
        [
            "--output-root",
            str(tmp_path / "processed"),
            "--reports-dir",
            str(tmp_path / "reports"),
            "--run-id",
            "v2_2_a_cli",
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "PASS" in captured.out
    assert "token" not in captured.out.lower()
    assert "secret" not in captured.out.lower()
    assert "AEGIS_RESEARCH_API_KEY" not in captured.out
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()
