"""Build a pending review queue from H/US simulation feedback follow-ups.

The queue is an evidence checklist for later virtual paper-trade work. It does
not create PaperTrade, Recommendation, Review, or Memory records.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Mapping, Sequence


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def build_h_us_feedback_review_queue(
    simulation_followup_candidates: Sequence[Mapping],
    *,
    evidence_ref: str,
    created_at: str | None = None,
) -> list[dict]:
    created = created_at or _now_iso()
    queue: list[dict] = []
    for item in simulation_followup_candidates:
        queue.append(
            {
                "queue_id": f"h_us_review_queue_{item['followup_id']}",
                "followup_id": item["followup_id"],
                "feedback_id": item["feedback_id"],
                "suggestion_id": item["suggestion_id"],
                "symbol": item["symbol"],
                "market": item["market"],
                "queue_status": "pending_user_price_date_evidence",
                "followup_action": item["followup_action"],
                "required_user_fields": [
                    "entry_price",
                    "entry_date",
                    "evidence_ref_or_screenshot",
                    "explicit_simulation_confirmation",
                ],
                "missing_fields": [
                    "entry_price",
                    "entry_date",
                    "evidence_ref_or_screenshot",
                    "explicit_simulation_confirmation",
                ],
                "entry_price": None,
                "entry_date": None,
                "evidence_ref_or_screenshot": None,
                "explicit_simulation_confirmation": False,
                "ready_for_user_supplied_entry_validation": False,
                "ready_to_create_paper_trade": False,
                "requires_user_price_before_paper_trade": True,
                "requires_user_entry_date_before_paper_trade": True,
                "requires_user_evidence_before_paper_trade": True,
                "requires_explicit_review_before_paper_trade": True,
                "requires_explicit_simulation_confirmation": True,
                "evidence_refs": [evidence_ref, *list(item.get("evidence_refs") or [])],
                "created_at": created,
                "simulation_only": True,
                "manual_external_execution_only": True,
                "review_queue_only": True,
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
        )
    return queue


def build_h_us_feedback_review_queue_report(
    source_report: Mapping,
    *,
    run_id: str,
    evidence_ref: str,
    command: str | None = None,
) -> dict:
    followups = list(source_report.get("simulation_followup_candidates") or [])
    queue = build_h_us_feedback_review_queue(followups, evidence_ref=evidence_ref)
    feedback_ids = {item.get("feedback_id") for item in queue}
    checks = {
        "source_is_v2_12_g": source_report.get("acceptance_target")
        == "V2.12-G H-US User Feedback Intake For Simulation Brief",
        "source_report_pass": source_report.get("overall_status") == "PASS",
        "source_has_followups": bool(followups),
        "queue_count_matches_followups": len(queue) == len(followups),
        "queue_items_unique": len({item["queue_id"] for item in queue}) == len(queue),
        "queue_only_accepted_followup_feedback": all(
            item.get("feedback_id") in feedback_ids for item in followups
        ),
        "all_items_pending_user_price_date_evidence": all(
            item["queue_status"] == "pending_user_price_date_evidence" for item in queue
        ),
        "all_items_require_user_price": all(
            item["requires_user_price_before_paper_trade"] for item in queue
        ),
        "all_items_require_entry_date": all(
            item["requires_user_entry_date_before_paper_trade"] for item in queue
        ),
        "all_items_require_user_evidence": all(
            item["requires_user_evidence_before_paper_trade"] for item in queue
        ),
        "all_items_require_explicit_review": all(
            item["requires_explicit_review_before_paper_trade"] for item in queue
        ),
        "all_items_require_explicit_simulation_confirmation": all(
            item["requires_explicit_simulation_confirmation"] for item in queue
        ),
        "entry_price_not_fabricated": all(item["entry_price"] is None for item in queue),
        "entry_date_not_fabricated": all(item["entry_date"] is None for item in queue),
        "not_ready_to_create_paper_trade": all(
            item["ready_to_create_paper_trade"] is False for item in queue
        ),
        "evidence_refs_present": all(item["evidence_refs"] for item in queue),
        "no_paper_trade_mutation": all(item["no_paper_trade_mutation"] for item in queue),
        "no_recommendation_mutation": all(item["no_recommendation_mutation"] for item in queue),
        "no_review_mutation": all(item["no_review_mutation"] for item in queue),
        "no_memory_mutation": all(item["no_memory_mutation"] for item in queue),
        "no_real_trade_execution": all(item["no_real_trade_execution"] for item in queue),
        "no_broker_api": all(item["no_broker_api"] for item in queue),
        "no_webhook": all(item["no_webhook"] for item in queue),
        "no_order_placement": all(item["no_order_placement"] for item in queue),
    }
    return {
        "overall_status": "PASS" if all(checks.values()) else "FAIL",
        "acceptance_target": "V2.12-H H-US Feedback To Paper Simulation Review Queue",
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
            "source_feedback_count": source_report.get("summary", {}).get("feedback_count"),
            "source_simulation_followup_count": len(followups),
            "review_queue_count": len(queue),
            "pending_user_price_date_evidence_count": len(queue),
            "symbols": [item["symbol"] for item in queue],
            "markets": sorted({item["market"] for item in queue}),
            "required_user_fields": [
                "entry_price",
                "entry_date",
                "evidence_ref_or_screenshot",
                "explicit_simulation_confirmation",
            ],
            "next_stage": "V2.12-I H-US User-Supplied Paper Evidence Validation",
        },
        "review_queue": queue,
        "checks": checks,
        "safety": {
            "simulation_only": True,
            "manual_external_execution_only": True,
            "review_queue_only": True,
            "requires_user_price_before_paper_trade": True,
            "requires_user_entry_date_before_paper_trade": True,
            "requires_user_evidence_before_paper_trade": True,
            "requires_explicit_review_before_paper_trade": True,
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
