from __future__ import annotations

import json
from pathlib import Path

from aegis.models.investment_memory import InvestmentMemory
from aegis.models.review import ReviewRecord
from aegis.paper.finnhub_quote_formal_review_memory import (
    build_finnhub_quote_formal_review_memory_report,
)
import scripts.validate_v2_13_o_finnhub_quote_formal_review_memory as validator


def _source_report() -> dict:
    return {
        "overall_status": "PASS",
        "acceptance_target": "V2.13-N Finnhub Quote Virtual PaperTrade Review/Memory Bridge",
        "summary": {
            "review_link_count": 1,
            "memory_candidate_count": 1,
            "social_sentiment_status": "blocked_plan_or_rate_limit",
        },
        "safety": {
            "candidate_evidence_only": True,
            "simulation_only": True,
            "social_sentiment_not_enabled": True,
        },
        "review_evidence_links": [
            {
                "review_evidence_link_id": "finnhub_quote_review_link_1",
                "source_type": "finnhub_quote_virtual_paper_trade_ledger",
                "paper_trade_id": "finnhub_quote_ptr_virtual_1",
                "recommendation_id": "finnhub_quote_manual_entry_1",
                "symbol": "AAPL.US",
                "market": "US",
                "entry_date": "2026-07-12",
                "entry_price": 188.88,
                "status": "open",
                "review_input_status": "candidate_evidence",
                "evidence_refs": ["v2_13_n_report.json", "v2_13_m_report.json"],
                "source_user_evidence_items": [{"evidence_ref": "entry.txt", "exists": True, "sha256": "abc"}],
                "simulation_only": True,
                "quote_context_research_only": True,
                "social_sentiment_not_enabled": True,
            }
        ],
        "memory_candidates": [
            {
                "memory_candidate_id": "finnhub_quote_memory_candidate_1",
                "source_type": "finnhub_quote_virtual_paper_trade_ledger",
                "linked_recommendation_id": "finnhub_quote_manual_entry_1",
                "paper_trade_id": "finnhub_quote_ptr_virtual_1",
                "symbol": "AAPL.US",
                "market": "US",
                "lesson_type": "finnhub_quote_virtual_trade_entry_context",
                "lesson": "AAPL.US simulation-only Finnhub quote entry context.",
                "tags": ["finnhub_quote", "virtual_paper_trade", "simulation_only", "US"],
                "confidence": 0.5,
                "evidence_refs": ["v2_13_n_report.json", "v2_13_m_report.json"],
                "source_user_evidence_items": [{"evidence_ref": "entry.txt", "exists": True, "sha256": "abc"}],
                "created_at": "2026-07-12T00:00:00+08:00",
                "requires_review_before_memory_write": True,
                "quote_context_research_only": True,
                "social_sentiment_not_enabled": True,
            }
        ],
    }


