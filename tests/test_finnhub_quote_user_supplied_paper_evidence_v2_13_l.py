from __future__ import annotations

import json
from pathlib import Path

from aegis.paper.finnhub_quote_user_supplied_evidence import (
    build_finnhub_quote_user_supplied_evidence_report,
    validate_finnhub_quote_user_supplied_evidence,
)
import scripts.validate_v2_13_l_finnhub_quote_user_supplied_paper_evidence as validator


def _source_report() -> dict:
    return {
        "overall_status": "PASS",
        "acceptance_target": "V2.13-K Finnhub Quote Feedback To Paper Simulation Review Queue",
        "summary": {
            "review_queue_count": 2,
            "pending_user_price_date_evidence_count": 2,
            "social_sentiment_status": "blocked_plan_or_rate_limit",
        },
        "review_queue": [
            {
                "queue_id": "finnhub_quote_review_queue_watch",
                "followup_id": "followup_watch",
                "feedback_id": "fb_watch",
                "suggestion_id": "sug_aapl",
                "symbol": "AAPL.US",
                "market": "US",
                "queue_status": "pending_user_price_date_evidence",
                "evidence_refs": ["v2_13_k_queue.json"],
                "no_paper_trade_mutation": True,
                "no_recommendation_mutation": True,
                "no_review_mutation": True,
                "no_memory_mutation": True,
                "no_real_trade_execution": True,
                "no_broker_api": True,
                "no_webhook": True,
                "no_order_placement": True,
            },
            {
                "queue_id": "finnhub_quote_review_queue_external",
                "followup_id": "followup_external",
                "feedback_id": "fb_external",
                "suggestion_id": "sug_aapl",
                "symbol": "AAPL.US",
                "market": "US",
                "queue_status": "pending_user_price_date_evidence",
                "evidence_refs": ["v2_13_k_queue.json"],
                "no_paper_trade_mutation": True,
                "no_recommendation_mutation": True,
                "no_review_mutation": True,
                "no_memory_mutation": True,
                "no_real_trade_execution": True,
                "no_broker_api": True,
                "no_webhook": True,
                "no_order_placement": True,
            },
        ],
    }


