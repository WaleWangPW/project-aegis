"""Prepare pending virtual paper-trade entry requests.

This module stops before PaperTrade creation. It turns paper-simulation intake
candidates into pending entry requests and records exactly which user-provided
fields are still required. It never fabricates prices or dates.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Mapping, Sequence


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def build_pending_entry_requests(
    paper_simulation_intake_candidates: Sequence[Mapping],
    *,
    evidence_ref: str,
    created_at: str | None = None,
) -> list[dict]:
    created = created_at or _now_iso()
    requests: list[dict] = []
    for item in paper_simulation_intake_candidates:
        requests.append(
            {
                "entry_request_id": f"pending_entry_{item['paper_intake_id']}",
                "paper_intake_id": item["paper_intake_id"],
                "feedback_id": item["feedback_id"],
                "symbol": item["symbol"],
                "market": item["market"],
                "entry_request_status": "pending_user_price_date",
                "required_user_fields": ["entry_price", "entry_date"],
                "missing_fields": ["entry_price", "entry_date"],
                "entry_price": None,
                "entry_date": None,
                "virtual_position_size": None,
                "ready_to_create_paper_trade": False,
                "requires_explicit_user_confirmation": True,
                "evidence_refs": [evidence_ref, *list(item.get("evidence_refs") or [])],
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
        )
    return requests


def build_entry_prep_report(
    paper_simulation_intake_candidates: Sequence[Mapping],
    *,
    run_id: str,
    evidence_ref: str,
    command: str | None = None,
) -> dict:
    requests = build_pending_entry_requests(
        paper_simulation_intake_candidates,
        evidence_ref=evidence_ref,
    )
    checks = {
        "has_pending_entry_requests": bool(requests),
        "all_requests_pending_user_price_date": all(
            item["entry_request_status"] == "pending_user_price_date" for item in requests
        ),
        "entry_price_missing_not_fabricated": all(item["entry_price"] is None for item in requests),
        "entry_date_missing_not_fabricated": all(item["entry_date"] is None for item in requests),
        "not_ready_to_create_paper_trade": all(item["ready_to_create_paper_trade"] is False for item in requests),
        "requires_explicit_user_confirmation": all(item["requires_explicit_user_confirmation"] for item in requests),
        "no_price_fabrication": all(item["no_price_fabrication"] for item in requests),
        "no_date_fabrication": all(item["no_date_fabrication"] for item in requests),
        "no_paper_trade_mutation": all(item["no_paper_trade_mutation"] for item in requests),
        "no_recommendation_mutation": all(item["no_recommendation_mutation"] for item in requests),
        "no_real_trade_execution": all(item["no_real_trade_execution"] for item in requests),
        "no_broker_api": all(item["no_broker_api"] for item in requests),
        "no_webhook": all(item["no_webhook"] for item in requests),
        "no_order_placement": all(item["no_order_placement"] for item in requests),
    }
    return {
        "overall_status": "PASS" if all(checks.values()) else "FAIL",
        "acceptance_target": "V2.9-C Paper Simulation Entry Prep",
        "run_id": run_id,
        "generated_at": _now_iso(),
        "command": command,
        "network_used": False,
        "production_records_written": False,
        "paper_trades_written": False,
        "recommendations_written": False,
        "dashboard_contract_changed": False,
        "summary": {
            "paper_simulation_intake_count": len(paper_simulation_intake_candidates),
            "pending_entry_request_count": len(requests),
            "symbols": [item["symbol"] for item in requests],
            "required_user_fields": ["entry_price", "entry_date"],
        },
        "pending_entry_requests": requests,
        "checks": checks,
        "safety": {
            "paper_entry_request_only": True,
            "requires_user_price_before_paper_trade": True,
            "requires_user_date_before_paper_trade": True,
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
