"""Phase 6 tests for scripts/export_review.py — PHASE6 doc §5.8/§7.4.3.

No network, no LLM — reads existing ReviewRecords only.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import scripts.export_review as export_review_module
from aegis.models.review import ReviewRecord
from aegis.utils.jsonl import append_jsonl


def _now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def _review(*, rec_id="rec_1", review_date="2026-07-06", outcome="success", actual_return=0.05, lessons=None) -> dict:
    return ReviewRecord(
        review_id=f"rev_{rec_id}_5d",
        recommendation_id=rec_id,
        review_date=review_date,
        horizon="5d",
        outcome=outcome,
        actual_return=actual_return,
        max_drawdown=-0.02,
        decision_quality="good_decision" if outcome == "success" else "poor_decision",
        expert_contribution={"TrendAgent": "support"},
        lessons=lessons if lessons is not None else [],
        created_at=_now(),
    ).model_dump()


def test_build_report_empty_records_is_honest(tmp_path: Path):
    records_dir = tmp_path / "records"
    report = export_review_module.build_report(start="2026-07-01", end="2026-07-31", records_dir=records_dir)

    assert report["total_reviewed"] == 0
    assert report["action_success_rate"] is None
    assert report["lessons"] == []


def test_build_report_aggregates_seeded_reviews(tmp_path: Path):
    records_dir = tmp_path / "records"
    append_jsonl(records_dir / "reviews.jsonl", _review(rec_id="rec_1", outcome="success", actual_return=0.10, lessons=["lesson A"]))
    append_jsonl(records_dir / "reviews.jsonl", _review(rec_id="rec_2", outcome="failure", actual_return=-0.02))

    report = export_review_module.build_report(start="2026-07-01", end="2026-07-31", records_dir=records_dir)

    assert report["total_reviewed"] == 2
    assert round(report["action_success_rate"], 4) == 0.5
    assert "lesson A" in report["lessons"]


def test_build_report_counts_inconclusive(tmp_path: Path):
    records_dir = tmp_path / "records"
    append_jsonl(records_dir / "reviews.jsonl", _review(rec_id="rec_1", outcome="pending", actual_return=None))

    report = export_review_module.build_report(start="2026-07-01", end="2026-07-31", records_dir=records_dir)

    assert report["inconclusive_count"] == 1


def test_render_markdown_has_no_marketing_language(tmp_path: Path):
    records_dir = tmp_path / "records"
    append_jsonl(records_dir / "reviews.jsonl", _review(rec_id="rec_1", outcome="success", actual_return=0.10))
    report = export_review_module.build_report(start="2026-07-01", end="2026-07-31", records_dir=records_dir)

    markdown = export_review_module.render_markdown(report)

    banned_phrases = ["稳赚", "guaranteed", "百分之百", "必涨", "躺赚"]
    for phrase in banned_phrases:
        assert phrase not in markdown


def test_cli_writes_md_summary(tmp_path: Path):
    records_dir = tmp_path / "records"
    append_jsonl(records_dir / "reviews.jsonl", _review(rec_id="rec_1"))
    output_dir = tmp_path / "processed"

    exit_code = export_review_module.main(
        [
            "--start", "2026-07-01",
            "--end", "2026-07-31",
            "--format", "md",
            "--records-dir", str(records_dir),
            "--output-dir", str(output_dir),
        ]
    )

    assert exit_code == 0
    output_path = output_dir / "reviews_20260701_20260731.md"
    assert output_path.exists()
    assert "# Project Aegis Review" in output_path.read_text(encoding="utf-8")


def test_cli_writes_json_summary(tmp_path: Path):
    records_dir = tmp_path / "records"
    append_jsonl(records_dir / "reviews.jsonl", _review(rec_id="rec_1"))
    output_dir = tmp_path / "processed"

    exit_code = export_review_module.main(
        [
            "--start", "2026-07-01",
            "--end", "2026-07-31",
            "--format", "json",
            "--records-dir", str(records_dir),
            "--output-dir", str(output_dir),
        ]
    )

    assert exit_code == 0
    output_path = output_dir / "reviews_20260701_20260731.json"
    assert output_path.exists()
    written = json.loads(output_path.read_text(encoding="utf-8"))
    assert written["total_reviewed"] == 1


def test_cli_does_not_crash_on_empty_records(tmp_path: Path):
    records_dir = tmp_path / "records"  # never created
    output_dir = tmp_path / "processed"

    exit_code = export_review_module.main(
        [
            "--start", "2026-07-01",
            "--end", "2026-07-31",
            "--records-dir", str(records_dir),
            "--output-dir", str(output_dir),
        ]
    )

    assert exit_code == 0
