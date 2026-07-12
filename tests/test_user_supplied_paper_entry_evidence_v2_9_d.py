from __future__ import annotations

import json
from pathlib import Path

import scripts.validate_v2_9_d_user_supplied_paper_entry_evidence as validator
from aegis.paper.entry_evidence import build_entry_evidence_report, validate_user_entry_evidence


def _pending_requests() -> list[dict]:
    return [
        {
            "entry_request_id": "pending_entry_1",
            "paper_intake_id": "paper_intake_1",
            "feedback_id": "feedback_1",
            "symbol": "600519.SH",
            "market": "A",
            "entry_request_status": "pending_user_price_date",
            "no_paper_trade_mutation": True,
            "no_recommendation_mutation": True,
            "no_real_trade_execution": True,
            "no_broker_api": True,
            "no_webhook": True,
            "no_order_placement": True,
        },
        {
            "entry_request_id": "pending_entry_2",
            "paper_intake_id": "paper_intake_2",
            "feedback_id": "feedback_2",
            "symbol": "MSFT",
            "market": "US",
            "entry_request_status": "pending_user_price_date",
            "no_paper_trade_mutation": True,
            "no_recommendation_mutation": True,
            "no_real_trade_execution": True,
            "no_broker_api": True,
            "no_webhook": True,
            "no_order_placement": True,
        },
    ]


def test_valid_user_entry_evidence_becomes_creation_candidate(tmp_path: Path):
    evidence = tmp_path / "entry.txt"
    evidence.write_text("manual entry evidence\n", encoding="utf-8")
    user_inputs = [
        {
            "entry_request_id": "pending_entry_1",
            "entry_price": 1688.88,
            "entry_date": "2026-07-11",
            "virtual_position_size": 1.0,
            "user_confirmed": True,
            "evidence_refs": [str(evidence)],
            "notes": "confirmed manually",
        }
    ]

    result = validate_user_entry_evidence(_pending_requests(), user_inputs)

    assert len(result["validated_entry_evidence_records"]) == 1
    record = result["validated_entry_evidence_records"][0]
    assert record["status"] == "ready_for_virtual_paper_trade_creation"
    assert record["entry_price"] == 1688.88
    assert record["entry_date"] == "2026-07-11"
    assert record["evidence_items"][0]["sha256"]
    assert record["no_paper_trade_mutation"] is True
    assert result["blocked_entry_evidence_records"] == []


def test_invalid_entry_evidence_is_blocked_without_exception(tmp_path: Path):
    missing = tmp_path / "missing.txt"
    user_inputs = [
        {
            "entry_request_id": "pending_entry_1",
            "entry_price": -1,
            "entry_date": "2026-99-99",
            "virtual_position_size": "bad",
            "user_confirmed": False,
            "evidence_refs": [str(missing)],
        }
    ]

    result = validate_user_entry_evidence(_pending_requests(), user_inputs)

    assert result["validated_entry_evidence_records"] == []
    blocked = result["blocked_entry_evidence_records"][0]
    assert "invalid_entry_price" in blocked["blocked_reasons"]
    assert "invalid_entry_date" in blocked["blocked_reasons"]
    assert "invalid_virtual_position_size" in blocked["blocked_reasons"]
    assert "missing_explicit_user_confirmation" in blocked["blocked_reasons"]
    assert "evidence_ref_missing" in blocked["blocked_reasons"]


def test_secret_like_text_blocks_entry_evidence(tmp_path: Path):
    evidence = tmp_path / "entry.txt"
    evidence.write_text("manual entry evidence\n", encoding="utf-8")
    user_inputs = [
        {
            "entry_request_id": "pending_entry_1",
            "entry_price": 100.0,
            "entry_date": "2026-07-11",
            "user_confirmed": True,
            "evidence_refs": [str(evidence)],
            "notes": "api_key=do-not-store",
        }
    ]

    result = validate_user_entry_evidence(_pending_requests(), user_inputs)

    assert result["validated_entry_evidence_records"] == []
    assert "secret_like_text_blocked" in result["blocked_entry_evidence_records"][0]["blocked_reasons"]


def test_entry_evidence_report_is_validation_only(tmp_path: Path):
    evidence = tmp_path / "entry.txt"
    evidence.write_text("manual entry evidence\n", encoding="utf-8")
    report = build_entry_evidence_report(
        _pending_requests(),
        [
            {
                "entry_request_id": "pending_entry_1",
                "entry_price": 1688.88,
                "entry_date": "2026-07-11",
                "user_confirmed": True,
                "evidence_refs": [str(evidence)],
            }
        ],
        run_id="unit",
    )

    assert report["overall_status"] == "PASS"
    assert report["paper_trades_written"] is False
    assert report["recommendations_written"] is False
    assert report["safety"]["paper_trade_creation_deferred"] is True
    assert report["checks"]["validated_evidence_hashed"] is True


def test_v2_9_d_acceptance_writes_reports_and_hashes(tmp_path: Path):
    pending_json = tmp_path / "pending.json"
    pending_json.write_text(json.dumps(_pending_requests(), ensure_ascii=False), encoding="utf-8")

    report = validator.run_acceptance(
        output_root=tmp_path / "processed",
        reports_dir=tmp_path / "reports",
        run_id="v2_9_d_test",
        command="test command",
        pending_entry_requests_json=pending_json,
    )

    assert report["overall_status"] == "PASS"
    assert report["checks"]["paper_trades_not_written"] is True
    assert report["summary"]["validated_entry_evidence_count"] == 1
    assert report["summary"]["blocked_entry_evidence_count"] == 1
    assert report["hashes"]["virtual_paper_trade_create_candidates_json"]
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()


def test_v2_9_d_cli_exits_zero(tmp_path: Path, capsys):
    pending_json = tmp_path / "pending.json"
    pending_json.write_text(json.dumps(_pending_requests(), ensure_ascii=False), encoding="utf-8")

    exit_code = validator.main(
        [
            "--output-root",
            str(tmp_path / "processed"),
            "--reports-dir",
            str(tmp_path / "reports"),
            "--run-id",
            "v2_9_d_cli",
            "--pending-entry-requests-json",
            str(pending_json),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "PASS" in captured.out
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()
