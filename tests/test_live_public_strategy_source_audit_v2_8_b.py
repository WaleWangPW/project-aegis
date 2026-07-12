from __future__ import annotations

from pathlib import Path

import scripts.validate_v2_8_b_live_public_strategy_source_audit as validator
from aegis.models.strategy_research import StrategyResearchRecord
from aegis.strategy.research_source_catalog import canonical_strategy_research_records
from aegis.strategy.source_audit import audit_strategy_research_sources_lenient


def test_lenient_live_audit_records_fetch_errors_without_crashing():
    records = canonical_strategy_research_records()[:3]

    def mixed_fetch(url: str, timeout: int):
        if "msci" in url.lower():
            raise RuntimeError("simulated 403")
        return 200, "text/html", b"bounded sample"

    report = audit_strategy_research_sources_lenient(
        records,
        run_id="unit",
        fetch_fn=mixed_fetch,
        network_used=True,
    )

    assert report["overall_status"] == "PASS"
    assert report["audited_count"] == 3
    assert report["reachable_count"] >= 1
    assert report["status_counts"]["fetch_error"] >= 1
    assert report["checks"]["fetch_errors_are_recorded"] is True
    assert report["checks"]["raw_text_not_stored"] is True
    assert report["checks"]["sample_bytes_not_stored"] is True


def test_lenient_live_audit_fails_secret_like_url_and_does_not_fetch():
    called = False

    def should_not_fetch(url: str, timeout: int):
        nonlocal called
        called = True
        return 200, "text/html", b"bad"

    record = StrategyResearchRecord(
        research_id="bad_secret_url",
        title="Bad Secret URL",
        source_type="public_web",
        publisher="Bad",
        url="https://example.com/research?token=SHOULD_NOT_BE_HERE",
        markets=["A"],
        strategy_families=["value"],
        evidence_level="context_only",
        summary="Bad record should be blocked.",
    )
    report = audit_strategy_research_sources_lenient([record], run_id="unit", fetch_fn=should_not_fetch)

    assert report["overall_status"] == "FAIL"
    assert report["audited_sources"][0]["status"] == "blocked_secret_like_url"
    assert called is False


def test_v2_8_b_acceptance_with_fixture_network_writes_reports(tmp_path: Path, monkeypatch):
    def fixture_audit(records, **kwargs):
        return audit_strategy_research_sources_lenient(
            records,
            fetch_fn=lambda url, timeout: (200, "text/html", b"bounded sample"),
            **kwargs,
        )

    monkeypatch.setattr(validator, "audit_strategy_research_sources_lenient", fixture_audit)
    report = validator.run_acceptance(
        output_root=tmp_path / "processed",
        reports_dir=tmp_path / "reports",
        run_id="v2_8_b_test",
        command="test command",
    )

    assert report["overall_status"] == "PASS"
    assert report["network_used"] is True
    assert report["checks"]["all_selected_sources_classified"] is True
    assert report["checks"]["requires_sandbox_before_suggestion"] is True
    assert report["production_records_written"] is False
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()


def test_v2_8_b_cli_exits_zero_with_fixture_network(tmp_path: Path, monkeypatch, capsys):
    def fixture_audit(records, **kwargs):
        return audit_strategy_research_sources_lenient(
            records,
            fetch_fn=lambda url, timeout: (200, "text/html", b"bounded sample"),
            **kwargs,
        )

    monkeypatch.setattr(validator, "audit_strategy_research_sources_lenient", fixture_audit)
    exit_code = validator.main(
        [
            "--output-root",
            str(tmp_path / "processed"),
            "--reports-dir",
            str(tmp_path / "reports"),
            "--run-id",
            "v2_8_b_cli",
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "PASS" in captured.out
    assert "secret" not in captured.out.lower()
    assert "token" not in captured.out.lower()
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()
