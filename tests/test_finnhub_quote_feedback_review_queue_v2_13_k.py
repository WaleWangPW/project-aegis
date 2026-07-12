from __future__ import annotations

import json
from pathlib import Path

from aegis.paper.finnhub_quote_feedback_review_queue import (
    build_finnhub_quote_feedback_review_queue,
    build_finnhub_quote_feedback_review_queue_report,
)
import scripts.validate_v2_13_k_finnhub_quote_feedback_review_queue as validator


def _source_report() -> dict:
    return {
        "overall_status": "PASS",
        "acceptance_target": "V2.13-J Finnhub Quote User Feedback Intake",
        "summary": {
            "feedback_count": 5,
            "simulation_followup_count": 2,
            "social_sentiment_status": "blocked_plan_or_rate_limit",
        },
        "simulation_followup_candidates": [
            {
                "followup_id": "finnhub_quote_feedback_followup_watch",
                "feedback_id": "fb_watch",
                "suggestion_id": "sug_aapl",
                "symbol": "AAPL.US",
                "market": "US",
                "followup_status": "simulation_evidence_candidate",
                "followup_action": "paper_watch_evidence",
                "requires_user_price_before_paper_trade": True,
                "requires_user_date_before_paper_trade": True,
                "requires_explicit_simulation_confirmation": True,
                "requires_explicit_review_before_paper_trade": True,
                "evidence_refs": ["v2_13_i_brief.json"],
                "quote_context_research_only": True,
                "social_sentiment_not_enabled": True,
                "no_paper_trade_mutation": True,
                "no_recommendation_mutation": True,
                "no_review_mutation": True,
                "no_memory_mutation": True,
                "no_real_trade_execution": True,
                "no_broker_api": True,
                "no_webhook": True,
                "no_order_placement": True,
                "no_live_price": True,
                "no_position_size": True,
                "no_live_order_signal": True,
            },
            {
                "followup_id": "finnhub_quote_feedback_followup_external",
                "feedback_id": "fb_external",
                "suggestion_id": "sug_aapl",
                "symbol": "AAPL.US",
                "market": "US",
                "followup_status": "simulation_evidence_candidate",
                "followup_action": "manual_external_action_evidence",
                "requires_user_price_before_paper_trade": True,
                "requires_user_date_before_paper_trade": True,
                "requires_explicit_simulation_confirmation": True,
                "requires_explicit_review_before_paper_trade": True,
                "evidence_refs": ["v2_13_i_brief.json"],
                "quote_context_research_only": True,
                "social_sentiment_not_enabled": True,
                "no_paper_trade_mutation": True,
                "no_recommendation_mutation": True,
                "no_review_mutation": True,
                "no_memory_mutation": True,
                "no_real_trade_execution": True,
                "no_broker_api": True,
                "no_webhook": True,
                "no_order_placement": True,
                "no_live_price": True,
                "no_position_size": True,
                "no_live_order_signal": True,
            },
        ],
    }


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def test_v2_13_k_queue_requires_user_price_date_evidence_confirmation_and_review():
    queue = build_finnhub_quote_feedback_review_queue(
        _source_report()["simulation_followup_candidates"],
        evidence_ref="v2_13_j_report.json",
    )

    assert len(queue) == 2
    assert all(item["source"] == "V2.13-J Finnhub Quote User Feedback Intake" for item in queue)
    assert all(item["queue_status"] == "pending_user_price_date_evidence" for item in queue)
    assert all(item["entry_price"] is None for item in queue)
    assert all(item["entry_date"] is None for item in queue)
    assert all(item["evidence_ref_or_screenshot"] is None for item in queue)
    assert all(item["explicit_simulation_confirmation"] is False for item in queue)
    assert all(item["explicit_review_before_paper_trade"] is False for item in queue)
    assert all(item["ready_to_create_paper_trade"] is False for item in queue)
    assert all(item["requires_user_price_before_paper_trade"] is True for item in queue)
    assert all(item["requires_user_entry_date_before_paper_trade"] is True for item in queue)
    assert all(item["requires_user_evidence_before_paper_trade"] is True for item in queue)
    assert all(item["requires_explicit_review_before_paper_trade"] is True for item in queue)
    assert all(item["requires_explicit_simulation_confirmation"] is True for item in queue)
    assert all(item["no_live_price"] is True for item in queue)
    assert all(item["no_position_size"] is True for item in queue)
    assert all(item["no_paper_trade_mutation"] is True for item in queue)


