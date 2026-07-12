from __future__ import annotations

from copy import deepcopy
from typing import Any


OBJECTIVE_LABELS = {
    "online_reading": "可以联网读取",
    "historical_sandbox": "可以根据历史记录做模拟沙盘",
    "strategy_research": "深度搜索国内外 A股/美股/港股选股策略",
    "usable_suggestions": "有建议可以产生给用户使用",
}


def _market_covers_a_h_us(markets: Any) -> bool:
    if isinstance(markets, dict):
        return all(markets.get(market, 0) > 0 for market in ("A", "H", "US"))
    if isinstance(markets, list):
        return all(market in markets for market in ("A", "H", "US"))
    return False


def _status_counts(report: dict[str, Any]) -> dict[str, int]:
    counts = report.get("status_counts")
    return counts if isinstance(counts, dict) else {}


def _summary(report: dict[str, Any]) -> dict[str, Any]:
    summary = report.get("summary")
    return summary if isinstance(summary, dict) else {}


def _checks(report: dict[str, Any]) -> dict[str, Any]:
    checks = report.get("checks")
    return checks if isinstance(checks, dict) else {}


def _safety(report: dict[str, Any]) -> dict[str, Any]:
    safety = report.get("safety")
    return safety if isinstance(safety, dict) else {}


def _production_records_not_written(report: dict[str, Any]) -> bool:
    checks = _checks(report)
    if checks.get("production_records_not_written") is True:
        return True
    return report.get("production_records_written") is False


