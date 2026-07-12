from __future__ import annotations

import json
from pathlib import Path

import scripts.validate_v2_6_b_manual_feedback_intake as validator
from aegis.feedback.intake import build_manual_feedback_intake_report, build_manual_feedback_records


def _brief() -> dict:
    return {
        "items": [
            {
                "item_id": "brief_sug_a_600036",
                "suggestion_id": "sug_a",
                "symbol": "600036.SH",
                "market": "A",
                "brief_status": "candidate",
                "evidence_refs": ["brief.json"],
            },
            {
                "item_id": "brief_sug_blocked",
                "suggestion_id": "sug_blocked",
                "symbol": "US_BLOCKED",
                "market": "US",
                "brief_status": "blocked",
                "evidence_refs": ["brief.json"],
            },
        ]
    }


def test_manual_feedback_records_accept_evidence_and_hash_screenshot(tmp_path: Path):
    screenshot = tmp_path / "screen.txt"
    screenshot.write_text("screenshot fixture without secrets\n", encoding="utf-8")
    records = build_manual_feedback_records(
        [
            {
                "feedback_id": "fb_1",
                "suggestion_id": "sug_a",
                "symbol": "600036.SH",
                "market": "A",
                "feedback_type": "manual_watch",
                "user_note": "加入观察，不下单。",
                "screenshot_paths": [str(screenshot)],
                "submitted_at": "2026-07-11T19:18:00+08:00",
            }
        ],
        brief=_brief(),
        evidence_ref="brief.json",
    )

    record = records[0]
    assert record.feedback_status == "accepted"
    assert record.screenshot_evidence[0]["exists"] is True
    assert record.screenshot_evidence[0]["sha256"]
    assert record.no_broker_api is True
    assert record.no_order_placement is True


def test_manual_feedback_blocks_blocked_path_execution_and_secret_like_text():
    report = build_manual_feedback_intake_report(
        [
            {
                "feedback_id": "fb_ok",
                "suggestion_id": "sug_a",
                "symbol": "600036.SH",
                "market": "A",
                "feedback_type": "manual_watch",
                "user_note": "accepted watch note",
                "submitted_at": "2026-07-11T19:18:00+08:00",
            },
            {
                "feedback_id": "fb_blocked_path",
                "suggestion_id": "sug_blocked",
                "symbol": "US_BLOCKED",
                "market": "US",
                "feedback_type": "external_manual_execution",
                "user_note": "attempt blocked execution",
                "external_execution_summary": "blocked path",
                "submitted_at": "2026-07-11T19:18:00+08:00",
            },
            {
                "feedback_id": "fb_secret",
                "suggestion_id": "sug_a",
                "symbol": "600036.SH",
                "market": "A",
                "feedback_type": "review_note",
                "user_note": "authorization: bearer abc",
                "submitted_at": "2026-07-11T19:18:00+08:00",
            },
        ],
        brief=_brief(),
        run_id="v2_6_b_unit",
        evidence_ref="brief.json",
    )

    assert report["overall_status"] == "PASS"
    blocked_reasons = {reason for item in report["records"] for reason in item["blocked_by"]}
    assert "cannot_record_external_execution_for_blocked_path" in blocked_reasons
    assert "secret_like_text_detected" in blocked_reasons
    assert report["checks"]["blocked_path_execution_blocked"] is True
    assert report["checks"]["secret_like_feedback_blocked"] is True


def test_v2_6_b_acceptance_writes_reports_and_hashes(tmp_path: Path):
    brief_json = tmp_path / "brief.json"
    brief_json.write_text(json.dumps(_brief(), ensure_ascii=False), encoding="utf-8")

    report = validator.run_acceptance(
        output_root=tmp_path / "processed",
        reports_dir=tmp_path / "reports",
        run_id="v2_6_b_test",
        command="test command",
        brief_json=brief_json,
    )

    assert report["overall_status"] == "PASS"
    assert report["checks"]["production_records_not_written"] is True
    assert report["checks"]["paper_trades_not_written"] is True
    assert report["checks"]["recommendations_not_written"] is True
    assert report["hashes"]["manual_feedback_records_json"]
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()


def test_v2_6_b_cli_exits_zero_and_prints_no_secrets(tmp_path: Path, capsys):
    brief_json = tmp_path / "brief.json"
    brief_json.write_text(json.dumps(_brief(), ensure_ascii=False), encoding="utf-8")

    exit_code = validator.main(
        [
            "--output-root",
            str(tmp_path / "processed"),
            "--reports-dir",
            str(tmp_path / "reports"),
            "--run-id",
            "v2_6_b_cli",
            "--brief-json",
            str(brief_json),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "PASS" in captured.out
    assert "token" not in captured.out.lower()
    assert "secret" not in captured.out.lower()
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()
