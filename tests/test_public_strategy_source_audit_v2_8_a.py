from __future__ import annotations

import json
from pathlib import Path

import scripts.validate_v2_8_a_public_strategy_source_audit as validator
from aegis.models.strategy_research import StrategyResearchRecord
from aegis.strategy.research_source_catalog import canonical_strategy_research_records
from aegis.strategy.source_audit import audit_strategy_research_sources


def test_public_strategy_source_audit_covers_a_h_us_and_records_hashes():
    report = audit_strategy_research_sources(
        canonical_strategy_research_records(),
        run_id="unit",
        fetch_fn=validator._fixture_fetch,
        network_used=False,
    )

    assert report["overall_status"] == "PASS"
    assert report["checks"]["covers_a_h_us"] is True
    assert report["checks"]["content_hashes_recorded"] is True
    assert report["checks"]["raw_text_not_stored"] is True
    assert report["checks"]["sample_bytes_not_stored"] is True
    assert report["safety"]["requires_sandbox_before_suggestion"] is True
    assert all(item["content_sample_hash"] for item in report["audited_sources"])


def test_public_strategy_source_audit_blocks_secret_like_url_without_fetch():
    called = False

    def should_not_fetch(url: str, timeout: int):
        nonlocal called
        called = True
        return 200, "text/plain", b"should not happen"

    record = StrategyResearchRecord(
        research_id="bad_secret_url",
        title="Bad Secret URL",
        source_type="public_web",
        publisher="Bad",
        url="https://example.com/research?api_key=SHOULD_NOT_BE_HERE",
        markets=["US"],
        strategy_families=["value"],
        evidence_level="context_only",
        summary="Bad record should be blocked.",
    )

    report = audit_strategy_research_sources([record], run_id="unit", fetch_fn=should_not_fetch, network_used=False)

    assert report["overall_status"] == "FAIL"
    assert report["audited_sources"][0]["status"] == "blocked_secret_like_url"
    assert called is False
    assert report["checks"]["secret_like_urls_blocked"] is False


def test_v2_8_a_acceptance_writes_reports_and_stores_no_raw_text(tmp_path: Path):
    report = validator.run_acceptance(
        output_root=tmp_path / "processed",
        reports_dir=tmp_path / "reports",
        run_id="v2_8_a_test",
        command="test command",
    )
    report_text = (tmp_path / "reports" / validator.REPORT_JSON).read_text(encoding="utf-8")

    assert report["overall_status"] == "PASS"
    assert report["checks"]["all_audited_sources_reachable"] is True
    assert report["checks"]["requires_sandbox_before_suggestion"] is True
    assert report["network_used"] is False
    assert report["production_records_written"] is False
    assert "Fixture bounded public strategy source response" not in report_text
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()


def test_v2_8_a_cli_exits_zero_and_prints_no_secret_or_token(tmp_path: Path, capsys):
    exit_code = validator.main(
        [
            "--output-root",
            str(tmp_path / "processed"),
            "--reports-dir",
            str(tmp_path / "reports"),
            "--run-id",
            "v2_8_a_cli",
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "PASS" in captured.out
    assert "secret" not in captured.out.lower()
    assert "token" not in captured.out.lower()
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()
