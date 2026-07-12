from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

import scripts.validate_v2_0_d_event_timeline as validator
from aegis.events.timeline import build_event_timeline_report, render_event_timeline_markdown
from aegis.models.event_timeline import EventRecord


def test_event_timeline_builds_verified_events_and_scenarios():
    events, scenarios = validator._fixture("2026-07-11T00:00:00+00:00")
    report = build_event_timeline_report(symbol="CRCL", market="US", events=events, scenarios=scenarios)

    assert report["event_count"] == 2
    assert report["verified_event_count"] == 1
    assert report["unverified_event_count"] == 1
    assert report["scenario_count"] == 1
    assert report["quality"]["accepted_for_decision_support"] is True
    assert report["safety"]["does_not_bypass_evidence_gate"] is True

    md = render_event_timeline_markdown(report)
    assert "Event Timeline" in md
    assert "Social/community discussion is context only" in md


def test_community_discussion_cannot_be_marked_verified():
    with pytest.raises(ValidationError):
        EventRecord(
            event_id="evt_bad",
            symbol="CRCL",
            market="US",
            event_date="2026-07-11",
            event_type="social_statement",
            title="Bad community evidence",
            summary="Should fail.",
            source_id="bad",
            evidence_level="community_discussion",
            verified=True,
            decision_relevance="Should fail.",
            created_at="2026-07-11T00:00:00+00:00",
        )


def test_v2_0_d_acceptance_writes_marker_and_reports(tmp_path: Path):
    report = validator.run_acceptance(
        output_root=tmp_path / "processed",
        reports_dir=tmp_path / "reports",
        run_id="v2_0_d_test",
        command="test command",
    )

    assert report["overall_status"] == "PASS"
    assert report["checks"]["events_present"] is True
    assert report["checks"]["scenario_has_evidence"] is True
    assert report["checks"]["does_not_bypass_evidence_gate"] is True
    assert report["network_used"] is False
    assert report["production_records_written"] is False
    assert report["hashes"]["timeline_json"]
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()
    payload = json.loads((tmp_path / "reports" / validator.REPORT_JSON).read_text(encoding="utf-8"))
    assert payload["summary"]["symbol"] == "CRCL"


def test_v2_0_d_cli_exits_zero_and_prints_no_secrets(tmp_path: Path, capsys):
    exit_code = validator.main(
        [
            "--output-root",
            str(tmp_path / "processed"),
            "--reports-dir",
            str(tmp_path / "reports"),
            "--run-id",
            "v2_0_d_cli",
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "PASS" in captured.out
    assert "token" not in captured.out.lower()
    assert "secret" not in captured.out.lower()
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()
