from __future__ import annotations

import json
from pathlib import Path

import pytest

import scripts.validate_v2_2_c_api_research_bridge as validator
from aegis.models.strategy_update import StrategyCandidateUpdateProposal
from aegis.strategy.library import default_strategy_candidates
from aegis.strategy.research_bridge import build_research_bridge_report, build_strategy_update_proposals


def test_api_research_bridge_creates_proposals_not_strategy_mutations():
    fetch_item = validator._fixture_fetch_item()
    proposals = build_strategy_update_proposals(
        fetch_items=[fetch_item],
        candidates=default_strategy_candidates(created_at="2026-07-11T00:00:00+08:00"),
        source_fetch_ref="fixture_fetch_ref",
        created_at="2026-07-11T00:00:00+08:00",
    )

    assert proposals
    assert all(proposal.requires_sandbox is True for proposal in proposals)
    assert all(proposal.auto_applied is False for proposal in proposals)
    assert all(proposal.user_facing_suggestion_allowed is False for proposal in proposals)
    assert all(proposal.proposed_research_refs for proposal in proposals)


def test_strategy_update_proposal_rejects_auto_apply():
    with pytest.raises(ValueError):
        StrategyCandidateUpdateProposal(
            proposal_id="bad_auto_apply",
            target_strategy_id="value_quality_defensive_a",
            source_connector_id="api_user_research_approved_env",
            source_fetch_ref="fixture",
            markets=["A"],
            proposed_research_refs=["hash"],
            requires_sandbox=True,
            auto_applied=True,
            user_facing_suggestion_allowed=False,
            created_at="2026-07-11T00:00:00+08:00",
        )


def test_research_bridge_report_keeps_suggestion_gate_required():
    report = build_research_bridge_report(
        fetch_items=[validator._fixture_fetch_item()],
        candidates=default_strategy_candidates(created_at="2026-07-11T00:00:00+08:00"),
        source_fetch_ref="fixture_fetch_ref",
        run_id="v2_2_c_unit",
        command="unit test",
    )

    assert report["overall_status"] == "PASS"
    assert report["summary"]["proposal_count"] >= 1
    assert report["safety"]["proposal_only"] is True
    assert report["safety"]["requires_sandbox"] is True
    assert report["safety"]["auto_applied"] is False
    assert report["safety"]["user_facing_suggestion_allowed"] is False


def test_v2_2_c_acceptance_writes_marker_hashes_and_reports(tmp_path: Path):
    report = validator.run_acceptance(
        output_root=tmp_path / "processed",
        reports_dir=tmp_path / "reports",
        run_id="v2_2_c_test",
        command="test command",
    )

    assert report["overall_status"] == "PASS"
    assert report["checks"]["proposal_created"] is True
    assert report["checks"]["requires_sandbox"] is True
    assert report["checks"]["not_auto_applied"] is True
    assert report["checks"]["no_user_facing_suggestion"] is True
    assert report["production_records_written"] is False
    assert report["hashes"]["strategy_update_proposals_json"]
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()
    payload = json.loads((tmp_path / "reports" / validator.REPORT_JSON).read_text(encoding="utf-8"))
    assert payload["summary"]["next_target"] == "V2.3-A Real User API Configuration Handoff"


def test_v2_2_c_cli_exits_zero_and_prints_no_secret_value(tmp_path: Path, capsys):
    exit_code = validator.main(
        [
            "--output-root",
            str(tmp_path / "processed"),
            "--reports-dir",
            str(tmp_path / "reports"),
            "--run-id",
            "v2_2_c_cli",
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "PASS" in captured.out
    assert "fixture-secret-value-must-not-appear" not in captured.out
    assert "secret" not in captured.out.lower()
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()
