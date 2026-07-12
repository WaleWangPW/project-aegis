from __future__ import annotations

import json
from pathlib import Path

from aegis.paper.finnhub_quote_review_memory_bridge import (
    build_finnhub_quote_review_memory_report,
)
import scripts.validate_v2_13_n_finnhub_quote_review_memory_bridge as validator


def _source_report() -> dict:
    return {
        "overall_status": "PASS",
        "acceptance_target": "V2.13-M Finnhub Quote Virtual PaperTrade Creation From Validated Evidence",
        "summary": {
            "virtual_paper_trade_count": 1,
            "social_sentiment_status": "blocked_plan_or_rate_limit",
        },
        "virtual_paper_trades": [
            {
                "paper_trade_id": "finnhub_quote_ptr_virtual_1",
                "recommendation_id": "finnhub_quote_manual_entry_1",
                "symbol": "AAPL.US",
                "market": "US",
                "direction": "long",
                "entry_date": "2026-07-12",
                "entry_price": 188.88,
                "virtual_position_size": 1.0,
                "status": "open",
                "simulation_only": True,
                "quote_context_research_only": True,
                "social_sentiment_not_enabled": True,
                "source_evidence_refs": ["v2_13_m_report.json", "v2_13_g_marker"],
                "source_user_evidence_items": [{"evidence_ref": "entry.txt", "exists": True, "sha256": "abc"}],
            }
        ],
    }


def _write_json(path: Path, payload: dict | list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def test_v2_13_n_creates_review_links_and_memory_candidates():
    report = build_finnhub_quote_review_memory_report(
        _source_report(),
        run_id="unit",
        evidence_ref="v2_13_m_report.json",
    )

    assert report["overall_status"] == "PASS"
    assert report["summary"]["virtual_paper_trade_count"] == 1
    assert report["summary"]["review_link_count"] == 1
    assert report["summary"]["memory_candidate_count"] == 1
    assert report["summary"]["social_sentiment_status"] == "blocked_plan_or_rate_limit"
    assert report["review_evidence_links"][0]["review_input_status"] == "candidate_evidence"
    assert report["review_evidence_links"][0]["requires_review_before_record_write"] is True
    assert report["memory_candidates"][0]["requires_review_before_memory_write"] is True
    assert report["memory_candidates"][0]["symbol"] == "AAPL.US"
    assert report["checks"]["no_review_record_mutation"] is True
    assert report["checks"]["no_memory_jsonl_mutation"] is True


def test_v2_13_n_preserves_simulation_safety():
    report = build_finnhub_quote_review_memory_report(
        _source_report(),
        run_id="unit",
        evidence_ref="v2_13_m_report.json",
    )

    assert report["safety"]["simulation_only"] is True
    assert report["safety"]["candidate_evidence_only"] is True
    assert report["safety"]["social_sentiment_not_enabled"] is True
    assert report["safety"]["no_real_trade_execution"] is True
    assert report["safety"]["no_broker_api"] is True
    assert report["safety"]["no_webhook"] is True
    assert report["safety"]["no_order_placement"] is True
    assert report["safety"]["no_strategy_mutation"] is True


def test_v2_13_n_fails_if_source_is_not_v2_13_m():
    source = _source_report()
    source["acceptance_target"] = "wrong"

    report = build_finnhub_quote_review_memory_report(
        source,
        run_id="unit",
        evidence_ref="v2_13_m_report.json",
    )

    assert report["overall_status"] == "FAIL"
    assert report["checks"]["source_is_v2_13_m"] is False


def test_v2_13_n_fails_if_social_sentiment_is_enabled_unexpectedly():
    source = _source_report()
    source["summary"]["social_sentiment_status"] = "pass"

    report = build_finnhub_quote_review_memory_report(
        source,
        run_id="unit",
        evidence_ref="v2_13_m_report.json",
    )

    assert report["overall_status"] == "FAIL"
    assert report["checks"]["source_social_sentiment_not_enabled"] is False


def test_v2_13_n_validator_writes_candidates_without_touching_records(tmp_path: Path):
    source_json = tmp_path / "v2_13_m.json"
    marker = tmp_path / "v2_13_m.marker"
    _write_json(source_json, _source_report())
    marker.write_text("exit_code=0\n", encoding="utf-8")
    records_dir = tmp_path / "records"
    records_dir.mkdir()
    paths = {
        "paper_trades_jsonl": records_dir / "paper_trades.jsonl",
        "reviews_jsonl": records_dir / "reviews.jsonl",
        "memory_jsonl": records_dir / "memory.jsonl",
        "investment_memory_jsonl": records_dir / "investment_memory.jsonl",
    }
    for path in paths.values():
        path.write_text("existing\n", encoding="utf-8")

    report = validator.run_acceptance(
        output_root=tmp_path / "processed",
        reports_dir=tmp_path / "reports",
        run_id="v2_13_n_test",
        command="test command",
        source_v2_13_m_report_json=source_json,
        source_v2_13_m_pass_marker=marker,
        record_paths=paths,
    )

    assert report["overall_status"] == "PASS"
    assert report["checks"]["production_record_files_unchanged"] is True
    assert report["checks"]["reviews_not_written"] is True
    assert report["checks"]["memory_records_not_written"] is True
    assert report["hashes"]["review_evidence_links_json"]
    assert report["hashes"]["memory_candidates_json"]
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()


def test_v2_13_n_cli_exits_zero_and_prints_no_secret_values(tmp_path: Path, capsys):
    source_json = tmp_path / "v2_13_m.json"
    marker = tmp_path / "v2_13_m.marker"
    _write_json(source_json, _source_report())
    marker.write_text("exit_code=0\n", encoding="utf-8")

    exit_code = validator.main(
        [
            "--output-root",
            str(tmp_path / "processed"),
            "--reports-dir",
            str(tmp_path / "reports"),
            "--run-id",
            "v2_13_n_cli",
            "--source-v2-13-m-report-json",
            str(source_json),
            "--source-v2-13-m-pass-marker",
            str(marker),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "PASS" in captured.out
    assert "token" not in captured.out.lower()
    assert "secret" not in captured.out.lower()
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()
