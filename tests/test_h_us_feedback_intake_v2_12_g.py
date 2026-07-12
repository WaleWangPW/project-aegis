from __future__ import annotations

import json
from pathlib import Path

from aegis.feedback.h_us_brief_intake import build_h_us_brief_feedback_intake_report
import scripts.validate_v2_12_g_h_us_feedback_intake as validator


def _brief() -> dict:
    return {
        "overall_status": "PASS",
        "acceptance_target": "V2.12-F H-US Current Usable Simulation Brief Refresh",
        "network_used": False,
        "production_records_written": False,
        "dashboard_contract_changed": False,
        "items": [
            {
                "item_id": "brief_h",
                "suggestion_id": "sug_h",
                "symbol": "H_API_SANDBOX_PAPER_BASKET",
                "market": "H",
                "brief_status": "simulation_candidate",
                "evidence_refs": ["h_evidence.json"],
            },
            {
                "item_id": "brief_us",
                "suggestion_id": "sug_us",
                "symbol": "US_API_SANDBOX_PAPER_BASKET",
                "market": "US",
                "brief_status": "simulation_candidate",
                "evidence_refs": ["us_evidence.json"],
            },
        ],
    }


def _feedbacks(screenshot: Path) -> list[dict]:
    return [
        {
            "feedback_id": "fb_watch",
            "suggestion_id": "sug_h",
            "symbol": "H_API_SANDBOX_PAPER_BASKET",
            "market": "H",
            "feedback_type": "manual_watch",
            "user_note": "加入观察",
            "screenshot_paths": [str(screenshot)],
            "submitted_at": "2026-07-12T01:00:00+08:00",
        },
        {
            "feedback_id": "fb_ignore",
            "suggestion_id": "sug_us",
            "symbol": "US_API_SANDBOX_PAPER_BASKET",
            "market": "US",
            "feedback_type": "manual_ignore",
            "user_note": "先忽略",
            "screenshot_paths": [],
            "submitted_at": "2026-07-12T01:00:00+08:00",
        },
        {
            "feedback_id": "fb_external",
            "suggestion_id": "sug_us",
            "symbol": "US_API_SANDBOX_PAPER_BASKET",
            "market": "US",
            "feedback_type": "external_manual_execution",
            "user_note": "外部手动纸面记录",
            "external_execution_summary": "external manual observation only",
            "screenshot_paths": [],
            "submitted_at": "2026-07-12T01:00:00+08:00",
        },
        {
            "feedback_id": "fb_unknown",
            "suggestion_id": "missing",
            "symbol": "MISSING.US",
            "market": "US",
            "feedback_type": "manual_watch",
            "user_note": "不存在",
            "screenshot_paths": [],
            "submitted_at": "2026-07-12T01:00:00+08:00",
        },
        {
            "feedback_id": "fb_secret",
            "suggestion_id": "sug_h",
            "symbol": "H_API_SANDBOX_PAPER_BASKET",
            "market": "H",
            "feedback_type": "manual_watch",
            "user_note": "authorization: bearer abc",
            "screenshot_paths": [],
            "submitted_at": "2026-07-12T01:00:00+08:00",
        },
    ]


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def test_v2_12_g_feedback_intake_accepts_valid_feedback_and_blocks_risky_inputs(tmp_path: Path):
    screenshot = tmp_path / "screen.txt"
    screenshot.write_text("screenshot placeholder\n", encoding="utf-8")
    report = build_h_us_brief_feedback_intake_report(
        _feedbacks(screenshot),
        brief=_brief(),
        run_id="unit",
        evidence_ref="brief.json",
    )

    assert report["overall_status"] == "PASS"
    assert report["summary"]["accepted_count"] == 3
    assert report["summary"]["blocked_count"] == 2
    assert report["summary"]["simulation_followup_count"] == 2
    assert report["checks"]["ignore_does_not_create_followup"] is True
    assert report["checks"]["unknown_item_blocked"] is True
    assert report["checks"]["secret_like_feedback_blocked"] is True
    assert report["checks"]["screenshots_hashed_when_present"] is True
    assert report["safety"]["no_paper_trade_mutation"] is True


def test_v2_12_g_fails_if_source_is_not_v2_12_f(tmp_path: Path):
    screenshot = tmp_path / "screen.txt"
    screenshot.write_text("screenshot placeholder\n", encoding="utf-8")
    brief = _brief()
    brief["acceptance_target"] = "wrong"

    report = build_h_us_brief_feedback_intake_report(
        _feedbacks(screenshot),
        brief=brief,
        run_id="unit",
        evidence_ref="brief.json",
    )

    assert report["overall_status"] == "FAIL"
    assert report["checks"]["source_is_v2_12_f"] is False


def test_v2_12_g_validator_writes_outputs_and_preserves_records(tmp_path: Path):
    brief_json = tmp_path / "brief.json"
    marker = tmp_path / "brief.marker"
    _write_json(brief_json, _brief())
    marker.write_text("exit_code=0\n", encoding="utf-8")
    record = tmp_path / "records" / "recommendations.jsonl"
    record.parent.mkdir()
    record.write_text("existing\n", encoding="utf-8")

    report = validator.run_acceptance(
        output_root=tmp_path / "processed",
        reports_dir=tmp_path / "reports",
        run_id="v2_12_g_test",
        command="test command",
        source_v2_12_f_brief_json=brief_json,
        source_v2_12_f_pass_marker=marker,
        record_paths={"recommendations_jsonl": record},
    )

    assert report["overall_status"] == "PASS"
    assert report["checks"]["feedback_records_json_written"] is True
    assert report["checks"]["followups_json_written"] is True
    assert report["checks"]["production_record_files_unchanged"] is True
    assert report["hashes"]["simulation_followups_json"]
    assert record.read_text(encoding="utf-8") == "existing\n"
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()


def test_v2_12_g_cli_exits_zero_and_prints_no_secret_values(tmp_path: Path, capsys):
    brief_json = tmp_path / "brief.json"
    marker = tmp_path / "brief.marker"
    _write_json(brief_json, _brief())
    marker.write_text("exit_code=0\n", encoding="utf-8")

    exit_code = validator.main(
        [
            "--output-root",
            str(tmp_path / "processed"),
            "--reports-dir",
            str(tmp_path / "reports"),
            "--run-id",
            "v2_12_g_cli",
            "--source-v2-12-f-brief-json",
            str(brief_json),
            "--source-v2-12-f-pass-marker",
            str(marker),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "PASS" in captured.out
    assert "token" not in captured.out.lower()
    assert "secret" not in captured.out.lower()
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()
