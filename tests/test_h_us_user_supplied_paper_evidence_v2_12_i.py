from __future__ import annotations

import json
from pathlib import Path

from aegis.paper.h_us_user_supplied_evidence import (
    build_h_us_user_supplied_evidence_report,
    validate_h_us_user_supplied_evidence,
)
import scripts.validate_v2_12_i_h_us_user_supplied_paper_evidence as validator


def _source_report() -> dict:
    return {
        "overall_status": "PASS",
        "acceptance_target": "V2.12-H H-US Feedback To Paper Simulation Review Queue",
        "summary": {
            "review_queue_count": 2,
            "pending_user_price_date_evidence_count": 2,
        },
        "review_queue": [
            {
                "queue_id": "h_queue_1",
                "followup_id": "followup_h",
                "feedback_id": "fb_h",
                "suggestion_id": "sug_h",
                "symbol": "H_API_SANDBOX_PAPER_BASKET",
                "market": "H",
                "queue_status": "pending_user_price_date_evidence",
                "evidence_refs": ["h_queue.json"],
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
                "queue_id": "us_queue_1",
                "followup_id": "followup_us",
                "feedback_id": "fb_us",
                "suggestion_id": "sug_us",
                "symbol": "US_API_SANDBOX_PAPER_BASKET",
                "market": "US",
                "queue_status": "pending_user_price_date_evidence",
                "evidence_refs": ["us_queue.json"],
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


def test_v2_12_i_valid_user_evidence_becomes_virtual_creation_candidate(tmp_path: Path):
    evidence = tmp_path / "entry.txt"
    evidence.write_text("manual H/US simulated entry evidence\n", encoding="utf-8")
    result = validate_h_us_user_supplied_evidence(
        _source_report()["review_queue"],
        [
            {
                "queue_id": "h_queue_1",
                "entry_price": 188.88,
                "entry_date": "2026-07-12",
                "virtual_position_size": 1.0,
                "explicit_simulation_confirmation": True,
                "evidence_refs": [str(evidence)],
                "notes": "confirmed manually",
            }
        ],
    )

    assert len(result["validated_user_evidence_records"]) == 1
    record = result["validated_user_evidence_records"][0]
    assert record["status"] == "ready_for_virtual_paper_trade_creation_candidate"
    assert record["queue_id"] == "h_queue_1"
    assert record["entry_price"] == 188.88
    assert record["entry_date"] == "2026-07-12"
    assert record["evidence_items"][0]["sha256"]
    assert record["ready_to_create_paper_trade"] is True
    assert record["no_paper_trade_mutation"] is True
    assert result["blocked_user_evidence_records"] == []


def test_v2_12_i_invalid_user_evidence_is_blocked(tmp_path: Path):
    missing = tmp_path / "missing.txt"
    result = validate_h_us_user_supplied_evidence(
        _source_report()["review_queue"],
        [
            {
                "queue_id": "us_queue_1",
                "entry_price": -1,
                "entry_date": "2026-99-99",
                "virtual_position_size": "bad",
                "explicit_simulation_confirmation": False,
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
    assert "evidence_ref_missing" in blocked["blocked_reasons"]
    assert blocked["ready_to_create_paper_trade"] is False


def test_v2_12_i_secret_like_text_blocks_evidence(tmp_path: Path):
    evidence = tmp_path / "entry.txt"
    evidence.write_text("manual H/US simulated entry evidence\n", encoding="utf-8")
    result = validate_h_us_user_supplied_evidence(
        _source_report()["review_queue"],
        [
            {
                "queue_id": "h_queue_1",
                "entry_price": 188.88,
                "entry_date": "2026-07-12",
                "explicit_simulation_confirmation": True,
                "evidence_refs": [str(evidence)],
                "notes": "authorization: bearer do-not-store",
            }
        ],
    )

    assert result["validated_user_evidence_records"] == []
    assert "secret_like_text_blocked" in result["blocked_user_evidence_records"][0]["blocked_reasons"]


def test_v2_12_i_report_is_validation_only_and_non_executing(tmp_path: Path):
    evidence = tmp_path / "entry.txt"
    evidence.write_text("manual H/US simulated entry evidence\n", encoding="utf-8")
    report = build_h_us_user_supplied_evidence_report(
        _source_report(),
        [
            {
                "queue_id": "h_queue_1",
                "entry_price": 188.88,
                "entry_date": "2026-07-12",
                "explicit_simulation_confirmation": True,
                "evidence_refs": [str(evidence)],
            },
            {
                "queue_id": "us_queue_1",
                "entry_price": None,
                "entry_date": "2026-07-12",
                "explicit_simulation_confirmation": False,
                "evidence_refs": [],
            },
        ],
        run_id="unit",
    )

    assert report["overall_status"] == "PASS"
    assert report["summary"]["validated_user_evidence_count"] == 1
    assert report["summary"]["blocked_user_evidence_count"] == 1
    assert report["checks"]["source_is_v2_12_h"] is True
    assert report["checks"]["validated_evidence_hashed"] is True
    assert report["checks"]["blocked_invalid_inputs_present"] is True
    assert report["paper_trades_written"] is False
    assert report["recommendations_written"] is False
    assert report["reviews_written"] is False
    assert report["memory_written"] is False
    assert report["safety"]["paper_trade_creation_deferred"] is True


def test_v2_12_i_fails_if_source_is_not_v2_12_h(tmp_path: Path):
    evidence = tmp_path / "entry.txt"
    evidence.write_text("manual H/US simulated entry evidence\n", encoding="utf-8")
    source = _source_report()
    source["acceptance_target"] = "wrong"

    report = build_h_us_user_supplied_evidence_report(
        source,
        [
            {
                "queue_id": "h_queue_1",
                "entry_price": 188.88,
                "entry_date": "2026-07-12",
                "explicit_simulation_confirmation": True,
                "evidence_refs": [str(evidence)],
            }
        ],
        run_id="unit",
    )

    assert report["overall_status"] == "FAIL"
    assert report["checks"]["source_is_v2_12_h"] is False


def test_v2_12_i_validator_writes_outputs_and_preserves_records(tmp_path: Path):
    source_json = tmp_path / "v2_12_h.json"
    marker = tmp_path / "v2_12_h.marker"
    _write_json(source_json, _source_report())
    marker.write_text("exit_code=0\n", encoding="utf-8")
    record = tmp_path / "records" / "recommendations.jsonl"
    record.parent.mkdir()
    record.write_text("existing\n", encoding="utf-8")

    report = validator.run_acceptance(
        output_root=tmp_path / "processed",
        reports_dir=tmp_path / "reports",
        run_id="v2_12_i_test",
        command="test command",
        source_v2_12_h_report_json=source_json,
        source_v2_12_h_pass_marker=marker,
        record_paths={"recommendations_jsonl": record},
    )

    assert report["overall_status"] == "PASS"
    assert report["checks"]["production_record_files_unchanged"] is True
    assert report["summary"]["validated_user_evidence_count"] == 1
    assert report["summary"]["blocked_user_evidence_count"] == 1
    assert report["hashes"]["virtual_paper_trade_create_candidates_json"]
    assert record.read_text(encoding="utf-8") == "existing\n"
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()


def test_v2_12_i_cli_exits_zero_and_prints_no_secret_values(tmp_path: Path, capsys):
    source_json = tmp_path / "v2_12_h.json"
    marker = tmp_path / "v2_12_h.marker"
    _write_json(source_json, _source_report())
    marker.write_text("exit_code=0\n", encoding="utf-8")

    exit_code = validator.main(
        [
            "--output-root",
            str(tmp_path / "processed"),
            "--reports-dir",
            str(tmp_path / "reports"),
            "--run-id",
            "v2_12_i_cli",
            "--source-v2-12-h-report-json",
            str(source_json),
            "--source-v2-12-h-pass-marker",
            str(marker),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "PASS" in captured.out
    assert "token" not in captured.out.lower()
    assert "secret" not in captured.out.lower()
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()
