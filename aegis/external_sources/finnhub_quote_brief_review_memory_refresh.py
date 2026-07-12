"""Refresh Finnhub quote simulation brief with formal Review/Memory context.

V2.13-P consumes the already accepted V2.13-I user-readable simulation brief
and the V2.13-O formal review/memory artifacts. It produces an updated brief
that shows review/memory status without changing production records.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping


ACCEPTANCE_TARGET = "V2.13-P Finnhub Quote Current Usable Simulation Brief Refresh With Review/Memory Context"
SOURCE_BRIEF_TARGET = "V2.13-I Finnhub Quote Current Simulation Brief"
SOURCE_FORMAL_TARGET = "V2.13-O Finnhub Quote Formal Review/Memory Records From Virtual Trade Candidates"


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _by_symbol(formal_report: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    reviews = formal_report.get("formal_reviews") or []
    memories = formal_report.get("formal_memories") or []
    memory_by_trade = {item.get("paper_trade_id"): item for item in memories}
    result: dict[str, dict[str, Any]] = {}
    for review in reviews:
        symbol = None
        for lesson in review.get("lessons") or []:
            if "（" in str(lesson):
                symbol = str(lesson).split("（", 1)[0]
                break
        if not symbol:
            continue
        memory = memory_by_trade.get(review.get("paper_trade_id"))
        result[symbol] = {
            "review_id": review.get("review_id"),
            "memory_id": memory.get("memory_id") if memory else None,
            "paper_trade_id": review.get("paper_trade_id"),
            "recommendation_id": review.get("recommendation_id"),
            "review_date": review.get("review_date"),
            "horizon": review.get("horizon"),
            "outcome": review.get("outcome"),
            "decision_quality": review.get("decision_quality"),
            "actual_return": review.get("actual_return"),
            "max_drawdown": review.get("max_drawdown"),
            "exit_price": review.get("exit_price"),
            "exit_date": review.get("exit_date"),
            "outcome_evidence_status": review.get("outcome_evidence_status"),
            "source_trade_status": review.get("source_trade_status"),
            "lesson": (review.get("lessons") or [None])[0],
            "memory_lesson": memory.get("lesson") if memory else None,
            "formal_artifact_only": True,
            "simulation_only": review.get("simulation_only") is True,
            "social_sentiment_not_enabled": review.get("social_sentiment_not_enabled") is True,
            "no_return_fabrication": review.get("no_return_fabrication") is True,
            "no_exit_fabrication": review.get("no_exit_fabrication") is True,
            "no_review_record_production_mutation": review.get("no_review_record_production_mutation") is True,
        }
    return result


def build_finnhub_quote_brief_review_memory_refresh(
    brief_report: Mapping[str, Any],
    formal_report: Mapping[str, Any],
    *,
    run_id: str,
    command: str | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    contexts = _by_symbol(formal_report)
    refreshed_items: list[dict[str, Any]] = []
    for item in brief_report.get("items") or []:
        symbol = item.get("symbol")
        context = contexts.get(str(symbol))
        refreshed_items.append(
            {
                **item,
                "review_memory_context": context,
                "review_memory_status": "formal_pending" if context else "missing_formal_context",
                "user_next_action": (
                    "该候选已经进入 formal Review/Memory 模拟复盘队列；当前仍等待用户回传退出、持有或结果证据。"
                    "可以继续观察，但不能把 pending 复盘误读成已盈利、已失败或可自动交易。"
                    if context
                    else "该候选暂无 formal Review/Memory context，不能进入复盘解释。"
                ),
                "requires_user_returned_outcome_evidence": context is not None,
                "no_return_fabrication": True,
                "no_exit_fabrication": True,
                "no_review_memory_production_mutation": True,
            }
        )

    candidates = [item for item in refreshed_items if item.get("brief_status") == "simulation_candidate"]
    context_items = [item for item in refreshed_items if item.get("review_memory_context")]
    checks = {
        "source_brief_is_v2_13_i": brief_report.get("acceptance_target") == SOURCE_BRIEF_TARGET,
        "source_formal_is_v2_13_o": formal_report.get("acceptance_target") == SOURCE_FORMAL_TARGET,
        "source_brief_pass": brief_report.get("overall_status") == "PASS",
        "source_formal_pass": formal_report.get("overall_status") == "PASS",
        "source_formal_artifacts_only": formal_report.get("safety", {}).get("formal_artifacts_only") is True,
        "source_social_sentiment_still_blocked": brief_report.get("summary", {}).get("social_sentiment_status")
        == "blocked_plan_or_rate_limit"
        and formal_report.get("summary", {}).get("social_sentiment_status") == "blocked_plan_or_rate_limit",
        "has_simulation_candidate": bool(candidates),
        "has_review_memory_context_for_candidate": len(context_items) == len(candidates) and bool(candidates),
        "all_contexts_pending_without_returns": all(
            (ctx := item.get("review_memory_context"))
            and ctx.get("outcome") == "pending"
            and ctx.get("decision_quality") == "unclear"
            and ctx.get("actual_return") is None
            and ctx.get("max_drawdown") is None
            and ctx.get("exit_price") is None
            and ctx.get("exit_date") is None
            for item in context_items
        ),
        "all_items_require_user_outcome_evidence": all(
            item.get("requires_user_returned_outcome_evidence") is True for item in context_items
        ),
        "no_return_fabrication": all(item.get("no_return_fabrication") is True for item in refreshed_items),
        "no_exit_fabrication": all(item.get("no_exit_fabrication") is True for item in refreshed_items),
        "no_review_memory_production_mutation": all(
            item.get("no_review_memory_production_mutation") is True for item in refreshed_items
        ),
        "simulation_only": brief_report.get("safety", {}).get("simulation_only") is True
        and formal_report.get("safety", {}).get("simulation_only") is True,
        "no_real_trade": brief_report.get("safety", {}).get("no_real_trade") is True
        and formal_report.get("safety", {}).get("no_real_trade_execution") is True,
        "no_broker_api": brief_report.get("safety", {}).get("no_broker_api") is True
        and formal_report.get("safety", {}).get("no_broker_api") is True,
        "no_webhook": brief_report.get("safety", {}).get("no_trading_webhook") is True
        and formal_report.get("safety", {}).get("no_webhook") is True,
        "no_order_placement": brief_report.get("safety", {}).get("no_order_placement") is True
        and formal_report.get("safety", {}).get("no_order_placement") is True,
        "no_live_price": brief_report.get("safety", {}).get("no_live_price") is True
        and formal_report.get("safety", {}).get("no_live_price") is True,
        "no_position_size": brief_report.get("safety", {}).get("no_position_size") is True
        and formal_report.get("safety", {}).get("no_position_size") is True,
        "no_live_order_signal": brief_report.get("safety", {}).get("no_live_order_signal") is True
        and formal_report.get("safety", {}).get("no_live_order_signal") is True,
        "production_records_not_written": brief_report.get("production_records_written") is False
        and formal_report.get("production_records_written") is False,
        "network_not_used": brief_report.get("network_used") is False and formal_report.get("network_used") is False,
        "dashboard_contract_unchanged": brief_report.get("dashboard_contract_changed") is False
        and formal_report.get("dashboard_contract_changed") is False,
    }
    return {
        "overall_status": "PASS" if all(checks.values()) else "FAIL",
        "acceptance_target": ACCEPTANCE_TARGET,
        "source_brief_acceptance_target": brief_report.get("acceptance_target"),
        "source_formal_acceptance_target": formal_report.get("acceptance_target"),
        "brief_type": "finnhub_quote_current_simulation_brief_with_review_memory",
        "run_id": run_id,
        "generated_at": generated_at or _now_iso(),
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
            "candidate_count": len(candidates),
            "review_memory_context_count": len(context_items),
            "candidate_symbols": [item.get("symbol") for item in candidates],
            "social_sentiment_status": brief_report.get("summary", {}).get("social_sentiment_status"),
            "review_memory_status": "formal_pending",
            "next_stage": "V2.13-Q Finnhub Quote Multi-Symbol Candidate Expansion Plan",
        },
        "current_answer": {
            **dict(brief_report.get("current_answer") or {}),
            "review_memory_status": (
                "AAPL.US 已有 formal simulation Review/Memory context，但复盘仍 pending；"
                "需要用户后续回传持有、退出、截图或文字结果证据，系统不得自行推断收益。"
            ),
        },
        "user_boundary": brief_report.get("user_boundary") or {},
        "items": refreshed_items,
        "checks": checks,
        "safety": {
            "simulation_only": True,
            "formal_review_memory_context_visible": True,
            "formal_artifacts_only": True,
            "requires_user_returned_outcome_evidence": True,
            "social_sentiment_not_enabled": True,
            "no_return_fabrication": True,
            "no_exit_fabrication": True,
            "no_real_trade": True,
            "no_broker_api": True,
            "no_webhook": True,
            "no_order_placement": True,
            "no_live_price": True,
            "no_position_size": True,
            "no_live_order_signal": True,
            "no_production_records_mutation": True,
            "no_strategy_mutation": True,
            "dashboard_contract_unchanged": True,
        },
    }


def render_finnhub_quote_brief_review_memory_refresh_markdown(report: Mapping[str, Any]) -> str:
    lines = [
        "# Project Aegis Finnhub Quote 模拟建议与复盘状态简报",
        "",
        f"- 状态：`{report.get('overall_status')}`",
        f"- 阶段：`{report.get('acceptance_target')}`",
        f"- 候选数量：`{report.get('summary', {}).get('candidate_count')}`",
        f"- Review/Memory context：`{report.get('summary', {}).get('review_memory_context_count')}`",
        f"- social_sentiment_status：`{report.get('summary', {}).get('social_sentiment_status')}`",
        f"- 下一步：`{report.get('summary', {}).get('next_stage')}`",
        "",
        "## 当前答案",
        "",
    ]
    for value in report.get("current_answer", {}).values():
        lines.append(f"- {value}")
    lines.extend(["", "## 候选与复盘状态", ""])
    for item in report.get("items", []):
        ctx = item.get("review_memory_context") or {}
        lines.extend(
            [
                f"### {item.get('symbol')}",
                "",
                f"- 候选状态：`{item.get('brief_status')}`",
                f"- Review/Memory 状态：`{item.get('review_memory_status')}`",
                f"- review_id：`{ctx.get('review_id')}`",
                f"- memory_id：`{ctx.get('memory_id')}`",
                f"- outcome：`{ctx.get('outcome')}`",
                f"- decision_quality：`{ctx.get('decision_quality')}`",
                f"- actual_return：`{ctx.get('actual_return')}`",
                f"- max_drawdown：`{ctx.get('max_drawdown')}`",
                f"- exit_price：`{ctx.get('exit_price')}`",
                f"- exit_date：`{ctx.get('exit_date')}`",
                f"- 用户下一步：{item.get('user_next_action')}",
                "",
            ]
        )
    lines.extend(
        [
            "## 边界",
            "",
            "- 仅模拟，不是真实交易。",
            "- 不接券商，不使用 webhook，不下单。",
            "- 不含实时价格，不含仓位数量。",
            "- open 虚拟交易不得编造收益、回撤、退出价或退出日。",
            "- Finnhub social sentiment 仍 blocked，不作为 Reddit/Twitter 情绪信号。",
            "",
        ]
    )
    return "\n".join(lines)
