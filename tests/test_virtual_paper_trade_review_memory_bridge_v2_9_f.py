from __future__ import annotations

import json
from pathlib import Path

import scripts.validate_v2_9_f_virtual_paper_trade_review_memory_bridge as validator
from aegis.paper.review_memory_bridge import build_virtual_trade_review_memory_report


def _virtual_trades() -> list[dict]:
    return [
        {
            "paper_trade_id": "ptr_virtual_1",
            "recommendation_id": "manual_entry_1",
            "symbol": "600519.SH",
            "market": "A",
            "direction": "long",
            "entry_date": "2026-07-11",
            "entry_price": 1688.88,
            "virtual_position_size": 1.0,
            "status": "open",
            "simulation_only": True,
            "source_evidence_items": [{"evidence_ref": "entry.txt", "exists": True, "sha256": "abc"}],
        }
    ]


def test_virtual_trade_bridge_creates_review_links_and_memory_candidates():
    report = build_virtual_trade_review_memory_report(
        _virtual_trades(),
        run_id="unit",
        evidence_ref="virtual_paper_trades.json",
    )

    assert report["overall_status"] == "PASS"
    assert report["summary"]["virtual_paper_trade_count"] == 1
    assert report["summary"]["review_link_count"] == 1
    assert report["summary"]["memory_candidate_count"] == 1
    assert report["review_evidence_links"][0]["review_input_status"] == "candidate_evidence"
    assert report["memory_candidates"][0]["requires_review_before_memory_write"] is True
    assert report["checks"]["no_review_record_mutation"] is True
    assert report["checks"]["no_memory_jsonl_mutation"] is True


def test_virtual_trade_bridge_preserves_simulation_safety():
    report = build_virtual_trade_review_memory_report(
        _virtual_trades(),
        run_id="unit",
        evidence_ref="virtual_paper_trades.json",
    )

    assert report["safety"]["simulation_only"] is True
    assert report["safety"]["no_real_trade_execution"] is True
    assert report["safety"]["no_broker_api"] is True
    assert report["safety"]["no_webhook"] is True
    assert report["safety"]["no_order_placement"] is True
    assert report["safety"]["no_strategy_mutation"] is True


def test_v2_9_f_acceptance_writes_candidates_without_touching_records(tmp_path: Path):
    virtual_json = tmp_path / "virtual_paper_trades.json"
    virtual_json.write_text(json.dumps(_virtual_trades(), ensure_ascii=False), encoding="utf-8")
    records_dir = tmp_path / "records"
    records_dir.mkdir()
    paths = {
        "paper_trades_jsonl": records_dir / "paper_trades.jsonl",
        "reviews_jsonl": records_dir / "reviews.jsonl",
        "memory_jsonl": records_dir / "memory.jsonl",
        "investment_memory_jsonl": records_dir / "investment_memory.jsonl",
    }
    for path in paths.values():
        path.write_text("", encoding="utf-8")

    report = validator.run_acceptance(
        output_root=tmp_path / "processed",
        reports_dir=tmp_path / "reports",
        run_id="v2_9_f_test",
        command="test command",
        virtual_paper_trades_json=virtual_json,
        record_paths=paths,
    )

    assert report["overall_status"] == "PASS"
    assert report["checks"]["production_record_files_unchanged"] is True
    assert report["checks"]["reviews_not_written"] is True
    assert report["checks"]["memory_records_not_written"] is True
    assert report["hashes"]["review_evidence_links_json"]
    assert report["hashes"]["memory_candidates_json"]
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()


def test_v2_9_f_cli_exits_zero(tmp_path: Path, capsys):
    virtual_json = tmp_path / "virtual_paper_trades.json"
    virtual_json.write_text(json.dumps(_virtual_trades(), ensure_ascii=False), encoding="utf-8")

    exit_code = validator.main(
        [
            "--output-root",
            str(tmp_path / "processed"),
            "--reports-dir",
            str(tmp_path / "reports"),
            "--run-id",
            "v2_9_f_cli",
            "--virtual-paper-trades-json",
            str(virtual_json),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "PASS" in captured.out
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()
