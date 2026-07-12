"""User-readable blocked-result brief for multi-symbol Finnhub quote sandbox."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Mapping

ACCEPTANCE_TARGET = "V2.13-W Finnhub Quote Multi-Symbol Sandbox Result Brief"
SOURCE_ACCEPTANCE_TARGET = "V2.13-V Finnhub Quote Multi-Symbol Sandbox Evaluation"

REASON_LABELS = {
    "win_rate_below_threshold": "历史胜率低于通过阈值",
    "average_return_below_threshold": "历史平均收益低于通过阈值",
    "max_drawdown_breached": "历史最大回撤超过允许底线",
    "sample_count_below_minimum": "历史样本数不足",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _symbol_for_strategy(source_report: Mapping[str, Any], strategy_id: str) -> str | None:
    for case in source_report.get("historical_cases", []) or []:
        if isinstance(case, dict) and case.get("strategy_id") == strategy_id:
            return str(case.get("symbol"))
    return None


def _brief_item(source_report: Mapping[str, Any], result: Mapping[str, Any]) -> dict[str, Any]:
    metrics = result.get("metrics") or {}
    failed_reasons = [str(value) for value in metrics.get("failed_reasons") or []]
    symbol = _symbol_for_strategy(source_report, str(result.get("strategy_id"))) or "UNKNOWN"
    return {
        "item_id": f"blocked_{str(result.get('strategy_id')).lower()}",
        "strategy_id": result.get("strategy_id"),
        "symbol": symbol,
        "market": "US",
        "brief_status": "blocked_by_sandbox",
        "user_action": "不要把这个候选作为当前模拟建议使用；等待重新筛选、重新设定策略或更多证据。",
        "plain_summary": (
            f"{symbol} 已完成联网 quote context、历史案例组装和 sandbox evaluation，但本轮沙盘没有通过。"
            "因此它不能进入 Suggestion Gate，也不能生成用户可执行建议。"
        ),
        "metrics": {
            "sample_count": metrics.get("sample_count"),
            "eligible_case_count": metrics.get("eligible_case_count"),
            "win_rate": metrics.get("win_rate"),
            "average_return": metrics.get("average_return"),
            "max_drawdown": metrics.get("max_drawdown"),
            "failed_reasons": failed_reasons,
            "failed_reason_labels": [REASON_LABELS.get(reason, reason) for reason in failed_reasons],
        },
        "evidence_summary": {
            "source_stage": SOURCE_ACCEPTANCE_TARGET,
            "historical_cases_used": metrics.get("sample_count"),
            "result_status": result.get("status"),
        },
        "next_allowed_actions": [
            "保留为 blocked evidence，供以后复盘。",
            "重新筛选候选池，而不是把失败候选包装成建议。",
            "如要继续研究，先调整策略假设并重新跑 historical sandbox。",
        ],
        "forbidden_actions": [
            "不得进入 Suggestion Gate。",
            "不得生成买入/卖出/持有建议。",
            "不得生成仓位数量。",
            "不得连接券商、webhook 或下单。",
        ],
        "simulation_only": True,
        "user_facing_suggestion_allowed": False,
        "no_live_price": True,
        "no_position_size": True,
        "no_real_trade": True,
        "no_broker_api": True,
        "no_webhook": True,
        "no_order_placement": True,
        "no_live_order_signal": True,
    }


def build_finnhub_quote_multi_symbol_result_brief(
    source_report: Mapping[str, Any],
    *,
    run_id: str,
    command: str | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    results = [item for item in source_report.get("results", []) or [] if isinstance(item, dict)]
    failed_results = [item for item in results if item.get("status") == "FAIL"]
    passed_results = [item for item in results if item.get("status") == "PASS"]
    items = [_brief_item(source_report, item) for item in failed_results]
    summary = source_report.get("summary") or {}
    blocked_symbols = sorted({str(item.get("symbol")) for item in items})
    all_reason_codes = sorted(
        {
            str(reason)
            for item in items
            for reason in (item.get("metrics", {}).get("failed_reasons") or [])
        }
    )
    checks = {
        "source_report_pass": source_report.get("overall_status") == "PASS",
        "source_acceptance_target_correct": source_report.get("acceptance_target") == SOURCE_ACCEPTANCE_TARGET,
        "source_sandbox_evaluation_run": summary.get("sandbox_evaluation_run") is True,
        "source_has_no_passed_strategies": int(summary.get("strategy_pass_count") or 0) == 0,
        "source_has_failed_strategies": int(summary.get("strategy_fail_count") or 0) > 0,
        "source_suggestion_gate_not_ready": summary.get("suggestion_gate_ready") is False,
        "source_user_facing_suggestion_not_allowed": summary.get("user_facing_suggestion_allowed") is False,
        "brief_items_match_failed_results": len(items) == len(failed_results) and bool(items),
        "all_items_blocked": all(item["brief_status"] == "blocked_by_sandbox" for item in items),
        "all_items_have_plain_summary": all(bool(item["plain_summary"]) for item in items),
        "all_items_have_failed_reasons": all(bool(item["metrics"]["failed_reasons"]) for item in items),
        "all_items_forbid_suggestion_gate": all("不得进入 Suggestion Gate。" in item["forbidden_actions"] for item in items),
        "no_passed_results_promoted": not passed_results,
        "network_not_used": source_report.get("network_used") is False,
        "production_records_not_written": source_report.get("production_records_written") is False,
        "production_cache_not_mutated": source_report.get("production_cache_mutated") is False,
        "production_provider_config_not_mutated": source_report.get("production_provider_config_mutated") is False,
        "dashboard_contract_unchanged": source_report.get("dashboard_contract_changed") is False,
        "no_live_price": all(item["no_live_price"] is True for item in items),
        "no_position_size": all(item["no_position_size"] is True for item in items),
        "no_real_trade": all(item["no_real_trade"] is True for item in items),
        "no_broker_api": all(item["no_broker_api"] is True for item in items),
        "no_webhook": all(item["no_webhook"] is True for item in items),
        "no_order_placement": all(item["no_order_placement"] is True for item in items),
        "no_live_order_signal": all(item["no_live_order_signal"] is True for item in items),
    }
    return {
        "overall_status": "PASS" if all(checks.values()) else "FAIL",
        "acceptance_target": ACCEPTANCE_TARGET,
        "source_acceptance_target": source_report.get("acceptance_target"),
        "brief_type": "multi_symbol_blocked_result_brief",
        "run_id": run_id,
        "generated_at": generated_at or _now_iso(),
        "command": command,
        "network_used": False,
        "production_records_written": False,
        "production_cache_mutated": False,
        "production_provider_config_mutated": False,
        "dashboard_contract_changed": False,
        "summary": {
            "blocked_item_count": len(items),
            "passed_item_count": len(passed_results),
            "blocked_symbols": blocked_symbols,
            "failed_reason_codes": all_reason_codes,
            "strategy_pass_count": summary.get("strategy_pass_count"),
            "strategy_fail_count": summary.get("strategy_fail_count"),
            "suggestion_gate_ready": False,
            "user_facing_suggestion_allowed": False,
            "real_trade_allowed": False,
            "next_stage": "Refresh candidate pool or continue V2.12-K Review/Memory Bridge",
        },
        "current_answer": {
            "online_reading_status": "Finnhub quote 和 EODHD historical bars 已完成联网读取并形成证据链。",
            "historical_sandbox_status": "本轮 3 个多股票候选已完成 81 个 historical cases 的 sandbox evaluation。",
            "usable_suggestion_status": "本轮没有可用建议：3 个候选全部未通过沙盘，不能进入 Suggestion Gate。",
            "strategy_research_status": "失败原因已结构化保存，可用于后续重新筛选或调整策略假设。",
        },
        "items": items,
        "source_evidence": {
            "source_target": source_report.get("acceptance_target"),
            "source_run_id": source_report.get("run_id"),
            "source_summary_sha256": _sha256_text(
                json.dumps(source_report.get("summary") or {}, ensure_ascii=False, sort_keys=True)
            ),
        },
        "checks": checks,
        "safety": {
            "blocked_result_brief_only": True,
            "not_a_suggestion": True,
            "suggestion_gate_not_ready": True,
            "simulation_only": True,
            "manual_external_execution_only": True,
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
            "dashboard_contract_unchanged": True,
        },
    }


def render_finnhub_quote_multi_symbol_result_brief_markdown(brief: Mapping[str, Any]) -> str:
    lines = [
        "# Project Aegis 多股票沙盘阻断简报",
        "",
        f"- 状态：`{brief.get('overall_status')}`",
        f"- 阶段：`{brief.get('acceptance_target')}`",
        f"- 阻断数量：`{brief.get('summary', {}).get('blocked_item_count')}`",
        f"- 通过数量：`{brief.get('summary', {}).get('passed_item_count')}`",
        f"- 阻断标的：`{brief.get('summary', {}).get('blocked_symbols')}`",
        f"- suggestion_gate_ready：`{brief.get('summary', {}).get('suggestion_gate_ready')}`",
        f"- user_facing_suggestion_allowed：`{brief.get('summary', {}).get('user_facing_suggestion_allowed')}`",
        "",
        "## 当前结论",
        "",
    ]
    for value in brief.get("current_answer", {}).values():
        lines.append(f"- {value}")
    lines.extend(["", "## 阻断明细", ""])
    for item in brief.get("items", []) or []:
        metrics = item.get("metrics") or {}
        lines.extend(
            [
                f"### {item.get('symbol')}",
                "",
                f"- 状态：`{item.get('brief_status')}`",
                f"- 动作：{item.get('user_action')}",
                f"- 样本数：`{metrics.get('sample_count')}`",
                f"- 胜率：`{metrics.get('win_rate')}`",
                f"- 平均收益：`{metrics.get('average_return')}`",
                f"- 最大回撤：`{metrics.get('max_drawdown')}`",
                f"- 失败原因：`{metrics.get('failed_reason_labels')}`",
                f"- 说明：{item.get('plain_summary')}",
                "",
            ]
        )
    lines.extend(
        [
            "## 边界",
            "",
            "- 这是阻断简报，不是建议。",
            "- 不进入 Suggestion Gate。",
            "- 不含实时价格。",
            "- 不含仓位数量。",
            "- 不接券商。",
            "- 不下单。",
            "",
        ]
    )
    return "\n".join(lines)
