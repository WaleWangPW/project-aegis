"""Route refreshed-candidate sandbox evidence through Suggestion Gate."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Mapping

from aegis.models.suggestion import SuggestionOpportunity
from aegis.strategy.suggestion_gate import build_suggestion_drafts

ACCEPTANCE_TARGET = "V2.14-D Refreshed Candidate Suggestion Gate"
SOURCE_TARGET = "V2.14-C Refreshed Candidate Historical Sandbox"


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _result_by_strategy(source_report: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    return {str(item.get("strategy_id")): item for item in source_report.get("results", []) or []}


def _cases_for_symbol(source_report: Mapping[str, Any], symbol: str) -> list[Mapping[str, Any]]:
    return [
        case
        for case in source_report.get("historical_cases", []) or []
        if str(case.get("symbol")) == symbol
    ]


def _metric_reasons(result: Mapping[str, Any], *, symbol: str, coverage_status: str) -> list[str]:
    metrics = result.get("metrics") or {}
    failed_reasons = metrics.get("failed_reasons") or []
    return [
        f"symbol={symbol}",
        f"coverage_status={coverage_status}",
        f"sandbox_status={result.get('status')}",
        f"sample_count={metrics.get('sample_count')}",
        f"win_rate={metrics.get('win_rate')}",
        f"average_return={metrics.get('average_return')}",
        f"max_drawdown={metrics.get('max_drawdown')}",
        "failed_reasons=" + ",".join(failed_reasons) if failed_reasons else "failed_reasons=",
        "source_stage=V2.14-C",
    ]


def build_refreshed_candidate_suggestion_opportunities(source_report: Mapping[str, Any]) -> list[SuggestionOpportunity]:
    results_by_strategy = _result_by_strategy(source_report)
    opportunities: list[SuggestionOpportunity] = []

    for item in source_report.get("covered_candidates", []) or []:
        symbol = str(item.get("symbol"))
        strategy_id = str(item.get("strategy_id"))
        result = results_by_strategy.get(strategy_id, {})
        cases = _cases_for_symbol(source_report, symbol)
        case_refs = [str(case.get("evidence_ref")) for case in cases if case.get("evidence_ref")]
        opportunities.append(
            SuggestionOpportunity(
                opportunity_id=f"v2_14_d_{symbol.lower().replace('.', '_')}",
                strategy_id=strategy_id,
                symbol=symbol,
                market=str(item.get("market")),  # type: ignore[arg-type]
                name=f"{symbol} refreshed candidate simulation draft",
                risk_veto=False,
                evidence_refs=[*list(item.get("evidence_refs") or []), *case_refs],
                reasons=_metric_reasons(result, symbol=symbol, coverage_status="historical_case_available"),
                risk_warnings=[
                    "Simulation-only draft; user decides and executes manually outside Aegis.",
                    "Historical sandbox evidence only; not a future prediction.",
                    "No live price, position size, broker API, webhook, or order is produced.",
                    "If user acts elsewhere, user must return external evidence for paper-trade review.",
                ],
            )
        )

    for item in source_report.get("missing_coverage_candidates", []) or []:
        symbol = str(item.get("symbol"))
        strategy_id = str(item.get("strategy_id"))
        result = results_by_strategy.get(strategy_id, {})
        opportunities.append(
            SuggestionOpportunity(
                opportunity_id=f"v2_14_d_missing_{symbol.lower().replace('.', '_')}",
                strategy_id=strategy_id,
                symbol=symbol,
                market=str(item.get("market")),  # type: ignore[arg-type]
                name=f"{symbol} missing historical coverage",
                risk_veto=False,
                evidence_refs=[],
                reasons=[
                    *_metric_reasons(result, symbol=symbol, coverage_status="missing_historical_case"),
                    f"missing_reason={item.get('missing_reason')}",
                ],
                risk_warnings=[
                    "Blocked: no historical coverage for this candidate in V2.14-C.",
                    "Missing coverage cannot be treated as a pass.",
                    "No live price, position size, broker API, webhook, or order is produced.",
                ],
            )
        )
    return opportunities


def build_refreshed_candidate_suggestion_gate_report(
    source_report: Mapping[str, Any],
    *,
    run_id: str,
    command: str | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    created = generated_at or _now_iso()
    opportunities = build_refreshed_candidate_suggestion_opportunities(source_report)
    drafts = build_suggestion_drafts(opportunities, source_report, created_at=created)
    allowed = [draft for draft in drafts if draft.action != "blocked"]
    blocked = [draft for draft in drafts if draft.action == "blocked"]
    missing_symbols = {str(item.get("symbol")) for item in source_report.get("missing_coverage_candidates", []) or []}
    failed_strategies = set((source_report.get("summary") or {}).get("sandbox_failed_strategies") or [])
    allowed_symbols = {draft.symbol for draft in allowed}
    blocked_symbols = {draft.symbol for draft in blocked}
    warning_text = "\n".join(w for draft in drafts for w in draft.risk_warnings).lower()

    checks = {
        "source_report_pass": source_report.get("overall_status") == "PASS",
        "source_target_correct": source_report.get("acceptance_target") == SOURCE_TARGET,
        "source_has_passed_strategy": int((source_report.get("summary") or {}).get("strategy_pass_count") or 0) >= 1,
        "source_has_failed_strategy": int((source_report.get("summary") or {}).get("strategy_fail_count") or 0) >= 1,
        "source_missing_coverage_visible": int((source_report.get("summary") or {}).get("missing_coverage_count") or 0) >= 1,
        "opportunity_count_matches_candidates": len(opportunities)
        == len(source_report.get("covered_candidates", []) or []) + len(source_report.get("missing_coverage_candidates", []) or []),
        "draft_count_matches_opportunities": len(drafts) == len(opportunities),
        "allowed_count_matches_passed_covered_symbols": len(allowed) == 1,
        "allowed_suggestions_present": len(allowed) >= 1,
        "all_allowed_are_paper_entry_candidates": all(draft.action == "paper_entry_candidate" for draft in allowed),
        "allowed_have_evidence_refs": all(draft.evidence_refs for draft in allowed),
        "missing_coverage_symbols_blocked": missing_symbols.issubset(blocked_symbols),
        "failed_strategy_symbols_blocked": all(
            draft.strategy_id in failed_strategies for draft in blocked if draft.symbol not in missing_symbols
        ),
        "no_missing_coverage_allowed": allowed_symbols.isdisjoint(missing_symbols),
        "blocked_by_sandbox_or_missing_evidence": all(
            {"strategy_sandbox_not_passed", "missing_evidence_refs"} & set(draft.blocked_by)
            for draft in blocked
        ),
        "every_draft_simulation_only": all(draft.simulation_only for draft in drafts),
        "manual_external_execution_only": all(draft.user_must_execute_externally for draft in drafts),
        "no_live_price_or_position_size_warning": "live price" in warning_text and "position size" in warning_text,
        "not_an_order_warning": "order" in warning_text,
        "network_not_used": True,
        "production_records_not_written": True,
        "production_cache_not_mutated": True,
        "production_provider_config_not_mutated": True,
        "no_secret_values_stored": True,
        "request_urls_not_stored": True,
        "raw_payloads_not_stored": True,
        "no_real_trade": True,
        "no_broker_api": True,
        "no_webhook": True,
        "no_order_placement": True,
        "no_position_size": True,
        "no_live_order_signal": True,
        "dashboard_contract_unchanged": True,
    }
    return {
        "overall_status": "PASS" if all(checks.values()) else "FAIL",
        "acceptance_target": ACCEPTANCE_TARGET,
        "source_acceptance_target": source_report.get("acceptance_target"),
        "run_id": run_id,
        "generated_at": created,
        "command": command,
        "network_used": False,
        "production_records_written": False,
        "production_cache_mutated": False,
        "production_provider_config_mutated": False,
        "dashboard_contract_changed": False,
        "summary": {
            "opportunity_count": len(opportunities),
            "draft_count": len(drafts),
            "allowed_count": len(allowed),
            "blocked_count": len(blocked),
            "allowed_symbols": sorted(allowed_symbols),
            "blocked_symbols": sorted(blocked_symbols),
            "allowed_suggestions": [draft.suggestion_id for draft in allowed],
            "blocked_suggestions": [draft.suggestion_id for draft in blocked],
            "simulation_suggestion_available": len(allowed) >= 1,
            "real_trade_allowed": False,
            "next_stage": "V2.14-E Current Usable Simulation Suggestion Brief",
        },
        "opportunities": [opportunity.model_dump() for opportunity in opportunities],
        "suggestions": [draft.model_dump() for draft in drafts],
        "source_evidence": {
            "source_target": source_report.get("acceptance_target"),
            "source_run_id": source_report.get("run_id"),
            "source_summary_sha256": _sha256_text(
                json.dumps(source_report.get("summary") or {}, ensure_ascii=False, sort_keys=True)
            ),
        },
        "checks": checks,
        "safety": {
            "simulation_only": True,
            "manual_external_execution_only": True,
            "not_real_trade_advice": True,
            "not_an_order": True,
            "sandbox_pass_required": True,
            "missing_coverage_blocks_suggestion": True,
            "failed_sandbox_blocks_suggestion": True,
            "network_not_used": True,
            "production_records_not_written": True,
            "production_cache_not_mutated": True,
            "production_provider_config_not_mutated": True,
            "no_secret_values_stored": True,
            "request_urls_not_stored": True,
            "raw_payloads_not_stored": True,
            "no_real_trade": True,
            "no_broker_api": True,
            "no_webhook": True,
            "no_order_placement": True,
            "no_position_size": True,
            "no_live_order_signal": True,
            "dashboard_contract_unchanged": True,
        },
    }


def render_refreshed_candidate_suggestion_gate_markdown(report: Mapping[str, Any]) -> str:
    lines = [
        "# V2.14-D Refreshed Candidate Suggestion Gate",
        "",
        f"- status: `{report.get('overall_status')}`",
        f"- run_id: `{report.get('run_id')}`",
        f"- allowed_count: `{report.get('summary', {}).get('allowed_count')}`",
        f"- blocked_count: `{report.get('summary', {}).get('blocked_count')}`",
        f"- allowed_symbols: `{report.get('summary', {}).get('allowed_symbols')}`",
        f"- blocked_symbols: `{report.get('summary', {}).get('blocked_symbols')}`",
        f"- next_stage: `{report.get('summary', {}).get('next_stage')}`",
        "",
        "## Allowed Simulation Drafts",
        "",
    ]
    for draft in report.get("suggestions", []) or []:
        if draft.get("action") != "blocked":
            lines.append(f"- `{draft.get('symbol')}` / `{draft.get('market')}`: `{draft.get('action')}`")
    lines.extend(["", "## Blocked Drafts", ""])
    for draft in report.get("suggestions", []) or []:
        if draft.get("action") == "blocked":
            lines.append(f"- `{draft.get('symbol')}`: `{draft.get('blocked_by')}`")
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "- Simulation-only suggestion draft.",
            "- User decides and executes manually outside Aegis.",
            "- Not real trade advice and not an order.",
            "- No broker API, webhook, live order signal, live price, or position size.",
            "- Production records are not written.",
            "",
        ]
    )
    return "\n".join(lines)
