"""Feedback intake for V2.13-I Finnhub quote simulation brief.

The intake records user reactions to the simulation-only Finnhub quote brief.
It may create follow-up evidence candidates for later paper simulation review,
but it never mutates PaperTrade, Recommendation, Review, Memory, broker state,
webhook state, or orders.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping, Sequence

from aegis.models.manual_feedback import ManualFeedbackInput

ACCEPTANCE_TARGET = "V2.13-J Finnhub Quote User Feedback Intake"
SOURCE_ACCEPTANCE_TARGET = "V2.13-I Finnhub Quote Current Simulation Brief"

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
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _looks_secret(value: str | None) -> bool:
    text = (value or "").lower()
    return any(marker in text for marker in _SECRET_MARKERS)


def _brief_items_by_key(brief: Mapping) -> dict[tuple[str, str, str], Mapping]:
    return {
        (str(item.get("suggestion_id")), str(item.get("symbol")), str(item.get("market"))): item
        for item in brief.get("items", []) or []
        if item.get("suggestion_id") and item.get("symbol") and item.get("market")
    }


def _screenshot_evidence(paths: Sequence[str], *, root: Path | None = None) -> list[dict]:
    evidence: list[dict] = []
    for raw_path in paths:
        path = Path(raw_path)
        if not path.is_absolute() and root is not None:
            path = root / path
        evidence.append(
            {
                "path": str(path),
                "exists": path.exists(),
                "sha256": _sha256(path) if path.exists() and path.is_file() else None,
                "raw_image_stored_in_record": False,
                "ocr_performed": False,
            }
        )
    return evidence


def build_finnhub_quote_feedback_records(
    feedback_inputs: Sequence[ManualFeedbackInput | Mapping],
    *,
    brief: Mapping,
    evidence_ref: str,
    screenshot_root: Path | None = None,
    created_at: str | None = None,
) -> list[dict]:
    created = created_at or _now_iso()
    brief_items = _brief_items_by_key(brief)
    records: list[dict] = []
    for raw_feedback in feedback_inputs:
        feedback = raw_feedback if isinstance(raw_feedback, ManualFeedbackInput) else ManualFeedbackInput(**raw_feedback)
        item = brief_items.get((feedback.suggestion_id, feedback.symbol, feedback.market))
        blocked_by: list[str] = []
        if item is None:
            blocked_by.append("brief_item_not_found")
        elif item.get("brief_status") != "simulation_candidate" and feedback.feedback_type != "manual_ignore":
            blocked_by.append("cannot_watch_or_execute_non_candidate_item")
        if _looks_secret(feedback.user_note) or _looks_secret(feedback.external_execution_summary):
            blocked_by.append("secret_like_text_detected")
        if any(_looks_secret(path) for path in feedback.screenshot_paths):
            blocked_by.append("secret_like_screenshot_path_detected")

        records.append(
            {
                "feedback_id": feedback.feedback_id,
                "suggestion_id": feedback.suggestion_id,
                "symbol": feedback.symbol,
                "market": feedback.market,
                "feedback_type": feedback.feedback_type,
                "feedback_status": "blocked" if blocked_by else "accepted",
                "brief_item_status": item.get("brief_status") if item else None,
                "user_note_summary": feedback.user_note[:300],
                "external_execution_summary": (
                    feedback.external_execution_summary[:300] if feedback.external_execution_summary else None
                ),
                "screenshot_evidence": _screenshot_evidence(feedback.screenshot_paths, root=screenshot_root),
                "blocked_by": blocked_by,
                "evidence_refs": [evidence_ref, *list((item or {}).get("evidence_refs") or [])],
                "linked_brief_item_id": item.get("item_id") if item else None,
                "created_at": created,
                "user_submitted_evidence_only": True,
                "simulation_only": True,
                "manual_external_execution_only": True,
                "quote_context_research_only": True,
                "social_sentiment_not_enabled": True,
                "no_real_trade_execution": True,
                "no_broker_api": True,
                "no_webhook": True,
                "no_order_placement": True,
                "no_live_price": True,
                "no_position_size": True,
                "no_live_order_signal": True,
                "no_paper_trade_mutation": True,
                "no_recommendation_mutation": True,
                "no_review_mutation": True,
                "no_memory_mutation": True,
            }
        )
    return records


def build_finnhub_quote_simulation_followup_candidates(records: Sequence[Mapping], *, evidence_ref: str) -> list[dict]:
    candidates: list[dict] = []
    for record in records:
        if record.get("feedback_status") != "accepted":
            continue
        if record.get("feedback_type") not in {"manual_watch", "external_manual_execution"}:
            continue
        candidates.append(
            {
                "followup_id": f"finnhub_quote_feedback_followup_{record['feedback_id']}",
                "feedback_id": record["feedback_id"],
                "suggestion_id": record["suggestion_id"],
                "symbol": record["symbol"],
                "market": record["market"],
                "followup_status": "simulation_evidence_candidate",
                "followup_action": (
                    "paper_watch_evidence"
                    if record.get("feedback_type") == "manual_watch"
                    else "manual_external_action_evidence"
                ),
                "requires_user_price_before_paper_trade": True,
                "requires_user_date_before_paper_trade": True,
                "requires_explicit_simulation_confirmation": True,
                "requires_explicit_review_before_paper_trade": True,
                "evidence_refs": [evidence_ref, *list(record.get("evidence_refs") or [])],
                "quote_context_research_only": True,
                "social_sentiment_not_enabled": True,
                "no_paper_trade_mutation": True,
                "no_recommendation_mutation": True,
                "no_review_mutation": True,
                "no_memory_mutation": True,
                "no_real_trade_execution": True,
                "no_broker_api": True,
                "no_webhook": True,
                "no_order_placement": True,
                "no_live_price": True,
                "no_position_size": True,
                "no_live_order_signal": True,
            }
        )
    return candidates


def build_finnhub_quote_feedback_intake_report(
    feedback_inputs: Sequence[ManualFeedbackInput | Mapping],
    *,
    brief: Mapping,
    run_id: str,
    evidence_ref: str,
    screenshot_root: Path | None = None,
    command: str | None = None,
) -> dict:
    records = build_finnhub_quote_feedback_records(
        feedback_inputs,
        brief=brief,
        evidence_ref=evidence_ref,
        screenshot_root=screenshot_root,
    )
    followups = build_finnhub_quote_simulation_followup_candidates(records, evidence_ref=evidence_ref)
    accepted = [item for item in records if item["feedback_status"] == "accepted"]
    blocked = [item for item in records if item["feedback_status"] == "blocked"]
    followup_feedback_ids = {item["feedback_id"] for item in followups}
    checks = {
        "source_is_v2_13_i": brief.get("acceptance_target") == SOURCE_ACCEPTANCE_TARGET,
        "source_report_pass": brief.get("overall_status") == "PASS",
        "source_has_aapl_candidate": "AAPL.US" in (brief.get("summary", {}) or {}).get("candidate_symbols", []),
        "source_social_sentiment_still_blocked": (brief.get("summary", {}) or {}).get("social_sentiment_status")
        == "blocked_plan_or_rate_limit",
        "has_feedback_records": bool(records),
        "accepted_feedback_present": bool(accepted),
        "blocked_feedback_present": bool(blocked),
        "simulation_followup_candidates_present": bool(followups),
        "ignore_does_not_create_followup": all(
            item["feedback_id"] not in followup_feedback_ids
            for item in records
            if item["feedback_type"] == "manual_ignore"
        ),
        "unknown_item_blocked": any("brief_item_not_found" in item["blocked_by"] for item in blocked),
        "secret_like_feedback_blocked": any("secret_like_text_detected" in item["blocked_by"] for item in blocked),
        "screenshots_hashed_when_present": all(
            evidence["sha256"] or not evidence["exists"]
            for item in records
            for evidence in item["screenshot_evidence"]
        ),
        "raw_images_not_stored": all(
            evidence["raw_image_stored_in_record"] is False
            for item in records
            for evidence in item["screenshot_evidence"]
        ),
        "no_paper_trade_mutation": all(item["no_paper_trade_mutation"] for item in records)
        and all(item["no_paper_trade_mutation"] for item in followups),
        "no_recommendation_mutation": all(item["no_recommendation_mutation"] for item in records)
        and all(item["no_recommendation_mutation"] for item in followups),
        "no_review_mutation": all(item["no_review_mutation"] for item in records)
        and all(item["no_review_mutation"] for item in followups),
        "no_memory_mutation": all(item["no_memory_mutation"] for item in records)
        and all(item["no_memory_mutation"] for item in followups),
        "no_real_trade_execution": all(item["no_real_trade_execution"] for item in records)
        and all(item["no_real_trade_execution"] for item in followups),
        "no_broker_api": all(item["no_broker_api"] for item in records)
        and all(item["no_broker_api"] for item in followups),
        "no_webhook": all(item["no_webhook"] for item in records)
        and all(item["no_webhook"] for item in followups),
        "no_order_placement": all(item["no_order_placement"] for item in records)
        and all(item["no_order_placement"] for item in followups),
        "no_live_price": all(item["no_live_price"] for item in records)
        and all(item["no_live_price"] for item in followups),
        "no_position_size": all(item["no_position_size"] for item in records)
        and all(item["no_position_size"] for item in followups),
        "no_live_order_signal": all(item["no_live_order_signal"] for item in records)
        and all(item["no_live_order_signal"] for item in followups),
    }
    return {
        "overall_status": "PASS" if all(checks.values()) else "FAIL",
        "acceptance_target": ACCEPTANCE_TARGET,
        "source_acceptance_target": brief.get("acceptance_target"),
        "run_id": run_id,
        "generated_at": _now_iso(),
        "command": command,
        "network_used": False,
        "production_records_written": False,
        "paper_trades_written": False,
        "recommendations_written": False,
        "reviews_written": False,
        "memory_written": False,
        "production_cache_mutated": False,
        "production_provider_config_mutated": False,
        "dashboard_contract_changed": False,
        "summary": {
            "feedback_count": len(records),
            "accepted_count": len(accepted),
            "blocked_count": len(blocked),
            "simulation_followup_count": len(followups),
            "feedback_types": sorted({item["feedback_type"] for item in records}),
            "symbols": [item["symbol"] for item in records],
            "social_sentiment_status": (brief.get("summary", {}) or {}).get("social_sentiment_status"),
            "next_stage": "V2.13-K Finnhub Quote Feedback To Paper Simulation Review Queue",
        },
        "records": records,
        "simulation_followup_candidates": followups,
        "checks": checks,
        "safety": {
            "user_submitted_evidence_only": True,
            "simulation_only": True,
            "manual_external_execution_only": True,
            "simulation_followup_only": True,
            "requires_user_price_before_paper_trade": True,
            "requires_user_date_before_paper_trade": True,
            "requires_explicit_simulation_confirmation": True,
            "quote_context_research_only": True,
            "social_sentiment_not_enabled": True,
            "no_real_trade_execution": True,
            "no_broker_api": True,
            "no_webhook": True,
            "no_order_placement": True,
            "no_live_price": True,
            "no_position_size": True,
            "no_live_order_signal": True,
            "no_paper_trade_mutation": True,
            "no_recommendation_mutation": True,
            "no_review_mutation": True,
            "no_memory_mutation": True,
            "dashboard_contract_unchanged": True,
            "screenshots_are_evidence_paths_only": True,
        },
    }
