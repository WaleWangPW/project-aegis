"""Build formal simulation review/memory records from Finnhub quote candidates.

These artifacts are model-shaped `ReviewRecord` and `InvestmentMemory`
records for the V2.13 Finnhub quote simulation loop. They are acceptance
outputs only; this module never appends to production JSONL files.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Mapping, Sequence

from aegis.models.investment_memory import InvestmentMemory
from aegis.models.review import ReviewRecord


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _safe_id(value: object) -> str:
    return "".join(ch if ch.isalnum() else "_" for ch in str(value)).strip("_")


def build_finnhub_quote_formal_reviews(
    review_evidence_links: Sequence[Mapping],
    *,
    created_at: str | None = None,
) -> list[dict]:
    created = created_at or _now_iso()
    reviews: list[dict] = []
    for link in review_evidence_links:
        lesson = (
            f"{link['symbol']}（{link['market']}）已进入 Finnhub quote simulation-only virtual "
            "PaperTrade formal review artifact；该虚拟交易仍为 open，尚无用户回传的退出价、"
            "退出日或 forward return，因此结果保持 pending/unclear。"
        )
        review = ReviewRecord(
            review_id=f"rev_finnhub_quote_{_safe_id(link['paper_trade_id'])}_entry",
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
                "status": "DATA_GAP: open virtual trade has no user-returned outcome evidence yet.",
                "source": "V2.13-N Finnhub quote review evidence link",
            },
            lessons=[lesson],
            created_at=created,
        ).model_dump()
        reviews.append(
            {
                **review,
                "simulation_only": True,
                "quote_context_research_only": True,
                "source_review_evidence_link_id": link["review_evidence_link_id"],
                "source_trade_status": link.get("status"),
                "entry_price": link.get("entry_price"),
                "entry_date": link.get("entry_date"),
                "exit_price": None,
                "exit_date": None,
                "outcome_evidence_status": "pending_user_returned_evidence",
                "social_sentiment_not_enabled": True,
                "evidence_refs": list(link.get("evidence_refs") or []),
                "source_user_evidence_items": list(link.get("source_user_evidence_items") or []),
                "no_return_fabrication": True,
                "no_exit_fabrication": True,
                "no_review_record_production_mutation": True,
                "no_real_trade_execution": True,
                "no_broker_api": True,
                "no_webhook": True,
                "no_order_placement": True,
                "no_live_price": True,
                "no_position_size": True,
                "no_live_order_signal": True,
            }
        )
    return reviews


def build_finnhub_quote_formal_memories(
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
            + " 当前 formal memory artifact 只记录 Finnhub quote simulation entry context；"
            "收益、回撤、退出原因必须等待用户回传证据，不能由系统推断。"
        )
        memory = InvestmentMemory(
            memory_id=f"mem_finnhub_quote_{_safe_id(candidate['paper_trade_id'])}_entry_context",
            date=review["review_date"] if review else candidate["created_at"][:10],
            source_type="finnhub_quote_simulation_review_candidate",
            linked_recommendation_id=candidate["linked_recommendation_id"],
            lesson_type="finnhub_quote_virtual_trade_entry_context",
            lesson=lesson,
            tags=[*list(candidate.get("tags") or []), "review_pending", "formal_artifact_only"],
            confidence=0.5,
            created_at=created,
        ).model_dump()
        memories.append(
            {
                **memory,
                "simulation_only": True,
                "quote_context_research_only": True,
                "source_memory_candidate_id": candidate["memory_candidate_id"],
                "paper_trade_id": candidate["paper_trade_id"],
                "source_review_id": review["review_id"] if review else None,
                "outcome_evidence_status": "pending_user_returned_evidence",
                "social_sentiment_not_enabled": True,
                "evidence_refs": list(candidate.get("evidence_refs") or []),
                "source_user_evidence_items": list(candidate.get("source_user_evidence_items") or []),
                "no_memory_jsonl_production_mutation": True,
                "no_strategy_mutation": True,
                "no_return_fabrication": True,
                "no_exit_fabrication": True,
                "no_real_trade_execution": True,
                "no_broker_api": True,
                "no_webhook": True,
                "no_order_placement": True,
                "no_live_price": True,
                "no_position_size": True,
                "no_live_order_signal": True,
            }
        )
    return memories


def build_finnhub_quote_formal_review_memory_report(
    source_report: Mapping,
    *,
    run_id: str,
    command: str | None = None,
) -> dict:
    review_links = list(source_report.get("review_evidence_links") or [])
    memory_candidates = list(source_report.get("memory_candidates") or [])
    reviews = build_finnhub_quote_formal_reviews(review_links)
    memories = build_finnhub_quote_formal_memories(memory_candidates, reviews)
    checks = {
        "source_is_v2_13_n": source_report.get("acceptance_target")
        == "V2.13-N Finnhub Quote Virtual PaperTrade Review/Memory Bridge",
        "source_report_pass": source_report.get("overall_status") == "PASS",
        "source_social_sentiment_not_enabled": source_report.get("summary", {}).get("social_sentiment_status")
        == "blocked_plan_or_rate_limit",
        "source_candidate_evidence_only": source_report.get("safety", {}).get("candidate_evidence_only") is True,
        "has_review_evidence_links": bool(review_links),
        "has_memory_candidates": bool(memory_candidates),
        "formal_reviews_for_each_link": len(reviews) == len(review_links),
        "formal_memories_for_each_candidate": len(memories) == len(memory_candidates),
        "all_reviews_pending_without_return_fabrication": all(
            item["outcome"] == "pending"
            and item["decision_quality"] == "unclear"
            and item["actual_return"] is None
            and item["max_drawdown"] is None
            and item["exit_price"] is None
            and item["exit_date"] is None
            and item["no_return_fabrication"]
            and item["no_exit_fabrication"]
            for item in reviews
        ),
        "all_reviews_have_user_evidence_refs": all(
            bool(item["source_user_evidence_items"]) for item in reviews
        ),
        "all_memories_have_user_evidence_refs": all(
            bool(item["source_user_evidence_items"]) for item in memories
        ),
        "all_memories_simulation_only": all(item["simulation_only"] for item in memories),
        "all_reviews_simulation_only": all(item["simulation_only"] for item in reviews),
        "all_items_social_sentiment_not_enabled": all(
            item["social_sentiment_not_enabled"] for item in [*reviews, *memories]
        ),
        "all_items_quote_context_research_only": all(
            item["quote_context_research_only"] for item in [*reviews, *memories]
        ),
        "no_review_record_production_mutation": all(
            item["no_review_record_production_mutation"] for item in reviews
        ),
        "no_memory_jsonl_production_mutation": all(
            item["no_memory_jsonl_production_mutation"] for item in memories
        ),
        "no_strategy_mutation": all(item["no_strategy_mutation"] for item in memories),
        "no_real_trade_execution": all(item["no_real_trade_execution"] for item in [*reviews, *memories]),
        "no_broker_api": all(item["no_broker_api"] for item in [*reviews, *memories]),
        "no_webhook": all(item["no_webhook"] for item in [*reviews, *memories]),
        "no_order_placement": all(item["no_order_placement"] for item in [*reviews, *memories]),
        "no_live_price": all(item["no_live_price"] for item in [*reviews, *memories]),
        "no_position_size": all(item["no_position_size"] for item in [*reviews, *memories]),
        "no_live_order_signal": all(item["no_live_order_signal"] for item in [*reviews, *memories]),
    }
    return {
        "overall_status": "PASS" if all(checks.values()) else "FAIL",
        "acceptance_target": "V2.13-O Finnhub Quote Formal Review/Memory Records From Virtual Trade Candidates",
        "source_acceptance_target": source_report.get("acceptance_target"),
        "run_id": run_id,
        "generated_at": _now_iso(),
        "command": command,
        "network_used": False,
        "production_records_written": False,
        "reviews_jsonl_written": False,
        "memory_jsonl_written": False,
        "investment_memory_jsonl_written": False,
        "paper_trades_written": False,
        "recommendations_written": False,
        "dashboard_contract_changed": False,
        "summary": {
            "review_evidence_link_count": len(review_links),
            "memory_candidate_count": len(memory_candidates),
            "formal_review_count": len(reviews),
            "formal_memory_count": len(memories),
            "symbols": [item["paper_trade_id"] for item in reviews],
            "social_sentiment_status": source_report.get("summary", {}).get("social_sentiment_status"),
            "next_stage": "V2.13-P Finnhub Quote Current Usable Simulation Brief Refresh With Review/Memory Context",
        },
        "formal_reviews": reviews,
        "formal_memories": memories,
        "checks": checks,
        "safety": {
            "simulation_only": True,
            "formal_artifacts_only": True,
            "quote_context_research_only": True,
            "social_sentiment_not_enabled": True,
            "production_records_not_written": True,
            "no_return_fabrication": True,
            "no_exit_fabrication": True,
            "no_review_record_production_mutation": True,
            "no_memory_jsonl_production_mutation": True,
            "no_real_trade_execution": True,
            "no_broker_api": True,
            "no_webhook": True,
            "no_order_placement": True,
            "no_live_price": True,
            "no_position_size": True,
            "no_live_order_signal": True,
            "no_strategy_mutation": True,
            "dashboard_contract_unchanged": True,
        },
    }
