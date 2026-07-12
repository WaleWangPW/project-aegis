from __future__ import annotations

import json
from pathlib import Path

import scripts.validate_v2_9_e_virtual_paper_trade_creation as validator
from aegis.models.paper_trade import PaperTrade
from aegis.paper.virtual_trade_creation import build_virtual_paper_trades, build_virtual_trade_creation_report


def _validated_records() -> list[dict]:
    return [
        {
            "entry_request_id": "pending_entry_1",
            "symbol": "600519.SH",
            "market": "A",
            "entry_price": 1688.88,
            "entry_date": "2026-07-11",
            "virtual_position_size": 1.0,
            "evidence_items": [{"evidence_ref": "entry.txt", "exists": True, "sha256": "abc"}],
            "source_paper_intake_id": "paper_intake_1",
            "source_feedback_id": "feedback_1",
            "status": "ready_for_virtual_paper_trade_creation",
            "ready_to_create_paper_trade": True,
        }
    ]


def test_build_virtual_paper_trades_creates_paper_trade_shaped_records():
    trades = build_virtual_paper_trades(_validated_records(), created_at="2026-07-11T00:00:00+08:00")

    assert len(trades) == 1
    trade = trades[0]
    assert trade["paper_trade_id"].startswith("ptr_virtual_")
    assert trade["symbol"] == "600519.SH"
    assert trade["entry_price"] == 1688.88
    assert trade["status"] == "open"
    assert trade["simulation_only"] is True
    assert trade["source_entry_request_id"] == "pending_entry_1"
    PaperTrade(**{key: trade[key] for key in PaperTrade.model_fields})


def test_virtual_trade_creation_report_is_simulation_only():
    report = build_virtual_trade_creation_report(_validated_records(), run_id="unit")

    assert report["overall_status"] == "PASS"
    assert report["summary"]["virtual_paper_trade_count"] == 1
    assert report["production_paper_trades_written"] is False
    assert report["recommendations_written"] is False
    assert report["safety"]["simulation_only"] is True
    assert report["checks"]["all_trades_have_source_evidence"] is True


def test_v2_9_e_acceptance_writes_ledger_without_touching_production_paper_trades(tmp_path: Path):
    validated_json = tmp_path / "validated.json"
    validated_json.write_text(json.dumps(_validated_records(), ensure_ascii=False), encoding="utf-8")
    production_paper_trades = tmp_path / "records" / "paper_trades.jsonl"
    production_paper_trades.parent.mkdir(parents=True)
    production_paper_trades.write_text('{"existing": "row"}\n', encoding="utf-8")
    before = production_paper_trades.read_text(encoding="utf-8")

    report = validator.run_acceptance(
        output_root=tmp_path / "processed",
        reports_dir=tmp_path / "reports",
        run_id="v2_9_e_test",
        command="test command",
        validated_evidence_json=validated_json,
        production_paper_trades_jsonl=production_paper_trades,
    )

    assert report["overall_status"] == "PASS"
    assert report["checks"]["production_paper_trades_file_unchanged"] is True
    assert production_paper_trades.read_text(encoding="utf-8") == before
    assert report["hashes"]["virtual_paper_trades_jsonl"]
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()


def test_v2_9_e_cli_exits_zero(tmp_path: Path, capsys):
    validated_json = tmp_path / "validated.json"
    validated_json.write_text(json.dumps(_validated_records(), ensure_ascii=False), encoding="utf-8")
    production_paper_trades = tmp_path / "records" / "paper_trades.jsonl"
    production_paper_trades.parent.mkdir(parents=True)
    production_paper_trades.write_text("", encoding="utf-8")

    exit_code = validator.main(
        [
            "--output-root",
            str(tmp_path / "processed"),
            "--reports-dir",
            str(tmp_path / "reports"),
            "--run-id",
            "v2_9_e_cli",
            "--validated-evidence-json",
            str(validated_json),
            "--production-paper-trades-jsonl",
            str(production_paper_trades),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "PASS" in captured.out
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()
