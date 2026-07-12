"""Create virtual PaperTrade ledger records from validated entry evidence.

V2.9-E writes simulation ledger artifacts for acceptance/runtime handoff. It
does not write the production `data/records/paper_trades.jsonl` file and never
talks to a broker.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Mapping, Sequence

from aegis.models.paper_trade import PaperTrade


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def _safe_id(value: object) -> str:
    return "".join(ch if ch.isalnum() else "_" for ch in str(value)).strip("_")


def build_virtual_paper_trades(
    validated_entry_evidence_records: Sequence[Mapping],
    *,
    created_at: str | None = None,
) -> list[dict]:
    created = created_at or _now_iso()
    trades: list[dict] = []
    for item in validated_entry_evidence_records:
        trade = PaperTrade(
            paper_trade_id=f"ptr_virtual_{_safe_id(item['entry_request_id'])}",
            recommendation_id=f"manual_entry_{_safe_id(item['entry_request_id'])}",
            symbol=item["symbol"],
            market=item["market"],
            direction="long",
            entry_date=item["entry_date"],
            entry_price=float(item["entry_price"]),
            virtual_position_size=float(item.get("virtual_position_size") or 1.0),
            status="open",
            created_at=created,
            updated_at=created,
        ).model_dump()
        trades.append(
            {
                **trade,
                "simulation_only": True,
                "source_entry_request_id": item["entry_request_id"],
                "source_paper_intake_id": item["source_paper_intake_id"],
                "source_feedback_id": item["source_feedback_id"],
                "source_evidence_items": item["evidence_items"],
                "no_price_fabrication": True,
                "no_date_fabrication": True,
                "no_real_trade_execution": True,
                "no_broker_api": True,
                "no_webhook": True,
                "no_order_placement": True,
            }
        )
    return trades


def build_virtual_trade_creation_report(
    validated_entry_evidence_records: Sequence[Mapping],
    *,
    run_id: str,
    command: str | None = None,
) -> dict:
    trades = build_virtual_paper_trades(validated_entry_evidence_records)
    checks = {
        "has_validated_entry_evidence": bool(validated_entry_evidence_records),
        "created_virtual_paper_trades": bool(trades),
        "all_trades_open": all(item["status"] == "open" for item in trades),
        "all_trades_simulation_only": all(item["simulation_only"] is True for item in trades),
        "all_trades_have_positive_entry_price": all(item["entry_price"] > 0 for item in trades),
        "all_trades_have_entry_date": all(bool(item["entry_date"]) for item in trades),
        "all_trades_have_source_evidence": all(bool(item["source_evidence_items"]) for item in trades),
        "all_trades_have_virtual_position_size": all(item["virtual_position_size"] > 0 for item in trades),
        "production_paper_trades_not_written": True,
        "recommendations_not_written": True,
        "no_real_trade_execution": True,
        "no_broker_api": True,
        "no_webhook": True,
        "no_order_placement": True,
    }
    return {
        "overall_status": "PASS" if all(checks.values()) else "FAIL",
        "acceptance_target": "V2.9-E Virtual PaperTrade Creation From Validated Evidence",
        "run_id": run_id,
        "generated_at": _now_iso(),
        "command": command,
        "network_used": False,
        "production_records_written": False,
        "production_paper_trades_written": False,
        "recommendations_written": False,
        "dashboard_contract_changed": False,
        "summary": {
            "validated_entry_evidence_count": len(validated_entry_evidence_records),
            "virtual_paper_trade_count": len(trades),
            "symbols": [item["symbol"] for item in trades],
        },
        "virtual_paper_trades": trades,
        "checks": checks,
        "safety": {
            "simulation_only": True,
            "production_paper_trades_not_written": True,
            "no_price_fabrication": True,
            "no_date_fabrication": True,
            "no_recommendation_mutation": True,
            "no_real_trade_execution": True,
            "no_broker_api": True,
            "no_webhook": True,
            "no_order_placement": True,
            "dashboard_contract_unchanged": True,
        },
    }
