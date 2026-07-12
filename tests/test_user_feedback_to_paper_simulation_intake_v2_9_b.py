from __future__ import annotations

import json
from pathlib import Path

import scripts.validate_v2_9_b_user_feedback_to_paper_simulation_intake as validator
from aegis.feedback.decision_packet import build_decision_packet_feedback_intake_report


def _packet() -> dict:
    return {
        "items": [
            {
                "symbol": "600036.SH",
                "market": "A",
                "decision_packet_status": "simulation_candidate",
                "source_mode": "approved_fixture_not_live_market_data",
                "evidence_refs": ["packet.json"],
            },
            {
                "symbol": "00700.HK",
                "market": "H",
                "decision_packet_status": "simulation_candidate",
                "source_mode": "approved_fixture_not_live_market_data",
                "evidence_refs": ["packet.json"],
            },
            {
                "symbol": "MSFT",
                "market": "US",
                "decision_packet_status": "simulation_candidate",
                "source_mode": "approved_fixture_not_live_market_data",
                "evidence_refs": ["packet.json"],
            },
            {
                "symbol": "A_BLOCKED",
                "market": "A",
                "decision_packet_status": "blocked",
                "source_mode": "approved_fixture_not_live_market_data",
                "evidence_refs": ["packet.json"],
            },
        ]
    }


def test_decision_packet_feedback_creates_paper_intake_without_mutation(tmp_path: Path):
    screenshot = tmp_path / "screen.txt"
    screenshot.write_text("feedback screenshot without secrets\n", encoding="utf-8")
    report = build_decision_packet_feedback_intake_report(
        [
            {
                "feedback_id": "fb_watch",
                "symbol": "600036.SH",
                "market": "A",
                "action": "watch",
                "user_note": "加入观察",
                "screenshot_paths": [str(screenshot)],
                "submitted_at": "2026-07-11T21:03:00+08:00",
            },
            {
                "feedback_id": "fb_ignore",
                "symbol": "00700.HK",
                "market": "H",
                "action": "ignore",
                "user_note": "暂时忽略",
                "submitted_at": "2026-07-11T21:03:00+08:00",
            },
            {
                "feedback_id": "fb_external",
                "symbol": "MSFT",
                "market": "US",
                "action": "manual_external_action",
                "user_note": "外部手动记录",
                "external_execution_summary": "external manual record only",
                "submitted_at": "2026-07-11T21:03:00+08:00",
            },
            {
                "feedback_id": "fb_blocked",
                "symbol": "A_BLOCKED",
                "market": "A",
                "action": "manual_external_action",
                "user_note": "blocked path",
                "external_execution_summary": "must block",
                "submitted_at": "2026-07-11T21:03:00+08:00",
            },
            {
                "feedback_id": "fb_secret",
                "symbol": "600036.SH",
                "market": "A",
                "action": "watch",
                "user_note": "authorization: bearer abc",
                "submitted_at": "2026-07-11T21:03:00+08:00",
            },
        ],
        packet=_packet(),
        run_id="unit",
        evidence_ref="packet.json",
    )

    assert report["overall_status"] == "PASS"
    assert report["summary"]["accepted_count"] == 3
    assert report["summary"]["blocked_count"] == 2
    assert report["summary"]["paper_simulation_intake_count"] == 2
    assert report["checks"]["ignore_does_not_create_paper_intake"] is True
    assert report["checks"]["blocked_path_execution_blocked"] is True
    assert report["checks"]["secret_like_feedback_blocked"] is True
    assert report["safety"]["no_paper_trade_mutation"] is True


def test_v2_9_b_acceptance_writes_reports_and_hashes(tmp_path: Path):
    packet_json = tmp_path / "packet.json"
    packet_json.write_text(json.dumps(_packet(), ensure_ascii=False), encoding="utf-8")

    report = validator.run_acceptance(
        output_root=tmp_path / "processed",
        reports_dir=tmp_path / "reports",
        run_id="v2_9_b_test",
        command="test command",
        packet_json=packet_json,
    )

    assert report["overall_status"] == "PASS"
    assert report["checks"]["production_records_not_written"] is True
    assert report["checks"]["paper_trades_not_written"] is True
    assert report["checks"]["recommendations_not_written"] is True
    assert report["hashes"]["paper_simulation_intake_json"]
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()


def test_v2_9_b_cli_exits_zero_and_prints_no_secret_values(tmp_path: Path, capsys):
    packet_json = tmp_path / "packet.json"
    packet_json.write_text(json.dumps(_packet(), ensure_ascii=False), encoding="utf-8")

    exit_code = validator.main(
        [
            "--output-root",
            str(tmp_path / "processed"),
            "--reports-dir",
            str(tmp_path / "reports"),
            "--run-id",
            "v2_9_b_cli",
            "--packet-json",
            str(packet_json),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "PASS" in captured.out
    assert "secret" not in captured.out.lower()
    assert "token" not in captured.out.lower()
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()
