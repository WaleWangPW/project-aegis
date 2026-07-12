"""Validate user-supplied H/US paper simulation evidence.

This module turns pending H/US review queue items into virtual PaperTrade
creation candidates only after user-provided price, date, evidence, and
explicit simulation confirmation are present. It still does not write
PaperTrade, Recommendation, Review, or Memory records.
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
    "passwd",
    "cookie",
    "authorization:",
    "webhook",
    "broker credential",
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _sha256_path(path: Path) -> str | None:
    if not path.exists() or not path.is_file():
        return None
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
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
    text = str(value or "").lower()
    return any(marker in text for marker in _SECRET_MARKERS)


def _queue_by_id(review_queue: Sequence[Mapping]) -> dict[str, Mapping]:
    return {str(item["queue_id"]): item for item in review_queue}


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
                "raw_image_stored_in_record": False,
                "ocr_performed": False,
            }
        )
    return items


def validate_h_us_user_supplied_evidence(
    review_queue: Sequence[Mapping],
    user_evidence_inputs: Sequence[Mapping],
    *,
    created_at: str | None = None,
) -> dict:
    created = created_at or _now_iso()
    queue_index = _queue_by_id(review_queue)
    validated: list[dict] = []
    blocked: list[dict] = []

    for item in user_evidence_inputs:
        queue_id = str(item.get("queue_id", ""))
        queue_item = queue_index.get(queue_id)
        reasons: list[str] = []

        if queue_item is None:
            reasons.append("unknown_review_queue_item")
        elif queue_item.get("queue_status") != "pending_user_price_date_evidence":
            reasons.append("review_queue_item_not_pending_user_price_date_evidence")

        if not _positive_price(item.get("entry_price")):
            reasons.append("invalid_entry_price")
        if not _valid_date(item.get("entry_date")):
            reasons.append("invalid_entry_date")
        if item.get("explicit_simulation_confirmation") is not True:
            reasons.append("missing_explicit_simulation_confirmation")
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
            "queue_id": queue_id,
            "followup_id": queue_item.get("followup_id") if queue_item else item.get("followup_id"),
            "feedback_id": queue_item.get("feedback_id") if queue_item else item.get("feedback_id"),
            "suggestion_id": queue_item.get("suggestion_id") if queue_item else item.get("suggestion_id"),
            "symbol": queue_item.get("symbol") if queue_item else item.get("symbol"),
            "market": queue_item.get("market") if queue_item else item.get("market"),
            "entry_price": float(item["entry_price"]) if _positive_price(item.get("entry_price")) else None,
            "entry_date": item.get("entry_date"),
            "virtual_position_size": float(item.get("virtual_position_size") or 1.0)
            if _positive_size(item.get("virtual_position_size") or 1.0)
            else None,
            "explicit_simulation_confirmation": item.get("explicit_simulation_confirmation") is True,
            "evidence_items": evidence,
            "notes_hash": hashlib.sha256(str(item.get("notes", "")).encode("utf-8")).hexdigest()
            if item.get("notes")
            else None,
            "created_at": created,
            "ready_to_create_paper_trade": False,
            "simulation_only": True,
            "manual_external_execution_only": True,
            "user_supplied_evidence_only": True,
            "no_price_fabrication": True,
            "no_date_fabrication": True,
            "no_paper_trade_mutation": True,
            "no_recommendation_mutation": True,
            "no_review_mutation": True,
            "no_memory_mutation": True,
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
                "status": "ready_for_virtual_paper_trade_creation_candidate",
                "virtual_paper_trade_create_candidate_id": f"h_us_paper_create_candidate_{queue_id}",
                "ready_to_create_paper_trade": True,
                "requires_paper_trade_creation_step": True,
                "source_review_queue_status": queue_item["queue_status"],
                "source_evidence_refs": list(queue_item.get("evidence_refs") or []),
            }
        )

    return {
        "validated_user_evidence_records": validated,
        "blocked_user_evidence_records": blocked,
    }


def build_h_us_user_supplied_evidence_report(
    source_report: Mapping,
    user_evidence_inputs: Sequence[Mapping],
    *,
    run_id: str,
    command: str | None = None,
) -> dict:
    review_queue = list(source_report.get("review_queue") or [])
    result = validate_h_us_user_supplied_evidence(review_queue, user_evidence_inputs)
    validated = result["validated_user_evidence_records"]
    blocked = result["blocked_user_evidence_records"]
    checks = {
        "source_is_v2_12_h": source_report.get("acceptance_target")
        == "V2.12-H H-US Feedback To Paper Simulation Review Queue",
        "source_report_pass": source_report.get("overall_status") == "PASS",
        "source_has_review_queue": bool(review_queue),
        "has_user_evidence_inputs": bool(user_evidence_inputs),
        "has_validated_user_evidence": bool(validated),
        "has_blocked_user_evidence": bool(blocked),
        "validated_records_ready_for_virtual_paper_trade_creation_candidate": all(
            item["status"] == "ready_for_virtual_paper_trade_creation_candidate"
            and item["ready_to_create_paper_trade"] is True
            for item in validated
        ),
        "blocked_records_not_ready": all(item["status"] == "blocked" for item in blocked),
        "validated_prices_positive": all(item["entry_price"] and item["entry_price"] > 0 for item in validated),
        "validated_dates_present": all(_valid_date(item["entry_date"]) for item in validated),
        "validated_evidence_hashed": all(
            item["evidence_items"] and all(ev["sha256"] for ev in item["evidence_items"])
            for item in validated
        ),
        "explicit_simulation_confirmation_required": all(
            item["explicit_simulation_confirmation"] is True for item in validated
        ),
        "blocked_invalid_inputs_present": bool(blocked),
        "no_price_fabrication": all(item["no_price_fabrication"] for item in [*validated, *blocked]),
        "no_date_fabrication": all(item["no_date_fabrication"] for item in [*validated, *blocked]),
        "no_paper_trade_mutation": all(item["no_paper_trade_mutation"] for item in [*validated, *blocked]),
        "no_recommendation_mutation": all(item["no_recommendation_mutation"] for item in [*validated, *blocked]),
        "no_review_mutation": all(item["no_review_mutation"] for item in [*validated, *blocked]),
        "no_memory_mutation": all(item["no_memory_mutation"] for item in [*validated, *blocked]),
        "no_real_trade_execution": all(item["no_real_trade_execution"] for item in [*validated, *blocked]),
        "no_broker_api": all(item["no_broker_api"] for item in [*validated, *blocked]),
        "no_webhook": all(item["no_webhook"] for item in [*validated, *blocked]),
        "no_order_placement": all(item["no_order_placement"] for item in [*validated, *blocked]),
    }
    return {
        "overall_status": "PASS" if all(checks.values()) else "FAIL",
        "acceptance_target": "V2.12-I H-US User-Supplied Paper Evidence Validation",
        "source_acceptance_target": source_report.get("acceptance_target"),
        "run_id": run_id,
        "generated_at": _now_iso(),
        "command": command,
        "network_used": False,
        "production_records_written": False,
        "paper_trades_written": False,
        "recommendations_written": False,
        "reviews_written": False,
        "memory_written": False,
        "dashboard_contract_changed": False,
        "summary": {
            "source_review_queue_count": len(review_queue),
            "user_evidence_input_count": len(user_evidence_inputs),
            "validated_user_evidence_count": len(validated),
            "blocked_user_evidence_count": len(blocked),
            "symbols_ready": [item["symbol"] for item in validated],
            "symbols_blocked": [item["symbol"] for item in blocked],
            "next_stage": "V2.12-J H-US Virtual PaperTrade Creation From Validated Evidence",
        },
        **result,
        "checks": checks,
        "safety": {
            "validation_only": True,
            "simulation_only": True,
            "manual_external_execution_only": True,
            "user_supplied_evidence_only": True,
            "paper_trade_creation_deferred": True,
            "requires_user_price": True,
            "requires_user_date": True,
            "requires_user_evidence": True,
            "requires_explicit_simulation_confirmation": True,
            "no_price_fabrication": True,
            "no_date_fabrication": True,
            "no_paper_trade_mutation": True,
            "no_recommendation_mutation": True,
            "no_review_mutation": True,
            "no_memory_mutation": True,
            "no_real_trade_execution": True,
            "no_broker_api": True,
            "no_webhook": True,
            "no_order_placement": True,
            "dashboard_contract_unchanged": True,
        },
    }
