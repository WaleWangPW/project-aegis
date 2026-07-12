from __future__ import annotations

import json
from pathlib import Path

import scripts.validate_v2_9_c_paper_simulation_entry_prep as validator
from aegis.paper.entry_prep import build_entry_prep_report, build_pending_entry_requests


def _paper_intake() -> list[dict]:
    return [
        {
            "paper_intake_id": "packet_paper_intake_fb_1",
            "feedback_id": "fb_1",
            "symbol": "600519.SH",
            "market": "A",
            "evidence_refs": ["feedback.json"],
            "no_paper_trade_mutation": True,
            "no_recommendation_mutation": True,
            "no_real_trade_execution": True,
            "no_broker_api": True,
            "no_webhook": True,
            "no_order_placement": True,
        },
        {
            "paper_intake_id": "packet_paper_intake_fb_2",
            "feedback_id": "fb_2",
            "symbol": "MSFT",
            "market": "US",
            "evidence_refs": ["feedback.json"],
            "no_paper_trade_mutation": True,
            "no_recommendation_mutation": True,
            "no_real_trade_execution": True,
            "no_broker_api": True,
            "no_webhook": True,
            "no_order_placement": True,
        },
    ]


def test_pending_entry_requests_require_user_price_and_date():
    requests = build_pending_entry_requests(_paper_intake(), evidence_ref="paper_intake.json")

    assert len(requests) == 2
    assert all(item["entry_request_status"] == "pending_user_price_date" for item in requests)
    assert all(item["entry_price"] is None for item in requests)
    assert all(item["entry_date"] is None for item in requests)
    assert all(item["ready_to_create_paper_trade"] is False for item in requests)
    assert all(item["no_price_fabrication"] is True for item in requests)
    assert all(item["no_paper_trade_mutation"] is True for item in requests)


def test_entry_prep_report_is_pending_only_and_non_executing():
    report = build_entry_prep_report(_paper_intake(), run_id="unit", evidence_ref="paper_intake.json")

    assert report["overall_status"] == "PASS"
    assert report["summary"]["pending_entry_request_count"] == 2
    assert report["checks"]["entry_price_missing_not_fabricated"] is True
    assert report["checks"]["entry_date_missing_not_fabricated"] is True
    assert report["checks"]["not_ready_to_create_paper_trade"] is True
    assert report["paper_trades_written"] is False
    assert report["safety"]["no_broker_api"] is True


def test_v2_9_c_acceptance_writes_reports_and_hashes(tmp_path: Path):
    intake_json = tmp_path / "paper_intake.json"
    intake_json.write_text(json.dumps(_paper_intake(), ensure_ascii=False), encoding="utf-8")

    report = validator.run_acceptance(
        output_root=tmp_path / "processed",
        reports_dir=tmp_path / "reports",
        run_id="v2_9_c_test",
        command="test command",
        paper_intake_json=intake_json,
    )

    assert report["overall_status"] == "PASS"
    assert report["checks"]["paper_trades_not_written"] is True
    assert report["checks"]["recommendations_not_written"] is True
    assert report["hashes"]["pending_entry_requests_json"]
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()


def test_v2_9_c_cli_exits_zero(tmp_path: Path, capsys):
    intake_json = tmp_path / "paper_intake.json"
    intake_json.write_text(json.dumps(_paper_intake(), ensure_ascii=False), encoding="utf-8")

    exit_code = validator.main(
        [
            "--output-root",
            str(tmp_path / "processed"),
            "--reports-dir",
            str(tmp_path / "reports"),
            "--run-id",
            "v2_9_c_cli",
            "--paper-intake-json",
            str(intake_json),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "PASS" in captured.out
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()
