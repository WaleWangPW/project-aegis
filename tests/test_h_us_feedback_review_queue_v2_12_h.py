from __future__ import annotations

import json
from pathlib import Path

from aegis.paper.h_us_feedback_review_queue import (
    build_h_us_feedback_review_queue,
    build_h_us_feedback_review_queue_report,
)
import scripts.validate_v2_12_h_h_us_feedback_review_queue as validator


def _source_report() -> dict:
    return {
        "overall_status": "PASS",
        "acceptance_target": "V2.12-G H-US User Feedback Intake For Simulation Brief",
        "summary": {
            "feedback_count": 5,
            "simulation_followup_count": 2,
        },
        "simulation_followup_candidates": [
            {
                "followup_id": "h_us_feedback_followup_h",
                "feedback_id": "fb_h",
                "suggestion_id": "sug_h",
                "symbol": "H_API_SANDBOX_PAPER_BASKET",
                "market": "H",
                "followup_status": "simulation_evidence_candidate",
                "followup_action": "paper_watch_evidence",
                "requires_user_price_before_paper_trade": True,
                "requires_explicit_review_before_paper_trade": True,
                "evidence_refs": ["h_feedback.json"],
                "no_paper_trade_mutation": True,
                "no_recommendation_mutation": True,
                "no_real_trade_execution": True,
                "no_broker_api": True,
                "no_webhook": True,
                "no_order_placement": True,
            },
            {
                "followup_id": "h_us_feedback_followup_us",
                "feedback_id": "fb_us",
                "suggestion_id": "sug_us",
                "symbol": "US_API_SANDBOX_PAPER_BASKET",
                "market": "US",
                "followup_status": "simulation_evidence_candidate",
                "followup_action": "manual_external_action_evidence",
                "requires_user_price_before_paper_trade": True,
                "requires_explicit_review_before_paper_trade": True,
                "evidence_refs": ["us_feedback.json"],
                "no_paper_trade_mutation": True,
                "no_recommendation_mutation": True,
                "no_real_trade_execution": True,
                "no_broker_api": True,
                "no_webhook": True,
                "no_order_placement": True,
            },
        ],
    }


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def test_v2_12_h_queue_requires_user_price_date_evidence_and_confirmation():
    queue = build_h_us_feedback_review_queue(
        _source_report()["simulation_followup_candidates"],
        evidence_ref="v2_12_g_report.json",
    )

    assert len(queue) == 2
    assert all(item["queue_status"] == "pending_user_price_date_evidence" for item in queue)
    assert all(item["entry_price"] is None for item in queue)
    assert all(item["entry_date"] is None for item in queue)
    assert all(item["evidence_ref_or_screenshot"] is None for item in queue)
    assert all(item["explicit_simulation_confirmation"] is False for item in queue)
    assert all(item["ready_to_create_paper_trade"] is False for item in queue)
    assert all(item["requires_user_price_before_paper_trade"] is True for item in queue)
    assert all(item["requires_user_entry_date_before_paper_trade"] is True for item in queue)
    assert all(item["requires_user_evidence_before_paper_trade"] is True for item in queue)
    assert all(item["requires_explicit_review_before_paper_trade"] is True for item in queue)
    assert all(item["no_paper_trade_mutation"] is True for item in queue)


def test_v2_12_h_report_is_review_queue_only_and_non_executing():
    report = build_h_us_feedback_review_queue_report(
        _source_report(),
        run_id="unit",
        evidence_ref="v2_12_g_report.json",
    )

    assert report["overall_status"] == "PASS"
    assert report["summary"]["review_queue_count"] == 2
    assert report["summary"]["pending_user_price_date_evidence_count"] == 2
    assert report["checks"]["source_is_v2_12_g"] is True
    assert report["checks"]["all_items_require_user_price"] is True
    assert report["checks"]["entry_price_not_fabricated"] is True
    assert report["checks"]["not_ready_to_create_paper_trade"] is True
    assert report["paper_trades_written"] is False
    assert report["recommendations_written"] is False
    assert report["reviews_written"] is False
    assert report["memory_written"] is False
    assert report["safety"]["no_broker_api"] is True


def test_v2_12_h_fails_if_source_is_not_v2_12_g():
    source = _source_report()
    source["acceptance_target"] = "wrong"

    report = build_h_us_feedback_review_queue_report(
        source,
        run_id="unit",
        evidence_ref="v2_12_g_report.json",
    )

    assert report["overall_status"] == "FAIL"
    assert report["checks"]["source_is_v2_12_g"] is False


def test_v2_12_h_validator_writes_outputs_and_preserves_records(tmp_path: Path):
    source_json = tmp_path / "v2_12_g.json"
    marker = tmp_path / "v2_12_g.marker"
    _write_json(source_json, _source_report())
    marker.write_text("exit_code=0\n", encoding="utf-8")
    record = tmp_path / "records" / "recommendations.jsonl"
    record.parent.mkdir()
    record.write_text("existing\n", encoding="utf-8")

    report = validator.run_acceptance(
        output_root=tmp_path / "processed",
        reports_dir=tmp_path / "reports",
        run_id="v2_12_h_test",
        command="test command",
        source_v2_12_g_report_json=source_json,
        source_v2_12_g_pass_marker=marker,
        record_paths={"recommendations_jsonl": record},
    )

    assert report["overall_status"] == "PASS"
    assert report["checks"]["review_queue_json_written"] is True
    assert report["checks"]["production_record_files_unchanged"] is True
    assert report["hashes"]["review_queue_json"]
    assert record.read_text(encoding="utf-8") == "existing\n"
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()


def test_v2_12_h_cli_exits_zero_and_prints_no_secret_values(tmp_path: Path, capsys):
    source_json = tmp_path / "v2_12_g.json"
    marker = tmp_path / "v2_12_g.marker"
    _write_json(source_json, _source_report())
    marker.write_text("exit_code=0\n", encoding="utf-8")

    exit_code = validator.main(
        [
            "--output-root",
            str(tmp_path / "processed"),
            "--reports-dir",
            str(tmp_path / "reports"),
            "--run-id",
            "v2_12_h_cli",
            "--source-v2-12-g-report-json",
            str(source_json),
            "--source-v2-12-g-pass-marker",
            str(marker),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "PASS" in captured.out
    assert "token" not in captured.out.lower()
    assert "secret" not in captured.out.lower()
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()
