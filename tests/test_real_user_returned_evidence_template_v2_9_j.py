from __future__ import annotations

import json
from pathlib import Path

import scripts.validate_v2_9_j_real_user_returned_evidence_intake_template as validator
from aegis.paper.returned_evidence_refresh import build_returned_evidence_refresh_report
from aegis.paper.returned_evidence_template import (
    materialize_example_returned_evidence,
    validate_materialized_example,
    validate_user_returned_evidence_template,
)


def _current_brief() -> dict:
    return {
        "summary": {"real_user_api_status": "blocked_missing_metadata"},
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


def _template() -> dict:
    return {
        "schema_version": "user_returned_evidence.user_template.v2_9_j",
        "local_file_path": "config/user_returned_evidence.local.json",
        "instructions": [
            "Do not include API keys, cookies, bearer tokens, broker credentials, or webhook URLs.",
        ],
        "records": [
            {
                "returned_evidence_id": "returned_outcome_REPLACE_WITH_SHORT_ID",
                "paper_trade_id": "REPLACE_WITH_PAPER_TRADE_ID_FROM_CURRENT_BRIEF",
                "evidence_type": "outcome",
                "submitted_at": "REPLACE_WITH_ISO8601_LOCAL_TIME",
                "user_note": "REPLACE_WITH_NOTE",
                "evidence_refs": ["REPLACE_WITH_PATH"],
                "outcome": "success",
                "decision_quality": "reasonable_decision",
                "actual_return": 0.0,
                "max_drawdown": 0.0,
                "user_confirmed": True,
            },
            {
                "returned_evidence_id": "returned_screenshot_REPLACE_WITH_SHORT_ID",
                "paper_trade_id": "REPLACE_WITH_PAPER_TRADE_ID_FROM_CURRENT_BRIEF",
                "evidence_type": "screenshot",
                "submitted_at": "REPLACE_WITH_ISO8601_LOCAL_TIME",
                "user_note": "REPLACE_WITH_NOTE",
                "evidence_refs": ["REPLACE_WITH_PATH"],
                "outcome": None,
                "decision_quality": None,
                "actual_return": None,
                "max_drawdown": None,
                "user_confirmed": True,
            },
            {
                "returned_evidence_id": "returned_note_REPLACE_WITH_SHORT_ID",
                "paper_trade_id": "REPLACE_WITH_PAPER_TRADE_ID_FROM_CURRENT_BRIEF",
                "evidence_type": "text_note",
                "submitted_at": "REPLACE_WITH_ISO8601_LOCAL_TIME",
                "user_note": "REPLACE_WITH_NOTE",
                "evidence_refs": [],
                "outcome": None,
                "decision_quality": None,
                "actual_return": None,
                "max_drawdown": None,
                "user_confirmed": True,
            },
        ],
        "safety": {
            "simulation_only": True,
            "user_returned_evidence_only": True,
            "no_api_keys": True,
            "no_cookies": True,
            "no_bearer_tokens": True,
            "no_broker_credentials": True,
            "no_webhook_urls": True,
            "no_real_trade_execution": True,
            "no_order_placement": True,
        },
    }


def test_v2_9_j_template_validation_passes_and_points_to_gitignored_local_file():
    result = validate_user_returned_evidence_template(
        _template(),
        current_brief=_current_brief(),
        gitignore_text="config/user_returned_evidence.local.json\n",
    )

    assert result["overall_status"] == "PASS"
    assert result["checks"]["has_outcome_screenshot_and_text_note"] is True
    assert result["checks"]["local_path_gitignored"] is True
    assert result["checks"]["no_secret_like_values"] is True
    assert result["known_paper_trade_ids"] == ["ptr_600519"]


def test_v2_9_j_materialized_example_is_v2_9_i_compatible(tmp_path: Path):
    evidence = tmp_path / "note.txt"
    evidence.write_text("user supplied example outcome evidence\n", encoding="utf-8")
    records = materialize_example_returned_evidence(
        _template(),
        current_brief=_current_brief(),
        evidence_path=evidence,
    )

    validation = validate_materialized_example(
        records,
        current_brief=_current_brief(),
        formal_review_memory_report=_review_memory_report(),
    )
    report = build_returned_evidence_refresh_report(
        current_brief=_current_brief(),
        formal_review_memory_report=_review_memory_report(),
        returned_inputs=records,
        run_id="unit",
    )

    assert validation["overall_status"] == "PASS"
    assert report["checks"]["outcome_refresh_present"] is True
    assert report["checks"]["refreshed_memory_present"] is True
    assert report["checks"]["actual_return_from_user_evidence_only"] is True
    assert report["summary"]["review_resolved_count"] == 1


def test_v2_9_j_acceptance_writes_template_report_without_records_mutation(tmp_path: Path):
    current = tmp_path / "current.json"
    review = tmp_path / "review.json"
    template = tmp_path / "template.json"
    current.write_text(json.dumps(_current_brief(), ensure_ascii=False), encoding="utf-8")
    review.write_text(json.dumps(_review_memory_report(), ensure_ascii=False), encoding="utf-8")
    template.write_text(json.dumps(_template(), ensure_ascii=False), encoding="utf-8")
    record_path = tmp_path / "records" / "reviews.jsonl"
    record_path.parent.mkdir()
    record_path.write_text("existing\n", encoding="utf-8")

    report = validator.run_acceptance(
        output_root=tmp_path / "processed",
        reports_dir=tmp_path / "reports",
        run_id="v2_9_j_test",
        command="test command",
        current_brief_json=current,
        review_memory_json=review,
        user_template=template,
        record_paths={"reviews_jsonl": record_path},
    )

    assert report["overall_status"] == "PASS"
    assert report["checks"]["template_validation_pass"] is True
    assert report["checks"]["v2_9_i_refresh_compatible"] is True
    assert report["checks"]["production_record_files_unchanged"] is True
    assert record_path.read_text(encoding="utf-8") == "existing\n"
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()


def test_v2_9_j_cli_exits_zero(tmp_path: Path, capsys):
    current = tmp_path / "current.json"
    review = tmp_path / "review.json"
    template = tmp_path / "template.json"
    current.write_text(json.dumps(_current_brief(), ensure_ascii=False), encoding="utf-8")
    review.write_text(json.dumps(_review_memory_report(), ensure_ascii=False), encoding="utf-8")
    template.write_text(json.dumps(_template(), ensure_ascii=False), encoding="utf-8")

    exit_code = validator.main(
        [
            "--output-root",
            str(tmp_path / "processed"),
            "--reports-dir",
            str(tmp_path / "reports"),
            "--run-id",
            "v2_9_j_cli",
            "--current-brief-json",
            str(current),
            "--review-memory-json",
            str(review),
            "--user-template",
            str(template),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "PASS" in captured.out
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()
