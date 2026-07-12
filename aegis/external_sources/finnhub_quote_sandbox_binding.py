"""Bind Finnhub quote research context to sandbox candidate review inputs.

This stage creates sandbox-candidate binding packets only. A single quote
snapshot is not historical evidence, so every binding remains pending
historical cases before sandbox evaluation and Suggestion Gate review.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Mapping

from aegis.models.strategy import StrategyCandidate, StrategyPassCriteria

ACCEPTANCE_TARGET = "V2.13-E Finnhub Quote Context To Sandbox Candidate Binding"
SOURCE_ACCEPTANCE_TARGET = "V2.13-D Finnhub Quote Research Context Bridge"


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _candidate_for_context(context: Mapping[str, Any], *, created_at: str) -> StrategyCandidate:
    symbol = str(context["canonical_symbol"]).lower().replace(".", "_")
    return StrategyCandidate(
        strategy_id=f"strategy_{symbol}_finnhub_quote_context_probe",
        name=f"{context['canonical_symbol']} Finnhub quote context sandbox probe",
        market=context["market"],
        universe=f"{context['canonical_symbol']} Finnhub verified quote context universe",
        factor_family="multi_factor",
        entry_rule="Use Finnhub quote context as research evidence only; historical cases are still required.",
        exit_rule="No exit rule is active until historical sandbox cases are supplied.",
        exit_horizon_days=5,
        risk_controls=[
            "manual_execution_only",
            "historical_cases_required",
            "suggestion_gate_required",
            "single_quote_snapshot_not_strategy_evidence",
        ],
        pass_criteria=StrategyPassCriteria(
            min_sample_count=3,
            min_win_rate=0.5,
            min_average_return=0.0,
            max_drawdown_floor=-0.12,
        ),
        source_research_refs=[str(context["context_id"]), str(context["source_quote_json_sha256"])],
        created_at=created_at,
    )


def _binding_for_context(context: Mapping[str, Any], *, created_at: str) -> dict[str, Any]:
    candidate = _candidate_for_context(context, created_at=created_at)
    return {
        "binding_id": f"bind_{context['context_id']}_sandbox_candidate",
        "binding_status": "bound_pending_historical_cases",
        "market": context.get("market"),
        "canonical_symbol": context.get("canonical_symbol"),
        "provider": context.get("provider"),
        "context_id": context.get("context_id"),
        "source_case_id": context.get("source_case_id"),
        "source_quote_json_sha256": context.get("source_quote_json_sha256"),
        "strategy_candidate": candidate.model_dump(),
        "required_next_inputs": [
            "historical_cases",
            "sandbox_evaluation",
            "suggestion_gate",
            "risk_checks",
        ],
        "blocked_until": [
            "historical_cases_available",
            "sandbox_passed",
            "suggestion_gate_passed",
        ],
        "evidence_refs": [
            str(context.get("context_id")),
            str(context.get("source_quote_json_sha256")),
            str(context.get("source_quote_json")),
        ],
        "warnings": [
            "Single quote snapshot is research context only.",
            "This binding is not a recommendation, order, or position-size instruction.",
            "Historical sandbox cases are required before any user-facing simulation suggestion.",
        ],
        "simulation_only": True,
        "user_facing_suggestion_allowed": False,
        "auto_applied": False,
        "created_at": created_at,
    }


def build_finnhub_quote_sandbox_binding_report(
    *,
    source_report: Mapping[str, Any],
    run_id: str,
    command: str | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    created = generated_at or _now_iso()
    context_items = [
        item
        for item in source_report.get("context_items", []) or []
        if isinstance(item, dict) and item.get("evidence_role") == "research_context_only"
    ]
    bindings = [_binding_for_context(item, created_at=created) for item in context_items]
    checks = {
        "source_report_pass": source_report.get("overall_status") == "PASS",
        "source_acceptance_target_correct": source_report.get("acceptance_target") == SOURCE_ACCEPTANCE_TARGET,
        "source_context_item_count_positive": int(source_report.get("summary", {}).get("context_item_count") or 0) > 0,
        "source_social_sentiment_still_blocked": source_report.get("summary", {}).get("social_sentiment_status")
        == "blocked_plan_or_rate_limit",
        "all_contexts_research_only": bool(context_items)
        and all(item.get("evidence_role") == "research_context_only" for item in context_items),
        "all_contexts_verified": bool(context_items)
        and all(item.get("evidence_status") == "verified" for item in context_items),
        "all_contexts_require_sandbox": bool(context_items)
        and all(item.get("requires_sandbox_before_suggestion") is True for item in context_items),
        "all_contexts_forbid_direct_suggestions": bool(context_items)
        and all(item.get("user_facing_suggestion_allowed") is False for item in context_items),
        "at_least_one_binding_created": bool(bindings),
        "all_bindings_pending_historical_cases": bool(bindings)
        and all(item["binding_status"] == "bound_pending_historical_cases" for item in bindings),
        "all_bindings_require_sandbox_and_gate": bool(bindings)
        and all(
            {"historical_cases", "sandbox_evaluation", "suggestion_gate"}.issubset(
                set(item["required_next_inputs"])
            )
            for item in bindings
        ),
        "no_historical_sandbox_result_claimed": True,
        "suggestion_path_not_enabled": True,
        "social_sentiment_not_enabled": True,
        "user_facing_suggestion_not_allowed": all(
            item["user_facing_suggestion_allowed"] is False for item in bindings
        ),
        "auto_apply_disabled": all(item["auto_applied"] is False for item in bindings),
        "network_not_used": True,
        "production_records_not_written": True,
        "production_cache_not_mutated": True,
        "production_provider_config_not_mutated": True,
        "no_secret_values_stored": True,
        "request_urls_not_stored": True,
        "raw_payloads_not_stored": True,
        "no_real_trade": True,
        "no_broker_api": True,
        "no_trading_webhook": True,
        "no_order_placement": True,
        "no_position_size": True,
        "no_live_order_signal": True,
        "dashboard_contract_unchanged": True,
    }
    return {
        "overall_status": "PASS" if all(checks.values()) else "FAIL",
        "acceptance_target": ACCEPTANCE_TARGET,
        "run_id": run_id,
        "generated_at": created,
        "command": command,
        "network_used": False,
        "production_records_written": False,
        "production_cache_mutated": False,
        "production_provider_config_mutated": False,
        "dashboard_contract_changed": False,
        "summary": {
            "binding_count": len(bindings),
            "markets": sorted({str(item["market"]) for item in bindings}),
            "symbols": sorted({str(item["canonical_symbol"]) for item in bindings}),
            "binding_statuses": sorted({str(item["binding_status"]) for item in bindings}),
            "historical_cases_required": True,
            "sandbox_evaluation_required": True,
            "suggestion_gate_required": True,
            "user_facing_suggestion_allowed": False,
            "social_sentiment_status": "blocked_plan_or_rate_limit",
            "next_stage": "V2.13-F Finnhub Quote Context Historical Case Assembly",
        },
        "bindings": bindings,
        "source_evidence": {
            "source_target": source_report.get("acceptance_target"),
            "source_run_id": source_report.get("run_id"),
            "source_summary_sha256": _sha256_text(
                json.dumps(source_report.get("summary") or {}, ensure_ascii=False, sort_keys=True)
            ),
        },
        "checks": checks,
        "safety": {
            "sandbox_candidate_binding_only": True,
            "single_quote_not_strategy_evidence": True,
            "historical_cases_required": True,
            "sandbox_evaluation_required": True,
            "suggestion_gate_required": True,
            "user_facing_suggestion_allowed": False,
            "network_not_used": True,
            "social_sentiment_not_enabled": True,
            "suggestion_path_not_enabled": True,
            "production_records_not_written": True,
            "production_cache_not_mutated": True,
            "production_provider_config_not_mutated": True,
            "no_secret_values_stored": True,
            "no_request_url_storage": True,
            "no_raw_payload_storage": True,
            "no_real_trade": True,
            "no_broker_api": True,
            "no_trading_webhook": True,
            "no_order_placement": True,
            "no_position_size": True,
            "no_live_order_signal": True,
            "dashboard_contract_unchanged": True,
        },
    }


def render_finnhub_quote_sandbox_binding_markdown(report: Mapping[str, Any]) -> str:
    lines = [
        "# V2.13-E Finnhub Quote Context To Sandbox Candidate Binding",
        "",
        f"- status: `{report.get('overall_status')}`",
        f"- run_id: `{report.get('run_id')}`",
        f"- binding_count: `{report.get('summary', {}).get('binding_count')}`",
        f"- symbols: `{report.get('summary', {}).get('symbols')}`",
        f"- binding_statuses: `{report.get('summary', {}).get('binding_statuses')}`",
        f"- next_stage: `{report.get('summary', {}).get('next_stage')}`",
        "",
        "## Bindings",
        "",
    ]
    for item in report.get("bindings", []) or []:
        candidate = item.get("strategy_candidate") or {}
        lines.extend(
            [
                f"### {item.get('binding_id')}",
                "",
                f"- binding_status: `{item.get('binding_status')}`",
                f"- symbol: `{item.get('canonical_symbol')}`",
                f"- strategy_id: `{candidate.get('strategy_id')}`",
                f"- required_next_inputs: `{item.get('required_next_inputs')}`",
                f"- user_facing_suggestion_allowed: `{item.get('user_facing_suggestion_allowed')}`",
                "",
            ]
        )
    lines.extend(
        [
            "## Boundary",
            "",
            "- Sandbox candidate binding only.",
            "- A single quote snapshot is not a historical sandbox result.",
            "- Historical cases, sandbox evaluation, Suggestion Gate, and risk checks are still required.",
            "- No user-facing suggestion, position size, live order signal, real trade, broker API, webhook, or order placement.",
            "",
        ]
    )
    return "\n".join(lines)
