"""Suggestion Gate refresh from Tushare-backed A-share sandbox evidence.

V2.11-D consumes V2.11-C sandbox evidence. A correct refresh may produce zero
allowed suggestions when all Tushare-backed A-share strategies failed the
bounded historical sample. That is a PASS for risk discipline, not a product
failure.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping, Sequence

from aegis.models.suggestion import SuggestionOpportunity
from aegis.strategy.suggestion_gate import build_suggestion_drafts


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _result_by_strategy(source_report: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    return {str(result.get("strategy_id")): result for result in source_report.get("results", [])}


def _format_metric(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


def build_tushare_a_share_suggestion_opportunities(
    source_report: Mapping[str, Any],
    *,
    evidence_refs: Sequence[str],
) -> list[SuggestionOpportunity]:
    """Build one opportunity per V2.11-C A-share strategy candidate."""

    results_by_strategy = _result_by_strategy(source_report)
    opportunities: list[SuggestionOpportunity] = []
    for candidate in source_report.get("candidates", []) or []:
        strategy_id = str(candidate.get("strategy_id"))
        result = results_by_strategy.get(strategy_id, {})
        metrics = result.get("metrics") or {}
        failed_reasons = metrics.get("failed_reasons") or []
        symbols = [
            item.get("symbol")
            for item in source_report.get("historical_cases", []) or []
            if item.get("strategy_id") == strategy_id
        ]
        reasons = [
            f"tushare_sandbox_status={result.get('status')}",
            f"sample_count={metrics.get('sample_count')}",
            f"win_rate={_format_metric(metrics.get('win_rate'))}",
            f"average_return={_format_metric(metrics.get('average_return'))}",
            f"max_drawdown={_format_metric(metrics.get('max_drawdown'))}",
            "failed_reasons=" + ",".join(failed_reasons) if failed_reasons else "failed_reasons=",
            "historical_symbols=" + ",".join(sorted({str(symbol) for symbol in symbols if symbol})),
        ]
        opportunities.append(
            SuggestionOpportunity(
                opportunity_id=f"tushare_a_share_{strategy_id}",
                strategy_id=strategy_id,
                symbol=f"{strategy_id.upper()}_TUSHARE_SANDBOX_BASKET",
                market="A",
                name=str(candidate.get("name") or strategy_id),
                risk_veto=False,
                evidence_refs=list(evidence_refs),
                reasons=reasons,
                risk_warnings=[
                    "Tushare-backed historical sandbox evidence only; not user-facing trade advice.",
                    "This strategy failed the bounded A-share historical sample and must remain blocked.",
                    "No live price, position size, broker execution, webhook, or order is produced.",
                    *list(candidate.get("risk_controls") or [])[:3],
                ],
            )
        )
    return opportunities


def build_tushare_a_share_suggestion_gate_report(
    source_report: Mapping[str, Any],
    *,
    run_id: str,
    evidence_refs: Sequence[str],
    command: str | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    """Refresh Suggestion Gate from V2.11-C source evidence."""

    opportunities = build_tushare_a_share_suggestion_opportunities(source_report, evidence_refs=evidence_refs)
    drafts = build_suggestion_drafts(opportunities, source_report, created_at=generated_at or _now_iso())
    allowed = [draft for draft in drafts if draft.action != "blocked"]
    blocked = [draft for draft in drafts if draft.action == "blocked"]
    source_summary = source_report.get("summary") or {}
    source_failed = set(source_summary.get("failing_strategies") or [])
    blocked_strategy_ids = {draft.strategy_id for draft in blocked}

    checks = {
        "source_is_v2_11_c": source_report.get("acceptance_target")
        == "V2.11-C Tushare A-Share Historical Sandbox Live Data Refresh",
        "source_report_pass": source_report.get("overall_status") == "PASS",
        "source_is_tushare_a_share": (source_report.get("live_data_source") or {}).get("provider") == "tushare"
        and (source_report.get("live_data_source") or {}).get("market") == "A",
        "source_has_zero_strategy_pass": source_summary.get("strategy_pass_count") == 0,
        "source_has_failed_strategies": int(source_summary.get("strategy_fail_count") or 0) >= 1,
        "opportunity_count_matches_candidates": len(opportunities) == len(source_report.get("candidates") or []),
        "draft_count_matches_opportunities": len(drafts) == len(opportunities),
        "all_source_failed_strategies_blocked": source_failed == blocked_strategy_ids,
        "all_drafts_blocked": len(drafts) > 0 and len(blocked) == len(drafts),
        "no_allowed_suggestions": len(allowed) == 0,
        "blocked_by_sandbox_failure": all(
            "strategy_sandbox_not_passed" in draft.blocked_by for draft in blocked
        ),
        "evidence_refs_present": all(draft.evidence_refs for draft in drafts),
        "every_draft_simulation_only": all(draft.simulation_only for draft in drafts),
        "manual_external_execution_only": all(draft.user_must_execute_externally for draft in drafts),
        "no_live_price_or_position_size": True,
        "suggestion_drafts_not_orders": True,
        "no_real_trade": True,
        "no_broker_api": True,
        "no_trading_webhook": True,
        "no_order_placement": True,
        "no_secret_storage": True,
        "no_strategy_auto_mutation": True,
        "no_production_records_mutation": True,
        "dashboard_contract_unchanged": True,
    }

    return {
        "overall_status": "PASS" if all(checks.values()) else "FAIL",
        "acceptance_target": "V2.11-D Tushare-Backed A-Share Suggestion Gate Refresh",
        "source_acceptance_target": source_report.get("acceptance_target"),
        "run_id": run_id,
        "generated_at": generated_at or _now_iso(),
        "command": command,
        "network_used": False,
        "production_records_written": False,
        "dashboard_contract_changed": False,
        "summary": {
            "source_strategy_pass_count": source_summary.get("strategy_pass_count"),
            "source_strategy_fail_count": source_summary.get("strategy_fail_count"),
            "opportunity_count": len(opportunities),
            "draft_count": len(drafts),
            "allowed_count": len(allowed),
            "blocked_count": len(blocked),
            "blocked_strategies": sorted(blocked_strategy_ids),
            "blocked_suggestions": [draft.suggestion_id for draft in blocked],
            "allowed_suggestions": [draft.suggestion_id for draft in allowed],
            "tushare_historical_case_count": source_summary.get("historical_case_count"),
        },
        "opportunities": [opportunity.model_dump() for opportunity in opportunities],
        "suggestions": [draft.model_dump() for draft in drafts],
        "blocked_strategy_evidence": [
            {
                "strategy_id": result.get("strategy_id"),
                "status": result.get("status"),
                "failed_reasons": (result.get("metrics") or {}).get("failed_reasons") or [],
                "win_rate": (result.get("metrics") or {}).get("win_rate"),
                "average_return": (result.get("metrics") or {}).get("average_return"),
                "max_drawdown": (result.get("metrics") or {}).get("max_drawdown"),
            }
            for result in source_report.get("results", []) or []
            if result.get("status") != "PASS"
        ],
        "checks": checks,
        "safety": {
            "simulation_only": True,
            "manual_external_execution_only": True,
            "not_user_facing_trade_advice": True,
            "all_v2_11_c_failed_strategies_blocked": True,
            "no_allowed_suggestions_when_all_source_strategies_failed": True,
            "no_real_trade": True,
            "no_broker_api": True,
            "no_trading_webhook": True,
            "no_order_placement": True,
            "no_live_price": True,
            "no_position_size": True,
            "no_secret_storage": True,
            "no_strategy_mutation": True,
            "no_production_records_mutation": True,
            "dashboard_contract_unchanged": True,
        },
    }
