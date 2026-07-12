"""User-readable H/US simulation brief from gated suggestion drafts.

V2.12-F turns V2.12-E Suggestion Gate drafts into a concise brief the user can
read. It does not fetch new data, mutate production records, provide live
prices, size positions, connect to a broker, trigger webhooks, or place orders.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _metric_from_reasons(reasons: list[str], name: str) -> str | None:
    prefix = f"{name}="
    for reason in reasons:
        if reason.startswith(prefix):
            return reason[len(prefix) :]
    return None


def _warning_text(items: list[Mapping[str, Any]]) -> str:
    return "\n".join(
        warning
        for item in items
        for warning in item.get("risk_warnings", []) or []
    ).lower()


def _build_items(gate_report: Mapping[str, Any]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for suggestion in gate_report.get("suggestions", []) or []:
        reasons = [str(value) for value in suggestion.get("reasons", []) or []]
        warnings = [str(value) for value in suggestion.get("risk_warnings", []) or []]
        status = "simulation_candidate" if suggestion.get("action") != "blocked" else "blocked"
        items.append(
            {
                "item_id": f"brief_{suggestion.get('suggestion_id')}",
                "suggestion_id": suggestion.get("suggestion_id"),
                "strategy_id": suggestion.get("strategy_id"),
                "symbol": suggestion.get("symbol"),
                "market": suggestion.get("market"),
                "brief_status": status,
                "user_action": (
                    "加入模拟观察清单；如你感兴趣，只能在外部软件手动核对实时价格、事件和风险，"
                    "再决定是否做纸面记录。"
                    if status == "simulation_candidate"
                    else "不要作为当前模拟入场候选。"
                ),
                "plain_summary": (
                    f"{suggestion.get('symbol')} 是基于 V2.12-D/V2.12-E 证据生成的"
                    " H/US 模拟候选篮子。它可用于观察和纸面验证，但不是实盘买卖建议。"
                ),
                "sandbox_metrics": {
                    "sample_count": _metric_from_reasons(reasons, "sample_count"),
                    "win_rate": _metric_from_reasons(reasons, "win_rate"),
                    "average_return": _metric_from_reasons(reasons, "average_return"),
                    "max_drawdown": _metric_from_reasons(reasons, "max_drawdown"),
                    "historical_symbols": _metric_from_reasons(reasons, "historical_symbols"),
                },
                "why": reasons[:8],
                "risk_warnings": warnings[:10],
                "evidence_refs": list(suggestion.get("evidence_refs") or [])[:12],
                "blocked_by": list(suggestion.get("blocked_by") or [])[:8],
                "simulation_only": suggestion.get("simulation_only") is True,
                "user_must_execute_externally": suggestion.get("user_must_execute_externally") is True,
                "no_live_price": True,
                "no_position_size": True,
                "no_real_trade": True,
                "no_broker_api": True,
                "no_webhook": True,
                "no_order_placement": True,
            }
        )
    return items


def build_h_us_current_simulation_brief(
    gate_report: Mapping[str, Any],
    *,
    run_id: str,
    command: str | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    """Build the current H/US user-readable simulation brief."""

    items = _build_items(gate_report)
    candidates = [item for item in items if item["brief_status"] == "simulation_candidate"]
    blocked = [item for item in items if item["brief_status"] == "blocked"]
    candidate_markets = sorted({str(item.get("market")) for item in candidates if item.get("market")})
    warning_text = _warning_text(items)

    checks = {
        "source_is_v2_12_e": gate_report.get("acceptance_target")
        == "V2.12-E H-US Suggestion Gate Refresh From Sandbox Evidence",
        "source_report_pass": gate_report.get("overall_status") == "PASS",
        "source_allows_user_facing_simulation_brief": (
            gate_report.get("summary", {}) or {}
        ).get("user_facing_simulation_brief_allowed")
        is True,
        "has_h_us_simulation_candidates": {"H", "US"}.issubset(set(candidate_markets)),
        "candidate_count_matches_allowed_count": len(candidates)
        == int((gate_report.get("summary", {}) or {}).get("allowed_count") or 0),
        "has_user_readable_items": len(items) > 0,
        "every_item_has_evidence": all(bool(item.get("evidence_refs")) for item in items),
        "every_item_simulation_only": all(item["simulation_only"] is True for item in items),
        "manual_external_execution_only": all(item["user_must_execute_externally"] is True for item in items),
        "sample_size_warning_visible": "sample size" in warning_text or "sample_size_warning" in warning_text,
        "preliminary_only_warning_visible": "preliminary" in warning_text,
        "no_live_price": all(item["no_live_price"] is True for item in items),
        "no_position_size": all(item["no_position_size"] is True for item in items),
        "no_real_trade": all(item["no_real_trade"] is True for item in items),
        "no_broker_api": all(item["no_broker_api"] is True for item in items),
        "no_trading_webhook": all(item["no_webhook"] is True for item in items),
        "no_order_placement": all(item["no_order_placement"] is True for item in items),
        "production_records_not_written": gate_report.get("production_records_written") is False,
        "dashboard_contract_unchanged": gate_report.get("dashboard_contract_changed") is False,
        "network_not_used": gate_report.get("network_used") is False,
    }

    return {
        "overall_status": "PASS" if all(checks.values()) else "FAIL",
        "acceptance_target": "V2.12-F H-US Current Usable Simulation Brief Refresh",
        "source_acceptance_target": gate_report.get("acceptance_target"),
        "brief_type": "h_us_current_usable_simulation_brief",
        "run_id": run_id,
        "generated_at": generated_at or _now_iso(),
        "command": command,
        "network_used": False,
        "production_records_written": False,
        "dashboard_contract_changed": False,
        "summary": {
            "candidate_count": len(candidates),
            "blocked_count": len(blocked),
            "candidate_markets": candidate_markets,
            "candidate_symbols": [item.get("symbol") for item in candidates],
            "source_allowed_count": (gate_report.get("summary", {}) or {}).get("allowed_count"),
            "source_blocked_count": (gate_report.get("summary", {}) or {}).get("blocked_count"),
            "preliminary_only": True,
            "real_trade_allowed": False,
            "next_stage": "V2.12-G H-US User Feedback Intake For Simulation Brief",
        },
        "current_answer": {
            "can_read_online_now": (
                "EODHD/Twelve Data/Tushare 等用户 API 已有 secret-safe probe、metadata gate、"
                "bounded cache readiness 和沙盘证据链；本简报复用已验收证据，不重新联网。"
            ),
            "history_sandbox_status": (
                "H/US normalized cache samples 已进入历史沙盘；当前只证明小样本纸面验证通过，"
                "不能证明生产策略稳定有效。"
            ),
            "strategy_research_status": (
                "A/H/US 策略研究已具备 source catalog、sandbox、Suggestion Gate 和 H/US API-backed "
                "simulation draft 链路。"
            ),
            "usable_suggestions_status": (
                "当前可给出 H/US simulation-only 观察候选；用户必须在外部软件自行核对和手动执行，"
                "再把截图或文字反馈回传给 Aegis。"
            ),
        },
        "user_boundary": {
            "allowed": [
                "把候选加入模拟观察清单。",
                "在外部行情/券商软件手动核对实时价格、新闻事件、持仓冲突和个人风险预算。",
                "把截图、成交记录或文字判断回传给 Aegis，作为后续模拟复盘证据。",
            ],
            "forbidden": [
                "Aegis 不真实下单。",
                "Aegis 不连接 Broker API。",
                "Aegis 不使用 trading webhook。",
                "Aegis 不给实时价格。",
                "Aegis 不给仓位数量。",
                "Aegis 不把小样本 sandbox PASS 解释成正式策略通过。",
            ],
        },
        "items": items,
        "checks": checks,
        "safety": {
            "simulation_only": True,
            "manual_external_execution_only": True,
            "not_real_trade_advice": True,
            "preliminary_sample_only": True,
            "sample_size_warning_required": True,
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


def render_h_us_current_simulation_brief_markdown(brief: Mapping[str, Any]) -> str:
    lines = [
        "# Project Aegis H/US 当前模拟建议简报",
        "",
        f"- 状态：`{brief.get('overall_status')}`",
        f"- 阶段：`{brief.get('acceptance_target')}`",
        f"- 候选数量：`{brief.get('summary', {}).get('candidate_count')}`",
        f"- 覆盖市场：`{brief.get('summary', {}).get('candidate_markets')}`",
        f"- 真实交易允许：`{brief.get('summary', {}).get('real_trade_allowed')}`",
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
    lines.extend(["", "## H/US 模拟候选", ""])
    for item in brief.get("items", []):
        metrics = item.get("sandbox_metrics") or {}
        lines.extend(
            [
                f"### {item.get('symbol')}",
                "",
                f"- 市场：`{item.get('market')}`",
                f"- 状态：`{item.get('brief_status')}`",
                f"- 动作：{item.get('user_action')}",
                f"- 历史样本：`{metrics.get('historical_symbols')}`",
                f"- 样本数：`{metrics.get('sample_count')}`",
                f"- win_rate：`{metrics.get('win_rate')}`",
                f"- average_return：`{metrics.get('average_return')}`",
                f"- max_drawdown：`{metrics.get('max_drawdown')}`",
                f"- 说明：{item.get('plain_summary')}",
                f"- 证据数：`{len(item.get('evidence_refs') or [])}`",
                "",
            ]
        )
    lines.extend(
        [
            "## 边界",
            "",
            "- 仅模拟。",
            "- 不是实盘建议。",
            "- 不含实时价格。",
            "- 不含仓位数量。",
            "- 不接券商。",
            "- 不下单。",
            "",
        ]
    )
    return "\n".join(lines)
