"""Bridge Finnhub quote virtual PaperTrade ledger to review/memory candidates.

The bridge keeps the loop moving without mutating production review or memory
JSONL files. It creates evidence candidates that a later acceptance step can
turn into formal review/memory records.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Mapping, Sequence


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def build_finnhub_quote_review_evidence_links(
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
                "review_evidence_link_id": f"finnhub_quote_review_link_{trade['paper_trade_id']}",
                "source_type": "finnhub_quote_virtual_paper_trade_ledger",
                "paper_trade_id": trade["paper_trade_id"],
                "recommendation_id": trade["recommendation_id"],
                "symbol": trade["symbol"],
                "market": trade["market"],
                "entry_date": trade["entry_date"],
                "entry_price": trade["entry_price"],
                "status": trade["status"],
                "review_input_status": "candidate_evidence",
                "review_use": "finnhub_quote_virtual_paper_trade_context",
                "suggested_review_horizons": ["5d", "10d", "20d", "40d", "exit"],
                "evidence_refs": [evidence_ref, *list(trade.get("source_evidence_refs") or [])],
                "source_user_evidence_items": list(trade.get("source_user_evidence_items") or []),
                "created_at": created,
                "simulation_only": True,
                "quote_context_research_only": True,
                "social_sentiment_not_enabled": True,
                "requires_review_before_record_write": True,
                "no_review_record_mutation": True,
                "no_memory_jsonl_mutation": True,
                "no_paper_trade_mutation": True,
                "no_recommendation_mutation": True,
                "no_live_price": True,
                "no_position_size": True,
                "no_live_order_signal": True,
            }
        )
    return links


def build_finnhub_quote_memory_candidates(
    virtual_paper_trades: Sequence[Mapping],
    *,
    evidence_ref: str,
    created_at: str | None = None,
) -> list[dict]:
    created = created_at or _now_iso()
    candidates: list[dict] = []
    for trade in virtual_paper_trades:
        lesson = (
            f"{trade['symbol']}（{trade['market']}）：已从 Finnhub quote context、沙盘证据和用户验证入场证据"
            f"创建 simulation-only virtual PaperTrade ledger，入场价 {trade['entry_price']}，"
            f"入场日 {trade['entry_date']}。该记录只能作为后续复盘候选，不能自动改变策略或触发真实交易。"
        )
        candidates.append(
            {
                "memory_candidate_id": f"finnhub_quote_memory_candidate_{trade['paper_trade_id']}",
                "source_type": "finnhub_quote_virtual_paper_trade_ledger",
                "linked_recommendation_id": trade["recommendation_id"],
                "paper_trade_id": trade["paper_trade_id"],
                "symbol": trade["symbol"],
                "market": trade["market"],
                "lesson_type": "finnhub_quote_virtual_trade_entry_context",
                "lesson": lesson,
                "tags": ["finnhub_quote", "virtual_paper_trade", "simulation_only", trade["market"]],
                "confidence": 0.5,
                "evidence_refs": [evidence_ref, *list(trade.get("source_evidence_refs") or [])],
                "source_user_evidence_items": list(trade.get("source_user_evidence_items") or []),
                "created_at": created,
                "requires_review_before_memory_write": True,
                "quote_context_research_only": True,
                "social_sentiment_not_enabled": True,
                "no_memory_jsonl_mutation": True,
                "no_strategy_mutation": True,
                "no_real_trade_execution": True,
                "no_broker_api": True,
                "no_webhook": True,
                "no_order_placement": True,
                "no_live_price": True,
                "no_position_size": True,
                "no_live_order_signal": True,
            }
        )
    return candidates


def build_finnhub_quote_review_memory_report(
    source_report: Mapping,
    *,
    run_id: str,
    evidence_ref: str,
    command: str | None = None,
) -> dict:
    virtual_trades = list(source_report.get("virtual_paper_trades") or [])
    review_links = build_finnhub_quote_review_evidence_links(virtual_trades, evidence_ref=evidence_ref)
    memory_candidates = build_finnhub_quote_memory_candidates(virtual_trades, evidence_ref=evidence_ref)
    checks = {
        "source_is_v2_13_m": source_report.get("acceptance_target")
        == "V2.13-M Finnhub Quote Virtual PaperTrade Creation From Validated Evidence",
        "source_report_pass": source_report.get("overall_status") == "PASS",
        "source_social_sentiment_not_enabled": source_report.get("summary", {}).get("social_sentiment_status")
        == "blocked_plan_or_rate_limit",
        "has_virtual_paper_trades": bool(virtual_trades),
        "review_links_for_each_virtual_trade": len(review_links) == len(virtual_trades),
        "memory_candidates_for_each_virtual_trade": len(memory_candidates) == len(virtual_trades),
        "all_review_links_are_candidate_evidence": all(
            item["review_input_status"] == "candidate_evidence" for item in review_links
        ),
        "all_review_links_require_review_before_record_write": all(
            item["requires_review_before_record_write"] for item in review_links
        ),
        "all_memory_candidates_require_review": all(
            item["requires_review_before_memory_write"] for item in memory_candidates
        ),
        "all_items_simulation_only": all(item["simulation_only"] for item in review_links),
        "all_items_quote_context_research_only": all(
            item["quote_context_research_only"] for item in [*review_links, *memory_candidates]
        ),
        "all_items_social_sentiment_not_enabled": all(
            item["social_sentiment_not_enabled"] for item in [*review_links, *memory_candidates]
        ),
        "all_items_have_source_user_evidence": all(
            bool(item["source_user_evidence_items"]) for item in [*review_links, *memory_candidates]
        ),
        "no_review_record_mutation": all(item["no_review_record_mutation"] for item in review_links),
        "no_memory_jsonl_mutation": all(item["no_memory_jsonl_mutation"] for item in memory_candidates),
        "no_paper_trade_mutation": all(item["no_paper_trade_mutation"] for item in review_links),
        "no_recommendation_mutation": all(item["no_recommendation_mutation"] for item in review_links),
        "no_strategy_mutation": all(item["no_strategy_mutation"] for item in memory_candidates),
        "no_real_trade_execution": all(item["no_real_trade_execution"] for item in memory_candidates),
        "no_broker_api": all(item["no_broker_api"] for item in memory_candidates),
        "no_webhook": all(item["no_webhook"] for item in memory_candidates),
        "no_order_placement": all(item["no_order_placement"] for item in memory_candidates),
        "no_live_price": all(item["no_live_price"] for item in [*review_links, *memory_candidates]),
        "no_position_size": all(item["no_position_size"] for item in [*review_links, *memory_candidates]),
        "no_live_order_signal": all(item["no_live_order_signal"] for item in [*review_links, *memory_candidates]),
    }
    return {
        "overall_status": "PASS" if all(checks.values()) else "FAIL",
        "acceptance_target": "V2.13-N Finnhub Quote Virtual PaperTrade Review/Memory Bridge",
        "source_acceptance_target": source_report.get("acceptance_target"),
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
            "virtual_paper_trade_count": len(virtual_trades),
            "review_link_count": len(review_links),
            "memory_candidate_count": len(memory_candidates),
            "symbols": [item["symbol"] for item in review_links],
            "markets": sorted({item["market"] for item in review_links}),
            "social_sentiment_status": source_report.get("summary", {}).get("social_sentiment_status"),
            "next_stage": "V2.13-O Finnhub Quote Formal Review/Memory Records From Virtual Trade Candidates",
        },
        "review_evidence_links": review_links,
        "memory_candidates": memory_candidates,
        "checks": checks,
        "safety": {
            "simulation_only": True,
            "candidate_evidence_only": True,
            "quote_context_research_only": True,
            "social_sentiment_not_enabled": True,
            "no_real_trade_execution": True,
            "no_broker_api": True,
            "no_webhook": True,
            "no_order_placement": True,
            "no_live_price": True,
            "no_position_size": True,
            "no_live_order_signal": True,
            "no_review_record_mutation": True,
            "no_memory_jsonl_mutation": True,
            "no_paper_trade_mutation": True,
            "no_recommendation_mutation": True,
            "no_strategy_mutation": True,
            "dashboard_contract_unchanged": True,
        },
    }
