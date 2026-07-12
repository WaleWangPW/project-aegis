"""Current usable simulation brief for the V2.9 paper/review/memory loop.

This module only aggregates accepted evidence into a user-readable brief. It
does not select new stocks, mutate strategy, append production records, or
perform live API/network work.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Mapping, Sequence


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def _candidate_items(packet: Mapping) -> list[Mapping]:
    return [
        item
        for item in packet.get("items", [])
        if item.get("decision_packet_status") == "simulation_candidate"
    ]


def _blocked_items(packet: Mapping) -> list[Mapping]:
    return [item for item in packet.get("items", []) if item.get("decision_packet_status") == "blocked"]


def _markets(items: Sequence[Mapping]) -> list[str]:
    return sorted({str(item.get("market")) for item in items if item.get("market")})


def _top_candidates(items: Sequence[Mapping], limit: int = 6) -> list[dict]:
    sorted_items = sorted(
        items,
        key=lambda item: (
            item.get("candidate_score") is None,
            -(float(item.get("candidate_score") or 0)),
            str(item.get("symbol") or ""),
        ),
    )
    top: list[dict] = []
    for item in sorted_items[:limit]:
        top.append(
            {
                "symbol": item.get("symbol"),
                "name": item.get("name"),
                "market": item.get("market"),
                "strategy_id": item.get("strategy_id"),
                "candidate_score": item.get("candidate_score"),
                "status": item.get("decision_packet_status"),
                "source_mode": item.get("source_mode"),
                "why": list(item.get("why") or [])[:5],
                "risk_warnings": list(item.get("risk_warnings") or [])[:6],
                "user_action": item.get("user_action"),
                "evidence_ref_count": len(item.get("evidence_refs") or []),
            }
        )
    return top


def _review_queue(formal_reviews: Sequence[Mapping], formal_memories: Sequence[Mapping]) -> list[dict]:
    memory_by_trade = {item.get("paper_trade_id"): item for item in formal_memories}
    queue: list[dict] = []
    for review in formal_reviews:
        memory = memory_by_trade.get(review.get("paper_trade_id"), {})
        queue.append(
            {
                "paper_trade_id": review.get("paper_trade_id"),
                "review_id": review.get("review_id"),
                "memory_id": memory.get("memory_id"),
                "review_date": review.get("review_date"),
                "horizon": review.get("horizon"),
                "outcome": review.get("outcome"),
                "decision_quality": review.get("decision_quality"),
                "actual_return": review.get("actual_return"),
                "lesson": (review.get("lessons") or [None])[0],
                "memory_lesson": memory.get("lesson"),
                "no_return_fabrication": review.get("no_return_fabrication") is True,
                "simulation_only": review.get("simulation_only") is True and memory.get("simulation_only") is True,
            }
        )
    return queue


def build_current_usable_simulation_brief(
    *,
    decision_packet: Mapping,
    formal_review_memory_report: Mapping,
    run_id: str,
    command: str | None = None,
    generated_at: str | None = None,
) -> dict:
    candidates = _candidate_items(decision_packet)
    blocked = _blocked_items(decision_packet)
    formal_reviews = list(formal_review_memory_report.get("formal_reviews") or [])
    formal_memories = list(formal_review_memory_report.get("formal_memories") or [])
    review_queue = _review_queue(formal_reviews, formal_memories)

    api_status = decision_packet.get("summary", {}).get("real_user_api_status")
    checks = {
        "has_current_decision_packet": bool(decision_packet),
        "has_simulation_candidates": bool(candidates),
        "has_a_h_us_candidates": {"A", "H", "US"}.issubset(_markets(candidates)),
        "has_blocked_paths": bool(blocked),
        "blocked_paths_visible": len(blocked) >= 3,
        "history_sandbox_visible": decision_packet.get("summary", {}).get("sandbox_pass_count", 0) > 0
        and decision_packet.get("summary", {}).get("sandbox_fail_count", 0) > 0,
        "api_blocker_visible": api_status == "blocked_missing_metadata",
        "review_memory_chain_visible": bool(review_queue),
        "reviews_pending_without_return_fabrication": all(
            item.get("outcome") == "pending"
            and item.get("decision_quality") == "unclear"
            and item.get("actual_return") is None
            and item.get("no_return_fabrication") is True
            for item in review_queue
        ),
        "manual_external_execution_only": decision_packet.get("safety", {}).get("manual_external_execution_only")
        is True,
        "no_live_price": decision_packet.get("safety", {}).get("no_live_price") is True,
        "no_position_size": decision_packet.get("safety", {}).get("no_position_size") is True,
        "no_real_trade": decision_packet.get("safety", {}).get("no_real_trade") is True
        and formal_review_memory_report.get("safety", {}).get("no_real_trade_execution") is True,
        "no_broker_api": decision_packet.get("safety", {}).get("no_broker_api") is True
        and formal_review_memory_report.get("safety", {}).get("no_broker_api") is True,
        "no_trading_webhook": decision_packet.get("safety", {}).get("no_trading_webhook") is True
        and formal_review_memory_report.get("safety", {}).get("no_webhook") is True,
        "no_order_placement": decision_packet.get("safety", {}).get("no_order_placement") is True
        and formal_review_memory_report.get("safety", {}).get("no_order_placement") is True,
        "production_records_not_written": decision_packet.get("production_records_written") is False
        and formal_review_memory_report.get("production_records_written") is False,
        "dashboard_contract_unchanged": decision_packet.get("dashboard_contract_changed") is False
        and formal_review_memory_report.get("dashboard_contract_changed") is False,
    }

    brief = {
        "overall_status": "PASS" if all(checks.values()) else "FAIL",
        "acceptance_target": "V2.9-H Current Usable Simulation Brief Refresh",
        "brief_type": "current_usable_simulation_brief",
        "run_id": run_id,
        "generated_at": generated_at or _now_iso(),
        "command": command,
        "network_used": False,
        "production_records_written": False,
        "dashboard_contract_changed": False,
        "summary": {
            "candidate_count": len(candidates),
            "blocked_count": len(blocked),
            "candidate_markets": _markets(candidates),
            "blocked_markets": _markets(blocked),
            "top_candidate_symbols": [item.get("symbol") for item in _top_candidates(candidates, limit=6)],
            "sandbox_pass_count": decision_packet.get("summary", {}).get("sandbox_pass_count"),
            "sandbox_fail_count": decision_packet.get("summary", {}).get("sandbox_fail_count"),
            "real_user_api_status": api_status,
            "formal_review_count": len(formal_reviews),
            "formal_memory_count": len(formal_memories),
            "review_pending_count": len([item for item in review_queue if item.get("outcome") == "pending"]),
        },
        "current_answer": {
            "can_read_online_now": (
                "系统已有 bounded API/live-public-source 读取入口和公开来源 hash 审计能力；"
                "真实用户 API 仍等待非敏感 metadata 与本机 env var。"
            ),
            "history_sandbox_status": (
                "已完成 A/H/US refresh hypotheses 的历史沙盘重跑；当前可见 pass/fail 证据，"
                "但通过项仍只允许进入 simulation-only suggestion path。"
            ),
            "strategy_research_status": (
                "A股、港股、美股策略研究已进入 source catalog、sandbox queue、Suggestion Gate、"
                "concrete candidate binding 和当前 decision packet。"
            ),
            "usable_suggestions_status": (
                "当前可输出 simulation-only 候选简报；用户若采用，必须在外部软件手动核对和执行，"
                "再把截图或文字回传给 Aegis。"
            ),
        },
        "user_boundary": {
            "allowed": [
                "阅读当前 simulation candidates，作为观察和纸面验证清单。",
                "在外部行情/券商软件手动核对实时价格、事件、持仓冲突和个人风险预算。",
                "把截图、成交记录或文字决策回传给 Aegis 作为证据。",
            ],
            "forbidden": [
                "Aegis 不真实下单。",
                "Aegis 不连接 Broker API。",
                "Aegis 不使用 trading webhook。",
                "Aegis 不给实时价格或仓位数量。",
                "Aegis 不把 fixture candidates 冒充为 live API candidates。",
            ],
            "current_blocker": decision_packet.get("user_boundary", {}).get("current_blocker"),
        },
        "top_candidates": _top_candidates(candidates, limit=6),
        "blocked_paths": [
            {
                "symbol": item.get("symbol"),
                "market": item.get("market"),
                "strategy_id": item.get("strategy_id"),
                "blocked_by": list(item.get("blocked_by") or []),
                "why": list(item.get("why") or [])[:5],
            }
            for item in blocked
        ],
        "review_memory_queue": review_queue,
        "checks": checks,
        "safety": {
            "simulation_only": True,
            "manual_external_execution_only": True,
            "real_user_api_blocked_missing_metadata": api_status == "blocked_missing_metadata",
            "review_pending_without_return_fabrication": True,
            "no_live_price": True,
            "no_position_size": True,
            "no_real_trade": True,
            "no_broker_api": True,
            "no_trading_webhook": True,
            "no_order_placement": True,
            "no_production_records_mutation": True,
            "no_strategy_mutation": True,
            "dashboard_contract_unchanged": True,
        },
    }
    return brief


def render_current_usable_simulation_brief_markdown(brief: Mapping) -> str:
    lines = [
        "# Project Aegis 当前可用模拟简报",
        "",
        f"- 状态：`{brief.get('overall_status')}`",
        f"- 阶段：`{brief.get('acceptance_target')}`",
        f"- 候选数量：`{brief.get('summary', {}).get('candidate_count')}`",
        f"- 阻断路径：`{brief.get('summary', {}).get('blocked_count')}`",
        f"- 覆盖市场：`{brief.get('summary', {}).get('candidate_markets')}`",
        f"- 真实 API 状态：`{brief.get('summary', {}).get('real_user_api_status')}`",
        "",
        "## 现在能做什么",
        "",
    ]
    for value in brief.get("current_answer", {}).values():
        lines.append(f"- {value}")
    lines.extend(["", "## 你可以怎么用", ""])
    for item in brief.get("user_boundary", {}).get("allowed", []):
        lines.append(f"- {item}")
    lines.extend(["", "## 不能做什么", ""])
    for item in brief.get("user_boundary", {}).get("forbidden", []):
        lines.append(f"- {item}")
    lines.extend(["", f"当前阻塞：{brief.get('user_boundary', {}).get('current_blocker')}", "", "## 重点模拟候选", ""])
    for item in brief.get("top_candidates", []):
        lines.extend(
            [
                f"### {item.get('symbol')} {item.get('name') or ''}".rstrip(),
                "",
                f"- 市场：`{item.get('market')}`",
                f"- 策略：`{item.get('strategy_id')}`",
                f"- 分数：`{item.get('candidate_score')}`",
                f"- 来源：`{item.get('source_mode')}`",
                f"- 建议动作：{item.get('user_action')}",
                f"- 证据数：`{item.get('evidence_ref_count')}`",
                "",
            ]
        )
    lines.extend(["## 当前复盘/记忆队列", ""])
    for item in brief.get("review_memory_queue", []):
        lines.extend(
            [
                f"### {item.get('paper_trade_id')}",
                "",
                f"- review_id：`{item.get('review_id')}`",
                f"- outcome：`{item.get('outcome')}`",
                f"- decision_quality：`{item.get('decision_quality')}`",
                f"- actual_return：`{item.get('actual_return')}`",
                f"- 说明：{item.get('lesson')}",
                "",
            ]
        )
    lines.extend(["## 阻断路径", ""])
    for item in brief.get("blocked_paths", []):
        lines.extend(
            [
                f"- `{item.get('symbol')}` / `{item.get('market')}` blocked_by=`{', '.join(item.get('blocked_by') or [])}`",
            ]
        )
    return "\n".join(lines) + "\n"
