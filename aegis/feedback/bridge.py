"""Bridge accepted manual feedback into review/memory evidence candidates."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Mapping, Sequence


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def _accepted_records(feedback_report: Mapping) -> list[Mapping]:
    return [item for item in feedback_report.get("records", []) if item.get("feedback_status") == "accepted"]


def build_feedback_review_evidence_links(
    feedback_report: Mapping,
    *,
    evidence_ref: str,
    created_at: str | None = None,
) -> list[dict]:
    created = created_at or _now_iso()
    links: list[dict] = []
    for record in _accepted_records(feedback_report):
        links.append(
            {
                "link_id": f"feedback_review_link_{record['feedback_id']}",
                "feedback_id": record["feedback_id"],
                "suggestion_id": record["suggestion_id"],
                "symbol": record["symbol"],
                "market": record["market"],
                "feedback_type": record["feedback_type"],
                "review_input_status": "candidate_evidence",
                "review_use": "manual_user_feedback_context",
                "evidence_refs": [evidence_ref, *list(record.get("evidence_refs") or [])],
                "screenshot_evidence": record.get("screenshot_evidence") or [],
                "created_at": created,
                "user_submitted_evidence_only": True,
                "no_review_record_mutation": True,
                "no_paper_trade_mutation": True,
                "no_recommendation_mutation": True,
            }
        )
    return links


def build_feedback_memory_candidates(
    feedback_report: Mapping,
    *,
    evidence_ref: str,
    created_at: str | None = None,
) -> list[dict]:
    created = created_at or _now_iso()
    candidates: list[dict] = []
    for record in _accepted_records(feedback_report):
        lesson = (
            f"{record['symbol']}（{record['market']}）：用户回传 `{record['feedback_type']}` 反馈，"
            "可作为后续复盘上下文，但不能自动改变策略或交易状态。"
        )
        candidates.append(
            {
                "memory_candidate_id": f"feedback_memory_candidate_{record['feedback_id']}",
                "source_type": "manual_feedback",
                "feedback_id": record["feedback_id"],
                "suggestion_id": record["suggestion_id"],
                "symbol": record["symbol"],
                "market": record["market"],
                "lesson_type": "user_feedback_context",
                "lesson": lesson,
                "tags": ["manual_feedback", record["feedback_type"], record["market"]],
                "confidence": 0.5,
                "evidence_refs": [evidence_ref, *list(record.get("evidence_refs") or [])],
                "created_at": created,
                "requires_review_before_memory_write": True,
                "no_memory_jsonl_mutation": True,
                "no_strategy_mutation": True,
            }
        )
    return candidates


def build_feedback_bridge_report(
    feedback_report: Mapping,
    *,
    run_id: str,
    evidence_ref: str,
    command: str | None = None,
) -> dict:
    review_links = build_feedback_review_evidence_links(feedback_report, evidence_ref=evidence_ref)
    memory_candidates = build_feedback_memory_candidates(feedback_report, evidence_ref=evidence_ref)
    accepted_count = len(_accepted_records(feedback_report))
    checks = {
        "has_accepted_feedback": accepted_count > 0,
        "review_links_for_each_accepted_feedback": len(review_links) == accepted_count,
        "memory_candidates_for_each_accepted_feedback": len(memory_candidates) == accepted_count,
        "all_review_links_are_evidence_only": all(item["user_submitted_evidence_only"] for item in review_links),
        "memory_candidates_require_review": all(
            item["requires_review_before_memory_write"] for item in memory_candidates
        ),
        "no_review_record_mutation": all(item["no_review_record_mutation"] for item in review_links),
        "no_memory_jsonl_mutation": all(item["no_memory_jsonl_mutation"] for item in memory_candidates),
        "no_paper_trade_mutation": all(item["no_paper_trade_mutation"] for item in review_links),
        "no_recommendation_mutation": all(item["no_recommendation_mutation"] for item in review_links),
        "no_strategy_mutation": all(item["no_strategy_mutation"] for item in memory_candidates),
    }
    return {
        "overall_status": "PASS" if all(checks.values()) else "FAIL",
        "acceptance_target": "V2.6-C Feedback To Review/Memory Bridge",
        "run_id": run_id,
        "generated_at": _now_iso(),
        "command": command,
        "network_used": False,
        "production_records_written": False,
        "reviews_written": False,
        "memory_records_written": False,
        "paper_trades_written": False,
        "recommendations_written": False,
        "dashboard_contract_changed": False,
        "summary": {
            "accepted_feedback_count": accepted_count,
            "review_link_count": len(review_links),
            "memory_candidate_count": len(memory_candidates),
            "symbols": [item["symbol"] for item in review_links],
        },
        "review_evidence_links": review_links,
        "memory_candidates": memory_candidates,
        "checks": checks,
        "safety": {
            "user_submitted_evidence_only": True,
            "simulation_only": True,
            "manual_external_execution_only": True,
            "no_real_trade_execution": True,
            "no_broker_api": True,
            "no_webhook": True,
            "no_order_placement": True,
            "no_review_record_mutation": True,
            "no_memory_jsonl_mutation": True,
            "no_paper_trade_mutation": True,
            "no_recommendation_mutation": True,
            "no_strategy_mutation": True,
            "dashboard_contract_unchanged": True,
        },
    }
