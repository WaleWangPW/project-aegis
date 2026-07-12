"""Build formal simulation review/memory records from virtual-trade candidates.

These records are model-shaped `ReviewRecord` and `InvestmentMemory` artifacts
for the V2.9 simulation loop. They are written to acceptance outputs only; this
module does not append to production JSONL files.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Mapping, Sequence

from aegis.models.investment_memory import InvestmentMemory
from aegis.models.review import ReviewRecord


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def _safe_id(value: object) -> str:
    return "".join(ch if ch.isalnum() else "_" for ch in str(value)).strip("_")


def build_formal_simulation_reviews(
    review_evidence_links: Sequence[Mapping],
    *,
    created_at: str | None = None,
) -> list[dict]:
    created = created_at or _now_iso()
    reviews: list[dict] = []
    for link in review_evidence_links:
        lesson = (
            f"{link['symbol']}（{link['market']}）已进入 simulation-only virtual PaperTrade 复盘队列；"
            "当前尚无 forward return，因此复盘结果保持 pending/unclear。"
        )
        review = ReviewRecord(
            review_id=f"rev_virtual_{_safe_id(link['paper_trade_id'])}_entry",
            recommendation_id=link["recommendation_id"],
            paper_trade_id=link["paper_trade_id"],
            review_date=link["entry_date"],
            horizon="5d",
            outcome="pending",
            actual_return=None,
            max_drawdown=None,
            decision_quality="unclear",
            success_reason=None,
            failure_reason=None,
            expert_contribution={
                "status": "DATA_GAP: no forward-return evidence yet; simulation review is pending.",
                "source": "V2.9-F virtual trade review evidence link",
            },
            lessons=[lesson],
            created_at=created,
        ).model_dump()
        reviews.append(
            {
                **review,
                "simulation_only": True,
                "source_review_evidence_link_id": link["review_evidence_link_id"],
                "evidence_refs": list(link.get("evidence_refs") or []),
                "source_evidence_items": list(link.get("source_evidence_items") or []),
                "no_return_fabrication": True,
                "no_review_record_production_mutation": True,
                "no_real_trade_execution": True,
                "no_broker_api": True,
                "no_webhook": True,
                "no_order_placement": True,
            }
        )
    return reviews


def build_formal_simulation_memories(
    memory_candidates: Sequence[Mapping],
    formal_reviews: Sequence[Mapping],
    *,
    created_at: str | None = None,
) -> list[dict]:
    created = created_at or _now_iso()
    review_by_trade = {item["paper_trade_id"]: item for item in formal_reviews}
    memories: list[dict] = []
    for candidate in memory_candidates:
        review = review_by_trade.get(candidate["paper_trade_id"])
        lesson = (
            candidate["lesson"]
            + " 当前记忆仅记录模拟入场上下文，后续收益/回撤需要等待正式复盘证据补齐。"
        )
        memory = InvestmentMemory(
            memory_id=f"mem_virtual_{_safe_id(candidate['paper_trade_id'])}_entry_context",
            date=review["review_date"] if review else candidate["created_at"][:10],
            source_type="simulation_review_candidate",
            linked_recommendation_id=candidate["linked_recommendation_id"],
            lesson_type="virtual_trade_entry_context",
            lesson=lesson,
            tags=[*list(candidate.get("tags") or []), "review_pending"],
            confidence=0.5,
            created_at=created,
        ).model_dump()
        memories.append(
            {
                **memory,
                "simulation_only": True,
                "source_memory_candidate_id": candidate["memory_candidate_id"],
                "paper_trade_id": candidate["paper_trade_id"],
                "source_review_id": review["review_id"] if review else None,
                "evidence_refs": list(candidate.get("evidence_refs") or []),
                "source_evidence_items": list(candidate.get("source_evidence_items") or []),
                "no_memory_jsonl_production_mutation": True,
                "no_strategy_mutation": True,
                "no_real_trade_execution": True,
                "no_broker_api": True,
                "no_webhook": True,
                "no_order_placement": True,
            }
        )
    return memories


def build_formal_review_memory_report(
    review_evidence_links: Sequence[Mapping],
    memory_candidates: Sequence[Mapping],
    *,
    run_id: str,
    command: str | None = None,
) -> dict:
    reviews = build_formal_simulation_reviews(review_evidence_links)
    memories = build_formal_simulation_memories(memory_candidates, reviews)
    checks = {
        "has_review_evidence_links": bool(review_evidence_links),
        "has_memory_candidates": bool(memory_candidates),
        "formal_reviews_for_each_link": len(reviews) == len(review_evidence_links),
        "formal_memories_for_each_candidate": len(memories) == len(memory_candidates),
        "all_reviews_pending_without_return_fabrication": all(
            item["outcome"] == "pending"
            and item["decision_quality"] == "unclear"
            and item["actual_return"] is None
            and item["no_return_fabrication"]
            for item in reviews
        ),
        "all_memories_simulation_only": all(item["simulation_only"] for item in memories),
        "all_reviews_simulation_only": all(item["simulation_only"] for item in reviews),
        "no_review_record_production_mutation": all(
            item["no_review_record_production_mutation"] for item in reviews
        ),
        "no_memory_jsonl_production_mutation": all(
            item["no_memory_jsonl_production_mutation"] for item in memories
        ),
        "no_strategy_mutation": all(item["no_strategy_mutation"] for item in memories),
        "no_real_trade_execution": all(item["no_real_trade_execution"] for item in memories),
        "no_broker_api": all(item["no_broker_api"] for item in memories),
        "no_webhook": all(item["no_webhook"] for item in memories),
        "no_order_placement": all(item["no_order_placement"] for item in memories),
    }
    return {
        "overall_status": "PASS" if all(checks.values()) else "FAIL",
        "acceptance_target": "V2.9-G Formal Review/Memory Records From Virtual Trade Candidates",
        "run_id": run_id,
        "generated_at": _now_iso(),
        "command": command,
        "network_used": False,
        "production_records_written": False,
        "reviews_jsonl_written": False,
        "memory_jsonl_written": False,
        "paper_trades_written": False,
        "recommendations_written": False,
        "dashboard_contract_changed": False,
        "summary": {
            "review_evidence_link_count": len(review_evidence_links),
            "memory_candidate_count": len(memory_candidates),
            "formal_review_count": len(reviews),
            "formal_memory_count": len(memories),
            "symbols": [item["paper_trade_id"] for item in reviews],
        },
        "formal_reviews": reviews,
        "formal_memories": memories,
        "checks": checks,
        "safety": {
            "simulation_only": True,
            "production_records_not_written": True,
            "no_return_fabrication": True,
            "no_review_record_production_mutation": True,
            "no_memory_jsonl_production_mutation": True,
            "no_real_trade_execution": True,
            "no_broker_api": True,
            "no_webhook": True,
            "no_order_placement": True,
            "no_strategy_mutation": True,
            "dashboard_contract_unchanged": True,
        },
    }
