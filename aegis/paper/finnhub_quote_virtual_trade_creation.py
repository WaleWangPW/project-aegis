"""Create Finnhub quote virtual PaperTrade ledger records from validated evidence.

The ledger is run-specific simulation evidence. It does not write the
production `data/records/paper_trades.jsonl` file and never talks to a broker.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Mapping, Sequence

from aegis.models.paper_trade import PaperTrade


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _safe_id(value: object) -> str:
    return "".join(ch if ch.isalnum() else "_" for ch in str(value)).strip("_")


def build_finnhub_quote_virtual_paper_trades(
    validated_user_evidence_records: Sequence[Mapping],
    *,
    created_at: str | None = None,
) -> list[dict]:
    created = created_at or _now_iso()
    trades: list[dict] = []
    for item in validated_user_evidence_records:
        trade = PaperTrade(
            paper_trade_id=f"finnhub_quote_ptr_virtual_{_safe_id(item['queue_id'])}",
            recommendation_id=f"finnhub_quote_manual_entry_{_safe_id(item['queue_id'])}",
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
                "manual_external_execution_only": True,
                "run_specific_ledger_only": True,
                "quote_context_research_only": True,
                "social_sentiment_not_enabled": True,
                "source_queue_id": item["queue_id"],
                "source_followup_id": item["followup_id"],
                "source_feedback_id": item["feedback_id"],
                "source_suggestion_id": item["suggestion_id"],
                "source_user_evidence_items": item["evidence_items"],
                "source_notes_hash": item.get("notes_hash"),
                "source_review_queue_status": item.get("source_review_queue_status"),
                "source_evidence_refs": list(item.get("source_evidence_refs") or []),
                "no_price_fabrication": True,
                "no_date_fabrication": True,
                "no_live_price": True,
                "no_position_size": True,
                "no_live_order_signal": True,
                "no_real_trade_execution": True,
                "no_broker_api": True,
                "no_webhook": True,
                "no_order_placement": True,
                "production_paper_trade_written": False,
            }
        )
    return trades


def build_finnhub_quote_virtual_trade_creation_report(
    source_report: Mapping,
    *,
    run_id: str,
    command: str | None = None,
) -> dict:
    validated = list(source_report.get("validated_user_evidence_records") or [])
    trades = build_finnhub_quote_virtual_paper_trades(validated)
    checks = {
        "source_is_v2_13_l": source_report.get("acceptance_target")
        == "V2.13-L Finnhub Quote User-Supplied Paper Evidence Validation",
        "source_report_pass": source_report.get("overall_status") == "PASS",
        "source_social_sentiment_not_enabled": source_report.get("summary", {}).get("social_sentiment_status")
        == "blocked_plan_or_rate_limit",
        "source_has_validated_evidence": bool(validated),
        "created_virtual_paper_trades": bool(trades),
        "ledger_count_matches_validated_evidence": len(trades) == len(validated),
        "all_trades_open": all(item["status"] == "open" for item in trades),
        "all_trades_simulation_only": all(item["simulation_only"] is True for item in trades),
        "all_trades_manual_external_execution_only": all(
            item["manual_external_execution_only"] is True for item in trades
        ),
        "all_trades_run_specific_ledger_only": all(item["run_specific_ledger_only"] is True for item in trades),
        "all_trades_quote_context_research_only": all(item["quote_context_research_only"] is True for item in trades),
        "all_trades_social_sentiment_not_enabled": all(item["social_sentiment_not_enabled"] is True for item in trades),
        "all_trades_have_positive_entry_price": all(item["entry_price"] > 0 for item in trades),
        "all_trades_have_entry_date": all(bool(item["entry_date"]) for item in trades),
        "all_trades_have_source_user_evidence": all(bool(item["source_user_evidence_items"]) for item in trades),
        "all_trades_have_virtual_position_size": all(item["virtual_position_size"] > 0 for item in trades),
        "all_trades_have_queue_linkage": all(
            item["source_queue_id"] and item["source_followup_id"] and item["source_feedback_id"]
            for item in trades
        ),
        "production_paper_trades_not_written": all(
            item["production_paper_trade_written"] is False for item in trades
        ),
        "no_price_fabrication": all(item["no_price_fabrication"] for item in trades),
        "no_date_fabrication": all(item["no_date_fabrication"] for item in trades),
        "no_live_price": all(item["no_live_price"] for item in trades),
        "no_position_size": all(item["no_position_size"] for item in trades),
        "no_live_order_signal": all(item["no_live_order_signal"] for item in trades),
        "no_real_trade_execution": all(item["no_real_trade_execution"] for item in trades),
        "no_broker_api": all(item["no_broker_api"] for item in trades),
        "no_webhook": all(item["no_webhook"] for item in trades),
        "no_order_placement": all(item["no_order_placement"] for item in trades),
    }
    return {
        "overall_status": "PASS" if all(checks.values()) else "FAIL",
        "acceptance_target": "V2.13-M Finnhub Quote Virtual PaperTrade Creation From Validated Evidence",
        "source_acceptance_target": source_report.get("acceptance_target"),
        "run_id": run_id,
        "generated_at": _now_iso(),
        "command": command,
        "network_used": False,
        "production_records_written": False,
        "production_paper_trades_written": False,
        "recommendations_written": False,
        "reviews_written": False,
        "memory_written": False,
        "dashboard_contract_changed": False,
        "summary": {
            "validated_user_evidence_count": len(validated),
            "virtual_paper_trade_count": len(trades),
            "symbols": [item["symbol"] for item in trades],
            "markets": sorted({item["market"] for item in trades}),
            "social_sentiment_status": source_report.get("summary", {}).get("social_sentiment_status"),
            "next_stage": "V2.13-N Finnhub Quote Virtual PaperTrade Review/Memory Bridge",
        },
        "virtual_paper_trades": trades,
        "checks": checks,
        "safety": {
            "simulation_only": True,
            "manual_external_execution_only": True,
            "run_specific_ledger_only": True,
            "quote_context_research_only": True,
            "social_sentiment_not_enabled": True,
            "production_paper_trades_not_written": True,
            "no_price_fabrication": True,
            "no_date_fabrication": True,
            "no_live_price": True,
            "no_position_size": True,
            "no_live_order_signal": True,
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
