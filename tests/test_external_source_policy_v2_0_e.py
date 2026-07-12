from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

import scripts.validate_v2_0_e_external_source_policy as validator
from aegis.external_sources.policy import evaluate_source_registry
from aegis.models.external_source import ExternalSourcePolicy


def test_external_source_policy_allows_official_and_denies_pending_or_unlicensed():
    report = evaluate_source_registry(validator._fixture_sources())
    decisions = {item["source_id"]: item for item in report["decisions"]}

    assert decisions["src_sec_company_filings"]["decision"] == "allow"
    assert decisions["src_bloomberg_unlicensed"]["decision"] == "deny"
    assert "licensed_financial_data_requires_approved_license" in decisions["src_bloomberg_unlicensed"]["reasons"]
    assert decisions["src_reddit_pending"]["decision"] == "deny"
    assert decisions["src_x_pending"]["decision"] == "deny"
    assert report["safety"]["no_live_fetch"] is True
    assert report["safety"]["no_cookie_access"] is True


def test_unauthorized_scrape_cannot_be_collectible():
    with pytest.raises(ValidationError):
        ExternalSourcePolicy(
            source_id="src_bad",
            name="Bad scrape",
            source_type="public_web",
            access_method="unauthorized_scrape",
            license_status="unknown",
            evidence_level="unverified_web",
            retention_policy="short_excerpt",
            can_collect=True,
        )


def test_v2_0_e_acceptance_writes_marker_and_reports(tmp_path: Path):
    report = validator.run_acceptance(
        output_root=tmp_path / "processed",
        reports_dir=tmp_path / "reports",
        run_id="v2_0_e_test",
        command="test command",
    )

    assert report["overall_status"] == "PASS"
    assert report["checks"]["official_source_allowed"] is True
    assert report["checks"]["bloomberg_unlicensed_denied"] is True
    assert report["checks"]["reddit_pending_denied"] is True
    assert report["checks"]["x_pending_denied"] is True
    assert report["network_used"] is False
    assert report["production_records_written"] is False
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()
    payload = json.loads((tmp_path / "reports" / validator.REPORT_JSON).read_text(encoding="utf-8"))
    assert payload["summary"]["allow_count"] == 1


def test_v2_0_e_cli_exits_zero_and_prints_no_secrets(tmp_path: Path, capsys):
    exit_code = validator.main(
        [
            "--output-root",
            str(tmp_path / "processed"),
            "--reports-dir",
            str(tmp_path / "reports"),
            "--run-id",
            "v2_0_e_cli",
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "PASS" in captured.out
    assert "token" not in captured.out.lower()
    assert "secret" not in captured.out.lower()
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()
