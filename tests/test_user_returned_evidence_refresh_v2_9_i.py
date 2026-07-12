from __future__ import annotations

import json
from pathlib import Path

import scripts.validate_v2_9_i_user_returned_evidence_refresh as validator
from aegis.paper.returned_evidence_refresh import build_returned_evidence_refresh_report


def _current_brief() -> dict:
    return {
        "summary": {
            "candidate_count": 3,
            "blocked_count": 3,
            "candidate_markets": ["A", "H", "US"],
            "real_user_api_status": "blocked_missing_metadata",
            "review_pending_count": 1,
        },
        "review_memory_queue": [
            {
                "paper_trade_id": "ptr_600519",
                "review_id": "rev_600519",
                "memory_id": "mem_600519",
                "review_date": "2026-07-11",
                "horizon": "5d",
                "outcome": "pending",
                "decision_quality": "unclear",
                "actual_return": None,
                "lesson": "pending",
                "memory_lesson": "entry context",
                "no_return_fabrication": True,
                "simulation_only": True,
            }
        ],
        "safety": {
            "simulation_only": True,
            "manual_external_execution_only": True,
            "no_real_trade": True,
            "no_broker_api": True,
            "no_trading_webhook": True,
            "no_order_placement": True,
        },
    }


def _review_memory_report() -> dict:
    return {
        "formal_reviews": [
            {
                "review_id": "rev_600519",
                "recommendation_id": "rec_600519",
                "paper_trade_id": "ptr_600519",
                "review_date": "2026-07-11",
                "horizon": "5d",
                "outcome": "pending",
                "actual_return": None,
                "max_drawdown": None,
                "decision_quality": "unclear",
                "success_reason": None,
                "failure_reason": None,
                "expert_contribution": {"status": "pending"},
                "lessons": ["pending"],
                "created_at": "2026-07-11T00:00:00+08:00",
                "simulation_only": True,
                "no_return_fabrication": True,
            }
        ],
        "formal_memories": [
            {
                "memory_id": "mem_600519",
                "date": "2026-07-11",
                "source_type": "simulation_review_candidate",
                "linked_recommendation_id": "rec_600519",
                "lesson_type": "virtual_trade_entry_context",
                "lesson": "entry context",
                "tags": ["simulation_only"],
                "confidence": 0.5,
                "created_at": "2026-07-11T00:00:00+08:00",
                "paper_trade_id": "ptr_600519",
                "simulation_only": True,
            }
        ],
    }


def _returned_inputs(evidence_path: Path) -> list[dict]:
    return [
        {
            "returned_evidence_id": "returned_outcome_001",
            "paper_trade_id": "ptr_600519",
            "evidence_type": "outcome",
            "submitted_at": "2026-07-11T21:55:00+08:00",
            "user_note": "User manually returned outcome evidence.",
            "evidence_refs": [str(evidence_path)],
            "outcome": "success",
            "decision_quality": "reasonable_decision",
            "actual_return": 0.012,
            "max_drawdown": -0.008,
            "user_confirmed": True,
        },
        {
            "returned_evidence_id": "returned_secret_001",
            "paper_trade_id": "ptr_600519",
            "evidence_type": "text_note",
            "submitted_at": "2026-07-11T21:56:00+08:00",
            "user_note": "api_key=SHOULD_BLOCK",
            "evidence_refs": [],
            "user_confirmed": True,
        },
    ]


def test_v2_9_i_refresh_accepts_outcome_and_blocks_secret(tmp_path: Path):
    evidence_path = tmp_path / "evidence.txt"
    evidence_path.write_text("manual outcome evidence\n", encoding="utf-8")

    report = build_returned_evidence_refresh_report(
        current_brief=_current_brief(),
        formal_review_memory_report=_review_memory_report(),
        returned_inputs=_returned_inputs(evidence_path),
        run_id="unit",
    )

    assert report["overall_status"] == "PASS"
    assert report["summary"]["accepted_returned_evidence_count"] == 1
    assert report["summary"]["blocked_returned_evidence_count"] == 1
    assert report["summary"]["review_resolved_count"] == 1
    assert report["checks"]["secret_like_input_blocked"] is True
    assert report["checks"]["actual_return_from_user_evidence_only"] is True
    assert report["refreshed_reviews"][0]["actual_return"] == 0.012
    assert report["refreshed_reviews"][0]["actual_return_source"] == "user_returned_evidence"
    assert report["refreshed_brief"]["review_memory_queue"][0]["outcome"] == "success"


def test_v2_9_i_acceptance_writes_artifacts_without_records_mutation(tmp_path: Path):
    current = tmp_path / "current.json"
    review = tmp_path / "review.json"
    current.write_text(json.dumps(_current_brief(), ensure_ascii=False), encoding="utf-8")
    review.write_text(json.dumps(_review_memory_report(), ensure_ascii=False), encoding="utf-8")
    record_path = tmp_path / "records" / "reviews.jsonl"
    record_path.parent.mkdir()
    record_path.write_text("existing\n", encoding="utf-8")

    report = validator.run_acceptance(
        output_root=tmp_path / "processed",
        reports_dir=tmp_path / "reports",
        run_id="v2_9_i_test",
        command="test command",
        current_brief_json=current,
        review_memory_json=review,
        record_paths={"reviews_jsonl": record_path},
    )

    assert report["overall_status"] == "PASS"
    assert report["checks"]["refreshed_reviews_json_written"] is True
    assert report["checks"]["refreshed_memories_json_written"] is True
    assert report["checks"]["refreshed_brief_json_written"] is True
    assert report["checks"]["production_record_files_unchanged"] is True
    assert record_path.read_text(encoding="utf-8") == "existing\n"
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()


def test_v2_9_i_cli_exits_zero(tmp_path: Path, capsys):
    current = tmp_path / "current.json"
    review = tmp_path / "review.json"
    current.write_text(json.dumps(_current_brief(), ensure_ascii=False), encoding="utf-8")
    review.write_text(json.dumps(_review_memory_report(), ensure_ascii=False), encoding="utf-8")

    exit_code = validator.main(
        [
            "--output-root",
            str(tmp_path / "processed"),
            "--reports-dir",
            str(tmp_path / "reports"),
            "--run-id",
            "v2_9_i_cli",
            "--current-brief-json",
            str(current),
            "--review-memory-json",
            str(review),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "PASS" in captured.out
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()
