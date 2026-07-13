#!/usr/bin/env python3
"""Record Feishu card button feedback from the OpenClaw stock assistant.

Input is the Feishu card `value` object, either as a JSON argument or a file.
The handler appends evidence-only records; it never mutates recommendations,
paper trades, holdings, broker state, or orders.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[1]
RECORDS = REPO / "data" / "records"
REPORTS = REPO / "data" / "reports"
EVENT_LOG = RECORDS / "aegis_stock_feedback_events.jsonl"
LATEST = REPORTS / "aegis_stock_feedback_latest.json"

ALLOWED_ACTIONS = {
    "aegis_watch": "user_wants_simulation_watch",
    "aegis_ignore": "user_ignored_candidate",
    "aegis_more_news": "user_requests_more_news",
    "aegis_manual_external": "user_reports_external_manual_action_intent",
}

SOURCE_LABELS = {
    "dashboard-local": "dashboard_local_intent_export",
    "dashboard_local_intent_export": "dashboard_local_intent_export",
    "openclaw_stock_assistant_feishu_card": "openclaw_stock_assistant_feishu_card",
}

SECRET_PATTERNS = [
    re.compile(r"(?i)(api[_-]?key|secret|token|password|cookie|bearer)\s*[:=]"),
    re.compile(r"(?i)xox[baprs]-[a-z0-9-]+"),
]


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _load_value(args: argparse.Namespace) -> dict[str, Any]:
    if args.file:
        raw = Path(args.file).read_text(encoding="utf-8")
    else:
        raw = args.value or "{}"
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("card value must be a JSON object")
    return data


def _reject_secret_like(data: dict[str, Any]) -> None:
    text = json.dumps(data, ensure_ascii=False)
    for pattern in SECRET_PATTERNS:
        if pattern.search(text):
            raise ValueError("secret-like content is not allowed in feedback")


def build_event(value: dict[str, Any]) -> dict[str, Any]:
    _reject_secret_like(value)
    action = str(value.get("action") or "")
    if action not in ALLOWED_ACTIONS:
        raise ValueError(f"unsupported action: {action}")
    source = SOURCE_LABELS.get(str(value.get("source") or ""), "openclaw_stock_assistant_feishu_card")
    event = {
        "event_id": "aegis_stock_feedback_" + dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"),
        "received_at": dt.datetime.now(dt.timezone.utc).astimezone().isoformat(),
        "source": source,
        "action": action,
        "feedback_type": ALLOWED_ACTIONS[action],
        "symbol": value.get("symbol"),
        "name": value.get("name"),
        "market": value.get("market"),
        "status": value.get("status"),
        "score": value.get("score"),
        "dashboard_recorded_at": value.get("dashboard_recorded_at") or value.get("time"),
        "raw_value_sha256": _sha256_text(json.dumps(value, ensure_ascii=False, sort_keys=True)),
        "record_mode": "feedback_evidence_only",
        "effects": {
            "recommendation_mutated": False,
            "paper_trade_created": False,
            "holding_mutated": False,
            "broker_called": False,
            "order_placed": False,
            "trading_webhook_called": False,
        },
    }
    return event


def append_event(event: dict[str, Any]) -> None:
    RECORDS.mkdir(parents=True, exist_ok=True)
    REPORTS.mkdir(parents=True, exist_ok=True)
    with EVENT_LOG.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
    latest = {
        "type": "aegis_stock_feedback_latest",
        "status": "RECORDED",
        "event": event,
        "event_log": str(EVENT_LOG),
        "safety": event["effects"],
    }
    LATEST.write_text(json.dumps(latest, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("value", nargs="?", help="Feishu card value JSON")
    parser.add_argument("--file", help="Read Feishu card value JSON from file")
    args = parser.parse_args()
    event = build_event(_load_value(args))
    append_event(event)
    print(f"status=RECORDED")
    print(f"event_id={event['event_id']}")
    print(f"action={event['action']}")
    print(f"event_log={EVENT_LOG}")
    print("effects=no_recommendation,no_paper_trade,no_holding,no_broker,no_order")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
