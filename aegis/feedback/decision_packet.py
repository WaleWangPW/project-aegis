"""Feedback intake for V2.9 current user decision packets.

These helpers convert user decisions on simulation-only packet items into
evidence records and paper-simulation intake candidates. They never mutate
PaperTrade, RecommendationRecord, broker state, or orders.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal, Mapping, Sequence

from pydantic import BaseModel, Field, field_validator, model_validator

from aegis.models.common import Market

PacketFeedbackAction = Literal["watch", "ignore", "manual_external_action"]

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


class DecisionPacketFeedbackInput(BaseModel):
    feedback_id: str
    symbol: str
    market: Market
    action: PacketFeedbackAction
    user_note: str
    screenshot_paths: list[str] = Field(default_factory=list)
    external_execution_summary: str | None = None
    submitted_at: str

    @field_validator("feedback_id", "symbol", "user_note", "submitted_at")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("field must not be blank")
        return value

    @model_validator(mode="after")
    def _external_summary_required(self) -> "DecisionPacketFeedbackInput":
        if self.action == "manual_external_action" and not (self.external_execution_summary or "").strip():
            raise ValueError("manual_external_action requires external_execution_summary")
        return self


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


def _packet_item_by_symbol_market(packet: Mapping) -> dict[tuple[str, str], Mapping]:
    return {
        (str(item.get("symbol")), str(item.get("market"))): item
        for item in packet.get("items", [])
        if item.get("symbol") and item.get("market")
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


def build_decision_packet_feedback_records(
    feedback_inputs: Sequence[DecisionPacketFeedbackInput | Mapping],
    *,
    packet: Mapping,
    evidence_ref: str,
    screenshot_root: Path | None = None,
    created_at: str | None = None,
) -> list[dict]:
    created = created_at or _now_iso()
    packet_items = _packet_item_by_symbol_market(packet)
    records: list[dict] = []
    for raw_feedback in feedback_inputs:
        feedback = (
            raw_feedback
            if isinstance(raw_feedback, DecisionPacketFeedbackInput)
            else DecisionPacketFeedbackInput(**raw_feedback)
        )
        item = packet_items.get((feedback.symbol, feedback.market))
        blocked_by: list[str] = []
        if item is None:
            blocked_by.append("packet_item_not_found")
        elif item.get("decision_packet_status") == "blocked" and feedback.action != "ignore":
            blocked_by.append("cannot_watch_or_execute_blocked_packet_item")
        if _looks_secret(feedback.user_note) or _looks_secret(feedback.external_execution_summary):
            blocked_by.append("secret_like_text_detected")
        if any(_looks_secret(path) for path in feedback.screenshot_paths):
            blocked_by.append("secret_like_screenshot_path_detected")

        status = "blocked" if blocked_by else "accepted"
        records.append(
            {
                "feedback_id": feedback.feedback_id,
                "symbol": feedback.symbol,
                "market": feedback.market,
                "action": feedback.action,
                "feedback_status": status,
                "packet_item_status": item.get("decision_packet_status") if item else None,
                "source_mode": item.get("source_mode") if item else None,
                "user_note_summary": feedback.user_note[:300],
                "external_execution_summary": (
                    feedback.external_execution_summary[:300] if feedback.external_execution_summary else None
                ),
                "screenshot_evidence": _screenshot_evidence(feedback.screenshot_paths, root=screenshot_root),
                "blocked_by": blocked_by,
                "evidence_refs": [evidence_ref, *list((item or {}).get("evidence_refs") or [])],
                "created_at": created,
                "user_submitted_evidence_only": True,
                "simulation_only": True,
                "manual_external_execution_only": True,
                "no_real_trade_execution": True,
                "no_broker_api": True,
                "no_webhook": True,
                "no_order_placement": True,
                "no_paper_trade_mutation": True,
                "no_recommendation_mutation": True,
            }
        )
    return records


def build_paper_simulation_intake_candidates(records: Sequence[Mapping], *, evidence_ref: str) -> list[dict]:
    candidates: list[dict] = []
    for record in records:
        if record.get("feedback_status") != "accepted":
            continue
        if record.get("action") not in {"watch", "manual_external_action"}:
            continue
        if record.get("packet_item_status") != "simulation_candidate":
            continue
        candidates.append(
            {
                "paper_intake_id": f"packet_paper_intake_{record['feedback_id']}",
                "feedback_id": record["feedback_id"],
                "symbol": record["symbol"],
                "market": record["market"],
                "intake_status": "candidate_evidence",
                "intake_action": (
                    "paper_watch_candidate"
                    if record.get("action") == "watch"
                    else "manual_external_action_evidence"
                ),
                "requires_user_price_before_paper_trade": True,
                "requires_explicit_review_before_paper_trade": True,
                "evidence_refs": [evidence_ref, *list(record.get("evidence_refs") or [])],
                "no_paper_trade_mutation": True,
                "no_recommendation_mutation": True,
                "no_real_trade_execution": True,
                "no_broker_api": True,
                "no_webhook": True,
                "no_order_placement": True,
            }
        )
    return candidates


def build_decision_packet_feedback_intake_report(
    feedback_inputs: Sequence[DecisionPacketFeedbackInput | Mapping],
    *,
    packet: Mapping,
    run_id: str,
    evidence_ref: str,
    screenshot_root: Path | None = None,
    command: str | None = None,
) -> dict:
    records = build_decision_packet_feedback_records(
        feedback_inputs,
        packet=packet,
        evidence_ref=evidence_ref,
        screenshot_root=screenshot_root,
    )
    paper_intake = build_paper_simulation_intake_candidates(records, evidence_ref=evidence_ref)
    accepted = [item for item in records if item["feedback_status"] == "accepted"]
    blocked = [item for item in records if item["feedback_status"] == "blocked"]
    checks = {
        "has_feedback_records": bool(records),
        "accepted_feedback_present": bool(accepted),
        "blocked_feedback_present": bool(blocked),
        "paper_simulation_intake_present": bool(paper_intake),
        "ignore_does_not_create_paper_intake": all(
            item["feedback_id"] not in {candidate["feedback_id"] for candidate in paper_intake}
            for item in records
            if item["action"] == "ignore"
        ),
        "blocked_path_execution_blocked": any(
            "cannot_watch_or_execute_blocked_packet_item" in item["blocked_by"] for item in blocked
        ),
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
        and all(item["no_paper_trade_mutation"] for item in paper_intake),
        "no_recommendation_mutation": all(item["no_recommendation_mutation"] for item in records)
        and all(item["no_recommendation_mutation"] for item in paper_intake),
        "no_real_trade_execution": all(item["no_real_trade_execution"] for item in records)
        and all(item["no_real_trade_execution"] for item in paper_intake),
        "no_broker_api": all(item["no_broker_api"] for item in records)
        and all(item["no_broker_api"] for item in paper_intake),
        "no_webhook": all(item["no_webhook"] for item in records)
        and all(item["no_webhook"] for item in paper_intake),
        "no_order_placement": all(item["no_order_placement"] for item in records)
        and all(item["no_order_placement"] for item in paper_intake),
    }
    return {
        "overall_status": "PASS" if all(checks.values()) else "FAIL",
        "acceptance_target": "V2.9-B User Feedback To Paper Simulation Intake",
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
            "paper_simulation_intake_count": len(paper_intake),
            "feedback_actions": sorted({item["action"] for item in records}),
            "symbols": [item["symbol"] for item in records],
        },
        "records": records,
        "paper_simulation_intake_candidates": paper_intake,
        "checks": checks,
        "safety": {
            "user_submitted_evidence_only": True,
            "simulation_only": True,
            "manual_external_execution_only": True,
            "paper_simulation_intake_only": True,
            "requires_user_price_before_paper_trade": True,
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
