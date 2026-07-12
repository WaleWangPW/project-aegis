from __future__ import annotations

import json
from pathlib import Path

import scripts.validate_v2_8_c_source_audit_sandbox_refresh_queue as validator
from aegis.strategy.source_audit_refresh import build_source_audit_sandbox_refresh_queue


def _audit_report() -> dict:
    sources = [
        {
            "research_id": "a_reachable",
            "publisher": "A Source",
            "url": "https://example.com/a",
            "status": "reachable",
            "status_code": 200,
            "content_type": "text/html",
            "content_sample_hash": "a" * 64,
            "sample_bytes_stored": False,
            "raw_text_stored": False,
            "markets": ["A"],
            "strategy_families": ["value", "quality"],
            "error_type": None,
            "error_message": None,
        },
        {
            "research_id": "h_reachable",
            "publisher": "H Source",
            "url": "https://example.com/h",
            "status": "reachable",
            "status_code": 206,
            "content_type": "application/pdf",
            "content_sample_hash": "b" * 64,
            "sample_bytes_stored": False,
            "raw_text_stored": False,
            "markets": ["H"],
            "strategy_families": ["low_volatility", "dividend"],
            "error_type": None,
            "error_message": None,
        },
        {
            "research_id": "us_reachable",
            "publisher": "US Source",
            "url": "https://example.com/us",
            "status": "reachable",
            "status_code": 206,
            "content_type": "text/html",
            "content_sample_hash": "c" * 64,
            "sample_bytes_stored": False,
            "raw_text_stored": False,
            "markets": ["US", "GLOBAL"],
            "strategy_families": ["momentum", "multi_factor"],
            "error_type": None,
            "error_message": None,
        },
        {
            "research_id": "blocked_fetch_error",
            "publisher": "Blocked Source",
            "url": "https://example.com/blocked",
            "status": "fetch_error",
            "status_code": 403,
            "content_type": None,
            "content_sample_hash": None,
            "sample_bytes_stored": False,
            "raw_text_stored": False,
            "markets": ["A"],
            "strategy_families": ["size"],
            "error_type": "HTTPError",
            "error_message": "HTTP Error 403: Forbidden",
        },
    ]
    return {
        "overall_status": "PASS",
        "acceptance_target": "V2.8-B Live Public Strategy Source Audit",
        "run_id": "v2_8_b_unit",
        "audited_count": len(sources),
        "reachable_count": 3,
        "audited_sources": sources,
    }


def test_source_audit_refresh_queue_groups_reachable_sources_by_market():
    queue = build_source_audit_sandbox_refresh_queue(_audit_report(), run_id="v2_8_c_unit")

    assert queue["overall_status"] == "PASS"
    assert queue["refresh_proposal_count"] == 3
    assert queue["reachable_source_count"] == 3
    assert queue["blocked_source_count"] == 1
    assert queue["market_coverage"] == {"A": 1, "H": 1, "US": 1}
    assert {proposal["market"] for proposal in queue["refresh_proposals"]} == {"A", "H", "US"}
    assert all(proposal["proposal_hash"] for proposal in queue["refresh_proposals"])


def test_fetch_error_sources_are_preserved_but_not_queued():
    queue = build_source_audit_sandbox_refresh_queue(_audit_report(), run_id="v2_8_c_unit")
    queued_ids = {
        source_id for proposal in queue["refresh_proposals"] for source_id in proposal["source_research_ids"]
    }

    assert "blocked_fetch_error" not in queued_ids
    assert queue["blocked_sources"][0]["research_id"] == "blocked_fetch_error"
    assert queue["blocked_sources"][0]["eligible_for_refresh"] is False
    assert queue["checks"]["blocked_sources_not_queued"] is True


def test_source_audit_refresh_queue_keeps_sandbox_gate_and_no_direct_suggestion():
    queue = build_source_audit_sandbox_refresh_queue(_audit_report(), run_id="v2_8_c_unit")

    assert queue["network_used"] is False
    assert queue["safety"]["requires_sandbox"] is True
    assert queue["safety"]["auto_applied"] is False
    assert queue["safety"]["user_facing_suggestion_allowed"] is False
    assert queue["safety"]["no_real_trade"] is True
    assert queue["safety"]["no_broker_api"] is True
    assert queue["safety"]["no_trading_webhook"] is True
    assert queue["checks"]["no_strategy_auto_mutation"] is True


def test_v2_8_c_acceptance_writes_reports_and_marker(tmp_path: Path):
    audit_report = tmp_path / "v2_8_b_report.json"
    audit_report.write_text(json.dumps(_audit_report(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    report = validator.run_acceptance(
        output_root=tmp_path / "processed",
        reports_dir=tmp_path / "reports",
        source_audit_report=audit_report,
        run_id="v2_8_c_test",
        command="test command",
    )

    assert report["overall_status"] == "PASS"
    assert report["checks"]["all_reachable_sources_queued"] is True
    assert report["checks"]["blocked_sources_not_queued"] is True
    assert report["production_records_written"] is False
    assert report["dashboard_contract_changed"] is False
    assert report["hashes"]["source_audit_sandbox_refresh_queue"]
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()


def test_v2_8_c_cli_exits_zero_and_prints_no_secrets(tmp_path: Path, capsys):
    audit_report = tmp_path / "v2_8_b_report.json"
    audit_report.write_text(json.dumps(_audit_report(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    exit_code = validator.main(
        [
            "--output-root",
            str(tmp_path / "processed"),
            "--reports-dir",
            str(tmp_path / "reports"),
            "--source-audit-report",
            str(audit_report),
            "--run-id",
            "v2_8_c_cli",
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "PASS" in captured.out
    assert "secret" not in captured.out.lower()
    assert "token" not in captured.out.lower()
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()
