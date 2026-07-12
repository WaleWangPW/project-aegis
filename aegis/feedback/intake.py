"""Manual feedback intake for user-submitted external evidence."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping, Sequence

from aegis.models.manual_feedback import ManualFeedbackInput, ManualFeedbackRecord

_SECRET_MARKERS = (
    "api_key",
    "apikey",
    "secret",
    "password",
    "passwd",
    "bearer ",
    "token=",
    "cookie:",
    "authorization:",
    "broker credential",
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _looks_secret(value: str | None) -> bool:
    text = (value or "").lower()
    return any(marker in text for marker in _SECRET_MARKERS)


def _brief_items_by_suggestion_id(brief: Mapping) -> dict[str, list[Mapping]]:
    items: dict[str, list[Mapping]] = {}
    for item in brief.get("items") or []:
        suggestion_id = str(item.get("suggestion_id"))
        items.setdefault(suggestion_id, []).append(item)
    return items


def _screenshot_evidence(paths: Sequence[str], *, root: Path | None = None) -> list[dict]:
    evidence: list[dict] = []
    for raw_path in paths:
        path = Path(raw_path)
        if not path.is_absolute() and root is not None:
            path = root / path
        item = {
            "path": str(path),
            "exists": path.exists(),
            "sha256": _sha256(path) if path.exists() and path.is_file() else None,
            "raw_image_stored_in_record": False,
            "ocr_performed": False,
        }
        evidence.append(item)
    return evidence


def build_manual_feedback_records(
    feedback_inputs: Sequence[ManualFeedbackInput | Mapping],
    *,
    brief: Mapping,
    evidence_ref: str,
    screenshot_root: Path | None = None,
    created_at: str | None = None,
) -> list[ManualFeedbackRecord]:
    created = created_at or _now_iso()
    brief_items = _brief_items_by_suggestion_id(brief)
    records: list[ManualFeedbackRecord] = []

    for raw_feedback in feedback_inputs:
        feedback = raw_feedback if isinstance(raw_feedback, ManualFeedbackInput) else ManualFeedbackInput(**raw_feedback)
        linked_items = brief_items.get(feedback.suggestion_id, [])
        matching_items = [
            item
            for item in linked_items
            if item.get("symbol") == feedback.symbol and item.get("market") == feedback.market
        ]
        linked_item = matching_items[0] if matching_items else (linked_items[0] if linked_items else None)

        blocked_by: list[str] = []
        if linked_item is None:
            blocked_by.append("suggestion_not_found_in_brief")
        elif linked_item.get("brief_status") == "blocked" and feedback.feedback_type == "external_manual_execution":
            blocked_by.append("cannot_record_external_execution_for_blocked_path")
        elif linked_item.get("symbol") != feedback.symbol or linked_item.get("market") != feedback.market:
            blocked_by.append("feedback_symbol_or_market_mismatch")
        if _looks_secret(feedback.user_note) or _looks_secret(feedback.external_execution_summary):
            blocked_by.append("secret_like_text_detected")
        if any(_looks_secret(path) for path in feedback.screenshot_paths):
            blocked_by.append("secret_like_screenshot_path_detected")

        records.append(
            ManualFeedbackRecord(
                feedback_id=feedback.feedback_id,
                suggestion_id=feedback.suggestion_id,
                symbol=feedback.symbol,
                market=feedback.market,
                feedback_type=feedback.feedback_type,
                feedback_status="blocked" if blocked_by else "accepted",
                user_note_summary=feedback.user_note[:300],
                screenshot_evidence=_screenshot_evidence(feedback.screenshot_paths, root=screenshot_root),
                external_execution_summary=(
                    feedback.external_execution_summary[:300] if feedback.external_execution_summary else None
                ),
                blocked_by=blocked_by,
                evidence_refs=[evidence_ref, *list((linked_item or {}).get("evidence_refs") or [])],
                linked_brief_item_id=linked_item.get("item_id") if linked_item else None,
                created_at=created,
            )
        )
    return records


def build_manual_feedback_intake_report(
    feedback_inputs: Sequence[ManualFeedbackInput | Mapping],
    *,
    brief: Mapping,
    run_id: str,
    evidence_ref: str,
    screenshot_root: Path | None = None,
    command: str | None = None,
) -> dict:
    records = build_manual_feedback_records(
        feedback_inputs,
        brief=brief,
        evidence_ref=evidence_ref,
        screenshot_root=screenshot_root,
    )
    accepted = [item for item in records if item.feedback_status == "accepted"]
    blocked = [item for item in records if item.feedback_status == "blocked"]
    checks = {
        "has_feedback_records": len(records) > 0,
        "accepted_feedback_present": len(accepted) > 0,
        "blocked_feedback_present": len(blocked) > 0,
        "external_execution_is_evidence_only": all(item.no_real_trade_execution for item in records),
        "screenshots_hashed_when_present": all(
            evidence["sha256"] or not evidence["exists"]
            for item in records
            for evidence in item.screenshot_evidence
        ),
        "raw_images_not_stored": all(
            evidence["raw_image_stored_in_record"] is False
            for item in records
            for evidence in item.screenshot_evidence
        ),
        "secret_like_feedback_blocked": any("secret_like_text_detected" in item.blocked_by for item in blocked),
        "blocked_path_execution_blocked": any(
            "cannot_record_external_execution_for_blocked_path" in item.blocked_by for item in blocked
        ),
        "no_broker_api": all(item.no_broker_api for item in records),
        "no_webhook": all(item.no_webhook for item in records),
        "no_order_placement": all(item.no_order_placement for item in records),
    }
    return {
        "overall_status": "PASS" if all(checks.values()) else "FAIL",
        "acceptance_target": "V2.6-B Manual Feedback Intake",
        "run_id": run_id,
        "generated_at": _now_iso(),
        "command": command,
        "network_used": False,
        "production_records_written": False,
        "paper_trades_written": False,
        "recommendations_written": False,
        "dashboard_contract_changed": False,
        "summary": {
            "feedback_count": len(records),
            "accepted_count": len(accepted),
            "blocked_count": len(blocked),
            "feedback_types": sorted({item.feedback_type for item in records}),
            "symbols": [item.symbol for item in records],
        },
        "records": [item.model_dump() for item in records],
        "checks": checks,
        "safety": {
            "user_submitted_evidence_only": True,
            "simulation_only": True,
            "manual_external_execution_only": True,
            "no_real_trade_execution": True,
            "no_broker_api": True,
            "no_webhook": True,
            "no_order_placement": True,
            "no_paper_trade_mutation": True,
            "no_recommendation_mutation": True,
            "dashboard_contract_unchanged": True,
            "screenshots_are_evidence_paths_only": True,
        },
    }
