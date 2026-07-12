from __future__ import annotations

import json
from pathlib import Path

import scripts.validate_v2_9_g_formal_review_memory_records as validator
from aegis.models.investment_memory import InvestmentMemory
from aegis.models.review import ReviewRecord
from aegis.paper.formal_review_memory import build_formal_review_memory_report


def _review_links() -> list[dict]:
    return [
        {
            "review_evidence_link_id": "virtual_trade_review_link_ptr_virtual_1",
            "paper_trade_id": "ptr_virtual_1",
            "recommendation_id": "manual_entry_1",
            "symbol": "600519.SH",
            "market": "A",
            "entry_date": "2026-07-11",
            "entry_price": 1688.88,
            "evidence_refs": ["virtual_paper_trades.json"],
            "source_evidence_items": [{"evidence_ref": "entry.txt", "exists": True, "sha256": "abc"}],
        }
    ]


def _memory_candidates() -> list[dict]:
    return [
        {
            "memory_candidate_id": "virtual_trade_memory_candidate_ptr_virtual_1",
            "linked_recommendation_id": "manual_entry_1",
            "paper_trade_id": "ptr_virtual_1",
            "symbol": "600519.SH",
            "market": "A",
            "lesson": "600519.SH simulation-only virtual PaperTrade entry context.",
            "tags": ["virtual_paper_trade", "simulation_only", "A"],
            "created_at": "2026-07-11T00:00:00+08:00",
            "evidence_refs": ["virtual_paper_trades.json"],
            "source_evidence_items": [{"evidence_ref": "entry.txt", "exists": True, "sha256": "abc"}],
        }
    ]


def test_formal_review_memory_report_creates_model_shaped_records():
    report = build_formal_review_memory_report(
        _review_links(),
        _memory_candidates(),
        run_id="unit",
    )

    assert report["overall_status"] == "PASS"
    assert report["summary"]["formal_review_count"] == 1
    assert report["summary"]["formal_memory_count"] == 1
    review = report["formal_reviews"][0]
    memory = report["formal_memories"][0]
    assert review["outcome"] == "pending"
    assert review["decision_quality"] == "unclear"
    assert review["actual_return"] is None
    assert review["no_return_fabrication"] is True
    ReviewRecord(**{key: review[key] for key in ReviewRecord.model_fields})
    InvestmentMemory(**{key: memory[key] for key in InvestmentMemory.model_fields})


def test_formal_review_memory_report_preserves_safety():
    report = build_formal_review_memory_report(
        _review_links(),
        _memory_candidates(),
        run_id="unit",
    )

    assert report["safety"]["simulation_only"] is True
    assert report["safety"]["production_records_not_written"] is True
    assert report["safety"]["no_return_fabrication"] is True
    assert report["safety"]["no_real_trade_execution"] is True
    assert report["safety"]["no_broker_api"] is True
    assert report["safety"]["no_strategy_mutation"] is True


def test_v2_9_g_acceptance_writes_formal_outputs_without_touching_records(tmp_path: Path):
    review_links_json = tmp_path / "review_links.json"
    memory_candidates_json = tmp_path / "memory_candidates.json"
    review_links_json.write_text(json.dumps(_review_links(), ensure_ascii=False), encoding="utf-8")
    memory_candidates_json.write_text(json.dumps(_memory_candidates(), ensure_ascii=False), encoding="utf-8")
    records_dir = tmp_path / "records"
    records_dir.mkdir()
    paths = {
        "reviews_jsonl": records_dir / "reviews.jsonl",
        "memory_jsonl": records_dir / "memory.jsonl",
        "investment_memory_jsonl": records_dir / "investment_memory.jsonl",
        "paper_trades_jsonl": records_dir / "paper_trades.jsonl",
    }
    for path in paths.values():
        path.write_text("", encoding="utf-8")

    report = validator.run_acceptance(
        output_root=tmp_path / "processed",
        reports_dir=tmp_path / "reports",
        run_id="v2_9_g_test",
        command="test command",
        review_links_json=review_links_json,
        memory_candidates_json=memory_candidates_json,
        record_paths=paths,
    )

    assert report["overall_status"] == "PASS"
    assert report["checks"]["production_record_files_unchanged"] is True
    assert report["checks"]["reviews_jsonl_not_written"] is True
    assert report["checks"]["memory_jsonl_not_written"] is True
    assert report["hashes"]["formal_reviews_json"]
    assert report["hashes"]["formal_memories_json"]
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()


def test_v2_9_g_cli_exits_zero(tmp_path: Path, capsys):
    review_links_json = tmp_path / "review_links.json"
    memory_candidates_json = tmp_path / "memory_candidates.json"
    review_links_json.write_text(json.dumps(_review_links(), ensure_ascii=False), encoding="utf-8")
    memory_candidates_json.write_text(json.dumps(_memory_candidates(), ensure_ascii=False), encoding="utf-8")

    exit_code = validator.main(
        [
            "--output-root",
            str(tmp_path / "processed"),
            "--reports-dir",
            str(tmp_path / "reports"),
            "--run-id",
            "v2_9_g_cli",
            "--review-links-json",
            str(review_links_json),
            "--memory-candidates-json",
            str(memory_candidates_json),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "PASS" in captured.out
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()
