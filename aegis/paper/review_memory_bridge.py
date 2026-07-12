"""Bridge virtual PaperTrade ledger records to review/memory candidates.

V2.9-F keeps the loop moving without mutating production review or memory
JSONL files. It creates evidence candidates that a later acceptance step can
turn into formal review/memory records.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Mapping, Sequence


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def build_virtual_trade_review_evidence_links(
    virtual_paper_trades: Sequence[Mapping],
    *,
    evidence_ref: str,
    created_at: str | None = None,
) -> list[dict]:
    created = created_at or _now_iso()
    links: list[dict] = []
    for trade in virtual_paper_trades:
        links.append(
            {
                "review_evidence_link_id": f"virtual_trade_review_link_{trade['paper_trade_id']}",
                "source_type": "virtual_paper_trade_ledger",
                "paper_trade_id": trade["paper_trade_id"],
                "recommendation_id": trade["recommendation_id"],
                "symbol": trade["symbol"],
                "market": trade["market"],
                "entry_date": trade["entry_date"],
                "entry_price": trade["entry_price"],
                "status": trade["status"],
                "review_input_status": "candidate_evidence",
                "review_use": "virtual_paper_trade_context",
                "suggested_review_horizons": ["5d", "10d", "20d", "40d", "exit"],
                "evidence_refs": [evidence_ref],
                "source_evidence_items": list(trade.get("source_evidence_items") or []),
                "created_at": created,
                "simulation_only": True,
                "requires_review_before_record_write": True,
                "no_review_record_mutation": True,
                "no_memory_jsonl_mutation": True,
                "no_paper_trade_mutation": True,
                "no_recommendation_mutation": True,
            }
        )
    return links


def build_virtual_trade_memory_candidates(
    virtual_paper_trades: Sequence[Mapping],
    *,
    evidence_ref: str,
    created_at: str | None = None,
) -> list[dict]:
    created = created_at or _now_iso()
    candidates: list[dict] = []
    for trade in virtual_paper_trades:
        lesson = (
            f"{trade['symbol']}（{trade['market']}）：已从用户验证入场证据创建 simulation-only "
            f"virtual PaperTrade ledger，入场价 {trade['entry_price']}，入场日 {trade['entry_date']}。"
            "该记录只能作为后续复盘候选，不能自动改变策略或触发真实交易。"
        )
        candidates.append(
            {
                "memory_candidate_id": f"virtual_trade_memory_candidate_{trade['paper_trade_id']}",
                "source_type": "virtual_paper_trade_ledger",
                "linked_recommendation_id": trade["recommendation_id"],
                "paper_trade_id": trade["paper_trade_id"],
                "symbol": trade["symbol"],
                "market": trade["market"],
                "lesson_type": "virtual_trade_entry_context",
                "lesson": lesson,
                "tags": ["virtual_paper_trade", "simulation_only", trade["market"]],
                "confidence": 0.5,
                "evidence_refs": [evidence_ref],
                "source_evidence_items": list(trade.get("source_evidence_items") or []),
                "created_at": created,
                "requires_review_before_memory_write": True,
                "no_memory_jsonl_mutation": True,
                "no_strategy_mutation": True,
                "no_real_trade_execution": True,
                "no_broker_api": True,
                "no_webhook": True,
                "no_order_placement": True,
            }
        )
    return candidates


def build_virtual_trade_review_memory_report(
    virtual_paper_trades: Sequence[Mapping],
    *,
    run_id: str,
    evidence_ref: str,
    command: str | None = None,
) -> dict:
    review_links = build_virtual_trade_review_evidence_links(virtual_paper_trades, evidence_ref=evidence_ref)
    memory_candidates = build_virtual_trade_memory_candidates(virtual_paper_trades, evidence_ref=evidence_ref)
    checks = {
        "has_virtual_paper_trades": bool(virtual_paper_trades),
        "review_links_for_each_virtual_trade": len(review_links) == len(virtual_paper_trades),
        "memory_candidates_for_each_virtual_trade": len(memory_candidates) == len(virtual_paper_trades),
        "all_review_links_are_candidate_evidence": all(
            item["review_input_status"] == "candidate_evidence" for item in review_links
        ),
        "all_memory_candidates_require_review": all(
            item["requires_review_before_memory_write"] for item in memory_candidates
        ),
        "all_items_simulation_only": all(item["simulation_only"] for item in review_links),
        "no_review_record_mutation": all(item["no_review_record_mutation"] for item in review_links),
        "no_memory_jsonl_mutation": all(item["no_memory_jsonl_mutation"] for item in memory_candidates),
        "no_paper_trade_mutation": all(item["no_paper_trade_mutation"] for item in review_links),
        "no_recommendation_mutation": all(item["no_recommendation_mutation"] for item in review_links),
        "no_strategy_mutation": all(item["no_strategy_mutation"] for item in memory_candidates),
        "no_real_trade_execution": all(item["no_real_trade_execution"] for item in memory_candidates),
        "no_broker_api": all(item["no_broker_api"] for item in memory_candidates),
        "no_webhook": all(item["no_webhook"] for item in memory_candidates),
        "no_order_placement": all(item["no_order_placement"] for item in memory_candidates),
    }
    return {
        "overall_status": "PASS" if all(checks.values()) else "FAIL",
        "acceptance_target": "V2.9-F Virtual PaperTrade Review/Memory Bridge",
        "run_id": run_id,
        "generated_at": _now_iso(),
        "command": command,
        "network_used": False,
        "production_records_written": False,
        "reviews_written": False,
        "memory_records_written": False,
        "paper_trades_written": False,
        "recommendations_written": False,
        "dashboard_contract_changed": False,
        "summary": {
            "virtual_paper_trade_count": len(virtual_paper_trades),
            "review_link_count": len(review_links),
            "memory_candidate_count": len(memory_candidates),
            "symbols": [item["symbol"] for item in review_links],
        },
        "review_evidence_links": review_links,
        "memory_candidates": memory_candidates,
        "checks": checks,
        "safety": {
            "simulation_only": True,
            "candidate_evidence_only": True,
            "no_real_trade_execution": True,
            "no_broker_api": True,
            "no_webhook": True,
            "no_order_placement": True,
            "no_review_record_mutation": True,
            "no_memory_jsonl_mutation": True,
            "no_paper_trade_mutation": True,
            "no_recommendation_mutation": True,
            "no_strategy_mutation": True,
            "dashboard_contract_unchanged": True,
        },
    }
