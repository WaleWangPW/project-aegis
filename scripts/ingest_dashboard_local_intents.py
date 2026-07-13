#!/usr/bin/env python3
"""Ingest Dashboard-local research intents into Aegis feedback evidence.

The Dashboard is a static page, so it cannot safely write repository files by
itself. This bridge consumes the machine-readable JSON copied/exported from the
Dashboard, validates it, and reuses the stock feedback handler. It only writes
feedback evidence; it never creates trades, mutates holdings, calls brokers, or
uses trading webhooks.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
from typing import Any

try:
    from scripts import handle_aegis_stock_card_action as feedback_handler
except ModuleNotFoundError:  # pragma: no cover - direct CLI execution path
    import handle_aegis_stock_card_action as feedback_handler


REPO = Path(__file__).resolve().parents[1]
REPORTS = REPO / "data" / "reports"
OUT = REPORTS / "aegis_dashboard_local_intent_ingest_latest.json"
MAX_INTENTS = 20


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).astimezone().isoformat()


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_payload(args: argparse.Namespace) -> Any:
    if args.file:
        raw = Path(args.file).read_text(encoding="utf-8")
    else:
        raw = args.value or "{}"
    return json.loads(raw)


def extract_intents(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        rows = payload
    elif isinstance(payload, dict):
        rows = payload.get("intents") or payload.get("rows") or []
    else:
        raise ValueError("payload must be a JSON object or list")
    if not isinstance(rows, list):
        raise ValueError("intents must be a list")
    if len(rows) > MAX_INTENTS:
        raise ValueError(f"too many intents: max {MAX_INTENTS}")
    return [normalise_intent(row) for row in rows]


def normalise_intent(row: Any) -> dict[str, Any]:
    if not isinstance(row, dict):
        raise ValueError("each intent must be a JSON object")
    feedback_handler._reject_secret_like(row)
    action = str(row.get("action") or "")
    if action not in feedback_handler.ALLOWED_ACTIONS:
        raise ValueError(f"unsupported action: {action}")
    symbol = str(row.get("symbol") or "").strip()
    if not symbol:
        raise ValueError("intent symbol is required")
    return {
        "system": "project_aegis",
        "source": "dashboard_local_intent_export",
        "action": action,
        "symbol": symbol,
        "name": row.get("name"),
        "market": row.get("market"),
        "status": row.get("status"),
        "score": row.get("score"),
        "dashboard_recorded_at": row.get("time") or row.get("dashboard_recorded_at"),
    }


def ingest(intents: list[dict[str, Any]], *, dry_run: bool = False) -> dict[str, Any]:
    events = []
    for intent in intents:
        event = feedback_handler.build_event(intent)
        events.append(event)
        if not dry_run:
            feedback_handler.append_event(event)
    latest_event = events[-1] if events else None
    report = {
        "type": "aegis_dashboard_local_intent_ingest",
        "generated_at": _now(),
        "status": "DRY_RUN" if dry_run else "RECORDED",
        "intent_count": len(intents),
        "event_count": len(events),
        "source": "dashboard_local_intent_export",
        "intent_payload_sha256": _sha256_text(json.dumps(intents, ensure_ascii=False, sort_keys=True)),
        "events": events,
        "latest_event": latest_event,
        "latest_symbol": latest_event.get("symbol") if latest_event else None,
        "latest_action": latest_event.get("action") if latest_event else None,
        "latest_feedback_type": latest_event.get("feedback_type") if latest_event else None,
        "latest_feedback": str(feedback_handler.LATEST),
        "event_log": str(feedback_handler.EVENT_LOG),
        "safety": {
            "simulation_only": True,
            "recommendation_mutated": False,
            "paper_trade_created": False,
            "holding_mutated": False,
            "broker_called": False,
            "order_placed": False,
            "trading_webhook_called": False,
            "no_secret_values_recorded": True,
        },
    }
    if not dry_run:
        REPORTS.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("value", nargs="?", help="Dashboard local intent JSON")
    parser.add_argument("--file", help="Read Dashboard local intent JSON from file")
    parser.add_argument("--dry-run", action="store_true", help="Validate only; do not write feedback evidence")
    args = parser.parse_args()
    intents = extract_intents(load_payload(args))
    report = ingest(intents, dry_run=args.dry_run)
    print(f"status={report['status']}")
    print(f"intent_count={report['intent_count']}")
    print(f"event_count={report['event_count']}")
    print(f"event_log={report['event_log']}")
    print("effects=no_recommendation,no_paper_trade,no_holding,no_broker,no_order,no_webhook")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