def _write_json(path: Path, payload: dict | list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def test_v2_13_o_creates_model_shaped_formal_records_without_outcome_fabrication():
    report = build_finnhub_quote_formal_review_memory_report(_source_report(), run_id="unit")

    assert report["overall_status"] == "PASS"
    assert report["summary"]["formal_review_count"] == 1
    assert report["summary"]["formal_memory_count"] == 1
    assert report["summary"]["social_sentiment_status"] == "blocked_plan_or_rate_limit"
    review = report["formal_reviews"][0]
    memory = report["formal_memories"][0]
    assert review["outcome"] == "pending"
    assert review["decision_quality"] == "unclear"
    assert review["actual_return"] is None
    assert review["max_drawdown"] is None
    assert review["exit_price"] is None
    assert review["exit_date"] is None
    assert review["outcome_evidence_status"] == "pending_user_returned_evidence"
    assert review["no_return_fabrication"] is True
    assert review["no_exit_fabrication"] is True
    assert memory["outcome_evidence_status"] == "pending_user_returned_evidence"
    assert memory["no_return_fabrication"] is True
    ReviewRecord(**{key: review[key] for key in ReviewRecord.model_fields})
    InvestmentMemory(**{key: memory[key] for key in InvestmentMemory.model_fields})


def test_v2_13_o_preserves_simulation_and_social_sentiment_boundaries():
    report = build_finnhub_quote_formal_review_memory_report(_source_report(), run_id="unit")

    assert report["safety"]["formal_artifacts_only"] is True
    assert report["safety"]["simulation_only"] is True
    assert report["safety"]["social_sentiment_not_enabled"] is True
    assert report["safety"]["no_real_trade_execution"] is True
    assert report["safety"]["no_broker_api"] is True
    assert report["safety"]["no_webhook"] is True
    assert report["safety"]["no_order_placement"] is True
    assert report["safety"]["no_live_price"] is True
    assert report["safety"]["no_position_size"] is True
    assert report["safety"]["no_live_order_signal"] is True


def test_v2_13_o_fails_if_source_is_not_v2_13_n():
    source = _source_report()
    source["acceptance_target"] = "wrong"

    report = build_finnhub_quote_formal_review_memory_report(source, run_id="unit")

    assert report["overall_status"] == "FAIL"
    assert report["checks"]["source_is_v2_13_n"] is False


def test_v2_13_o_fails_if_social_sentiment_is_enabled_unexpectedly():
    source = _source_report()
    source["summary"]["social_sentiment_status"] = "pass"

    report = build_finnhub_quote_formal_review_memory_report(source, run_id="unit")

    assert report["overall_status"] == "FAIL"
    assert report["checks"]["source_social_sentiment_not_enabled"] is False


def test_v2_13_o_validator_writes_formal_outputs_without_touching_records(tmp_path: Path):
    source_json = tmp_path / "v2_13_n.json"
    marker = tmp_path / "v2_13_n.marker"
    _write_json(source_json, _source_report())
    marker.write_text("exit_code=0\n", encoding="utf-8")
    records_dir = tmp_path / "records"
    records_dir.mkdir()
    paths = {
        "paper_trades_jsonl": records_dir / "paper_trades.jsonl",
        "reviews_jsonl": records_dir / "reviews.jsonl",
        "memory_jsonl": records_dir / "memory.jsonl",
        "investment_memory_jsonl": records_dir / "investment_memory.jsonl",
        "recommendations_jsonl": records_dir / "recommendations.jsonl",
    }
    for path in paths.values():
        path.write_text("existing\n", encoding="utf-8")

    report = validator.run_acceptance(
        output_root=tmp_path / "processed",
        reports_dir=tmp_path / "reports",
        run_id="v2_13_o_test",
        command="test command",
        source_v2_13_n_report_json=source_json,
        source_v2_13_n_pass_marker=marker,
        record_paths=paths,
    )

    assert report["overall_status"] == "PASS"
    assert report["checks"]["production_record_files_unchanged"] is True
    assert report["checks"]["reviews_jsonl_not_written"] is True
    assert report["checks"]["memory_jsonl_not_written"] is True
    assert report["checks"]["recommendations_not_written"] is True
    assert report["hashes"]["formal_reviews_json"]
    assert report["hashes"]["formal_memories_json"]
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()


def test_v2_13_o_cli_exits_zero_and_prints_no_secret_values(tmp_path: Path, capsys):
    source_json = tmp_path / "v2_13_n.json"
    marker = tmp_path / "v2_13_n.marker"
    _write_json(source_json, _source_report())
    marker.write_text("exit_code=0\n", encoding="utf-8")

    exit_code = validator.main(
        [
            "--output-root",
            str(tmp_path / "processed"),
            "--reports-dir",
            str(tmp_path / "reports"),
            "--run-id",
            "v2_13_o_cli",
            "--source-v2-13-n-report-json",
            str(source_json),
            "--source-v2-13-n-pass-marker",
            str(marker),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "PASS" in captured.out
    assert "token" not in captured.out.lower()
    assert "secret" not in captured.out.lower()
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()
