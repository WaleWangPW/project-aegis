"""Validate user-supplied paper entry evidence.

V2.9-D bridges pending entry requests to virtual PaperTrade creation
candidates. It validates user-provided entry price/date and evidence refs, but
it still does not create PaperTrade records.
"""

from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping, Sequence

_DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_SECRET_MARKERS = (
    "api_key",
    "apikey",
    "secret",
    "bearer ",
    "token=",
    "password",
    "cookie",
    "webhook",
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def _sha256_path(path: Path) -> str | None:
    if not path.exists() or not path.is_file():
        return None
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _valid_date(value: object) -> bool:
    if not isinstance(value, str) or not _DATE_PATTERN.match(value):
        return False
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        return False
    return True


def _positive_price(value: object) -> bool:
    try:
        return float(value) > 0
    except (TypeError, ValueError):
        return False


def _positive_size(value: object) -> bool:
    try:
        return float(value) > 0
    except (TypeError, ValueError):
        return False


def _contains_secret_like_text(value: object) -> bool:
    text = str(value).lower()
    return any(marker in text for marker in _SECRET_MARKERS)


def _index_pending_requests(pending_entry_requests: Sequence[Mapping]) -> dict[str, Mapping]:
    return {str(item["entry_request_id"]): item for item in pending_entry_requests}


def _evidence_items(evidence_refs: Sequence[object] | None) -> list[dict]:
    items: list[dict] = []
    for ref in evidence_refs or []:
        ref_text = str(ref)
        path = Path(ref_text).expanduser()
        items.append(
            {
                "evidence_ref": ref_text,
                "exists": path.exists(),
                "sha256": _sha256_path(path),
            }
        )
    return items


def validate_user_entry_evidence(
    pending_entry_requests: Sequence[Mapping],
    user_entry_inputs: Sequence[Mapping],
    *,
    created_at: str | None = None,
) -> dict:
    created = created_at or _now_iso()
    pending_by_id = _index_pending_requests(pending_entry_requests)
    validated: list[dict] = []
    blocked: list[dict] = []

    for item in user_entry_inputs:
        entry_request_id = str(item.get("entry_request_id", ""))
        pending = pending_by_id.get(entry_request_id)
        reasons: list[str] = []

        if pending is None:
            reasons.append("unknown_entry_request")
        elif pending.get("entry_request_status") != "pending_user_price_date":
            reasons.append("entry_request_not_pending_user_price_date")

        if not _positive_price(item.get("entry_price")):
            reasons.append("invalid_entry_price")
        if not _valid_date(item.get("entry_date")):
            reasons.append("invalid_entry_date")
        if item.get("user_confirmed") is not True:
            reasons.append("missing_explicit_user_confirmation")
        if item.get("virtual_position_size") is not None and not _positive_size(item.get("virtual_position_size")):
            reasons.append("invalid_virtual_position_size")

        evidence_refs = item.get("evidence_refs") or []
        if not evidence_refs:
            reasons.append("missing_evidence_refs")
        if any(_contains_secret_like_text(value) for value in [item.get("notes", ""), *evidence_refs]):
            reasons.append("secret_like_text_blocked")

        evidence = _evidence_items(evidence_refs)
        if any(not evidence_item["exists"] for evidence_item in evidence):
            reasons.append("evidence_ref_missing")

        base = {
            "entry_request_id": entry_request_id,
            "symbol": pending.get("symbol") if pending else item.get("symbol"),
            "market": pending.get("market") if pending else item.get("market"),
            "entry_price": float(item["entry_price"]) if _positive_price(item.get("entry_price")) else None,
            "entry_date": item.get("entry_date"),
            "virtual_position_size": float(item.get("virtual_position_size") or 1.0)
            if _positive_size(item.get("virtual_position_size") or 1.0)
            else None,
            "user_confirmed": item.get("user_confirmed") is True,
            "evidence_items": evidence,
            "notes_hash": hashlib.sha256(str(item.get("notes", "")).encode("utf-8")).hexdigest()
            if item.get("notes")
            else None,
            "created_at": created,
            "no_price_fabrication": True,
            "no_date_fabrication": True,
            "no_paper_trade_mutation": True,
            "no_recommendation_mutation": True,
            "no_real_trade_execution": True,
            "no_broker_api": True,
            "no_webhook": True,
            "no_order_placement": True,
        }

        if reasons:
            blocked.append({**base, "status": "blocked", "blocked_reasons": reasons})
            continue

        validated.append(
            {
                **base,
                "status": "ready_for_virtual_paper_trade_creation",
                "paper_trade_create_candidate_id": f"paper_create_candidate_{entry_request_id}",
                "source_paper_intake_id": pending["paper_intake_id"],
                "source_feedback_id": pending["feedback_id"],
                "ready_to_create_paper_trade": True,
                "requires_paper_trade_creation_step": True,
            }
        )

    return {
        "validated_entry_evidence_records": validated,
        "blocked_entry_evidence_records": blocked,
    }


def build_entry_evidence_report(
    pending_entry_requests: Sequence[Mapping],
    user_entry_inputs: Sequence[Mapping],
    *,
    run_id: str,
    command: str | None = None,
) -> dict:
    result = validate_user_entry_evidence(pending_entry_requests, user_entry_inputs)
    validated = result["validated_entry_evidence_records"]
    blocked = result["blocked_entry_evidence_records"]
    checks = {
        "has_user_entry_inputs": bool(user_entry_inputs),
        "has_validated_entry_evidence": bool(validated),
        "validated_records_ready_for_virtual_paper_trade_creation": all(
            item["status"] == "ready_for_virtual_paper_trade_creation"
            and item["ready_to_create_paper_trade"] is True
            for item in validated
        ),
        "blocked_records_not_ready": all(item["status"] == "blocked" for item in blocked),
        "validated_prices_positive": all(item["entry_price"] and item["entry_price"] > 0 for item in validated),
        "validated_dates_present": all(_valid_date(item["entry_date"]) for item in validated),
        "validated_evidence_hashed": all(
            item["evidence_items"] and all(ev["sha256"] for ev in item["evidence_items"]) for item in validated
        ),
        "explicit_user_confirmation_required": all(item["user_confirmed"] is True for item in validated),
        "paper_trades_not_written": True,
        "recommendations_not_written": True,
        "production_records_not_written": True,
        "no_real_trade_execution": True,
        "no_broker_api": True,
        "no_webhook": True,
        "no_order_placement": True,
    }
    return {
        "overall_status": "PASS" if all(checks.values()) else "FAIL",
        "acceptance_target": "V2.9-D User-Supplied Paper Entry Evidence Validation",
        "run_id": run_id,
        "generated_at": _now_iso(),
        "command": command,
        "network_used": False,
        "production_records_written": False,
        "paper_trades_written": False,
        "recommendations_written": False,
        "dashboard_contract_changed": False,
        "summary": {
            "pending_entry_request_count": len(pending_entry_requests),
            "user_entry_input_count": len(user_entry_inputs),
            "validated_entry_evidence_count": len(validated),
            "blocked_entry_evidence_count": len(blocked),
            "symbols_ready": [item["symbol"] for item in validated],
            "symbols_blocked": [item["symbol"] for item in blocked],
        },
        **result,
        "checks": checks,
        "safety": {
            "validation_only": True,
            "paper_trade_creation_deferred": True,
            "requires_user_price": True,
            "requires_user_date": True,
            "requires_user_evidence": True,
            "requires_explicit_user_confirmation": True,
            "no_price_fabrication": True,
            "no_date_fabrication": True,
            "no_paper_trade_mutation": True,
            "no_recommendation_mutation": True,
            "no_real_trade_execution": True,
            "no_broker_api": True,
            "no_webhook": True,
            "no_order_placement": True,
            "dashboard_contract_unchanged": True,
        },
    }
