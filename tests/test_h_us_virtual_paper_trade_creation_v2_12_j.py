from __future__ import annotations

import json
from pathlib import Path

from aegis.models.paper_trade import PaperTrade
from aegis.paper.h_us_virtual_trade_creation import (
    build_h_us_virtual_paper_trades,
    build_h_us_virtual_trade_creation_report,
)
import scripts.validate_v2_12_j_h_us_virtual_paper_trade_creation as validator


def _source_report() -> dict:
    return {
        "overall_status": "PASS",
        "acceptance_target": "V2.12-I H-US User-Supplied Paper Evidence Validation",
        "summary": {
            "validated_user_evidence_count": 1,
            "blocked_user_evidence_count": 1,
        },
        "validated_user_evidence_records": [
            {
                "queue_id": "h_queue_1",
                "followup_id": "followup_h",
                "feedback_id": "fb_h",
                "suggestion_id": "sug_h",
                "symbol": "H_API_SANDBOX_PAPER_BASKET",
                "market": "H",
                "entry_price": 188.88,
                "entry_date": "2026-07-12",
                "virtual_position_size": 1.0,
                "explicit_simulation_confirmation": True,
                "evidence_items": [{"evidence_ref": "entry.txt", "exists": True, "sha256": "abc"}],
                "notes_hash": "notehash",
                "status": "ready_for_virtual_paper_trade_creation_candidate",
                "ready_to_create_paper_trade": True,
                "source_review_queue_status": "pending_user_price_date_evidence",
                "source_evidence_refs": ["queue.json"],
            }
        ],
        "blocked_user_evidence_records": [
            {
                "queue_id": "us_queue_1",
                "symbol": "US_API_SANDBOX_PAPER_BASKET",
                "market": "US",
                "status": "blocked",
                "blocked_reasons": ["invalid_entry_price"],
            }
        ],
    }


def _write_json(path: Path, payload: dict | list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def test_v2_12_j_builds_paper_trade_shaped_h_us_ledger():
    trades = build_h_us_virtual_paper_trades(
        _source_report()["validated_user_evidence_records"],
        created_at="2026-07-12T01:00:00+08:00",
    )

    assert len(trades) == 1
    trade = trades[0]
    assert trade["paper_trade_id"].startswith("h_us_ptr_virtual_")
    assert trade["recommendation_id"].startswith("h_us_manual_entry_")
    assert trade["symbol"] == "H_API_SANDBOX_PAPER_BASKET"
    assert trade["market"] == "H"
    assert trade["entry_price"] == 188.88
    assert trade["entry_date"] == "2026-07-12"
    assert trade["status"] == "open"
    assert trade["simulation_only"] is True
    assert trade["run_specific_ledger_only"] is True
    assert trade["source_queue_id"] == "h_queue_1"
    assert trade["source_followup_id"] == "followup_h"
    assert trade["source_user_evidence_items"][0]["sha256"] == "abc"
    PaperTrade(**{key: trade[key] for key in PaperTrade.model_fields})


def test_v2_12_j_report_is_simulation_ledger_only():
    report = build_h_us_virtual_trade_creation_report(_source_report(), run_id="unit")

    assert report["overall_status"] == "PASS"
    assert report["summary"]["virtual_paper_trade_count"] == 1
    assert report["checks"]["source_is_v2_12_i"] is True
    assert report["checks"]["all_trades_have_queue_linkage"] is True
    assert report["checks"]["production_paper_trades_not_written"] is True
    assert report["production_paper_trades_written"] is False
    assert report["recommendations_written"] is False
    assert report["reviews_written"] is False
    assert report["memory_written"] is False
    assert report["safety"]["run_specific_ledger_only"] is True


def test_v2_12_j_fails_if_source_is_not_v2_12_i():
    source = _source_report()
    source["acceptance_target"] = "wrong"

    report = build_h_us_virtual_trade_creation_report(source, run_id="unit")

    assert report["overall_status"] == "FAIL"
    assert report["checks"]["source_is_v2_12_i"] is False


def test_v2_12_j_validator_writes_ledger_without_touching_production_records(tmp_path: Path):
    source_json = tmp_path / "v2_12_i.json"
    marker = tmp_path / "v2_12_i.marker"
    _write_json(source_json, _source_report())
    marker.write_text("exit_code=0\n", encoding="utf-8")
    production_paper_trades = tmp_path / "records" / "paper_trades.jsonl"
    production_paper_trades.parent.mkdir(parents=True)
    production_paper_trades.write_text('{"existing": "row"}\n', encoding="utf-8")
    before = production_paper_trades.read_text(encoding="utf-8")

    report = validator.run_acceptance(
        output_root=tmp_path / "processed",
        reports_dir=tmp_path / "reports",
        run_id="v2_12_j_test",
        command="test command",
        source_v2_12_i_report_json=source_json,
        source_v2_12_i_pass_marker=marker,
        record_paths={"paper_trades_jsonl": production_paper_trades},
    )

    assert report["overall_status"] == "PASS"
    assert report["checks"]["production_record_files_unchanged"] is True
    assert production_paper_trades.read_text(encoding="utf-8") == before
    assert report["hashes"]["virtual_paper_trades_jsonl"]
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()


def test_v2_12_j_cli_exits_zero_and_prints_no_secret_values(tmp_path: Path, capsys):
    source_json = tmp_path / "v2_12_i.json"
    marker = tmp_path / "v2_12_i.marker"
    _write_json(source_json, _source_report())
    marker.write_text("exit_code=0\n", encoding="utf-8")

    exit_code = validator.main(
        [
            "--output-root",
            str(tmp_path / "processed"),
            "--reports-dir",
            str(tmp_path / "reports"),
            "--run-id",
            "v2_12_j_cli",
            "--source-v2-12-i-report-json",
            str(source_json),
            "--source-v2-12-i-pass-marker",
            str(marker),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "PASS" in captured.out
    assert "token" not in captured.out.lower()
    assert "secret" not in captured.out.lower()
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()
