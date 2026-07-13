#!/usr/bin/env python3
"""Low-cost daily smoke check for the local Aegis dashboard.

The smoke check verifies that the local dashboard bridge is reachable and that
the current reports support simulation-only daily use. It does not read
secrets, fetch market data, call brokers, place orders, or invoke webhooks.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "data" / "reports"
OUT_JSON = REPORTS / "dashboard_daily_use_smoke_latest.json"
OUT_MD = REPORTS / "dashboard_daily_use_smoke_latest.md"
DEFAULT_BASE_URL = "http://127.0.0.1:8080"


def now_local() -> datetime:
    return datetime.now().astimezone()


def read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def fetch_json(url: str, *, timeout: float = 2.0) -> dict[str, Any] | None:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            if response.status != 200:
                return None
            return json.loads(response.read().decode("utf-8"))
    except (OSError, urllib.error.URLError, json.JSONDecodeError):
        return None


def fetch_text(url: str, *, timeout: float = 2.0) -> str | None:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            if response.status != 200:
                return None
            return response.read().decode("utf-8", errors="replace")
    except (OSError, urllib.error.URLError):
        return None


def build_smoke(
    *,
    health_response: dict[str, Any] | None,
    dashboard_html: str | None,
    daily_use_readiness: dict[str, Any] | None,
    intent_ingest: dict[str, Any] | None,
    real_click_acceptance: dict[str, Any] | None,
    ranking_gate: dict[str, Any] | None,
    retry_readiness: dict[str, Any] | None,
    now: datetime,
    base_url: str = DEFAULT_BASE_URL,
) -> dict[str, Any]:
    health_safety = (health_response or {}).get("safety", {})
    daily_safety = (daily_use_readiness or {}).get("safety", {})
    intent_safety = (intent_ingest or {}).get("safety", {})
    real_click_safety = (real_click_acceptance or {}).get("safety", {})
    gate_summary = (ranking_gate or {}).get("summary", {})
    retry_safety = (retry_readiness or {}).get("safety", {})

    checks = {
        "bridge_health_ready": (health_response or {}).get("status") == "READY",
        "bridge_safety_no_trading": health_safety.get("simulation_only") is True
        and health_safety.get("no_broker_api") is True
        and health_safety.get("no_order_placement") is True
        and health_safety.get("no_trading_webhook") is True,
        "dashboard_html_available": bool(dashboard_html) and "Project Aegis" in dashboard_html,
        "daily_readiness_ready": (daily_use_readiness or {}).get("status") in {
            "READY_FOR_SIMULATION_USE",
            "READY_WITH_GUARDS",
        },
        "daily_readiness_safety": daily_safety.get("simulation_only") is True
        and daily_safety.get("no_broker_api") is True
        and daily_safety.get("no_order_placement") is True
        and daily_safety.get("no_trading_webhook") is True,
        "button_feedback_recorded": (intent_ingest or {}).get("status") == "RECORDED",
        "button_feedback_no_trading_side_effects": intent_safety.get("recommendation_mutated") is False
        and intent_safety.get("paper_trade_created") is False
        and intent_safety.get("holding_mutated") is False
        and intent_safety.get("broker_called") is False
        and intent_safety.get("order_placed") is False
        and intent_safety.get("trading_webhook_called") is False,
        "real_dashboard_click_accepted": (real_click_acceptance or {}).get("status") == "ACCEPTED",
        "real_dashboard_click_safe": real_click_safety.get("feedback_evidence_only") is True
        and real_click_safety.get("no_broker_api") is True
        and real_click_safety.get("no_order_placement") is True
        and real_click_safety.get("no_trading_webhook") is True,
        "ranking_gate_blocks_suggestions": gate_summary.get("ranking_gate_approved_count", 0) == 0
        and gate_summary.get("user_facing_suggestion_allowed") is False,
        "retry_preflight_safe": retry_safety.get("secret_values_read") is False
        and retry_safety.get("executes_retry") is False
        and retry_safety.get("no_broker_api") is True
        and retry_safety.get("no_order_placement") is True
        and retry_safety.get("no_trading_webhook") is True,
    }
    blockers = [key for key, value in checks.items() if not value]
    return {
        "type": "dashboard_daily_use_smoke",
        "status": "PASS" if not blockers else "FAIL",
        "generated_at": now.isoformat(timespec="seconds"),
        "base_url": base_url,
        "checks": checks,
        "blockers": blockers,
        "summary": {
            "daily_use_status": (daily_use_readiness or {}).get("status"),
            "latest_feedback_symbol": (intent_ingest or {}).get("latest_symbol"),
            "latest_feedback_action": (intent_ingest or {}).get("latest_action"),
            "real_click_acceptance_status": (real_click_acceptance or {}).get("status"),
            "ranking_gate_approved_count": gate_summary.get("ranking_gate_approved_count", 0),
            "a_share_retry_status": (retry_readiness or {}).get("status"),
            "a_share_retry_ready_to_run": (retry_readiness or {}).get("ready_to_run"),
        },
        "safety": {
            "simulation_only": True,
            "network_scope": "local_dashboard_only",
            "market_data_fetch": False,
            "secret_values_read": False,
            "no_broker_api": True,
            "no_order_placement": True,
            "no_trading_webhook": True,
        },
    }


def render_markdown(report: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# Dashboard Daily Use Smoke",
            "",
            f"- status: `{report['status']}`",
            f"- base_url: `{report['base_url']}`",
            f"- blockers: `{', '.join(report.get('blockers') or []) or 'none'}`",
            "",
            "## Checks",
            "",
            *[f"- {key}: `{value}`" for key, value in report.get("checks", {}).items()],
            "",
            "## Safety",
            "",
            "- Local dashboard only.",
            "- No market data fetch, no secret values, no broker API, no order, no trading webhook.",
            "",
        ]
    )


def main() -> int:
    base_url = DEFAULT_BASE_URL
    report = build_smoke(
        health_response=fetch_json(f"{base_url}/api/dashboard-intents/health"),
        dashboard_html=fetch_text(f"{base_url}/dashboard/index.html"),
        daily_use_readiness=read_json(REPORTS / "dashboard_daily_use_readiness_latest.json"),
        intent_ingest=read_json(REPORTS / "aegis_dashboard_local_intent_ingest_latest.json"),
        real_click_acceptance=read_json(REPORTS / "dashboard_real_click_acceptance_latest.json"),
        ranking_gate=read_json(REPORTS / "a_share_refined_strategy_ranking_gate_latest.json"),
        retry_readiness=read_json(REPORTS / "a_share_current_day_retry_readiness_latest.json"),
        now=now_local(),
        base_url=base_url,
    )
    OUT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    OUT_MD.write_text(render_markdown(report), encoding="utf-8")
    print(f"status={report['status']}")
    print(f"blockers={','.join(report['blockers']) or 'none'}")
    print(f"out_json={OUT_JSON}")
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