def test_v2_13_k_report_is_review_queue_only_and_non_executing():
    report = build_finnhub_quote_feedback_review_queue_report(
        _source_report(),
        run_id="unit",
        evidence_ref="v2_13_j_report.json",
    )

    assert report["overall_status"] == "PASS"
    assert report["summary"]["review_queue_count"] == 2
    assert report["summary"]["pending_user_price_date_evidence_count"] == 2
    assert report["summary"]["social_sentiment_status"] == "blocked_plan_or_rate_limit"
    assert report["checks"]["source_is_v2_13_j"] is True
    assert report["checks"]["source_social_sentiment_not_enabled"] is True
    assert report["checks"]["all_items_include_explicit_review_field"] is True
    assert report["checks"]["entry_price_not_fabricated"] is True
    assert report["checks"]["not_ready_to_create_paper_trade"] is True
    assert report["paper_trades_written"] is False
    assert report["recommendations_written"] is False
    assert report["reviews_written"] is False
    assert report["memory_written"] is False
    assert report["safety"]["no_broker_api"] is True


def test_v2_13_k_fails_if_source_is_not_v2_13_j():
    source = _source_report()
    source["acceptance_target"] = "wrong"

    report = build_finnhub_quote_feedback_review_queue_report(
        source,
        run_id="unit",
        evidence_ref="v2_13_j_report.json",
    )

    assert report["overall_status"] == "FAIL"
    assert report["checks"]["source_is_v2_13_j"] is False


def test_v2_13_k_fails_if_social_sentiment_is_enabled_unexpectedly():
    source = _source_report()
    source["summary"]["social_sentiment_status"] = "pass"

    report = build_finnhub_quote_feedback_review_queue_report(
        source,
        run_id="unit",
        evidence_ref="v2_13_j_report.json",
    )

    assert report["overall_status"] == "FAIL"
    assert report["checks"]["source_social_sentiment_not_enabled"] is False


def test_v2_13_k_validator_writes_outputs_and_preserves_records(tmp_path: Path):
    source_json = tmp_path / "v2_13_j.json"
    marker = tmp_path / "v2_13_j.marker"
    _write_json(source_json, _source_report())
    marker.write_text("exit_code=0\n", encoding="utf-8")
    record = tmp_path / "records" / "paper_trades.jsonl"
    record.parent.mkdir()
    record.write_text("existing\n", encoding="utf-8")

    report = validator.run_acceptance(
        output_root=tmp_path / "processed",
        reports_dir=tmp_path / "reports",
        run_id="v2_13_k_test",
        command="test command",
        source_v2_13_j_report_json=source_json,
        source_v2_13_j_pass_marker=marker,
        record_paths={"paper_trades_jsonl": record},
    )

    assert report["overall_status"] == "PASS"
    assert report["checks"]["review_queue_json_written"] is True
    assert report["checks"]["pending_items_json_written"] is True
    assert report["checks"]["production_record_files_unchanged"] is True
    assert report["hashes"]["review_queue_json"]
    assert report["hashes"]["pending_items_json"]
    assert record.read_text(encoding="utf-8") == "existing\n"
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()


def test_v2_13_k_cli_exits_zero_and_prints_no_secret_values(tmp_path: Path, capsys):
    source_json = tmp_path / "v2_13_j.json"
    marker = tmp_path / "v2_13_j.marker"
    _write_json(source_json, _source_report())
    marker.write_text("exit_code=0\n", encoding="utf-8")

    exit_code = validator.main(
        [
            "--output-root",
            str(tmp_path / "processed"),
            "--reports-dir",
            str(tmp_path / "reports"),
            "--run-id",
            "v2_13_k_cli",
            "--source-v2-13-j-report-json",
            str(source_json),
            "--source-v2-13-j-pass-marker",
            str(marker),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "PASS" in captured.out
    assert "token" not in captured.out.lower()
    assert "secret" not in captured.out.lower()
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()
