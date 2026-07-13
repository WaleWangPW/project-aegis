#!/usr/bin/env python3
"""Dry-run smoke check for Dashboard intent ingestion.

This verifies the local Dashboard intent bridge can accept the same payload
shape produced by candidate-card buttons without mutating feedback evidence.
It is safe for daily startup: no market data fetch, no secrets, no broker, no
orders, and no trading webhooks.
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
RECORDS = ROOT / "data" / "records"
OUT_JSON = REPORTS / "dashboard_intent_bridge_dry_run_smoke_latest.json"
OUT_MD = REPORTS / "dashboard_intent_bridge_dry_run_smoke_latest.md"
DEFAULT_BASE_URL = "http://127.0.0.1:8080"
LATEST_FEEDBACK = REPORTS / "aegis_stock_feedback_latest.json"
EVENT_LOG = RECORDS / "aegis_stock_feedback_events.jsonl"


def now_local() -> datetime:
    return datetime.now().astimezone()


def file_fingerprint(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"exists": False, "size": 0, "mtime_ns": None}
    stat = path.stat()
    return {"exists": True, "size": stat.st_size, "mtime_ns": stat.st_mtime_ns}


def post_json(url: str, payload: dict[str, Any], *, timeout: float = 2.0) -> tuple[int | None, dict[str, Any] | None, str | None]:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            text = response.read().decode("utf-8")
            return response.status, json.loads(text), None
    except urllib.error.HTTPError as exc:
        return exc.code, None, str(exc)
    except (OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
        return None, None, str(exc)


def sample_payload(now: datetime) -> dict[str, Any]:
    return {
        "type": "aegis_dashboard_local_intents",
        "source": "dashboard-local-smoke",
        "intents": [
            {
                "symbol": "VRTX",
                "name": "Vertex Pharmaceuticals Incorporated",
                "market": "US",
                "status": "research_candidate",
                "score": 25,
                "action": "aegis_more_news",
                "time": now.isoformat(timespec="seconds"),
                "source": "dashboard-local",
            }
        ],
    }


def build_report(*, base_url: str = DEFAULT_BASE_URL, now: datetime | None = None) -> dict[str, Any]:
    generated_at = now or now_local()
    before_latest = file_fingerprint(LATEST_FEEDBACK)
    before_log = file_fingerprint(EVENT_LOG)
    status_code, response, error = post_json(
        f"{base_url}/api/dashboard-intents?dry_run=1",
        sample_payload(generated_at),
    )
    after_latest = file_fingerprint(LATEST_FEEDBACK)
    after_log = file_fingerprint(EVENT_LOG)
    safety = (response or {}).get("safety", {})
    checks = {
        "http_200": status_code == 200,
        "dry_run_status": (response or {}).get("status") == "DRY_RUN",
        "event_count_one": (response or {}).get("event_count") == 1,
        "latest_symbol_matches": (response or {}).get("latest_symbol") == "VRTX",
        "latest_action_matches": (response or {}).get("latest_action") == "aegis_more_news",
        "no_feedback_latest_mutation": before_latest == after_latest,
        "no_event_log_mutation": before_log == after_log,
        "no_trading_side_effects": safety.get("recommendation_mutated") is False
        and safety.get("paper_trade_created") is False
        and safety.get("holding_mutated") is False
        and safety.get("broker_called") is False
        and safety.get("order_placed") is False
        and safety.get("trading_webhook_called") is False,
    }
    blockers = [key for key, value in checks.items() if not value]
    return {
        "type": "dashboard_intent_bridge_dry_run_smoke",
        "status": "PASS" if not blockers else "FAIL",
        "generated_at": generated_at.isoformat(timespec="seconds"),
        "base_url": base_url,
        "status_code": status_code,
        "error": error,
        "checks": checks,
        "blockers": blockers,
        "response_summary": {
            "status": (response or {}).get("status"),
            "intent_count": (response or {}).get("intent_count"),
            "event_count": (response or {}).get("event_count"),
            "latest_symbol": (response or {}).get("latest_symbol"),
            "latest_action": (response or {}).get("latest_action"),
            "latest_feedback_type": (response or {}).get("latest_feedback_type"),
        },
        "mutation_guard": {
            "latest_feedback_before": before_latest,
            "latest_feedback_after": after_latest,
            "event_log_before": before_log,
            "event_log_after": after_log,
        },
        "safety": {
            "simulation_only": True,
            "dry_run": True,
            "market_data_fetch": False,
            "secret_values_read": False,
            "feedback_evidence_mutated": False,
            "no_broker_api": True,
            "no_order_placement": True,
            "no_trading_webhook": True,
        },
    }


def render_markdown(report: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# Dashboard Intent Bridge Dry-Run Smoke",
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
            "- Dry-run only; latest feedback and event log must not change.",
            "- No market data fetch, no secret values, no broker API, no order, no trading webhook.",
            "",
        ]
    )


def main() -> int:
    report = build_report()
    OUT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    OUT_MD.write_text(render_markdown(report), encoding="utf-8")
    print(f"status={report['status']}")
    print(f"blockers={','.join(report['blockers']) or 'none'}")
    print(f"out_json={OUT_JSON}")
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
