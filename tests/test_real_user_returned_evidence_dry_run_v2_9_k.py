from __future__ import annotations

import json
from pathlib import Path

import scripts.validate_v2_9_k_real_user_returned_evidence_dry_run as validator


def _current_brief() -> dict:
    return {
        "review_memory_queue": [
            {
                "paper_trade_id": "ptr_600519",
                "review_id": "rev_600519",
                "memory_id": "mem_600519",
                "outcome": "pending",
                "decision_quality": "unclear",
                "actual_return": None,
                "no_return_fabrication": True,
                "simulation_only": True,
            }
        ],
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


def _local_records(evidence_path: Path) -> list[dict]:
    return [
        {
            "returned_evidence_id": "returned_real_user_001",
            "paper_trade_id": "ptr_600519",
            "evidence_type": "outcome",
            "submitted_at": "2026-07-11T22:20:00+08:00",
            "user_note": "Real user local dry-run example.",
            "evidence_refs": [str(evidence_path)],
            "outcome": "success",
            "decision_quality": "reasonable_decision",
            "actual_return": 0.011,
            "max_drawdown": -0.004,
            "user_confirmed": True,
        }
    ]


def test_v2_9_k_missing_local_file_writes_blocked_report(tmp_path: Path):
    missing = tmp_path / "config" / "user_returned_evidence.local.json"
    template = tmp_path / "template.json"
    record_path = tmp_path / "records" / "reviews.jsonl"
    template.write_text("{}", encoding="utf-8")
    record_path.parent.mkdir()
    record_path.write_text("existing\n", encoding="utf-8")

    report = validator.run_acceptance(
        output_root=tmp_path / "processed",
        reports_dir=tmp_path / "reports",
        run_id="v2_9_k_blocked",
        command="test command",
        local_returned_evidence_json=missing,
        user_template=template,
        record_paths={"reviews_jsonl": record_path},
    )

    assert report["overall_status"] == "PASS"
    assert report["real_user_returned_evidence_status"] == "blocked_missing_user_returned_evidence"
    assert report["checks"]["no_fake_real_user_evidence"] is True
    assert report["checks"]["production_record_files_unchanged"] is True
    assert record_path.read_text(encoding="utf-8") == "existing\n"
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()


def test_v2_9_k_present_local_file_runs_real_user_dry_run(tmp_path: Path):
    current = tmp_path / "current.json"
    review = tmp_path / "review.json"
    evidence = tmp_path / "evidence.txt"
    local = tmp_path / "config" / "user_returned_evidence.local.json"
    template = tmp_path / "template.json"
    record_path = tmp_path / "records" / "reviews.jsonl"
    current.write_text(json.dumps(_current_brief(), ensure_ascii=False), encoding="utf-8")
    review.write_text(json.dumps(_review_memory_report(), ensure_ascii=False), encoding="utf-8")
    evidence.write_text("user evidence\n", encoding="utf-8")
    template.write_text("{}", encoding="utf-8")
    local.parent.mkdir()
    local.write_text(json.dumps({"records": _local_records(evidence)}, ensure_ascii=False), encoding="utf-8")
    record_path.parent.mkdir()
    record_path.write_text("existing\n", encoding="utf-8")

    report = validator.run_acceptance(
        output_root=tmp_path / "processed",
        reports_dir=tmp_path / "reports",
        run_id="v2_9_k_completed",
        command="test command",
        current_brief_json=current,
        review_memory_json=review,
        local_returned_evidence_json=local,
        user_template=template,
        record_paths={"reviews_jsonl": record_path},
    )

    assert report["overall_status"] == "PASS"
    assert report["real_user_returned_evidence_status"] == "completed"
    assert report["summary"]["accepted_count"] == 1
    assert report["summary"]["refreshed_review_count"] == 1
    assert report["checks"]["actual_return_from_user_evidence_only"] is True
    assert report["checks"]["production_record_files_unchanged"] is True
    assert record_path.read_text(encoding="utf-8") == "existing\n"


def test_v2_9_k_cli_exits_zero_when_missing_local_file(tmp_path: Path, capsys):
    template = tmp_path / "template.json"
    template.write_text("{}", encoding="utf-8")

    exit_code = validator.main(
        [
            "--output-root",
            str(tmp_path / "processed"),
            "--reports-dir",
            str(tmp_path / "reports"),
            "--run-id",
            "v2_9_k_cli",
            "--local-returned-evidence-json",
            str(tmp_path / "missing.json"),
            "--user-template",
            str(template),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "blocked_missing_user_returned_evidence" in captured.out
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()