def _write_json(path: Path, payload: dict | list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def test_v2_13_l_valid_user_evidence_becomes_virtual_creation_candidate(tmp_path: Path):
    evidence = tmp_path / "entry.txt"
    evidence.write_text("manual Finnhub quote simulated entry evidence\n", encoding="utf-8")
    result = validate_finnhub_quote_user_supplied_evidence(
        _source_report()["review_queue"],
        [
            {
                "queue_id": "finnhub_quote_review_queue_watch",
                "entry_price": 188.88,
                "entry_date": "2026-07-12",
                "virtual_position_size": 1.0,
                "explicit_simulation_confirmation": True,
                "explicit_review_before_paper_trade": True,
                "evidence_refs": [str(evidence)],
                "notes": "confirmed manually",
            }
        ],
    )

    assert len(result["validated_user_evidence_records"]) == 1
    record = result["validated_user_evidence_records"][0]
    assert record["status"] == "ready_for_virtual_paper_trade_creation_candidate"
    assert record["queue_id"] == "finnhub_quote_review_queue_watch"
    assert record["entry_price"] == 188.88
    assert record["entry_date"] == "2026-07-12"
    assert record["explicit_simulation_confirmation"] is True
    assert record["explicit_review_before_paper_trade"] is True
    assert record["evidence_items"][0]["sha256"]
    assert record["ready_to_create_paper_trade"] is True
    assert record["no_paper_trade_mutation"] is True
    assert result["blocked_user_evidence_records"] == []


def test_v2_13_l_invalid_user_evidence_is_blocked(tmp_path: Path):
    missing = tmp_path / "missing.txt"
    result = validate_finnhub_quote_user_supplied_evidence(
        _source_report()["review_queue"],
        [
            {
                "queue_id": "finnhub_quote_review_queue_external",
                "entry_price": -1,
                "entry_date": "2026-99-99",
                "virtual_position_size": "bad",
                "explicit_simulation_confirmation": False,
                "explicit_review_before_paper_trade": False,
                "evidence_refs": [str(missing)],
            }
        ],
    )

    assert result["validated_user_evidence_records"] == []
    blocked = result["blocked_user_evidence_records"][0]
    assert "invalid_entry_price" in blocked["blocked_reasons"]
    assert "invalid_entry_date" in blocked["blocked_reasons"]
    assert "invalid_virtual_position_size" in blocked["blocked_reasons"]
    assert "missing_explicit_simulation_confirmation" in blocked["blocked_reasons"]
    assert "missing_explicit_review_before_paper_trade" in blocked["blocked_reasons"]
    assert "evidence_ref_missing" in blocked["blocked_reasons"]
    assert blocked["ready_to_create_paper_trade"] is False


def test_v2_13_l_secret_like_text_blocks_evidence(tmp_path: Path):
    evidence = tmp_path / "entry.txt"
    evidence.write_text("manual Finnhub quote simulated entry evidence\n", encoding="utf-8")
    result = validate_finnhub_quote_user_supplied_evidence(
        _source_report()["review_queue"],
        [
            {
                "queue_id": "finnhub_quote_review_queue_watch",
                "entry_price": 188.88,
                "entry_date": "2026-07-12",
                "explicit_simulation_confirmation": True,
                "explicit_review_before_paper_trade": True,
                "evidence_refs": [str(evidence)],
                "notes": "authorization: bearer do-not-store",
            }
        ],
    )

    assert result["validated_user_evidence_records"] == []
    assert "secret_like_text_blocked" in result["blocked_user_evidence_records"][0]["blocked_reasons"]


def test_v2_13_l_report_is_validation_only_and_non_executing(tmp_path: Path):
    evidence = tmp_path / "entry.txt"
    evidence.write_text("manual Finnhub quote simulated entry evidence\n", encoding="utf-8")
    report = build_finnhub_quote_user_supplied_evidence_report(
        _source_report(),
        [
            {
                "queue_id": "finnhub_quote_review_queue_watch",
                "entry_price": 188.88,
                "entry_date": "2026-07-12",
                "explicit_simulation_confirmation": True,
                "explicit_review_before_paper_trade": True,
                "evidence_refs": [str(evidence)],
            },
            {
                "queue_id": "finnhub_quote_review_queue_external",
                "entry_price": None,
                "entry_date": "2026-07-12",
                "explicit_simulation_confirmation": False,
                "explicit_review_before_paper_trade": False,
                "evidence_refs": [],
            },
        ],
        run_id="unit",
    )

    assert report["overall_status"] == "PASS"
    assert report["summary"]["validated_user_evidence_count"] == 1
    assert report["summary"]["blocked_user_evidence_count"] == 1
    assert report["summary"]["social_sentiment_status"] == "blocked_plan_or_rate_limit"
    assert report["checks"]["source_is_v2_13_k"] is True
    assert report["checks"]["validated_evidence_hashed"] is True
    assert report["checks"]["explicit_review_confirmation_required"] is True
    assert report["checks"]["blocked_invalid_inputs_present"] is True
    assert report["paper_trades_written"] is False
    assert report["recommendations_written"] is False
    assert report["reviews_written"] is False
    assert report["memory_written"] is False
    assert report["safety"]["paper_trade_creation_deferred"] is True


def test_v2_13_l_fails_if_source_is_not_v2_13_k(tmp_path: Path):
    evidence = tmp_path / "entry.txt"
    evidence.write_text("manual Finnhub quote simulated entry evidence\n", encoding="utf-8")
    source = _source_report()
    source["acceptance_target"] = "wrong"

    report = build_finnhub_quote_user_supplied_evidence_report(
        source,
        [
            {
                "queue_id": "finnhub_quote_review_queue_watch",
                "entry_price": 188.88,
                "entry_date": "2026-07-12",
                "explicit_simulation_confirmation": True,
                "explicit_review_before_paper_trade": True,
                "evidence_refs": [str(evidence)],
            }
        ],
        run_id="unit",
    )

    assert report["overall_status"] == "FAIL"
    assert report["checks"]["source_is_v2_13_k"] is False


def test_v2_13_l_fails_if_social_sentiment_is_enabled_unexpectedly(tmp_path: Path):
    evidence = tmp_path / "entry.txt"
    evidence.write_text("manual Finnhub quote simulated entry evidence\n", encoding="utf-8")
    source = _source_report()
    source["summary"]["social_sentiment_status"] = "pass"

    report = build_finnhub_quote_user_supplied_evidence_report(
        source,
        [
            {
                "queue_id": "finnhub_quote_review_queue_watch",
                "entry_price": 188.88,
                "entry_date": "2026-07-12",
                "explicit_simulation_confirmation": True,
                "explicit_review_before_paper_trade": True,
                "evidence_refs": [str(evidence)],
            }
        ],
        run_id="unit",
    )

    assert report["overall_status"] == "FAIL"
    assert report["checks"]["source_social_sentiment_not_enabled"] is False


def test_v2_13_l_validator_writes_outputs_and_preserves_records(tmp_path: Path):
    source_json = tmp_path / "v2_13_k.json"
    marker = tmp_path / "v2_13_k.marker"
    _write_json(source_json, _source_report())
    marker.write_text("exit_code=0\n", encoding="utf-8")
    record = tmp_path / "records" / "paper_trades.jsonl"
    record.parent.mkdir()
    record.write_text("existing\n", encoding="utf-8")

    report = validator.run_acceptance(
        output_root=tmp_path / "processed",
        reports_dir=tmp_path / "reports",
        run_id="v2_13_l_test",
        command="test command",
        source_v2_13_k_report_json=source_json,
        source_v2_13_k_pass_marker=marker,
        record_paths={"paper_trades_jsonl": record},
    )

    assert report["overall_status"] == "PASS"
    assert report["checks"]["production_record_files_unchanged"] is True
    assert report["summary"]["validated_user_evidence_count"] == 1
    assert report["summary"]["blocked_user_evidence_count"] == 1
    assert report["hashes"]["virtual_paper_trade_create_candidates_json"]
    assert record.read_text(encoding="utf-8") == "existing\n"
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()


def test_v2_13_l_cli_exits_zero_and_prints_no_secret_values(tmp_path: Path, capsys):
    source_json = tmp_path / "v2_13_k.json"
    marker = tmp_path / "v2_13_k.marker"
    _write_json(source_json, _source_report())
    marker.write_text("exit_code=0\n", encoding="utf-8")

    exit_code = validator.main(
        [
            "--output-root",
            str(tmp_path / "processed"),
            "--reports-dir",
            str(tmp_path / "reports"),
            "--run-id",
            "v2_13_l_cli",
            "--source-v2-13-k-report-json",
            str(source_json),
            "--source-v2-13-k-pass-marker",
            str(marker),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "PASS" in captured.out
    assert "token" not in captured.out.lower()
    assert "secret" not in captured.out.lower()
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()
