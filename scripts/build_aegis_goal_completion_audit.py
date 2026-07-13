#!/usr/bin/env python3
"""Build an evidence-backed audit for the current Project Aegis goal.

The audit is intentionally conservative: it can say the Dashboard is usable
for simulation-only daily research while still marking the A-share current-day
retry as pending until the 15:30 preflight becomes READY.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "data" / "reports"
OUT_JSON = REPORTS / "aegis_goal_completion_audit_latest.json"
OUT_MD = REPORTS / "aegis_goal_completion_audit_latest.md"


def now_local() -> datetime:
    return datetime.now().astimezone()


def read_json(name: str) -> dict[str, Any] | None:
    path = REPORTS / name
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def has_no_trading_side_effects(safety: dict[str, Any] | None) -> bool:
    safety = safety or {}
    broker = safety.get("no_broker_api") is True or safety.get("broker_called") is False
    order = safety.get("no_order_placement") is True or safety.get("order_placed") is False
    webhook = safety.get("no_trading_webhook") is True or safety.get("trading_webhook_called") is False
    return broker and order and webhook


def item(
    requirement: str,
    status: str,
    evidence: list[str],
    *,
    detail: dict[str, Any] | None = None,
    pending: str | None = None,
) -> dict[str, Any]:
    return {
        "requirement": requirement,
        "status": status,
        "evidence": evidence,
        "detail": detail or {},
        "pending": pending,
    }


def build_audit(
    *,
    dashboard_readiness: dict[str, Any] | None,
    dashboard_smoke: dict[str, Any] | None,
    real_click: dict[str, Any] | None,
    intent_dry_run: dict[str, Any] | None,
    stock_selection: dict[str, Any] | None,
    stock_agent_cycle: dict[str, Any] | None,
    ranking_gate: dict[str, Any] | None,
    retry_readiness: dict[str, Any] | None,
    now: datetime,
    retry_guard: dict[str, Any] | None = None,
) -> dict[str, Any]:
    selection_summary = (stock_selection or {}).get("summary", {})
    cycle_summary = (stock_agent_cycle or {}).get("summary", {})
    gate_summary = (ranking_gate or {}).get("summary", {})
    markets = selection_summary.get("markets_passed") or []

    retry_status = (retry_readiness or {}).get("status")
    retry_guard_status = (retry_guard or {}).get("status")
    retry_guard_failure = (retry_guard or {}).get("retry_failure") or {}
    if retry_status == "WAITING":
        retry_requirement_status = "PENDING"
        retry_pending = "Wait until the 15:30 Asia/Shanghai preflight returns READY before running make a-share-current-day-retry-guarded."
    elif retry_status == "NOT_NEEDED":
        retry_requirement_status = "ACHIEVED"
        retry_pending = None
    elif retry_status == "READY" and retry_guard_status == "PASS":
        retry_requirement_status = "ACHIEVED"
        retry_pending = None
    elif retry_status == "READY" and retry_guard_status == "FAIL":
        retry_requirement_status = "PENDING"
        retry_pending = "Guarded retry ran after READY but the retry chain failed; inspect a_share_current_day_retry_guarded_latest.json and retry later."
    elif retry_status == "READY":
        retry_requirement_status = "PENDING"
        retry_pending = "Preflight is READY; run make a-share-current-day-retry-guarded, not the raw retry chain."
    else:
        retry_requirement_status = "MISSING"
        retry_pending = None

    requirements = [
        item(
            "Dashboard daily-use check passes and homepage is usable for simulation research.",
            "ACHIEVED"
            if (dashboard_readiness or {}).get("status") == "READY_FOR_SIMULATION_USE"
            and (dashboard_smoke or {}).get("status") == "PASS"
            else "MISSING",
            [
                "data/reports/dashboard_daily_use_readiness_latest.json",
                "data/reports/dashboard_daily_use_smoke_latest.json",
            ],
            detail={
                "readiness_status": (dashboard_readiness or {}).get("status"),
                "smoke_status": (dashboard_smoke or {}).get("status"),
                "blockers": (dashboard_readiness or {}).get("blockers") or (dashboard_smoke or {}).get("blockers"),
            },
        ),
        item(
            "Dashboard candidate buttons can record user research intent to backend evidence.",
            "ACHIEVED"
            if (real_click or {}).get("status") == "ACCEPTED"
            and (intent_dry_run or {}).get("status") == "PASS"
            else "MISSING",
            [
                "data/reports/dashboard_real_click_acceptance_latest.json",
                "data/reports/dashboard_intent_bridge_dry_run_smoke_latest.json",
            ],
            detail={
                "real_click_status": (real_click or {}).get("status"),
                "latest_click": (real_click or {}).get("latest_click"),
                "dry_run_status": (intent_dry_run or {}).get("status"),
            },
        ),
        item(
            "A/H/US candidates and news summaries are available for simulation research.",
            "ACHIEVED"
            if selection_summary.get("research_candidate_count", 0) > 0
            and selection_summary.get("news_enriched_count", 0) > 0
            and all(market in markets for market in ["A", "HK", "US"])
            else "MISSING",
            ["data/reports/stock_selection_workbench_latest.json"],
            detail={
                "total_candidates": selection_summary.get("total_candidates"),
                "research_candidate_count": selection_summary.get("research_candidate_count"),
                "news_enriched_count": selection_summary.get("news_enriched_count"),
                "markets_passed": markets,
            },
        ),
        item(
            "A-share strategy work has been run through stock-agent and remains blocked from suggestions until Gate approves.",
            "ACHIEVED"
            if (stock_agent_cycle or {}).get("status") == "PASS"
            and cycle_summary.get("command_count", 0) >= 10
            and cycle_summary.get("failed_command_count", 1) == 0
            and (ranking_gate or {}).get("status") == "PASS"
            and gate_summary.get("ranking_gate_approved_count", 1) == 0
            and gate_summary.get("user_facing_suggestion_allowed") is False
            else "MISSING",
            [
                "data/reports/stock_agent_a_share_strategy_cycle_latest.json",
                "data/reports/a_share_refined_strategy_ranking_gate_latest.json",
            ],
            detail={
                "stock_agent_status": (stock_agent_cycle or {}).get("status"),
                "command_count": cycle_summary.get("command_count"),
                "failed_command_count": cycle_summary.get("failed_command_count"),
                "ranking_gate_approved_count": gate_summary.get("ranking_gate_approved_count"),
                "user_facing_suggestion_allowed": gate_summary.get("user_facing_suggestion_allowed"),
                "rankable_strategy_count": cycle_summary.get("rankable_strategy_count"),
            },
        ),
        item(
            "No real trading, broker API, order placement, trading webhook, or secret exposure is allowed by the checked reports.",
            "ACHIEVED"
            if all(
                [
                    has_no_trading_side_effects((dashboard_readiness or {}).get("safety")),
                    has_no_trading_side_effects((dashboard_smoke or {}).get("safety")),
                    has_no_trading_side_effects((real_click or {}).get("safety")),
                    has_no_trading_side_effects((ranking_gate or {}).get("safety")),
                    has_no_trading_side_effects((retry_readiness or {}).get("safety")),
                    ((dashboard_readiness or {}).get("safety") or {}).get("no_secret_values_read") is True,
                    ((dashboard_smoke or {}).get("safety") or {}).get("secret_values_read") is False,
                    ((retry_readiness or {}).get("safety") or {}).get("secret_values_read") is False,
                ]
            )
            else "MISSING",
            [
                "data/reports/dashboard_daily_use_readiness_latest.json",
                "data/reports/dashboard_daily_use_smoke_latest.json",
                "data/reports/dashboard_real_click_acceptance_latest.json",
                "data/reports/a_share_refined_strategy_ranking_gate_latest.json",
                "data/reports/a_share_current_day_retry_readiness_latest.json",
            ],
        ),
        item(
            "A-share current-day cache retry is only executed after the preflight becomes READY.",
            retry_requirement_status,
            [
                "data/reports/a_share_current_day_retry_readiness_latest.json",
                "data/reports/a_share_current_day_retry_guarded_latest.json",
            ],
            detail={
                "retry_status": retry_status,
                "ready_to_run": (retry_readiness or {}).get("ready_to_run"),
                "recommended_command": (retry_readiness or {}).get("recommended_command"),
                "guard_status": retry_guard_status,
                "guard_retry_exit_code": (retry_guard or {}).get("retry_exit_code"),
                "guard_audit_exit_code": (retry_guard or {}).get("audit_exit_code"),
                "guard_failed_dates": retry_guard_failure.get("failed_dates"),
            },
            pending=retry_pending,
        ),
    ]

    missing = [row["requirement"] for row in requirements if row["status"] == "MISSING"]
    pending = [row for row in requirements if row["status"] == "PENDING"]
    status = "READY_FOR_DAILY_SIMULATION_USE"
    if missing:
        status = "NOT_READY"
    elif pending:
        status = "READY_FOR_DAILY_USE_WITH_PENDING_A_SHARE_RETRY"

    return {
        "type": "aegis_goal_completion_audit",
        "status": status,
        "generated_at": now.isoformat(timespec="seconds"),
        "objective_scope": "daily_simulation_use_dashboard_and_stock_agent_gate",
        "requirements": requirements,
        "missing_count": len(missing),
        "pending_count": len(pending),
        "next_actions": [
            "Use Dashboard for simulation research only.",
            "Run make a-share-current-day-retry-guarded for the A-share current-day retry; do not run the raw retry chain directly.",
            "If the guarded retry fails because today's Tushare daily rows are still unavailable, retry later without relaxing the Gate.",
            "Do not allow A-share strategy into user-facing suggestions while ranking_gate_approved_count is 0.",
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
    lines = [
        "# Aegis Goal Completion Audit",
        "",
        f"- status: `{report['status']}`",
        f"- missing_count: `{report['missing_count']}`",
        f"- pending_count: `{report['pending_count']}`",
        "",
        "## Requirements",
        "",
    ]
    for idx, row in enumerate(report["requirements"], start=1):
        lines.append(f"{idx}. `{row['status']}` {row['requirement']}")
        if row.get("pending"):
            lines.append(f"   - pending: {row['pending']}")
        lines.append(f"   - evidence: {', '.join(row['evidence'])}")
    lines.extend(
        [
            "",
            "## Safety",
            "",
            "- Simulation-only.",
            "- No broker API, no order placement, no trading webhook, no secret values read.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    report = build_audit(
        dashboard_readiness=read_json("dashboard_daily_use_readiness_latest.json"),
        dashboard_smoke=read_json("dashboard_daily_use_smoke_latest.json"),
        real_click=read_json("dashboard_real_click_acceptance_latest.json"),
        intent_dry_run=read_json("dashboard_intent_bridge_dry_run_smoke_latest.json"),
        stock_selection=read_json("stock_selection_workbench_latest.json"),
        stock_agent_cycle=read_json("stock_agent_a_share_strategy_cycle_latest.json"),
        ranking_gate=read_json("a_share_refined_strategy_ranking_gate_latest.json"),
        retry_readiness=read_json("a_share_current_day_retry_readiness_latest.json"),
        retry_guard=read_json("a_share_current_day_retry_guarded_latest.json"),
        now=now_local(),
    )
    OUT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    OUT_MD.write_text(render_markdown(report), encoding="utf-8")
    print(f"status={report['status']}")
    print(f"missing_count={report['missing_count']}")
    print(f"pending_count={report['pending_count']}")
    print(f"out_json={OUT_JSON}")
    return 0 if report["missing_count"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