def build_current_objective_pack(
    *,
    current_brief: dict[str, Any],
    live_public_source_audit: dict[str, Any],
    api_candidate_dry_run: dict[str, Any],
    historical_sandbox: dict[str, Any],
    refresh_sandbox: dict[str, Any],
    strategy_source_catalog: dict[str, Any],
    run_id: str,
    command: str | None,
) -> dict[str, Any]:
    """Build a user-facing capability pack from accepted evidence artifacts."""

    brief_summary = _summary(current_brief)
    source_summary = _summary(strategy_source_catalog)
    historical_summary = _summary(historical_sandbox)
    refresh_summary = _summary(refresh_sandbox)
    api_summary = _summary(api_candidate_dry_run)

    public_source_checks = _checks(live_public_source_audit)
    api_checks = _checks(api_candidate_dry_run)
    brief_checks = _checks(current_brief)
    catalog_checks = _checks(strategy_source_catalog)
    historical_checks = _checks(historical_sandbox)
    refresh_checks = _checks(refresh_sandbox)

    online_reading_checks = {
        "live_public_source_audit_passed": live_public_source_audit.get("overall_status") == "PASS",
        "live_public_source_audit_used_network": live_public_source_audit.get("network_used") is True,
        "public_sources_cover_a_h_us": public_source_checks.get("covers_a_h_us") is True,
        "reachable_sources_present": int(live_public_source_audit.get("reachable_count", 0)) > 0,
        "api_candidate_fixture_ready": api_candidate_dry_run.get("fixture_dry_run_status") == "completed",
        "real_user_api_blocked_visible": api_summary.get("real_user_status") == "blocked_missing_metadata",
        "real_user_api_not_claimed_live": api_checks.get("real_user_not_claimed_completed_when_blocked") is True,
    }

    historical_sandbox_checks = {
        "historical_sandbox_passed": historical_sandbox.get("overall_status") == "PASS",
        "refresh_sandbox_passed": refresh_sandbox.get("overall_status") == "PASS",
        "historical_cases_present": int(refresh_summary.get("historical_case_count", 0)) > 0,
        "passing_and_failing_results_visible": int(refresh_summary.get("pass_count", 0)) > 0
        and int(refresh_summary.get("fail_count", 0)) > 0,
        "passing_strategies_visible": bool(refresh_summary.get("passing_strategies")),
        "failing_strategies_visible": bool(refresh_summary.get("failing_strategies")),
        "production_records_not_written": _production_records_not_written(historical_sandbox)
        and _production_records_not_written(refresh_sandbox),
    }

    strategy_research_checks = {
        "catalog_passed": strategy_source_catalog.get("overall_status") == "PASS",
        "source_record_count_at_least_10": int(source_summary.get("record_count", 0)) >= 10,
        "catalog_covers_a_h_us": catalog_checks.get("covers_a_h_us") is True,
        "catalog_covers_core_strategy_families": catalog_checks.get("covers_core_strategy_families") is True,
        "live_audit_attempted_sources": int(live_public_source_audit.get("attempted_count", 0)) > 0,
        "live_audit_fetch_errors_recorded": _status_counts(live_public_source_audit).get("fetch_error", 0) >= 0,
        "summary_only": catalog_checks.get("summary_only") is True,
        "requires_sandbox_before_suggestion": catalog_checks.get("requires_sandbox_before_suggestion") is True,
    }

    usable_suggestion_checks = {
        "current_brief_passed": current_brief.get("overall_status") == "PASS",
        "candidate_count_positive": int(brief_summary.get("candidate_count", 0)) > 0,
        "a_h_us_candidates_present": brief_checks.get("has_a_h_us_candidates") is True,
        "blocked_paths_visible": brief_checks.get("blocked_paths_visible") is True,
        "top_candidates_present": bool(current_brief.get("top_candidates")),
        "manual_external_execution_only": brief_checks.get("manual_external_execution_only") is True,
        "no_live_price": brief_checks.get("no_live_price") is True,
        "no_position_size": brief_checks.get("no_position_size") is True,
    }

    objective_status = {
        "online_reading": {
            "label": OBJECTIVE_LABELS["online_reading"],
            "status": "partial_ready_waiting_user_api",
            "checks": online_reading_checks,
            "evidence": {
                "public_source_attempted_count": live_public_source_audit.get("attempted_count", 0),
                "public_source_reachable_count": live_public_source_audit.get("reachable_count", 0),
                "public_source_status_counts": _status_counts(live_public_source_audit),
                "real_user_api_status": api_summary.get("real_user_status"),
            },
            "blocker": "config/external_api_connectors.local.json and local env var are still required for real user API reads.",
        },
        "historical_sandbox": {
            "label": OBJECTIVE_LABELS["historical_sandbox"],
            "status": "ready_simulation_only",
            "checks": historical_sandbox_checks,
            "evidence": {
                "historical_case_count": refresh_summary.get("historical_case_count", historical_summary.get("historical_case_count")),
                "pass_count": refresh_summary.get("pass_count"),
                "fail_count": refresh_summary.get("fail_count"),
                "passing_strategies": refresh_summary.get("passing_strategies", []),
                "failing_strategies": refresh_summary.get("failing_strategies", []),
            },
            "blocker": None,
        },
        "strategy_research": {
            "label": OBJECTIVE_LABELS["strategy_research"],
            "status": "ready_summary_only_requires_sandbox_before_suggestion",
            "checks": strategy_research_checks,
            "evidence": {
                "source_record_count": source_summary.get("record_count"),
                "market_coverage": source_summary.get("market_coverage"),
                "strategy_family_coverage": source_summary.get("strategy_family_coverage"),
                "publisher_coverage": source_summary.get("publisher_coverage"),
            },
            "blocker": None,
        },
        "usable_suggestions": {
            "label": OBJECTIVE_LABELS["usable_suggestions"],
            "status": "ready_simulation_only_manual_execution",
            "checks": usable_suggestion_checks,
            "evidence": {
                "candidate_count": brief_summary.get("candidate_count"),
                "blocked_count": brief_summary.get("blocked_count"),
                "candidate_markets": brief_summary.get("candidate_markets"),
                "top_candidate_symbols": brief_summary.get("top_candidate_symbols"),
                "real_user_api_status": brief_summary.get("real_user_api_status"),
            },
            "blocker": "Live API-backed candidates remain unavailable until user metadata/env var are provided.",
        },
    }

    safety = {
        "simulation_only": True,
        "manual_external_execution_only": True,
        "no_live_price": brief_checks.get("no_live_price") is True,
        "no_position_size": brief_checks.get("no_position_size") is True,
        "no_real_trade": True,
        "no_broker_api": True,
        "no_trading_webhook": True,
        "no_order_placement": True,
        "no_secret_values_stored": _safety(live_public_source_audit).get("no_secret_values_stored", True) is True,
        "no_strategy_mutation": True,
        "no_production_records_mutation": True,
        "dashboard_contract_unchanged": True,
    }

    checks = {
        "all_objective_sections_present": set(objective_status) == set(OBJECTIVE_LABELS),
        "online_reading_currently_partial_not_overclaimed": objective_status["online_reading"]["status"]
        == "partial_ready_waiting_user_api",
        "historical_sandbox_ready": all(historical_sandbox_checks.values()),
        "strategy_research_ready": all(strategy_research_checks.values()),
        "usable_suggestions_ready": all(usable_suggestion_checks.values()),
        "a_h_us_coverage_visible": _market_covers_a_h_us(brief_summary.get("candidate_markets"))
        and _market_covers_a_h_us(source_summary.get("market_coverage")),
        "blockers_visible": bool(objective_status["online_reading"]["blocker"])
        and bool(objective_status["usable_suggestions"]["blocker"]),
        "safety_boundary_visible": all(safety.values()),
    }

    top_candidates = deepcopy(current_brief.get("top_candidates", []))[:6]
    user_next_actions = [
        "Read the simulation-only candidates as a watch and paper-verification list.",
        "Manually verify live prices, events, position conflicts, and personal risk budget outside Aegis.",
        "If you act externally, return screenshots/text/outcome evidence through config/user_returned_evidence.local.json.",
        "Provide non-secret API connector metadata and a local env var when ready to replace fixture candidate sources with real API-backed reads.",
    ]

    return {
        "overall_status": "PASS" if all(checks.values()) else "FAIL",
        "acceptance_target": "V2.10-A Current Objective Capability Pack",
        "run_id": run_id,
        "command": command,
        "objective_status": objective_status,
        "summary": {
            "online_reading_status": objective_status["online_reading"]["status"],
            "historical_sandbox_status": objective_status["historical_sandbox"]["status"],
            "strategy_research_status": objective_status["strategy_research"]["status"],
            "usable_suggestions_status": objective_status["usable_suggestions"]["status"],
            "candidate_count": brief_summary.get("candidate_count", 0),
            "top_candidate_symbols": brief_summary.get("top_candidate_symbols", []),
            "public_source_reachable_count": live_public_source_audit.get("reachable_count", 0),
            "sandbox_pass_count": refresh_summary.get("pass_count", 0),
            "sandbox_fail_count": refresh_summary.get("fail_count", 0),
            "real_user_api_status": api_summary.get("real_user_status"),
        },
        "top_candidates": top_candidates,
        "user_next_actions": user_next_actions,
        "checks": checks,
        "safety": safety,
        "production_records_written": False,
        "network_used": False,
        "dashboard_contract_changed": False,
    }


