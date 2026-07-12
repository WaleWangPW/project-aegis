"""User-readable simulation brief for V2.14 refreshed candidates."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Mapping

ACCEPTANCE_TARGET = "V2.14-E Current Usable Simulation Suggestion Brief"
SOURCE_ACCEPTANCE_TARGET = "V2.14-D Refreshed Candidate Suggestion Gate"


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _metric_from_reasons(reasons: list[str], name: str) -> str | None:
    prefix = f"{name}="
    for reason in reasons:
        if reason.startswith(prefix):
            return reason[len(prefix) :]
    return None


def _brief_status(suggestion: Mapping[str, Any]) -> str:
    return "simulation_candidate" if suggestion.get("action") != "blocked" else "blocked"


def _blocked_reason_label(reason: str) -> str:
    labels = {
        "strategy_sandbox_not_passed": "历史沙盘未通过",
        "missing_evidence_refs": "缺少完整证据引用",
        "risk_veto_triggered": "风险引擎否决",
    }
    return labels.get(reason, reason)


def _build_item(suggestion: Mapping[str, Any]) -> dict[str, Any]:
    reasons = [str(value) for value in suggestion.get("reasons", []) or []]
    warnings = [str(value) for value in suggestion.get("risk_warnings", []) or []]
    blocked_by = [str(value) for value in suggestion.get("blocked_by", []) or []]
    status = _brief_status(suggestion)
    symbol = str(suggestion.get("symbol"))
    evidence_refs = list(suggestion.get("evidence_refs") or [])
    metric_summary = {
        "coverage_status": _metric_from_reasons(reasons, "coverage_status"),
        "sandbox_status": _metric_from_reasons(reasons, "sandbox_status"),
        "sample_count": _metric_from_reasons(reasons, "sample_count"),
        "win_rate": _metric_from_reasons(reasons, "win_rate"),
        "average_return": _metric_from_reasons(reasons, "average_return"),
        "max_drawdown": _metric_from_reasons(reasons, "max_drawdown"),
        "failed_reasons": _metric_from_reasons(reasons, "failed_reasons"),
    }
    allowed = status == "simulation_candidate"
    return {
        "item_id": f"brief_{suggestion.get('suggestion_id')}",
        "suggestion_id": suggestion.get("suggestion_id"),
        "strategy_id": suggestion.get("strategy_id"),
        "symbol": symbol,
        "market": suggestion.get("market"),
        "brief_status": status,
        "user_action": (
            "可加入模拟观察清单；如果你感兴趣，只能在外部软件手动核对实时价格、公告、新闻、"
            "持仓冲突和个人风险预算，再决定是否记录一笔纸面模拟。"
            if allowed
            else "不要作为当前模拟候选使用；等待补历史覆盖、重新沙盘或重新筛选。"
        ),
        "plain_summary": (
            f"{symbol} 是本轮 refreshed candidate 中唯一通过历史沙盘和 Suggestion Gate 的模拟候选。"
            "它不是实盘买卖建议，也不包含实时价格、仓位或订单。"
            if allowed
            else f"{symbol} 当前被阻断，原因是："
            + "、".join(_blocked_reason_label(reason) for reason in blocked_by)
            + "。"
        ),
        "sandbox_metrics": metric_summary,
        "why": reasons[:12],
        "risk_warnings": warnings[:12],
        "evidence_refs": evidence_refs[:16],
        "blocked_by": blocked_by,
        "blocked_reason_labels": [_blocked_reason_label(reason) for reason in blocked_by],
        "simulation_only": suggestion.get("simulation_only") is True,
        "user_must_execute_externally": suggestion.get("user_must_execute_externally") is True,
        "no_live_price": True,
        "no_position_size": True,
        "no_real_trade": True,
        "no_broker_api": True,
        "no_webhook": True,
        "no_order_placement": True,
        "no_live_order_signal": True,
    }


def build_refreshed_candidate_current_simulation_brief(
    gate_report: Mapping[str, Any],
    *,
    run_id: str,
    command: str | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    items = [_build_item(suggestion) for suggestion in gate_report.get("suggestions", []) or []]
    candidates = [item for item in items if item["brief_status"] == "simulation_candidate"]
    blocked = [item for item in items if item["brief_status"] == "blocked"]
    summary = gate_report.get("summary") or {}
    candidate_symbols = [str(item.get("symbol")) for item in candidates]
    blocked_symbols = sorted(str(item.get("symbol")) for item in blocked)
    warning_text = "\n".join(
        warning
        for item in items
        for warning in item.get("risk_warnings", []) or []
    ).lower()

    checks = {
        "source_is_v2_14_d": gate_report.get("acceptance_target") == SOURCE_ACCEPTANCE_TARGET,
        "source_report_pass": gate_report.get("overall_status") == "PASS",
        "source_has_allowed_draft": int(summary.get("allowed_count") or 0) >= 1,
        "source_has_blocked_drafts": int(summary.get("blocked_count") or 0) >= 1,
        "candidate_count_matches_allowed_count": len(candidates) == int(summary.get("allowed_count") or 0),
        "blocked_count_matches_source": len(blocked) == int(summary.get("blocked_count") or 0),
        "has_user_readable_items": len(items) > 0,
        "has_00700_candidate": "00700.HK" in candidate_symbols,
        "all_candidates_have_evidence": all(bool(item.get("evidence_refs")) for item in candidates),
        "blocked_symbols_visible": set(summary.get("blocked_symbols") or []) == set(blocked_symbols),
        "every_item_simulation_only": all(item["simulation_only"] is True for item in items),
        "manual_external_execution_only": all(item["user_must_execute_externally"] is True for item in items),
        "warning_blocks_live_price_and_position_size": "live price" in warning_text and "position size" in warning_text,
        "no_live_price": all(item["no_live_price"] is True for item in items),
        "no_position_size": all(item["no_position_size"] is True for item in items),
        "no_real_trade": all(item["no_real_trade"] is True for item in items),
        "no_broker_api": all(item["no_broker_api"] is True for item in items),
        "no_webhook": all(item["no_webhook"] is True for item in items),
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
        "brief_type": "refreshed_candidate_current_simulation_brief",
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
            "blocked_symbols": blocked_symbols,
            "candidate_markets": sorted({str(item.get("market")) for item in candidates if item.get("market")}),
            "source_allowed_count": summary.get("allowed_count"),
            "source_blocked_count": summary.get("blocked_count"),
            "simulation_suggestion_available": bool(candidates),
            "real_trade_allowed": False,
            "next_stage": "V2.14-F User Feedback Intake For Refreshed Simulation Brief",
        },
        "current_answer": {
            "online_reading_status": (
                "Aegis 已能通过批准 API 路线读取外部数据；本简报复用已验收的 V2.14-D evidence，"
                "不重新联网。"
            ),
            "historical_sandbox_status": (
                "V2.14-C 已对 refreshed A/H 候选做历史沙盘；只有 H 股低波股息策略通过，"
                "A 股防御策略未通过，缺覆盖标的继续阻断。"
            ),
            "strategy_research_status": (
                "当前建议来自已研究的低波/股息/防御类策略假设，并经过历史沙盘和 Suggestion Gate。"
            ),
            "usable_suggestion_status": (
                "当前可给出 1 条 simulation-only 观察候选：00700.HK。你必须在外部软件自行核对并手动决策，"
                "再把截图、价格、日期或文字判断回传给 Aegis 做复盘。"
            ),
        },
        "user_boundary": {
            "allowed": [
                "把 00700.HK 加入模拟观察清单。",
                "在外部行情或券商软件手动核对实时价格、公告、新闻事件、持仓冲突和个人风险预算。",
                "如果你手动做了模拟或真实外部动作，可把截图、价格、日期和文字判断回传给 Aegis 做复盘证据。",
            ],
            "forbidden": [
                "Aegis 不真实下单。",
                "Aegis 不连接 Broker API。",
                "Aegis 不使用 trading webhook。",
                "Aegis 不给实时价格。",
                "Aegis 不给仓位数量。",
                "Aegis 不把小样本 sandbox PASS 解释成正式策略稳定通过。",
            ],
        },
        "items": items,
        "source_evidence": {
            "source_target": gate_report.get("acceptance_target"),
            "source_run_id": gate_report.get("run_id"),
            "source_summary_sha256": _sha256_text(
                json.dumps(gate_report.get("summary") or {}, ensure_ascii=False, sort_keys=True)
            ),
        },
        "checks": checks,
        "safety": {
            "simulation_only": True,
            "manual_external_execution_only": True,
            "not_real_trade_advice": True,
            "no_live_price": True,
            "no_position_size": True,
            "no_real_trade": True,
            "no_broker_api": True,
            "no_webhook": True,
            "no_order_placement": True,
            "no_live_order_signal": True,
            "no_production_records_mutation": True,
            "no_production_cache_mutation": True,
            "no_production_provider_config_mutation": True,
            "no_strategy_mutation": True,
            "dashboard_contract_unchanged": True,
        },
    }


def render_refreshed_candidate_current_simulation_brief_markdown(brief: Mapping[str, Any]) -> str:
    lines = [
        "# Project Aegis 当前模拟建议简报",
        "",
        f"- 状态：`{brief.get('overall_status')}`",
        f"- 阶段：`{brief.get('acceptance_target')}`",
        f"- 候选数量：`{brief.get('summary', {}).get('candidate_count')}`",
        f"- 候选标的：`{brief.get('summary', {}).get('candidate_symbols')}`",
        f"- 阻断数量：`{brief.get('summary', {}).get('blocked_count')}`",
        f"- 阻断标的：`{brief.get('summary', {}).get('blocked_symbols')}`",
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
    for item in brief.get("items", []) or []:
        metrics = item.get("sandbox_metrics") or {}
        if item.get("brief_status") == "simulation_candidate":
            lines.extend(
                [
                    f"### {item.get('symbol')}",
                    "",
                    f"- 市场：`{item.get('market')}`",
                    f"- 状态：`{item.get('brief_status')}`",
                    f"- 动作：{item.get('user_action')}",
                    f"- 覆盖状态：`{metrics.get('coverage_status')}`",
                    f"- 沙盘状态：`{metrics.get('sandbox_status')}`",
                    f"- 样本数：`{metrics.get('sample_count')}`",
                    f"- win_rate：`{metrics.get('win_rate')}`",
                    f"- average_return：`{metrics.get('average_return')}`",
                    f"- max_drawdown：`{metrics.get('max_drawdown')}`",
                    f"- 说明：{item.get('plain_summary')}",
                    f"- 证据数：`{len(item.get('evidence_refs') or [])}`",
                    "",
                ]
            )
    lines.extend(["", "## 阻断标的", ""])
    for item in brief.get("items", []) or []:
        if item.get("brief_status") == "blocked":
            metrics = item.get("sandbox_metrics") or {}
            lines.extend(
                [
                    f"### {item.get('symbol')}",
                    "",
                    f"- 市场：`{item.get('market')}`",
                    f"- 阻断原因：`{item.get('blocked_reason_labels')}`",
                    f"- 覆盖状态：`{metrics.get('coverage_status')}`",
                    f"- 沙盘状态：`{metrics.get('sandbox_status')}`",
                    f"- 说明：{item.get('plain_summary')}",
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
