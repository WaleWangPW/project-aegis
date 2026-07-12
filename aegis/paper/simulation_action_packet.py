"""Simulation-only action packet for daily user review.

This module formats already-accepted evidence into a practical packet. It does
not select new stocks, fetch the network, mutate strategy, write production
records, or place trades.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping, Sequence


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _as_list(values: Sequence[Any] | None, *, limit: int | None = None) -> list[Any]:
    items = list(values or [])
    return items[:limit] if limit is not None else items


def _market_order(market: str | None) -> int:
    return {"A": 0, "H": 1, "US": 2}.get(str(market), 9)


def _action_items(candidates: Sequence[Mapping[str, Any]], *, limit: int = 6) -> list[dict[str, Any]]:
    sorted_candidates = sorted(
        candidates,
        key=lambda item: (
            _market_order(item.get("market")),
            item.get("candidate_score") is None,
            -(float(item.get("candidate_score") or 0)),
            str(item.get("symbol") or ""),
        ),
    )
    actions: list[dict[str, Any]] = []
    for priority, item in enumerate(sorted_candidates[:limit], start=1):
        actions.append(
            {
                "priority": priority,
                "symbol": item.get("symbol"),
                "name": item.get("name"),
                "market": item.get("market"),
                "strategy_id": item.get("strategy_id"),
                "source_mode": item.get("source_mode"),
                "candidate_score": item.get("candidate_score"),
                "action_type": "manual_review_for_simulation_watch",
                "user_steps": [
                    "在外部行情软件核对实时价格、公告、新闻和流动性。",
                    "检查是否与当前持仓、现金计划和个人风险预算冲突。",
                    "如果你决定手动操作，只能在 Aegis 外部完成，并把截图或文字结果回传。",
                ],
                "do_not_include": [
                    "live_price",
                    "position_size",
                    "order_instruction",
                    "broker_action",
                ],
                "why": _as_list(item.get("why"), limit=5),
                "risk_warnings": _as_list(item.get("risk_warnings"), limit=6),
                "evidence_ref_count": item.get("evidence_ref_count"),
                "simulation_only": True,
                "manual_external_execution_only": True,
            }
        )
    return actions


def _blocked_actions(blocked_paths: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    for item in blocked_paths:
        actions.append(
            {
                "symbol": item.get("symbol"),
                "market": item.get("market"),
                "strategy_id": item.get("strategy_id"),
                "action_type": "do_not_use_for_entry",
                "blocked_by": _as_list(item.get("blocked_by"), limit=8),
                "why": _as_list(item.get("why"), limit=5),
                "simulation_only": True,
            }
        )
    return actions


def _return_evidence_requests(review_queue: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    requests: list[dict[str, Any]] = []
    for item in review_queue:
        requests.append(
            {
                "paper_trade_id": item.get("paper_trade_id"),
                "review_id": item.get("review_id"),
                "current_outcome": item.get("outcome"),
                "current_decision_quality": item.get("decision_quality"),
                "requested_user_evidence": [
                    "如果你已在外部软件手动观察或操作，请回传截图路径或文字说明。",
                    "如果已有模拟结果，请回传 entry/exit 日期、价格和原因。",
                    "如果没有新证据，保持 pending，不编造收益。",
                ],
                "no_return_fabrication": item.get("no_return_fabrication") is True,
                "simulation_only": item.get("simulation_only") is True,
            }
        )
    return requests


def build_simulation_action_packet(
    *,
    current_brief: Mapping[str, Any],
    api_backed_brief: Mapping[str, Any],
    run_id: str,
    command: str | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    """Build a daily action packet from accepted simulation evidence."""

    top_candidates = list(current_brief.get("top_candidates") or [])
    blocked_paths = list(current_brief.get("blocked_paths") or [])
    review_queue = list(current_brief.get("review_memory_queue") or [])
    current_summary = dict(current_brief.get("summary") or {})
    api_status = api_backed_brief.get("brief_status")

    today_focus = _action_items(top_candidates, limit=6)
    blocked_actions = _blocked_actions(blocked_paths)
    return_requests = _return_evidence_requests(review_queue)

    checks = {
        "source_current_brief_pass": current_brief.get("overall_status") == "PASS",
        "source_api_gate_pass": api_backed_brief.get("overall_status") == "PASS",
        "has_today_focus": bool(today_focus),
        "has_a_h_us_focus": {"A", "H", "US"}.issubset({str(item.get("market")) for item in today_focus}),
        "blocked_paths_visible": len(blocked_actions) >= 3,
        "return_evidence_request_visible": bool(return_requests),
        "api_blocker_visible": api_status in {
            "blocked_missing_real_api_artifacts",
            "blocked_missing_metadata",
        },
        "no_api_backed_claim_without_artifacts": api_status != "completed",
        "every_focus_item_simulation_only": all(item.get("simulation_only") is True for item in today_focus),
        "manual_external_execution_only": all(
            item.get("manual_external_execution_only") is True for item in today_focus
        ),
        "no_live_price": all("live_price" not in item for item in today_focus),
        "no_position_size": all("position_size" not in item for item in today_focus),
        "no_order_instruction": all("order_instruction" not in item for item in today_focus),
        "source_production_records_not_written": current_brief.get("production_records_written") is False
        and api_backed_brief.get("production_records_written") is False,
        "dashboard_contract_unchanged": current_brief.get("dashboard_contract_changed") is False
        and api_backed_brief.get("dashboard_contract_changed") is False,
        "network_not_used": current_brief.get("network_used") is False
        and api_backed_brief.get("network_used") is False,
    }

    return {
        "overall_status": "PASS" if all(checks.values()) else "FAIL",
        "acceptance_target": "V2.11-A Simulation Suggestion Action Packet",
        "packet_type": "simulation_suggestion_action_packet",
        "run_id": run_id,
        "generated_at": generated_at or _now_iso(),
        "command": command,
        "network_used": False,
        "production_records_written": False,
        "dashboard_contract_changed": False,
        "summary": {
            "today_focus_count": len(today_focus),
            "blocked_count": len(blocked_actions),
            "return_evidence_request_count": len(return_requests),
            "candidate_markets": current_summary.get("candidate_markets") or [],
            "top_candidate_symbols": [item.get("symbol") for item in today_focus],
            "real_user_api_status": current_summary.get("real_user_api_status"),
            "api_backed_brief_status": api_status,
            "sandbox_pass_count": current_summary.get("sandbox_pass_count"),
            "sandbox_fail_count": current_summary.get("sandbox_fail_count"),
        },
        "daily_answer": {
            "what_can_i_use_today": (
                "可以使用 today_focus 作为模拟观察和人工核对清单；它不是买卖指令，"
                "不包含实时价格、仓位或订单。"
            ),
            "what_must_not_be_used": (
                "do_not_use 列出的路径已经被历史沙盘或门控阻断，不能作为入场依据。"
            ),
            "what_to_return": (
                "如果你在外部软件手动观察、买入、卖出或放弃，请回传截图路径、价格/日期"
                "和文字原因；没有证据时保持 pending。"
            ),
            "api_status": (
                "真实 API-backed 候选仍未启用；当前使用的是已验收的 simulation/fixture-backed "
                "evidence，不冒充 live API data。"
            ),
        },
        "today_focus": today_focus,
        "do_not_use": blocked_actions,
        "return_evidence_requests": return_requests,
        "user_boundary": {
            "allowed": [
                "把 today_focus 当作模拟观察清单。",
                "在外部软件人工核对实时行情和公司事件。",
                "把外部手动决策、截图或文字说明回传给 Aegis。",
            ],
            "forbidden": [
                "Aegis 不真实交易。",
                "Aegis 不连接 Broker API。",
                "Aegis 不使用 trading webhook。",
                "Aegis 不生成订单、实时价格或仓位数量。",
                "Aegis 不把 fixture-backed 候选冒充为 API-backed 候选。",
            ],
        },
        "checks": checks,
        "safety": {
            "simulation_only": True,
            "manual_external_execution_only": True,
            "no_real_trade": True,
            "no_broker_api": True,
            "no_trading_webhook": True,
            "no_order_placement": True,
            "no_live_price": True,
            "no_position_size": True,
            "no_production_records_mutation": True,
            "no_strategy_mutation": True,
            "dashboard_contract_unchanged": True,
            "api_backed_candidates_not_claimed": api_status != "completed",
        },
    }


def render_simulation_action_packet_markdown(packet: Mapping[str, Any]) -> str:
    lines = [
        "# Project Aegis Simulation Action Packet",
        "",
        f"- status: `{packet.get('overall_status')}`",
        f"- target: `{packet.get('acceptance_target')}`",
        f"- today_focus_count: `{packet.get('summary', {}).get('today_focus_count')}`",
        f"- blocked_count: `{packet.get('summary', {}).get('blocked_count')}`",
        f"- api_backed_brief_status: `{packet.get('summary', {}).get('api_backed_brief_status')}`",
        "",
        "## Today Focus",
        "",
    ]
    for item in packet.get("today_focus", []):
        lines.extend(
            [
                f"### {item.get('priority')}. {item.get('symbol')} - {item.get('name') or ''}",
                "",
                f"- market: `{item.get('market')}`",
                f"- action_type: `{item.get('action_type')}`",
                f"- source_mode: `{item.get('source_mode')}`",
                f"- candidate_score: `{item.get('candidate_score')}`",
                f"- evidence_ref_count: `{item.get('evidence_ref_count')}`",
                "- user_steps:",
                *[f"  - {step}" for step in item.get("user_steps", [])],
                "",
            ]
        )

    lines.extend(["## Do Not Use", ""])
    for item in packet.get("do_not_use", []):
        lines.extend(
            [
                f"- `{item.get('symbol')}` ({item.get('market')}): "
                f"{', '.join(item.get('blocked_by') or []) or 'blocked'}",
            ]
        )

    lines.extend(["", "## Return Evidence Requests", ""])
    for item in packet.get("return_evidence_requests", []):
        lines.extend(
            [
                f"- paper_trade_id: `{item.get('paper_trade_id')}`",
                f"  outcome: `{item.get('current_outcome')}`",
                f"  no_return_fabrication: `{item.get('no_return_fabrication')}`",
            ]
        )

    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "- 只做模拟观察和证据整理。",
            "- 不做真实交易。",
            "- 不接 Broker API。",
            "- 不使用 trading webhook。",
            "- 不生成实时价格、仓位数量或订单。",
            "",
        ]
    )
    return "\n".join(lines)
