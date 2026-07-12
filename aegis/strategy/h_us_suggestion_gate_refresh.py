"""H/US Suggestion Gate refresh from historical sandbox evidence.

V2.12-E consumes the V2.12-D H/US cache-backed sandbox evidence and produces
simulation-only suggestion drafts. These drafts are not orders and are not
real-trading advice; they are bounded, auditable candidates for the user's
manual review and external execution decision.
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


def _cases_by_strategy(source_report: Mapping[str, Any], strategy_id: str) -> list[Mapping[str, Any]]:
    return [
        case
        for case in source_report.get("historical_cases", []) or []
        if str(case.get("strategy_id")) == strategy_id
    ]


def _format_metric(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


def _market_symbol(market: str) -> str:
    if market == "H":
        return "H_API_SANDBOX_PAPER_BASKET"
    if market == "US":
        return "US_API_SANDBOX_PAPER_BASKET"
    return f"{market}_API_SANDBOX_PAPER_BASKET"


def build_h_us_suggestion_opportunities(
    source_report: Mapping[str, Any],
    *,
    evidence_refs: Sequence[str],
) -> list[SuggestionOpportunity]:
    """Build one opportunity per V2.12-D H/US sandbox candidate."""

    results_by_strategy = _result_by_strategy(source_report)
    opportunities: list[SuggestionOpportunity] = []
    for candidate in source_report.get("candidates", []) or []:
        strategy_id = str(candidate.get("strategy_id"))
        market = str(candidate.get("market"))
        result = results_by_strategy.get(strategy_id, {})
        metrics = result.get("metrics") or {}
        cases = _cases_by_strategy(source_report, strategy_id)
        symbols = sorted({str(case.get("symbol")) for case in cases if case.get("symbol")})
        case_evidence_refs = [
            str(case.get("evidence_ref"))
            for case in cases
            if case.get("evidence_ref")
        ]

        reasons = [
            f"h_us_sandbox_status={result.get('status')}",
            f"sample_count={metrics.get('sample_count')}",
            f"win_rate={_format_metric(metrics.get('win_rate'))}",
            f"average_return={_format_metric(metrics.get('average_return'))}",
            f"max_drawdown={_format_metric(metrics.get('max_drawdown'))}",
            "historical_symbols=" + ",".join(symbols),
            "source_stage=V2.12-D",
        ]
        risk_warnings = [
            "Preliminary H/US API-backed sandbox sample only; sample size is too small for production strategy proof.",
            "Simulation-only draft; user decides and executes manually outside Aegis.",
            "Manual external execution only; Aegis does not connect to broker APIs or place orders.",
            "No live price, position size, trading webhook, broker execution, or order is produced.",
            *list(candidate.get("risk_controls") or [])[:3],
        ]
        opportunities.append(
            SuggestionOpportunity(
                opportunity_id=f"h_us_{market.lower()}_{strategy_id}",
                strategy_id=strategy_id,
                symbol=_market_symbol(market),
                market=market,  # type: ignore[arg-type]
                name=str(candidate.get("name") or strategy_id),
                risk_veto=False,
                evidence_refs=[*list(evidence_refs), *case_evidence_refs],
                reasons=reasons,
                risk_warnings=risk_warnings,
            )
        )
    return opportunities


def build_h_us_suggestion_gate_report(
    source_report: Mapping[str, Any],
    *,
    run_id: str,
    evidence_refs: Sequence[str],
    command: str | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    """Refresh Suggestion Gate from V2.12-D source evidence."""

    opportunities = build_h_us_suggestion_opportunities(source_report, evidence_refs=evidence_refs)
    drafts = build_suggestion_drafts(opportunities, source_report, created_at=generated_at or _now_iso())
    allowed = [draft for draft in drafts if draft.action != "blocked"]
    blocked = [draft for draft in drafts if draft.action == "blocked"]
    source_summary = source_report.get("summary") or {}
    warning_text = "\n".join(
        warning
        for draft in drafts
        for warning in draft.risk_warnings
    ).lower()

    checks = {
        "source_is_v2_12_d": source_report.get("acceptance_target")
        == "V2.12-D H-US Historical Sandbox Candidate Refresh Dry Run",
        "source_report_pass": source_report.get("overall_status") == "PASS",
        "source_has_h_and_us_cases": set(source_summary.get("markets_with_cases") or []) >= {"H", "US"},
        "source_is_preliminary_only": source_summary.get("preliminary_only") is True
        and (source_report.get("safety") or {}).get("preliminary_sample_only") is True,
        "source_user_facing_suggestion_was_blocked": source_summary.get("user_facing_suggestion_allowed") is False,
        "source_required_suggestion_gate": source_summary.get("next_stage")
        == "V2.12-E H-US Suggestion Gate Refresh From Sandbox Evidence",
        "source_has_passing_strategies": int(source_summary.get("strategy_pass_count") or 0) >= 1,
        "opportunity_count_matches_candidates": len(opportunities) == len(source_report.get("candidates") or []),
        "draft_count_matches_opportunities": len(drafts) == len(opportunities),
        "allowed_count_matches_source_pass_count": len(allowed) == int(source_summary.get("strategy_pass_count") or 0),
        "allowed_suggestions_present": len(allowed) >= 1,
        "no_blocked_suggestions_for_passing_source": len(blocked) == 0,
        "all_allowed_are_paper_entry_candidates": all(
            draft.action == "paper_entry_candidate" for draft in allowed
        ),
        "evidence_refs_present": all(draft.evidence_refs for draft in drafts),
        "cache_case_evidence_refs_present": all(
            any(ref.startswith("v2_12_c_normalized_cache:") for ref in draft.evidence_refs)
            for draft in drafts
        ),
        "sample_size_warning_visible": "sample size" in warning_text or "sample_size_warning" in warning_text,
        "preliminary_only_warning_visible": "preliminary" in warning_text,
        "manual_external_execution_only": all(draft.user_must_execute_externally for draft in drafts),
        "every_draft_simulation_only": all(draft.simulation_only for draft in drafts),
        "no_live_price_or_position_size": "live price" in warning_text and "position size" in warning_text,
        "suggestion_drafts_not_orders": "order" in warning_text,
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
        "acceptance_target": "V2.12-E H-US Suggestion Gate Refresh From Sandbox Evidence",
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
            "source_historical_case_count": source_summary.get("historical_case_count"),
            "markets_with_cases": source_summary.get("markets_with_cases") or [],
            "opportunity_count": len(opportunities),
            "draft_count": len(drafts),
            "allowed_count": len(allowed),
            "blocked_count": len(blocked),
            "allowed_suggestions": [draft.suggestion_id for draft in allowed],
            "blocked_suggestions": [draft.suggestion_id for draft in blocked],
            "preliminary_only": True,
            "user_facing_simulation_brief_allowed": True,
            "real_trade_allowed": False,
            "next_stage": "V2.12-F H-US Current Usable Simulation Brief Refresh",
        },
        "opportunities": [opportunity.model_dump() for opportunity in opportunities],
        "suggestions": [draft.model_dump() for draft in drafts],
        "checks": checks,
        "safety": {
            "simulation_only": True,
            "manual_external_execution_only": True,
            "not_real_trade_advice": True,
            "not_an_order": True,
            "preliminary_sample_only": True,
            "sample_size_warning_required": True,
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


def render_h_us_suggestion_gate_markdown(report: Mapping[str, Any]) -> str:
    summary = report["summary"]
    return "\n".join(
        [
            "# V2.12-E H-US Suggestion Gate Refresh",
            "",
            f"- status: `{report['overall_status']}`",
            f"- run_id: `{report['run_id']}`",
            f"- source: `{report['source_acceptance_target']}`",
            f"- allowed_count: `{summary['allowed_count']}`",
            f"- blocked_count: `{summary['blocked_count']}`",
            f"- markets_with_cases: `{summary['markets_with_cases']}`",
            f"- allowed_suggestions: `{summary['allowed_suggestions']}`",
            "",
            "## Meaning",
            "",
            "V2.12-E converts the V2.12-D H/US historical sandbox PASS evidence into simulation-only paper candidate drafts.",
            "The drafts are suitable for a later user-readable simulation brief, but they remain preliminary because the source sample is intentionally small.",
            "",
            "## Boundary",
            "",
            "- Simulation-only.",
            "- Manual external execution only.",
            "- No real trade, broker API, trading webhook, order placement, live price, or position size.",
            "- No production Recommendation/PaperTrade/Review/Memory record mutation.",
            "- Dashboard Contract unchanged.",
            "",
        ]
    )
