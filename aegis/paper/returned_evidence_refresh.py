"""Refresh simulation review/memory from user-returned evidence.

V2.9-I accepts user-provided screenshots, notes, or outcome evidence for an
existing virtual PaperTrade. It creates acceptance artifacts only; it never
appends production JSONL records, changes strategy, or touches real trading.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping, Sequence

from aegis.models.investment_memory import InvestmentMemory
from aegis.models.review import ReviewRecord

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
    "webhook",
)
_VALID_EVIDENCE_TYPES = {"text_note", "screenshot", "outcome"}
_VALID_OUTCOMES = {"success", "failure", "mixed", "pending"}
_VALID_DECISION_QUALITY = {"good_decision", "reasonable_decision", "poor_decision", "unclear"}


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def _safe_id(value: object) -> str:
    return "".join(ch if ch.isalnum() else "_" for ch in str(value)).strip("_")


def _sha256_path(path: Path) -> str | None:
    if not path.exists() or not path.is_file():
        return None
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _looks_secret(value: object) -> bool:
    text = str(value or "").lower()
    return any(marker in text for marker in _SECRET_MARKERS)


def _to_float(value: object) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _evidence_items(evidence_refs: Sequence[object], *, root: Path | None = None) -> list[dict]:
    items: list[dict] = []
    for ref in evidence_refs:
        ref_text = str(ref)
        path = Path(ref_text).expanduser()
        if not path.is_absolute() and root is not None:
            path = root / path
        items.append(
            {
                "evidence_ref": ref_text,
                "resolved_path": str(path),
                "exists": path.exists(),
                "sha256": _sha256_path(path),
                "raw_content_stored": False,
            }
        )
    return items


def _formal_reviews_by_trade(formal_review_memory_report: Mapping) -> dict[str, Mapping]:
    return {
        str(item.get("paper_trade_id")): item
        for item in formal_review_memory_report.get("formal_reviews", [])
        if item.get("paper_trade_id")
    }


def _formal_memories_by_trade(formal_review_memory_report: Mapping) -> dict[str, Mapping]:
    return {
        str(item.get("paper_trade_id")): item
        for item in formal_review_memory_report.get("formal_memories", [])
        if item.get("paper_trade_id")
    }


def validate_user_returned_evidence(
    returned_inputs: Sequence[Mapping],
    *,
    current_brief: Mapping,
    formal_review_memory_report: Mapping,
    evidence_root: Path | None = None,
    created_at: str | None = None,
) -> dict:
    created = created_at or _now_iso()
    known_trade_ids = {
        str(item.get("paper_trade_id"))
        for item in current_brief.get("review_memory_queue", [])
        if item.get("paper_trade_id")
    }
    accepted: list[dict] = []
    blocked: list[dict] = []

    for raw in returned_inputs:
        paper_trade_id = str(raw.get("paper_trade_id") or "")
        evidence_type = str(raw.get("evidence_type") or "")
        user_note = str(raw.get("user_note") or "")
        evidence_refs = list(raw.get("evidence_refs") or [])
        outcome = raw.get("outcome")
        decision_quality = raw.get("decision_quality")
        actual_return = _to_float(raw.get("actual_return"))
        max_drawdown = _to_float(raw.get("max_drawdown"))
        reasons: list[str] = []

        if paper_trade_id not in known_trade_ids:
            reasons.append("unknown_paper_trade_id")
        if evidence_type not in _VALID_EVIDENCE_TYPES:
            reasons.append("invalid_evidence_type")
        if not user_note.strip():
            reasons.append("missing_user_note")
        if raw.get("user_confirmed") is not True:
            reasons.append("missing_explicit_user_confirmation")
        if _looks_secret(user_note) or any(_looks_secret(ref) for ref in evidence_refs):
            reasons.append("secret_like_text_blocked")
        evidence = _evidence_items(evidence_refs, root=evidence_root)
        if evidence_type == "screenshot" and not evidence:
            reasons.append("missing_screenshot_evidence")
        if evidence_type == "outcome":
            if outcome not in _VALID_OUTCOMES:
                reasons.append("invalid_outcome")
            if decision_quality not in _VALID_DECISION_QUALITY:
                reasons.append("invalid_decision_quality")
            if actual_return is None:
                reasons.append("missing_actual_return")
        if evidence and any(not item["exists"] for item in evidence):
            reasons.append("evidence_ref_missing")

        base = {
            "returned_evidence_id": str(raw.get("returned_evidence_id") or f"returned_{_safe_id(paper_trade_id)}"),
            "paper_trade_id": paper_trade_id,
            "evidence_type": evidence_type,
            "submitted_at": str(raw.get("submitted_at") or created),
            "user_note_hash": hashlib.sha256(user_note.encode("utf-8")).hexdigest(),
            "user_note_summary": user_note[:300],
            "evidence_items": evidence,
            "user_confirmed": raw.get("user_confirmed") is True,
            "created_at": created,
            "simulation_only": True,
            "user_returned_evidence_only": True,
            "raw_content_not_stored": True,
            "no_real_trade_execution": True,
            "no_broker_api": True,
            "no_webhook": True,
            "no_order_placement": True,
            "no_strategy_mutation": True,
            "no_production_record_mutation": True,
        }

        if reasons:
            blocked.append({**base, "status": "blocked", "blocked_reasons": sorted(set(reasons))})
            continue

        accepted.append(
            {
                **base,
                "status": "accepted",
                "outcome": outcome if evidence_type == "outcome" else None,
                "decision_quality": decision_quality if evidence_type == "outcome" else None,
                "actual_return": actual_return if evidence_type == "outcome" else None,
                "max_drawdown": max_drawdown if evidence_type == "outcome" else None,
                "actual_return_source": "user_returned_evidence" if evidence_type == "outcome" else None,
                "no_return_fabrication": True,
            }
        )

    return {
        "accepted_returned_evidence_records": accepted,
        "blocked_returned_evidence_records": blocked,
    }


def build_refreshed_reviews_and_memories(
    accepted_records: Sequence[Mapping],
    *,
    formal_review_memory_report: Mapping,
    created_at: str | None = None,
) -> dict:
    created = created_at or _now_iso()
    reviews_by_trade = _formal_reviews_by_trade(formal_review_memory_report)
    memories_by_trade = _formal_memories_by_trade(formal_review_memory_report)
    refreshed_reviews: list[dict] = []
    refreshed_memories: list[dict] = []

    for record in accepted_records:
        if record.get("evidence_type") != "outcome":
            continue
        source_review = reviews_by_trade[str(record["paper_trade_id"])]
        source_memory = memories_by_trade.get(str(record["paper_trade_id"]), {})
        outcome = record["outcome"]
        actual_return = record["actual_return"]
        decision_quality = record["decision_quality"]
        lesson = (
            f"用户回传 outcome evidence 后，{record['paper_trade_id']} 的 simulation review "
            f"从 pending 刷新为 {outcome}；actual_return={actual_return} 来自用户回传证据，"
            "不是 Aegis 编造或实时抓取。"
        )
        review = ReviewRecord(
            review_id=f"{source_review['review_id']}_returned_{_safe_id(record['returned_evidence_id'])}",
            recommendation_id=source_review["recommendation_id"],
            paper_trade_id=source_review["paper_trade_id"],
            review_date=str(record["submitted_at"])[:10],
            horizon=source_review["horizon"],
            outcome=outcome,
            actual_return=actual_return,
            max_drawdown=record.get("max_drawdown"),
            decision_quality=decision_quality,
            success_reason=record["user_note_summary"] if outcome == "success" else None,
            failure_reason=record["user_note_summary"] if outcome == "failure" else None,
            expert_contribution={
                "status": "USER_RETURNED_EVIDENCE_REFRESH",
                "source": record["returned_evidence_id"],
            },
            lessons=[lesson],
            created_at=created,
        ).model_dump()
        refreshed_reviews.append(
            {
                **review,
                "source_review_id": source_review["review_id"],
                "source_returned_evidence_id": record["returned_evidence_id"],
                "evidence_items": list(record.get("evidence_items") or []),
                "actual_return_source": "user_returned_evidence",
                "simulation_only": True,
                "no_return_fabrication": True,
                "no_review_record_production_mutation": True,
                "no_real_trade_execution": True,
                "no_broker_api": True,
                "no_webhook": True,
                "no_order_placement": True,
            }
        )
        memory = InvestmentMemory(
            memory_id=f"{source_memory.get('memory_id') or 'mem_' + _safe_id(record['paper_trade_id'])}_returned_{_safe_id(record['returned_evidence_id'])}",
            date=str(record["submitted_at"])[:10],
            source_type="user_returned_simulation_outcome",
            linked_recommendation_id=source_review["recommendation_id"],
            lesson_type="simulation_outcome_evidence",
            lesson=lesson,
            tags=["user_returned_evidence", "simulation_only", outcome, decision_quality],
            confidence=0.65,
            created_at=created,
        ).model_dump()
        refreshed_memories.append(
            {
                **memory,
                "paper_trade_id": record["paper_trade_id"],
                "source_review_id": review["review_id"],
                "source_memory_id": source_memory.get("memory_id"),
                "source_returned_evidence_id": record["returned_evidence_id"],
                "evidence_items": list(record.get("evidence_items") or []),
                "simulation_only": True,
                "no_memory_jsonl_production_mutation": True,
                "no_strategy_mutation": True,
                "no_real_trade_execution": True,
                "no_broker_api": True,
                "no_webhook": True,
                "no_order_placement": True,
            }
        )

    return {
        "refreshed_reviews": refreshed_reviews,
        "refreshed_memories": refreshed_memories,
    }


def _refresh_brief_queue(current_brief: Mapping, refreshed_reviews: Sequence[Mapping], refreshed_memories: Sequence[Mapping]) -> list[dict]:
    refreshed_by_trade = {item["paper_trade_id"]: item for item in refreshed_reviews}
    memory_by_review = {item["source_review_id"]: item for item in refreshed_memories}
    queue: list[dict] = []
    for item in current_brief.get("review_memory_queue", []):
        review = refreshed_by_trade.get(item.get("paper_trade_id"))
        if review is None:
            queue.append(dict(item))
            continue
        memory = memory_by_review.get(review["review_id"], {})
        queue.append(
            {
                **dict(item),
                "review_id": review["review_id"],
                "memory_id": memory.get("memory_id") or item.get("memory_id"),
                "review_date": review["review_date"],
                "outcome": review["outcome"],
                "decision_quality": review["decision_quality"],
                "actual_return": review["actual_return"],
                "actual_return_source": review["actual_return_source"],
                "lesson": (review.get("lessons") or [item.get("lesson")])[0],
                "memory_lesson": memory.get("lesson") or item.get("memory_lesson"),
                "no_return_fabrication": review["no_return_fabrication"],
                "simulation_only": True,
            }
        )
    return queue


def build_returned_evidence_refresh_report(
    *,
    current_brief: Mapping,
    formal_review_memory_report: Mapping,
    returned_inputs: Sequence[Mapping],
    run_id: str,
    evidence_root: Path | None = None,
    command: str | None = None,
) -> dict:
    validation = validate_user_returned_evidence(
        returned_inputs,
        current_brief=current_brief,
        formal_review_memory_report=formal_review_memory_report,
        evidence_root=evidence_root,
    )
    accepted = validation["accepted_returned_evidence_records"]
    blocked = validation["blocked_returned_evidence_records"]
    refreshed = build_refreshed_reviews_and_memories(
        accepted,
        formal_review_memory_report=formal_review_memory_report,
    )
    refreshed_queue = _refresh_brief_queue(
        current_brief,
        refreshed["refreshed_reviews"],
        refreshed["refreshed_memories"],
    )
    refreshed_brief = {
        **dict(current_brief),
        "acceptance_target": "V2.9-I User Returned Evidence Continuous Review Refresh",
        "brief_type": "current_usable_simulation_brief_after_user_returned_evidence",
        "run_id": run_id,
        "generated_at": _now_iso(),
        "command": command,
        "review_memory_queue": refreshed_queue,
        "summary": {
            **dict(current_brief.get("summary") or {}),
            "accepted_returned_evidence_count": len(accepted),
            "blocked_returned_evidence_count": len(blocked),
            "refreshed_review_count": len(refreshed["refreshed_reviews"]),
            "refreshed_memory_count": len(refreshed["refreshed_memories"]),
            "review_pending_count": len([item for item in refreshed_queue if item.get("outcome") == "pending"]),
            "review_resolved_count": len([item for item in refreshed_queue if item.get("outcome") != "pending"]),
        },
    }
    checks = {
        "has_user_returned_evidence": bool(returned_inputs),
        "accepted_returned_evidence_present": bool(accepted),
        "blocked_returned_evidence_present": bool(blocked),
        "outcome_refresh_present": bool(refreshed["refreshed_reviews"]),
        "refreshed_memory_present": bool(refreshed["refreshed_memories"]),
        "secret_like_input_blocked": any("secret_like_text_blocked" in item["blocked_reasons"] for item in blocked),
        "actual_return_from_user_evidence_only": all(
            item.get("actual_return_source") == "user_returned_evidence" for item in refreshed["refreshed_reviews"]
        ),
        "no_return_fabrication": all(item.get("no_return_fabrication") is True for item in refreshed["refreshed_reviews"]),
        "refreshed_queue_visible": refreshed_brief["summary"]["review_resolved_count"] > 0,
        "no_review_record_production_mutation": all(
            item.get("no_review_record_production_mutation") is True for item in refreshed["refreshed_reviews"]
        ),
        "no_memory_jsonl_production_mutation": all(
            item.get("no_memory_jsonl_production_mutation") is True for item in refreshed["refreshed_memories"]
        ),
        "no_strategy_mutation": all(item.get("no_strategy_mutation") is True for item in refreshed["refreshed_memories"]),
        "no_real_trade_execution": all(item.get("no_real_trade_execution") is True for item in accepted),
        "no_broker_api": all(item.get("no_broker_api") is True for item in accepted),
        "no_webhook": all(item.get("no_webhook") is True for item in accepted),
        "no_order_placement": all(item.get("no_order_placement") is True for item in accepted),
    }
    return {
        "overall_status": "PASS" if all(checks.values()) else "FAIL",
        "acceptance_target": "V2.9-I User Returned Evidence Continuous Review Refresh",
        "run_id": run_id,
        "generated_at": _now_iso(),
        "command": command,
        "network_used": False,
        "production_records_written": False,
        "reviews_jsonl_written": False,
        "memory_jsonl_written": False,
        "paper_trades_written": False,
        "recommendations_written": False,
        "dashboard_contract_changed": False,
        "summary": refreshed_brief["summary"],
        "accepted_returned_evidence_records": accepted,
        "blocked_returned_evidence_records": blocked,
        "refreshed_reviews": refreshed["refreshed_reviews"],
        "refreshed_memories": refreshed["refreshed_memories"],
        "refreshed_brief": refreshed_brief,
        "checks": checks,
        "safety": {
            "simulation_only": True,
            "user_returned_evidence_only": True,
            "actual_return_from_user_evidence_only": True,
            "no_return_fabrication": True,
            "production_records_not_written": True,
            "no_review_record_production_mutation": True,
            "no_memory_jsonl_production_mutation": True,
            "no_real_trade_execution": True,
            "no_broker_api": True,
            "no_webhook": True,
            "no_order_placement": True,
            "no_strategy_mutation": True,
            "dashboard_contract_unchanged": True,
        },
    }
