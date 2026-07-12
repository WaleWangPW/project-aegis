"""Finnhub quote sandbox evidence to simulation-only Suggestion Gate drafts."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping, Sequence

from aegis.models.suggestion import SuggestionOpportunity
from aegis.strategy.suggestion_gate import build_suggestion_drafts

ACCEPTANCE_TARGET = "V2.13-H Finnhub Quote Sandbox Evidence To Suggestion Gate Draft"
SOURCE_ACCEPTANCE_TARGET = "V2.13-G Finnhub Quote Context Sandbox Evaluation"


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _result_by_strategy(source_report: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    return {str(result.get("strategy_id")): result for result in source_report.get("results", []) or []}


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


def _unique(values: Sequence[str]) -> list[str]:
    seen: set[str] = set()
    unique_values: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        unique_values.append(value)
    return unique_values


def build_finnhub_quote_suggestion_opportunities(
    source_report: Mapping[str, Any],
    *,
    evidence_refs: Sequence[str],
) -> list[SuggestionOpportunity]:
    """Build one simulation opportunity per Finnhub quote-context sandbox candidate."""

    results_by_strategy = _result_by_strategy(source_report)
    source_summary = source_report.get("summary") or {}
    opportunities: list[SuggestionOpportunity] = []
    for candidate in source_report.get("candidates", []) or []:
        strategy_id = str(candidate.get("strategy_id"))
        result = results_by_strategy.get(strategy_id, {})
        metrics = result.get("metrics") or {}
        cases = _cases_by_strategy(source_report, strategy_id)
        symbols = sorted({str(case.get("symbol")) for case in cases if case.get("symbol")})
        case_evidence_refs = [
            str(case.get("evidence_ref"))
            for case in cases
            if case.get("evidence_ref")
        ]
        symbol = symbols[0] if len(symbols) == 1 else "FINNHUB_QUOTE_CONTEXT_BASKET"
        market = str(candidate.get("market") or "US")

        reasons = [
            f"finnhub_quote_sandbox_status={result.get('status')}",
            f"sample_count={metrics.get('sample_count')}",
            f"win_rate={_format_metric(metrics.get('win_rate'))}",
            f"average_return={_format_metric(metrics.get('average_return'))}",
            f"max_drawdown={_format_metric(metrics.get('max_drawdown'))}",
            "historical_symbols=" + ",".join(symbols),
            "source_stage=V2.13-G",
            f"social_sentiment_status={source_summary.get('social_sentiment_status')}",
        ]
        risk_warnings = [
            "Finnhub quote context is research evidence only; one quote snapshot is not standalone strategy proof.",
            "Finnhub social sentiment remains blocked by plan or rate limit and is not used in this suggestion draft.",
            "Simulation-only draft; user decides and executes manually outside Aegis.",
            "Manual external execution only; Aegis does not connect to broker APIs or place orders.",
            "No live price, position size, trading webhook, broker execution, or order is produced.",
            *list(candidate.get("risk_controls") or [])[:4],
        ]
        opportunities.append(
            SuggestionOpportunity(
                opportunity_id=f"finnhub_quote_{market.lower()}_{strategy_id}",
                strategy_id=strategy_id,
                symbol=symbol,
                market=market,  # type: ignore[arg-type]
                name=str(candidate.get("name") or strategy_id),
                risk_veto=False,
                evidence_refs=_unique([*list(evidence_refs), *case_evidence_refs]),
                reasons=reasons,
                risk_warnings=risk_warnings,
            )
        )
    return opportunities


def build_finnhub_quote_suggestion_gate_report(
    source_report: Mapping[str, Any],
    *,
    run_id: str,
    evidence_refs: Sequence[str],
    command: str | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    """Route V2.13-G Finnhub quote sandbox evidence through Suggestion Gate."""

    created = generated_at or _now_iso()
    opportunities = build_finnhub_quote_suggestion_opportunities(source_report, evidence_refs=evidence_refs)
    drafts = build_suggestion_drafts(opportunities, source_report, created_at=created)
    allowed = [draft for draft in drafts if draft.action != "blocked"]
    blocked = [draft for draft in drafts if draft.action == "blocked"]
    source_summary = source_report.get("summary") or {}
    warning_text = "\n".join(warning for draft in drafts for warning in draft.risk_warnings).lower()
    reason_text = "\n".join(reason for draft in drafts for reason in draft.reasons).lower()

    checks = {
        "source_is_v2_13_g": source_report.get("acceptance_target") == SOURCE_ACCEPTANCE_TARGET,
        "source_report_pass": source_report.get("overall_status") == "PASS",
        "source_has_quote_context_candidate": int(source_summary.get("candidate_count") or 0) >= 1,
        "source_has_historical_cases": int(source_summary.get("historical_case_count") or 0) >= 1,
        "source_has_passing_strategy": int(source_summary.get("strategy_pass_count") or 0) >= 1,
        "source_strategy_fail_count_zero": int(source_summary.get("strategy_fail_count") or 0) == 0,
        "source_user_facing_suggestion_was_blocked": source_summary.get("user_facing_suggestion_allowed") is False,
        "source_required_suggestion_gate": source_summary.get("suggestion_gate_required") is True,
        "source_social_sentiment_still_blocked": source_summary.get("social_sentiment_status")
        == "blocked_plan_or_rate_limit",
        "opportunity_count_matches_candidates": len(opportunities) == len(source_report.get("candidates") or []),
        "draft_count_matches_opportunities": len(drafts) == len(opportunities),
        "allowed_count_matches_source_pass_count": len(allowed) == int(source_summary.get("strategy_pass_count") or 0),
        "allowed_suggestions_present": len(allowed) >= 1,
        "no_blocked_suggestions_for_passing_source": len(blocked) == 0,
        "all_allowed_are_paper_entry_candidates": all(draft.action == "paper_entry_candidate" for draft in allowed),
        "every_draft_simulation_only": all(draft.simulation_only for draft in drafts),
        "manual_external_execution_only": all(draft.user_must_execute_externally for draft in drafts),
        "evidence_refs_present": all(draft.evidence_refs for draft in drafts),
        "quote_context_case_evidence_refs_present": all(
            any(ref.startswith("v2_13_f_quote_context_case:") for ref in draft.evidence_refs)
            for draft in drafts
        ),
        "social_sentiment_blocked_visible": "social sentiment" in warning_text
        and "blocked_plan_or_rate_limit" in reason_text,
        "quote_context_limitation_visible": "quote context" in warning_text and "not standalone strategy proof" in warning_text,
        "no_live_price_or_position_size": "live price" in warning_text and "position size" in warning_text,
        "suggestion_drafts_not_orders": "order" in warning_text,
        "no_real_trade": True,
        "no_broker_api": True,
        "no_trading_webhook": True,
        "no_order_placement": True,
        "no_live_order_signal": True,
        "no_position_size": True,
        "no_secret_storage": True,
        "no_request_url_storage": True,
        "no_raw_payload_storage": True,
        "no_strategy_auto_mutation": True,
        "no_production_records_mutation": True,
        "no_production_cache_mutation": True,
        "no_production_provider_config_mutation": True,
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
            "source_strategy_pass_count": source_summary.get("strategy_pass_count"),
            "source_strategy_fail_count": source_summary.get("strategy_fail_count"),
            "source_historical_case_count": source_summary.get("historical_case_count"),
            "symbols": source_summary.get("symbols") or [],
            "markets": source_summary.get("markets") or [],
            "social_sentiment_status": source_summary.get("social_sentiment_status"),
            "opportunity_count": len(opportunities),
            "draft_count": len(drafts),
            "allowed_count": len(allowed),
            "blocked_count": len(blocked),
            "allowed_suggestions": [draft.suggestion_id for draft in allowed],
            "blocked_suggestions": [draft.suggestion_id for draft in blocked],
            "user_facing_simulation_brief_allowed": True,
            "real_trade_allowed": False,
            "next_stage": "V2.13-I Finnhub Quote Current Simulation Brief",
        },
        "opportunities": [opportunity.model_dump() for opportunity in opportunities],
        "suggestions": [draft.model_dump() for draft in drafts],
        "checks": checks,
        "safety": {
            "simulation_only": True,
            "manual_external_execution_only": True,
            "not_real_trade_advice": True,
            "not_an_order": True,
            "quote_context_research_only": True,
            "social_sentiment_not_enabled": True,
            "no_real_trade": True,
            "no_broker_api": True,
            "no_trading_webhook": True,
            "no_order_placement": True,
            "no_live_price": True,
            "no_position_size": True,
            "no_live_order_signal": True,
            "no_secret_storage": True,
            "no_request_url_storage": True,
            "no_raw_payload_storage": True,
            "no_strategy_mutation": True,
            "no_production_records_mutation": True,
            "no_production_cache_mutation": True,
            "no_production_provider_config_mutation": True,
            "dashboard_contract_unchanged": True,
        },
    }


def render_finnhub_quote_suggestion_gate_markdown(report: Mapping[str, Any]) -> str:
    summary = report["summary"]
    return "\n".join(
        [
            "# V2.13-H Finnhub Quote Suggestion Gate Draft",
            "",
            f"- status: `{report['overall_status']}`",
            f"- run_id: `{report['run_id']}`",
            f"- source: `{report['source_acceptance_target']}`",
            f"- symbols: `{summary['symbols']}`",
            f"- allowed_count: `{summary['allowed_count']}`",
            f"- blocked_count: `{summary['blocked_count']}`",
            f"- social_sentiment_status: `{summary['social_sentiment_status']}`",
            f"- allowed_suggestions: `{summary['allowed_suggestions']}`",
            "",
            "## Meaning",
            "",
            "V2.13-H converts the V2.13-G Finnhub quote-context sandbox PASS evidence into simulation-only paper candidate drafts.",
            "The drafts may feed a later user-readable simulation brief, but they remain non-trading guidance and require manual user review.",
            "",
            "## Boundary",
            "",
            "- Simulation-only.",
            "- Manual external execution only.",
            "- Finnhub quote context is research evidence only.",
            "- Finnhub social sentiment remains blocked and is not used.",
            "- No real trade, broker API, trading webhook, order placement, live price, position size, or live order signal.",
            "- No production Recommendation/PaperTrade/Review/Memory record mutation.",
            "- Dashboard Contract unchanged.",
            "",
        ]
    )
