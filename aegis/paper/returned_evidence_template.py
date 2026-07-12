"""Template helpers for real user-returned evidence intake.

The template is a local-file handoff format for user screenshots, notes, and
outcome evidence. It must never contain secrets or broker/trading automation.
"""

from __future__ import annotations

from pathlib import Path
from typing import Mapping, Sequence

from aegis.paper.returned_evidence_refresh import validate_user_returned_evidence

REQUIRED_TOP_LEVEL_FIELDS = {"schema_version", "local_file_path", "instructions", "records", "safety"}
REQUIRED_RECORD_FIELDS = {
    "returned_evidence_id",
    "paper_trade_id",
    "evidence_type",
    "submitted_at",
    "user_note",
    "evidence_refs",
    "outcome",
    "decision_quality",
    "actual_return",
    "max_drawdown",
    "user_confirmed",
}
ALLOWED_EVIDENCE_TYPES = {"outcome", "screenshot", "text_note"}
SECRET_MARKERS = (
    "api_key=",
    "apikey=",
    "secret=",
    "password=",
    "passwd=",
    "bearer ",
    "token=",
    "cookie:",
    "authorization:",
    "broker credential",
    "webhook_url=",
)
FORBIDDEN_AUTOMATION_TERMS = ("broker_api", "trading_webhook", "real_trade_execution", "place_order")


def _walk_strings(value: object) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, Mapping):
        strings: list[str] = []
        for child in value.values():
            strings.extend(_walk_strings(child))
        return strings
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        strings = []
        for child in value:
            strings.extend(_walk_strings(child))
        return strings
    return []


def _has_secret_like_value(payload: Mapping) -> bool:
    # Instructional warning text may mention "bearer tokens" or cookies. Only
    # scan user-fillable record content for concrete secret-like values.
    records_only = {"records": payload.get("records", [])}
    return any(marker in text.lower() for text in _walk_strings(records_only) for marker in SECRET_MARKERS)


def _has_forbidden_automation(payload: Mapping) -> bool:
    return any(term in text.lower() for text in _walk_strings(payload) for term in FORBIDDEN_AUTOMATION_TERMS)


def _known_paper_trade_ids(current_brief: Mapping) -> set[str]:
    return {
        str(item.get("paper_trade_id"))
        for item in current_brief.get("review_memory_queue", [])
        if item.get("paper_trade_id")
    }


def validate_user_returned_evidence_template(
    payload: Mapping,
    *,
    current_brief: Mapping,
    gitignore_text: str = "",
) -> dict:
    records = list(payload.get("records") or [])
    record_types = {str(item.get("evidence_type")) for item in records}
    local_file_path = str(payload.get("local_file_path") or "")
    instructions = "\n".join(str(item) for item in payload.get("instructions") or [])
    safety = payload.get("safety") or {}
    known_trade_ids = _known_paper_trade_ids(current_brief)
    checks = {
        "top_level_fields_present": REQUIRED_TOP_LEVEL_FIELDS.issubset(payload.keys()),
        "schema_version_correct": payload.get("schema_version") == "user_returned_evidence.user_template.v2_9_j",
        "local_path_is_local_json": local_file_path == "config/user_returned_evidence.local.json",
        "local_path_gitignored": local_file_path in gitignore_text,
        "instructions_warn_no_secrets": all(
            term in instructions
            for term in ["API keys", "cookies", "bearer tokens", "broker credentials", "webhook"]
        ),
        "has_records": bool(records),
        "record_fields_present": all(REQUIRED_RECORD_FIELDS.issubset(item.keys()) for item in records),
        "has_outcome_screenshot_and_text_note": {"outcome", "screenshot", "text_note"}.issubset(record_types),
        "record_types_allowed": record_types.issubset(ALLOWED_EVIDENCE_TYPES),
        "template_uses_placeholders_for_trade_id": all(
            str(item.get("paper_trade_id", "")).startswith("REPLACE_WITH_") for item in records
        ),
        "current_brief_has_trade_id_to_fill": bool(known_trade_ids),
        "no_secret_like_values": not _has_secret_like_value(payload),
        "no_forbidden_automation_terms": not _has_forbidden_automation(payload),
        "safety_flags_present": all(
            safety.get(flag) is True
            for flag in [
                "simulation_only",
                "user_returned_evidence_only",
                "no_api_keys",
                "no_cookies",
                "no_bearer_tokens",
                "no_broker_credentials",
                "no_webhook_urls",
                "no_real_trade_execution",
                "no_order_placement",
            ]
        ),
    }
    return {
        "overall_status": "PASS" if all(checks.values()) else "FAIL",
        "known_paper_trade_ids": sorted(known_trade_ids),
        "record_types": sorted(record_types),
        "checks": checks,
    }


def materialize_example_returned_evidence(
    payload: Mapping,
    *,
    current_brief: Mapping,
    evidence_path: Path,
) -> list[dict]:
    known_trade_ids = sorted(_known_paper_trade_ids(current_brief))
    if not known_trade_ids:
        raise ValueError("current brief has no paper_trade_id")
    paper_trade_id = known_trade_ids[0]
    outcome_template = next(item for item in payload.get("records", []) if item.get("evidence_type") == "outcome")
    materialized = {
        **dict(outcome_template),
        "returned_evidence_id": "returned_real_user_template_example_001",
        "paper_trade_id": paper_trade_id,
        "submitted_at": "2026-07-11T22:10:00+08:00",
        "user_note": "Template validation example: user manually supplied simulation outcome evidence.",
        "evidence_refs": [str(evidence_path)],
        "outcome": "mixed",
        "decision_quality": "reasonable_decision",
        "actual_return": 0.003,
        "max_drawdown": -0.006,
        "user_confirmed": True,
    }
    return [materialized]


def validate_materialized_example(
    records: Sequence[Mapping],
    *,
    current_brief: Mapping,
    formal_review_memory_report: Mapping,
) -> dict:
    result = validate_user_returned_evidence(
        records,
        current_brief=current_brief,
        formal_review_memory_report=formal_review_memory_report,
    )
    accepted = result["accepted_returned_evidence_records"]
    blocked = result["blocked_returned_evidence_records"]
    checks = {
        "example_has_records": bool(records),
        "example_accepted": len(accepted) == len(records) and not blocked,
        "example_actual_return_user_supplied": all(
            item.get("actual_return_source") == "user_returned_evidence" for item in accepted
        ),
        "example_no_return_fabrication": all(item.get("no_return_fabrication") is True for item in accepted),
        "example_no_real_trade": all(item.get("no_real_trade_execution") is True for item in accepted),
        "example_no_broker_api": all(item.get("no_broker_api") is True for item in accepted),
        "example_no_webhook": all(item.get("no_webhook") is True for item in accepted),
        "example_no_order_placement": all(item.get("no_order_placement") is True for item in accepted),
    }
    return {
        "overall_status": "PASS" if all(checks.values()) else "FAIL",
        "accepted_returned_evidence_records": accepted,
        "blocked_returned_evidence_records": blocked,
        "checks": checks,
    }
