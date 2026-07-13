#!/usr/bin/env python3
"""Build a daily-use readiness report for the Aegis dashboard.

This report answers whether the current dashboard can be used for
simulation-only daily research. It never reads secrets, calls brokers, places
orders, or executes trading webhooks.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "data" / "reports"
OUT_JSON = REPORTS / "dashboard_daily_use_readiness_latest.json"
OUT_MD = REPORTS / "dashboard_daily_use_readiness_latest.md"


def now_local() -> datetime:
    return datetime.now().astimezone()


def read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def all_false(mapping: dict[str, Any], keys: list[str]) -> bool:
    return all(mapping.get(key) is False for key in keys)


def build_readiness(
    *,
    stock_selection: dict[str, Any] | None,
    intent_ingest: dict[str, Any] | None,
    ranking_gate: dict[str, Any] | None,
    retry_readiness: dict[str, Any] | None,
    health: dict[str, Any] | None,
    now: datetime,
) -> dict[str, Any]:
    selection_summary = (stock_selection or {}).get("summary", {})
    intent_safety = (intent_ingest or {}).get("safety", {})
    gate_summary = (ranking_gate or {}).get("summary", {})
    gate_safety = (ranking_gate or {}).get("safety", {})
    retry_safety = (retry_readiness or {}).get("safety", {})
    markets = selection_summary.get("markets_passed") or []

    checks = {
        "dashboard_health_normal": (health or {}).get("health_status") == "NORMAL",
        "candidate_pool_available": selection_summary.get("research_candidate_count", 0) > 0,
        "news_summary_available": selection_summary.get("news_enriched_count", 0) > 0,
        "multi_market_available": all(market in markets for market in ["A", "HK", "US"]),
        "button_feedback_recorded": (intent_ingest or {}).get("status") == "RECORDED",
        "button_feedback_has_no_trading_side_effects": all_false(
            intent_safety,
            [
                "recommendation_mutated",
                "paper_trade_created",
                "holding_mutated",
                "broker_called",
                "order_placed",
                "trading_webhook_called",
            ],
        ),
        "ranking_gate_blocks_unapproved_strategy": gate_summary.get("user_facing_suggestion_allowed") is False
        and gate_summary.get("ranking_gate_approved_count", 0) == 0,
        "ranking_gate_has_no_trading_side_effects": gate_safety.get("no_broker_api") is True
        and gate_safety.get("no_order_placement") is True
        and gate_safety.get("no_trading_webhook") is True,
        "a_share_retry_preflight_available": retry_readiness is not None
        and retry_readiness.get("status") in {"WAITING", "READY", "NOT_NEEDED"},
        "a_share_retry_preflight_safe": retry_safety.get("secret_values_read") is False
        and retry_safety.get("executes_retry") is False
        and retry_safety.get("no_broker_api") is True
        and retry_safety.get("no_order_placement") is True
        and retry_safety.get("no_trading_webhook") is True,
    }

    required = [
        "candidate_pool_available",
        "news_summary_available",
        "multi_market_available",
        "button_feedback_recorded",
        "button_feedback_has_no_trading_side_effects",
        "ranking_gate_blocks_unapproved_strategy",
        "ranking_gate_has_no_trading_side_effects",
        "a_share_retry_preflight_available",
        "a_share_retry_preflight_safe",
    ]
    blockers = [key for key in required if not checks[key]]
    status = "READY_FOR_SIMULATION_USE" if not blockers else "NOT_READY"
    if status == "READY_FOR_SIMULATION_USE" and not checks["dashboard_health_normal"]:
        status = "READY_WITH_GUARDS"

    return {
        "type": "dashboard_daily_use_readiness",
        "status": status,
        "generated_at": now.isoformat(timespec="seconds"),
        "usable_for": "simulation_research_only",
        "not_usable_for": ["real_trading", "broker_execution", "order_placement", "trading_webhook"],
        "summary": {
            "total_candidates": selection_summary.get("total_candidates"),
            "research_candidate_count": selection_summary.get("research_candidate_count"),
            "news_enriched_count": selection_summary.get("news_enriched_count"),
            "markets_passed": markets,
            "latest_feedback_symbol": (intent_ingest or {}).get("latest_symbol"),
            "latest_feedback_action": (intent_ingest or {}).get("latest_action"),
            "ranking_gate_approved_count": gate_summary.get("ranking_gate_approved_count", 0),
            "user_facing_suggestion_allowed": gate_summary.get("user_facing_suggestion_allowed"),
            "a_share_retry_status": (retry_readiness or {}).get("status"),
            "a_share_retry_ready_to_run": (retry_readiness or {}).get("ready_to_run"),
        },
        "checks": checks,
        "blockers": blockers,
        "next_actions": [
            "Use Dashboard Top 3 candidate cards for simulation research only.",
            "Use candidate buttons to record research intent; verify backend evidence after clicking.",
            "Do not let A-share strategy affect recommendations while ranking_gate_approved_count is 0.",
            "After 15:30 Asia/Shanghai rerun the A-share retry preflight before any retry chain.",
        ],
        "safety": {
            "simulation_only": True,
            "no_broker_api": True,
            "no_order_placement": True,
            "no_trading_webhook": True,
            "no_secret_values_read": True,
        },
    }


def render_markdown(report: dict[str, Any]) -> str:
    checks = report.get("checks", {})
    return "\n".join(
        [
            "# Dashboard Daily Use Readiness",
            "",
            f"- status: `{report['status']}`",
            f"- usable_for: `{report['usable_for']}`",
            f"- blockers: `{', '.join(report.get('blockers') or []) or 'none'}`",
            "",
            "## Summary",
            "",
            *[f"- {key}: `{value}`" for key, value in report.get("summary", {}).items()],
            "",
            "## Checks",
            "",
            *[f"- {key}: `{value}`" for key, value in checks.items()],
            "",
            "## Safety",
            "",
            "- Simulation-only.",
            "- No broker API, no order placement, no trading webhook, no secret values read.",
            "",
        ]
    )


def main() -> int:
    report = build_readiness(
        stock_selection=read_json(REPORTS / "stock_selection_workbench_latest.json"),
        intent_ingest=read_json(REPORTS / "aegis_dashboard_local_intent_ingest_latest.json"),
        ranking_gate=read_json(REPORTS / "a_share_refined_strategy_ranking_gate_latest.json"),
        retry_readiness=read_json(REPORTS / "a_share_current_day_retry_readiness_latest.json"),
        health=read_json(REPORTS / "aegis_health_status_latest.json"),
        now=now_local(),
    )
    OUT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    OUT_MD.write_text(render_markdown(report), encoding="utf-8")
    print(f"status={report['status']}")
    print(f"blockers={','.join(report['blockers']) or 'none'}")
    print(f"out_json={OUT_JSON}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
