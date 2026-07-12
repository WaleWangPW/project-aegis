"""User-readable Finnhub quote-context simulation brief.

V2.13-I consumes the V2.13-H simulation-only Suggestion Gate draft and renders a
brief the user can read. It does not fetch new data, mutate production records,
provide live prices, size positions, connect to brokers, trigger webhooks, or
place orders.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping

ACCEPTANCE_TARGET = "V2.13-I Finnhub Quote Current Simulation Brief"
SOURCE_ACCEPTANCE_TARGET = "V2.13-H Finnhub Quote Sandbox Evidence To Suggestion Gate Draft"


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
        symbol = suggestion.get("symbol")
        items.append(
            {
                "item_id": f"brief_{suggestion.get('suggestion_id')}",
                "suggestion_id": suggestion.get("suggestion_id"),
                "strategy_id": suggestion.get("strategy_id"),
                "symbol": symbol,
                "market": suggestion.get("market"),
                "brief_status": status,
                "user_action": (
                    "可加入模拟观察清单；如果你感兴趣，只能在外部软件手动核对实时价格、公告、新闻、"
                    "持仓冲突和个人风险预算，再决定是否记录一笔纸面模拟。"
                    if status == "simulation_candidate"
                    else "不要作为当前模拟候选使用。"
                ),
                "plain_summary": (
                    f"{symbol} 是 Finnhub quote-context 证据链经过历史沙盘和 Suggestion Gate 后形成的"
                    "模拟观察候选。它不是实盘买卖建议，也不包含实时价格或仓位。"
                ),
                "sandbox_metrics": {
                    "sample_count": _metric_from_reasons(reasons, "sample_count"),
                    "win_rate": _metric_from_reasons(reasons, "win_rate"),
                    "average_return": _metric_from_reasons(reasons, "average_return"),
                    "max_drawdown": _metric_from_reasons(reasons, "max_drawdown"),
                    "historical_symbols": _metric_from_reasons(reasons, "historical_symbols"),
                    "social_sentiment_status": _metric_from_reasons(reasons, "social_sentiment_status"),
                },
                "why": reasons[:10],
                "risk_warnings": warnings[:12],
                "evidence_refs": list(suggestion.get("evidence_refs") or [])[:12],
                "blocked_by": list(suggestion.get("blocked_by") or [])[:8],
                "simulation_only": suggestion.get("simulation_only") is True,
                "user_must_execute_externally": suggestion.get("user_must_execute_externally") is True,
                "quote_context_research_only": True,
                "social_sentiment_not_enabled": True,
                "no_live_price": True,
                "no_position_size": True,
                "no_real_trade": True,
                "no_broker_api": True,
                "no_webhook": True,
                "no_order_placement": True,
                "no_live_order_signal": True,
            }
        )
    return items


def build_finnhub_quote_current_simulation_brief(
    gate_report: Mapping[str, Any],
    *,
    run_id: str,
    command: str | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    """Build the current Finnhub quote-context user-readable simulation brief."""

    items = _build_items(gate_report)
    candidates = [item for item in items if item["brief_status"] == "simulation_candidate"]
    blocked = [item for item in items if item["brief_status"] == "blocked"]
    warning_text = _warning_text(items)
    source_summary = gate_report.get("summary") or {}
    candidate_symbols = [item.get("symbol") for item in candidates]

    checks = {
        "source_is_v2_13_h": gate_report.get("acceptance_target") == SOURCE_ACCEPTANCE_TARGET,
        "source_report_pass": gate_report.get("overall_status") == "PASS",
        "source_allows_user_facing_simulation_brief": source_summary.get("user_facing_simulation_brief_allowed")
        is True,
        "source_social_sentiment_still_blocked": source_summary.get("social_sentiment_status")
        == "blocked_plan_or_rate_limit",
        "source_has_allowed_draft": int(source_summary.get("allowed_count") or 0) >= 1,
        "candidate_count_matches_allowed_count": len(candidates) == int(source_summary.get("allowed_count") or 0),
        "blocked_count_matches_source": len(blocked) == int(source_summary.get("blocked_count") or 0),
        "has_user_readable_items": len(items) > 0,
        "has_aapl_candidate": "AAPL.US" in candidate_symbols,
        "every_item_has_evidence": all(bool(item.get("evidence_refs")) for item in items),
        "every_item_simulation_only": all(item["simulation_only"] is True for item in items),
        "manual_external_execution_only": all(item["user_must_execute_externally"] is True for item in items),
        "quote_context_research_only_visible": "quote context" in warning_text
        or "quote-context" in "\n".join(item.get("plain_summary", "") for item in items).lower(),
        "social_sentiment_blocked_visible": "social sentiment" in warning_text
        and all(item["sandbox_metrics"].get("social_sentiment_status") == "blocked_plan_or_rate_limit" for item in items),
        "no_live_price": all(item["no_live_price"] is True for item in items),
        "no_position_size": all(item["no_position_size"] is True for item in items),
        "no_real_trade": all(item["no_real_trade"] is True for item in items),
        "no_broker_api": all(item["no_broker_api"] is True for item in items),
        "no_trading_webhook": all(item["no_webhook"] is True for item in items),
        "no_order_placement": all(item["no_order_placement"] is True for item in items),
        "no_live_order_signal": all(item["no_live_order_signal"] is True for item in items),
        "production_records_not_written": gate_report.get("production_records_written") is False,
        "production_cache_not_mutated": gate_report.get("production_cache_mutated") is False,
        "production_provider_config_not_mutated": gate_report.get("production_provider_config_mutated") is False,
        "dashboard_contract_unchanged": gate_report.get("dashboard_contract_changed") is False,
        "network_not_used": gate_report.get("network_used") is False,
    }

    return {
        "overall_status": "PASS" if all(checks.values()) else "FAIL",
        "acceptance_target": ACCEPTANCE_TARGET,
        "source_acceptance_target": gate_report.get("acceptance_target"),
        "brief_type": "finnhub_quote_current_simulation_brief",
        "run_id": run_id,
        "generated_at": generated_at or _now_iso(),
        "command": command,
        "network_used": False,
        "production_records_written": False,
        "production_cache_mutated": False,
        "production_provider_config_mutated": False,
        "dashboard_contract_changed": False,
        "summary": {
            "candidate_count": len(candidates),
            "blocked_count": len(blocked),
            "candidate_symbols": candidate_symbols,
            "candidate_markets": sorted({str(item.get("market")) for item in candidates if item.get("market")}),
            "source_allowed_count": source_summary.get("allowed_count"),
            "source_blocked_count": source_summary.get("blocked_count"),
            "social_sentiment_status": source_summary.get("social_sentiment_status"),
            "quote_context_research_only": True,
            "real_trade_allowed": False,
            "next_stage": "V2.13-J Finnhub Quote User Feedback Intake",
        },
        "current_answer": {
            "can_read_online_now": (
                "Finnhub quote 已通过 secret-safe live probe 和 cache-readiness；本简报复用已验收的"
                " V2.13-H gate evidence，不重新联网。"
            ),
            "history_sandbox_status": (
                "AAPL.US quote-context candidate 已在 8 个 historical cases 上通过 sandbox，并经过 Suggestion Gate。"
            ),
            "strategy_research_status": (
                "该候选只证明 Finnhub quote-context 证据链可以进入模拟观察；social sentiment 仍 blocked，"
                "不能作为 Reddit/Twitter 情绪信号。"
            ),
            "usable_suggestions_status": (
                "当前可给出 1 条 AAPL.US simulation-only 观察候选；用户必须在外部软件自行核对并手动决策，"
                "再把截图或文字反馈回传给 Aegis。"
            ),
        },
        "user_boundary": {
            "allowed": [
                "把 AAPL.US 加入模拟观察清单。",
                "在外部行情或券商软件手动核对实时价格、公告、新闻事件、持仓冲突和个人风险预算。",
                "如果你手动做了模拟或真实外部动作，可把截图、价格、日期和文字判断回传给 Aegis 做复盘证据。",
            ],
            "forbidden": [
                "Aegis 不真实下单。",
                "Aegis 不连接 Broker API。",
                "Aegis 不使用 trading webhook。",
                "Aegis 不给实时价格。",
                "Aegis 不给仓位数量。",
                "Aegis 不使用 Finnhub social sentiment 作为信号。",
                "Aegis 不把小样本 sandbox PASS 解释成正式策略稳定通过。",
            ],
        },
        "items": items,
        "checks": checks,
        "safety": {
            "simulation_only": True,
            "manual_external_execution_only": True,
            "not_real_trade_advice": True,
            "quote_context_research_only": True,
            "social_sentiment_not_enabled": True,
            "no_live_price": True,
            "no_position_size": True,
            "no_real_trade": True,
            "no_broker_api": True,
            "no_trading_webhook": True,
            "no_order_placement": True,
            "no_live_order_signal": True,
            "no_production_records_mutation": True,
            "no_production_cache_mutation": True,
            "no_production_provider_config_mutation": True,
            "no_strategy_mutation": True,
            "dashboard_contract_unchanged": True,
        },
    }


def render_finnhub_quote_current_simulation_brief_markdown(brief: Mapping[str, Any]) -> str:
    lines = [
        "# Project Aegis Finnhub Quote 当前模拟建议简报",
        "",
        f"- 状态：`{brief.get('overall_status')}`",
        f"- 阶段：`{brief.get('acceptance_target')}`",
        f"- 候选数量：`{brief.get('summary', {}).get('candidate_count')}`",
        f"- 候选标的：`{brief.get('summary', {}).get('candidate_symbols')}`",
        f"- social_sentiment_status：`{brief.get('summary', {}).get('social_sentiment_status')}`",
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
    lines.extend(["", "## 模拟候选", ""])
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
                f"- social_sentiment_status：`{metrics.get('social_sentiment_status')}`",
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
            "- 不使用 Finnhub social sentiment。",
            "",
        ]
    )
    return "\n".join(lines)