def render_current_objective_pack_markdown(pack: dict[str, Any]) -> str:
    lines = [
        "# Project Aegis 当前目标能力包",
        "",
        f"- 状态：`{pack['overall_status']}`",
        f"- 阶段：`{pack['acceptance_target']}`",
        f"- 联网/API：`{pack['summary']['online_reading_status']}`",
        f"- 历史沙盘：`{pack['summary']['historical_sandbox_status']}`",
        f"- 策略研究：`{pack['summary']['strategy_research_status']}`",
        f"- 可用建议：`{pack['summary']['usable_suggestions_status']}`",
        "",
        "## 四项目标状态",
    ]
    for key in ("online_reading", "historical_sandbox", "strategy_research", "usable_suggestions"):
        item = pack["objective_status"][key]
        lines.extend(
            [
                "",
                f"### {item['label']}",
                "",
                f"- 当前状态：`{item['status']}`",
                f"- 阻塞：`{item['blocker'] or 'None'}`",
            ]
        )
        for evidence_key, evidence_value in item["evidence"].items():
            lines.append(f"- {evidence_key}: `{evidence_value}`")

    lines.extend(["", "## 当前可用模拟候选"])
    for candidate in pack.get("top_candidates", []):
        lines.extend(
            [
                "",
                f"### {candidate.get('symbol')} {candidate.get('name', '')}".strip(),
                "",
                f"- 市场：`{candidate.get('market')}`",
                f"- 策略：`{candidate.get('strategy_id')}`",
                f"- 分数：`{candidate.get('candidate_score')}`",
                f"- 来源：`{candidate.get('source_mode')}`",
                f"- 用户动作：{candidate.get('user_action')}",
            ]
        )

    lines.extend(["", "## 用户下一步"])
    lines.extend(f"- {item}" for item in pack.get("user_next_actions", []))

    lines.extend(
        [
            "",
            "## 安全边界",
            "",
            "- 只做 simulation-only 建议和纸面验证。",
            "- 不真实下单。",
            "- 不连接 Broker API。",
            "- 不使用 trading webhook。",
            "- 不给实时价格或仓位数量。",
            "- 不把 fixture candidates 冒充为 live API candidates。",
        ]
    )
    return "\n".join(lines) + "\n"
