from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

import scripts.validate_v2_0_c_research_workspace as validator
from aegis.models.research import ResearchEvidenceLink
from aegis.research.workspace import build_research_workspace, render_research_workspace_markdown


def test_research_workspace_requires_verified_evidence_for_decision_support():
    notes, evidence = validator._fixture("2026-07-11T00:00:00+00:00")
    report = build_research_workspace(
        symbol="CRCL",
        market="US",
        notes=notes,
        evidence=evidence,
        created_at="2026-07-11T00:00:00+00:00",
    )

    assert report["workspace"]["symbol"] == "CRCL"
    assert report["quality"]["note_count"] == 1
    assert report["quality"]["verified_evidence_count"] == 2
    assert report["quality"]["accepted_for_decision_support"] is True
    assert report["safety"]["llm_unverified_not_evidence"] is True

    md = render_research_workspace_markdown(report)
    assert "Research Workspace" in md
    assert "Unverified LLM output is not accepted evidence" in md


def test_llm_unverified_cannot_be_marked_verified():
    with pytest.raises(ValidationError):
        ResearchEvidenceLink(
            evidence_id="ev_bad",
            evidence_type="llm_unverified",
            title="Bad LLM Evidence",
            source="llm",
            captured_at="2026-07-11T00:00:00+00:00",
            status="verified",
            summary="Should fail.",
        )


def test_v2_0_c_acceptance_writes_marker_and_reports(tmp_path: Path):
    report = validator.run_acceptance(
        output_root=tmp_path / "processed",
        reports_dir=tmp_path / "reports",
        run_id="v2_0_c_test",
        command="test command",
    )

    assert report["overall_status"] == "PASS"
    assert report["checks"]["per_symbol_workspace"] is True
    assert report["checks"]["llm_unverified_not_accepted"] is True
    assert report["checks"]["decision_support_accepts_only_verified_links"] is True
    assert report["production_records_written"] is False
    assert report["hashes"]["workspace_json"]
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()
    payload = json.loads((tmp_path / "reports" / validator.REPORT_JSON).read_text(encoding="utf-8"))
    assert payload["summary"]["symbol"] == "CRCL"


def test_v2_0_c_cli_exits_zero_and_prints_no_secrets(tmp_path: Path, capsys):
    exit_code = validator.main(
        [
            "--output-root",
            str(tmp_path / "processed"),
            "--reports-dir",
            str(tmp_path / "reports"),
            "--run-id",
            "v2_0_c_cli",
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "PASS" in captured.out
    assert "token" not in captured.out.lower()
    assert "secret" not in captured.out.lower()
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()
