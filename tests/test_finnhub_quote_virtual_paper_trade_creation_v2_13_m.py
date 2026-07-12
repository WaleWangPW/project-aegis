from __future__ import annotations

import json
from pathlib import Path

from aegis.models.paper_trade import PaperTrade
from aegis.paper.finnhub_quote_virtual_trade_creation import (
    build_finnhub_quote_virtual_paper_trades,
    build_finnhub_quote_virtual_trade_creation_report,
)
import scripts.validate_v2_13_m_finnhub_quote_virtual_paper_trade_creation as validator


def _source_report() -> dict:
    return {
        "overall_status": "PASS",
        "acceptance_target": "V2.13-L Finnhub Quote User-Supplied Paper Evidence Validation",
        "summary": {
            "validated_user_evidence_count": 1,
            "blocked_user_evidence_count": 1,
            "social_sentiment_status": "blocked_plan_or_rate_limit",
        },
        "validated_user_evidence_records": [
            {
                "queue_id": "finnhub_quote_review_queue_watch",
                "followup_id": "followup_watch",
                "feedback_id": "fb_watch",
                "suggestion_id": "sug_aapl",
                "symbol": "AAPL.US",
                "market": "US",
                "entry_price": 188.88,
                "entry_date": "2026-07-12",
                "virtual_position_size": 1.0,
                "explicit_simulation_confirmation": True,
                "explicit_review_before_paper_trade": True,
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
                "queue_id": "finnhub_quote_review_queue_external",
                "symbol": "AAPL.US",
                "market": "US",
                "status": "blocked",
                "blocked_reasons": ["invalid_entry_price"],
            }
        ],
    }


def _write_json(path: Path, payload: dict | list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def test_v2_13_m_builds_paper_trade_shaped_finnhub_quote_ledger():
    trades = build_finnhub_quote_virtual_paper_trades(
        _source_report()["validated_user_evidence_records"],
        created_at="2026-07-12T01:00:00+08:00",
    )

    assert len(trades) == 1
    trade = trades[0]
    assert trade["paper_trade_id"].startswith("finnhub_quote_ptr_virtual_")
    assert trade["recommendation_id"].startswith("finnhub_quote_manual_entry_")
    assert trade["symbol"] == "AAPL.US"
    assert trade["market"] == "US"
    assert trade["entry_price"] == 188.88
    assert trade["entry_date"] == "2026-07-12"
    assert trade["status"] == "open"
    assert trade["simulation_only"] is True
    assert trade["run_specific_ledger_only"] is True
    assert trade["social_sentiment_not_enabled"] is True
    assert trade["source_queue_id"] == "finnhub_quote_review_queue_watch"
    assert trade["source_followup_id"] == "followup_watch"
    assert trade["source_user_evidence_items"][0]["sha256"] == "abc"
    assert trade["no_live_price"] is True
    assert trade["no_position_size"] is True
    PaperTrade(**{key: trade[key] for key in PaperTrade.model_fields})


def test_v2_13_m_report_is_simulation_ledger_only():
    report = build_finnhub_quote_virtual_trade_creation_report(_source_report(), run_id="unit")

    assert report["overall_status"] == "PASS"
    assert report["summary"]["virtual_paper_trade_count"] == 1
    assert report["summary"]["social_sentiment_status"] == "blocked_plan_or_rate_limit"
    assert report["checks"]["source_is_v2_13_l"] is True
    assert report["checks"]["source_social_sentiment_not_enabled"] is True
    assert report["checks"]["all_trades_have_queue_linkage"] is True
    assert report["checks"]["production_paper_trades_not_written"] is True
    assert report["production_paper_trades_written"] is False
    assert report["recommendations_written"] is False
    assert report["reviews_written"] is False
    assert report["memory_written"] is False
    assert report["safety"]["run_specific_ledger_only"] is True


def test_v2_13_m_fails_if_source_is_not_v2_13_l():
    source = _source_report()
    source["acceptance_target"] = "wrong"

    report = build_finnhub_quote_virtual_trade_creation_report(source, run_id="unit")

    assert report["overall_status"] == "FAIL"
    assert report["checks"]["source_is_v2_13_l"] is False


def test_v2_13_m_fails_if_social_sentiment_is_enabled_unexpectedly():
    source = _source_report()
    source["summary"]["social_sentiment_status"] = "pass"

    report = build_finnhub_quote_virtual_trade_creation_report(source, run_id="unit")

    assert report["overall_status"] == "FAIL"
    assert report["checks"]["source_social_sentiment_not_enabled"] is False


def test_v2_13_m_validator_writes_ledger_without_touching_production_records(tmp_path: Path):
    source_json = tmp_path / "v2_13_l.json"
    marker = tmp_path / "v2_13_l.marker"
    _write_json(source_json, _source_report())
    marker.write_text("exit_code=0\n", encoding="utf-8")
    production_paper_trades = tmp_path / "records" / "paper_trades.jsonl"
    production_paper_trades.parent.mkdir(parents=True)
    production_paper_trades.write_text('{"existing": "row"}\n', encoding="utf-8")
    before = production_paper_trades.read_text(encoding="utf-8")

    report = validator.run_acceptance(
        output_root=tmp_path / "processed",
        reports_dir=tmp_path / "reports",
        run_id="v2_13_m_test",
        command="test command",
        source_v2_13_l_report_json=source_json,
        source_v2_13_l_pass_marker=marker,
        record_paths={"paper_trades_jsonl": production_paper_trades},
    )

    assert report["overall_status"] == "PASS"
    assert report["checks"]["production_record_files_unchanged"] is True
    assert production_paper_trades.read_text(encoding="utf-8") == before
    assert report["hashes"]["virtual_paper_trades_jsonl"]
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()


def test_v2_13_m_cli_exits_zero_and_prints_no_secret_values(tmp_path: Path, capsys):
    source_json = tmp_path / "v2_13_l.json"
    marker = tmp_path / "v2_13_l.marker"
    _write_json(source_json, _source_report())
    marker.write_text("exit_code=0\n", encoding="utf-8")

    exit_code = validator.main(
        [
            "--output-root",
            str(tmp_path / "processed"),
            "--reports-dir",
            str(tmp_path / "reports"),
            "--run-id",
            "v2_13_m_cli",
            "--source-v2-13-l-report-json",
            str(source_json),
            "--source-v2-13-l-pass-marker",
            str(marker),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "PASS" in captured.out
    assert "token" not in captured.out.lower()
    assert "secret" not in captured.out.lower()
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()
