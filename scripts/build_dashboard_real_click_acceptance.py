#!/usr/bin/env python3
"""Build acceptance evidence for a real Dashboard candidate-button click.

This is stricter than the dry-run smoke check: it verifies the latest persisted
feedback evidence was produced by the Dashboard local intent bridge, and that
the persisted event did not mutate recommendations, paper trades, holdings,
broker state, orders, or trading webhooks.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "data" / "reports"
OUT_JSON = REPORTS / "dashboard_real_click_acceptance_latest.json"
OUT_MD = REPORTS / "dashboard_real_click_acceptance_latest.md"
INTENT_REPORT = REPORTS / "aegis_dashboard_local_intent_ingest_latest.json"
FEEDBACK_REPORT = REPORTS / "aegis_stock_feedback_latest.json"
MAX_ACCEPTED_AGE_HOURS = 36
SIDE_EFFECT_KEYS = [
    "recommendation_mutated",
    "paper_trade_created",
    "holding_mutated",
    "broker_called",
    "order_placed",
    "trading_webhook_called",
]


def now_local() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc).astimezone()


def read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str | None:
    if not path.exists():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_time(value: str | None) -> dt.datetime | None:
    if not value:
        return None
    try:
        parsed = dt.datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    return parsed.astimezone()


def event_digest(event: dict[str, Any] | None) -> str | None:
    if not event:
        return None
    keys = ["event_id", "source", "action", "symbol", "raw_value_sha256"]
    payload = {key: event.get(key) for key in keys}
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()


def build_acceptance(
    *,
    intent_report: dict[str, Any] | None,
    feedback_report: dict[str, Any] | None,
    now: dt.datetime,
) -> dict[str, Any]:
    intent_event = (intent_report or {}).get("latest_event")
    feedback_event = (feedback_report or {}).get("event")
    event = feedback_event or intent_event
    effects = (event or {}).get("effects") or (feedback_report or {}).get("safety") or {}
    received_at = parse_time((event or {}).get("received_at"))
    age_hours = (now - received_at).total_seconds() / 3600 if received_at else None
    intent_hash = event_digest(intent_event)
    feedback_hash = event_digest(feedback_event)

    checks = {
        "intent_report_recorded": (intent_report or {}).get("status") == "RECORDED",
        "feedback_report_recorded": (feedback_report or {}).get("status") == "RECORDED",
        "source_is_dashboard_local": (event or {}).get("source") == "dashboard_local_intent_export",
        "event_has_symbol_and_action": bool((event or {}).get("symbol")) and bool((event or {}).get("action")),
        "intent_and_feedback_match": bool(intent_hash) and intent_hash == feedback_hash,
        "event_is_recent": age_hours is not None and 0 <= age_hours <= MAX_ACCEPTED_AGE_HOURS,
        "feedback_evidence_only": (event or {}).get("record_mode") == "feedback_evidence_only",
        "no_trading_side_effects": all(effects.get(key) is False for key in SIDE_EFFECT_KEYS),
    }
    blockers = [key for key, value in checks.items() if not value]
    status = "ACCEPTED" if not blockers else "WAITING_FOR_USER_CLICK"
    return {
        "type": "dashboard_real_click_acceptance",
        "status": status,
        "generated_at": now.isoformat(timespec="seconds"),
        "checks": checks,
        "blockers": blockers,
        "latest_click": {
            "symbol": (event or {}).get("symbol"),
            "action": (event or {}).get("action"),
            "feedback_type": (event or {}).get("feedback_type"),
            "source": (event or {}).get("source"),
            "received_at": (event or {}).get("received_at"),
            "age_hours": round(age_hours, 3) if age_hours is not None else None,
            "dashboard_recorded_at": (event or {}).get("dashboard_recorded_at"),
        },
        "evidence": {
            "intent_report": str(INTENT_REPORT),
            "intent_report_sha256": sha256_file(INTENT_REPORT),
            "feedback_report": str(FEEDBACK_REPORT),
            "feedback_report_sha256": sha256_file(FEEDBACK_REPORT),
        },
        "safety": {
            "simulation_only": True,
            "feedback_evidence_only": True,
            "no_broker_api": True,
            "no_order_placement": True,
            "no_trading_webhook": True,
            "no_secret_values_read": True,
        },
    }


def render_markdown(report: dict[str, Any]) -> str:
    click = report.get("latest_click", {})
    return "\n".join(
        [
            "# Dashboard Real Click Acceptance",
            "",
            f"- status: `{report['status']}`",
            f"- blockers: `{', '.join(report.get('blockers') or []) or 'none'}`",
            f"- latest_click: `{click.get('symbol') or 'N/A'} / {click.get('action') or 'N/A'}`",
            f"- received_at: `{click.get('received_at') or 'N/A'}`",
            "",
            "## Checks",
            "",
            *[f"- {key}: `{value}`" for key, value in report.get("checks", {}).items()],
            "",
            "## Safety",
            "",
            "- Feedback evidence only.",
            "- No recommendation mutation, no paper trade, no holding mutation, no broker, no order, no trading webhook.",
            "",
        ]
    )


def main() -> int:
    report = build_acceptance(
        intent_report=read_json(INTENT_REPORT),
        feedback_report=read_json(FEEDBACK_REPORT),
        now=now_local(),
    )
    OUT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    OUT_MD.write_text(render_markdown(report), encoding="utf-8")
    print(f"status={report['status']}")
    print(f"blockers={','.join(report['blockers']) or 'none'}")
    print(f"out_json={OUT_JSON}")
    return 0 if report["status"] == "ACCEPTED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
