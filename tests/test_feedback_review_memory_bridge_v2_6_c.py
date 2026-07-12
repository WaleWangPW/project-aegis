from __future__ import annotations

import json
from pathlib import Path

import scripts.validate_v2_6_c_feedback_review_memory_bridge as validator
from aegis.feedback.bridge import build_feedback_bridge_report


def _feedback_report() -> dict:
    return {
        "records": [
            {
                "feedback_id": "fb_accepted_1",
                "suggestion_id": "sug_a",
                "symbol": "600036.SH",
                "market": "A",
                "feedback_type": "manual_watch",
                "feedback_status": "accepted",
                "evidence_refs": ["feedback_report.json"],
                "screenshot_evidence": [{"path": "screen.png", "exists": True, "sha256": "abc"}],
                "blocked_by": [],
            },
            {
                "feedback_id": "fb_blocked_1",
                "suggestion_id": "sug_b",
                "symbol": "US_BLOCKED",
                "market": "US",
                "feedback_type": "external_manual_execution",
                "feedback_status": "blocked",
                "evidence_refs": ["feedback_report.json"],
                "screenshot_evidence": [],
                "blocked_by": ["cannot_record_external_execution_for_blocked_path"],
            },
        ]
    }


def test_feedback_bridge_creates_review_links_and_memory_candidates_only_for_accepted():
    report = build_feedback_bridge_report(
        _feedback_report(),
        run_id="v2_6_c_unit",
        evidence_ref="feedback_report.json",
    )

    assert report["overall_status"] == "PASS"
    assert report["summary"]["accepted_feedback_count"] == 1
    assert report["summary"]["review_link_count"] == 1
    assert report["summary"]["memory_candidate_count"] == 1
    assert report["review_evidence_links"][0]["feedback_id"] == "fb_accepted_1"
    assert report["memory_candidates"][0]["requires_review_before_memory_write"] is True
    assert report["safety"]["no_review_record_mutation"] is True
    assert report["safety"]["no_memory_jsonl_mutation"] is True


def test_v2_6_c_acceptance_writes_reports_and_hashes(tmp_path: Path):
    feedback_json = tmp_path / "feedback.json"
    feedback_json.write_text(json.dumps(_feedback_report(), ensure_ascii=False), encoding="utf-8")

    report = validator.run_acceptance(
        output_root=tmp_path / "processed",
        reports_dir=tmp_path / "reports",
        run_id="v2_6_c_test",
        command="test command",
        feedback_report_json=feedback_json,
    )

    assert report["overall_status"] == "PASS"
    assert report["checks"]["reviews_not_written"] is True
    assert report["checks"]["memory_records_not_written"] is True
    assert report["checks"]["paper_trades_not_written"] is True
    assert report["hashes"]["review_evidence_links_json"]
    assert report["hashes"]["memory_candidates_json"]
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()


def test_v2_6_c_cli_exits_zero_and_prints_no_secrets(tmp_path: Path, capsys):
    feedback_json = tmp_path / "feedback.json"
    feedback_json.write_text(json.dumps(_feedback_report(), ensure_ascii=False), encoding="utf-8")

    exit_code = validator.main(
        [
            "--output-root",
            str(tmp_path / "processed"),
            "--reports-dir",
            str(tmp_path / "reports"),
            "--run-id",
            "v2_6_c_cli",
            "--feedback-report-json",
            str(feedback_json),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "PASS" in captured.out
    assert "token" not in captured.out.lower()
    assert "secret" not in captured.out.lower()
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()
