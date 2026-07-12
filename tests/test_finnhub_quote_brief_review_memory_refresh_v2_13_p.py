from __future__ import annotations

import json
from pathlib import Path

from aegis.external_sources.finnhub_quote_brief_review_memory_refresh import (
    ACCEPTANCE_TARGET,
    build_finnhub_quote_brief_review_memory_refresh,
    render_finnhub_quote_brief_review_memory_refresh_markdown,
)
import scripts.validate_v2_13_p_finnhub_quote_brief_review_memory_refresh as validator


def _brief_report() -> dict:
    return {
        "overall_status": "PASS",
        "acceptance_target": "V2.13-I Finnhub Quote Current Simulation Brief",
        "network_used": False,
        "production_records_written": False,
        "dashboard_contract_changed": False,
        "summary": {
            "candidate_count": 1,
            "candidate_symbols": ["AAPL.US"],
            "social_sentiment_status": "blocked_plan_or_rate_limit",
        },
        "current_answer": {
            "usable_suggestions_status": "当前可给出 1 条 AAPL.US simulation-only 观察候选。",
        },
        "user_boundary": {"allowed": ["模拟观察"], "forbidden": ["不下单"]},
        "items": [
            {
                "item_id": "brief_sug_1",
                "suggestion_id": "sug_1",
                "symbol": "AAPL.US",
                "market": "US",
                "brief_status": "simulation_candidate",
                "plain_summary": "AAPL.US simulation-only candidate.",
                "simulation_only": True,
                "user_must_execute_externally": True,
                "no_live_price": True,
                "no_position_size": True,
                "no_real_trade": True,
                "no_broker_api": True,
                "no_webhook": True,
                "no_order_placement": True,
                "no_live_order_signal": True,
            }
        ],
        "safety": {
            "simulation_only": True,
            "no_real_trade": True,
            "no_broker_api": True,
            "no_trading_webhook": True,
            "no_order_placement": True,
            "no_live_price": True,
            "no_position_size": True,
            "no_live_order_signal": True,
        },
    }


def _formal_report() -> dict:
    return {
        "overall_status": "PASS",
        "acceptance_target": "V2.13-O Finnhub Quote Formal Review/Memory Records From Virtual Trade Candidates",
        "network_used": False,
        "production_records_written": False,
        "dashboard_contract_changed": False,
        "summary": {
            "formal_review_count": 1,
            "formal_memory_count": 1,
            "social_sentiment_status": "blocked_plan_or_rate_limit",
        },
        "formal_reviews": [
            {
                "review_id": "rev_finnhub_quote_1",
                "recommendation_id": "rec_1",
                "paper_trade_id": "ptr_1",
                "review_date": "2026-07-12",
                "horizon": "5d",
                "outcome": "pending",
                "actual_return": None,
                "max_drawdown": None,
                "decision_quality": "unclear",
                "lessons": ["AAPL.US（US）已进入 Finnhub quote simulation-only virtual PaperTrade formal review artifact。"],
                "exit_price": None,
                "exit_date": None,
                "outcome_evidence_status": "pending_user_returned_evidence",
                "source_trade_status": "open",
                "simulation_only": True,
                "social_sentiment_not_enabled": True,
                "no_return_fabrication": True,
                "no_exit_fabrication": True,
                "no_review_record_production_mutation": True,
            }
        ],
        "formal_memories": [
            {
                "memory_id": "mem_finnhub_quote_1",
                "paper_trade_id": "ptr_1",
                "lesson": "AAPL.US memory context.",
            }
        ],
        "safety": {
            "simulation_only": True,
            "formal_artifacts_only": True,
            "no_real_trade_execution": True,
            "no_broker_api": True,
            "no_webhook": True,
            "no_order_placement": True,
            "no_live_price": True,
            "no_position_size": True,
            "no_live_order_signal": True,
        },
    }


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def test_v2_13_p_refreshes_brief_with_formal_review_memory_context():
    report = build_finnhub_quote_brief_review_memory_refresh(
        _brief_report(),
        _formal_report(),
        run_id="unit",
    )

    assert report["overall_status"] == "PASS"
    assert report["acceptance_target"] == ACCEPTANCE_TARGET
    assert report["summary"]["candidate_count"] == 1
    assert report["summary"]["review_memory_context_count"] == 1
    item = report["items"][0]
    assert item["review_memory_status"] == "formal_pending"
    assert item["requires_user_returned_outcome_evidence"] is True
    assert item["review_memory_context"]["outcome"] == "pending"
    assert item["review_memory_context"]["actual_return"] is None
    assert item["review_memory_context"]["exit_price"] is None
    assert report["checks"]["all_contexts_pending_without_returns"] is True
    assert report["checks"]["no_return_fabrication"] is True


