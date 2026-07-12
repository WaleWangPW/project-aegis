from __future__ import annotations

import json
from pathlib import Path

import scripts.validate_v2_9_h_current_usable_simulation_brief as validator
from aegis.paper.current_simulation_brief import (
    build_current_usable_simulation_brief,
    render_current_usable_simulation_brief_markdown,
)


def _decision_packet() -> dict:
    items = []
    for market, symbol in [("A", "600519.SH"), ("H", "00700.HK"), ("US", "MSFT")]:
        items.append(
            {
                "symbol": symbol,
                "name": f"name_{symbol}",
                "market": market,
                "strategy_id": f"strategy_{market}",
                "candidate_score": 0.8,
                "source_mode": "approved_fixture_not_live_market_data",
                "decision_packet_status": "simulation_candidate",
                "user_action": "Only manual external execution after user review.",
                "why": ["sandbox_status=PASS"],
                "risk_warnings": ["simulation-only"],
                "evidence_refs": ["evidence.json"],
            }
        )
        items.append(
            {
                "symbol": f"{market}_BLOCKED",
                "market": market,
                "strategy_id": f"strategy_{market}_blocked",
                "source_mode": "approved_fixture_not_live_market_data",
                "decision_packet_status": "blocked",
                "user_action": "Do not use.",
                "why": ["sandbox_status=FAIL"],
                "risk_warnings": ["blocked"],
                "blocked_by": ["strategy_sandbox_not_passed"],
                "evidence_refs": ["evidence.json"],
            }
        )
    return {
        "summary": {
            "sandbox_pass_count": 3,
            "sandbox_fail_count": 3,
            "real_user_api_status": "blocked_missing_metadata",
        },
        "user_boundary": {
            "current_blocker": "真实用户 API 仍缺非敏感 metadata 和本机 env var。"
        },
        "items": items,
        "network_used": False,
        "production_records_written": False,
        "dashboard_contract_changed": False,
        "safety": {
            "manual_external_execution_only": True,
            "no_live_price": True,
            "no_position_size": True,
            "no_real_trade": True,
            "no_broker_api": True,
            "no_trading_webhook": True,
            "no_order_placement": True,
        },
    }


def _review_memory_report() -> dict:
    return {
        "formal_reviews": [
            {
                "paper_trade_id": "ptr_600519",
                "review_id": "rev_600519",
                "review_date": "2026-07-11",
                "horizon": "5d",
                "outcome": "pending",
                "decision_quality": "unclear",
                "actual_return": None,
                "lessons": ["600519.SH remains pending until forward-return evidence exists."],
                "no_return_fabrication": True,
                "simulation_only": True,
            }
        ],
        "formal_memories": [
            {
                "paper_trade_id": "ptr_600519",
                "memory_id": "mem_600519",
                "lesson": "Simulation entry context only.",
                "simulation_only": True,
            }
        ],
        "production_records_written": False,
        "dashboard_contract_changed": False,
        "safety": {
            "no_real_trade_execution": True,
            "no_broker_api": True,
            "no_webhook": True,
            "no_order_placement": True,
        },
    }


def test_v2_9_h_brief_answers_current_capabilities_and_boundaries():
    brief = build_current_usable_simulation_brief(
        decision_packet=_decision_packet(),
        formal_review_memory_report=_review_memory_report(),
        run_id="unit",
        generated_at="2026-07-11T00:00:00+08:00",
    )

    assert brief["overall_status"] == "PASS"
    assert brief["summary"]["candidate_count"] == 3
    assert brief["summary"]["blocked_count"] == 3
    assert brief["summary"]["candidate_markets"] == ["A", "H", "US"]
    assert brief["summary"]["real_user_api_status"] == "blocked_missing_metadata"
    assert brief["checks"]["history_sandbox_visible"] is True
    assert brief["checks"]["review_memory_chain_visible"] is True
    assert brief["checks"]["reviews_pending_without_return_fabrication"] is True
    assert brief["safety"]["no_real_trade"] is True
    assert "bounded API" in brief["current_answer"]["can_read_online_now"]


def test_v2_9_h_markdown_is_user_readable_and_safety_explicit():
    brief = build_current_usable_simulation_brief(
        decision_packet=_decision_packet(),
        formal_review_memory_report=_review_memory_report(),
        run_id="unit",
    )

    md = render_current_usable_simulation_brief_markdown(brief)

    assert "Project Aegis 当前可用模拟简报" in md
    assert "真实 API 状态：`blocked_missing_metadata`" in md
    assert "Aegis 不真实下单" in md
    assert "actual_return：`None`" in md


def test_v2_9_h_acceptance_writes_brief_without_records_mutation(tmp_path: Path):
    decision_packet = tmp_path / "decision_packet.json"
    review_memory = tmp_path / "review_memory.json"
    decision_packet.write_text(json.dumps(_decision_packet(), ensure_ascii=False), encoding="utf-8")
    review_memory.write_text(json.dumps(_review_memory_report(), ensure_ascii=False), encoding="utf-8")
    record_path = tmp_path / "records" / "reviews.jsonl"
    record_path.parent.mkdir()
    record_path.write_text("existing\n", encoding="utf-8")

    report = validator.run_acceptance(
        output_root=tmp_path / "processed",
        reports_dir=tmp_path / "reports",
        run_id="v2_9_h_test",
        command="test command",
        decision_packet_json=decision_packet,
        review_memory_json=review_memory,
        record_paths={"reviews_jsonl": record_path},
    )

    assert report["overall_status"] == "PASS"
    assert report["checks"]["brief_json_written"] is True
    assert report["checks"]["brief_md_written"] is True
    assert report["checks"]["production_record_files_unchanged"] is True
    assert record_path.read_text(encoding="utf-8") == "existing\n"
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()


def test_v2_9_h_cli_exits_zero(tmp_path: Path, capsys):
    decision_packet = tmp_path / "decision_packet.json"
    review_memory = tmp_path / "review_memory.json"
    decision_packet.write_text(json.dumps(_decision_packet(), ensure_ascii=False), encoding="utf-8")
    review_memory.write_text(json.dumps(_review_memory_report(), ensure_ascii=False), encoding="utf-8")

    exit_code = validator.main(
        [
            "--output-root",
            str(tmp_path / "processed"),
            "--reports-dir",
            str(tmp_path / "reports"),
            "--run-id",
            "v2_9_h_cli",
            "--decision-packet-json",
            str(decision_packet),
            "--review-memory-json",
            str(review_memory),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "PASS" in captured.out
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()