def test_v2_13_p_markdown_exposes_pending_boundary():
    report = build_finnhub_quote_brief_review_memory_refresh(_brief_report(), _formal_report(), run_id="unit")

    md = render_finnhub_quote_brief_review_memory_refresh_markdown(report)

    assert "Project Aegis Finnhub Quote 模拟建议与复盘状态简报" in md
    assert "AAPL.US" in md
    assert "formal_pending" in md
    assert "actual_return：`None`" in md
    assert "open 虚拟交易不得编造收益" in md
    assert "不接券商" in md
    assert "不下单" in md


def test_v2_13_p_fails_when_formal_context_missing_for_candidate():
    formal = _formal_report()
    formal["formal_reviews"] = []
    formal["formal_memories"] = []

    report = build_finnhub_quote_brief_review_memory_refresh(_brief_report(), formal, run_id="unit")

    assert report["overall_status"] == "FAIL"
    assert report["checks"]["has_review_memory_context_for_candidate"] is False


def test_v2_13_p_validator_writes_outputs_without_touching_records(tmp_path: Path):
    brief_json = tmp_path / "v2_13_i.json"
    brief_marker = tmp_path / "v2_13_i.marker"
    formal_json = tmp_path / "v2_13_o.json"
    formal_marker = tmp_path / "v2_13_o.marker"
    _write_json(brief_json, _brief_report())
    _write_json(formal_json, _formal_report())
    brief_marker.write_text("exit_code=0\n", encoding="utf-8")
    formal_marker.write_text("exit_code=0\n", encoding="utf-8")
    record = tmp_path / "records" / "recommendations.jsonl"
    record.parent.mkdir()
    record.write_text("existing\n", encoding="utf-8")

    report = validator.run_acceptance(
        output_root=tmp_path / "processed",
        reports_dir=tmp_path / "reports",
        run_id="v2_13_p_test",
        command="test command",
        source_v2_13_i_report_json=brief_json,
        source_v2_13_i_pass_marker=brief_marker,
        source_v2_13_o_report_json=formal_json,
        source_v2_13_o_pass_marker=formal_marker,
        record_paths={"recommendations_jsonl": record},
    )

    assert report["overall_status"] == "PASS"
    assert report["checks"]["production_record_files_unchanged"] is True
    assert report["checks"]["recommendations_not_written"] is True
    assert report["hashes"]["brief_json"]
    assert record.read_text(encoding="utf-8") == "existing\n"
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()


def test_v2_13_p_cli_exits_zero_and_prints_no_secret_values(tmp_path: Path, capsys):
    brief_json = tmp_path / "v2_13_i.json"
    brief_marker = tmp_path / "v2_13_i.marker"
    formal_json = tmp_path / "v2_13_o.json"
    formal_marker = tmp_path / "v2_13_o.marker"
    _write_json(brief_json, _brief_report())
    _write_json(formal_json, _formal_report())
    brief_marker.write_text("exit_code=0\n", encoding="utf-8")
    formal_marker.write_text("exit_code=0\n", encoding="utf-8")

    exit_code = validator.main(
        [
            "--output-root",
            str(tmp_path / "processed"),
            "--reports-dir",
            str(tmp_path / "reports"),
            "--run-id",
            "v2_13_p_cli",
            "--source-v2-13-i-report-json",
            str(brief_json),
            "--source-v2-13-i-pass-marker",
            str(brief_marker),
            "--source-v2-13-o-report-json",
            str(formal_json),
            "--source-v2-13-o-pass-marker",
            str(formal_marker),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "PASS" in captured.out
    assert "token" not in captured.out.lower()
    assert "secret" not in captured.out.lower()
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()
