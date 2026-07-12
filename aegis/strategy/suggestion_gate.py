"""Suggestion gate for simulation-only user drafts."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Mapping, Sequence

from aegis.models.suggestion import SuggestionDraft, SuggestionOpportunity


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def _sandbox_status_by_strategy(sandbox_report: Mapping) -> dict[str, str]:
    return {result["strategy_id"]: result["status"] for result in sandbox_report.get("results", [])}


def _has_strategy_evidence(opportunity: SuggestionOpportunity, sandbox_report: Mapping) -> bool:
    if not opportunity.evidence_refs:
        return False
    strategy_id = opportunity.strategy_id
    return any(result.get("strategy_id") == strategy_id for result in sandbox_report.get("results", []))


def build_suggestion_drafts(
    opportunities: Sequence[SuggestionOpportunity],
    sandbox_report: Mapping,
    *,
    created_at: str | None = None,
) -> list[SuggestionDraft]:
    created = created_at or _now_iso()
    status_by_strategy = _sandbox_status_by_strategy(sandbox_report)
    drafts: list[SuggestionDraft] = []

    for opportunity in opportunities:
        blocked_by: list[str] = []
        sandbox_status = status_by_strategy.get(opportunity.strategy_id)
        if sandbox_status != "PASS":
            blocked_by.append("strategy_sandbox_not_passed")
        if opportunity.risk_veto:
            blocked_by.append("risk_veto_triggered")
        if not _has_strategy_evidence(opportunity, sandbox_report):
            blocked_by.append("missing_evidence_refs")

        action = "blocked" if blocked_by else "paper_entry_candidate"
        drafts.append(
            SuggestionDraft(
                suggestion_id=f"sug_{opportunity.opportunity_id}",
                opportunity_id=opportunity.opportunity_id,
                strategy_id=opportunity.strategy_id,
                symbol=opportunity.symbol,
                market=opportunity.market,
                action=action,
                reasons=opportunity.reasons,
                risk_warnings=opportunity.risk_warnings
                + ["Simulation-only draft; user decides and executes manually outside Aegis."],
                evidence_refs=opportunity.evidence_refs,
                blocked_by=blocked_by,
                created_at=created,
            )
        )
    return drafts


def build_suggestion_gate_report(
    opportunities: Sequence[SuggestionOpportunity],
    sandbox_report: Mapping,
    *,
    run_id: str,
    command: str | None = None,
) -> dict:
    drafts = build_suggestion_drafts(opportunities, sandbox_report)
    allowed_count = sum(1 for draft in drafts if draft.action != "blocked")
    blocked_count = sum(1 for draft in drafts if draft.action == "blocked")
    return {
        "overall_status": "PASS" if allowed_count >= 1 and blocked_count >= 1 else "FAIL",
        "generated_at": _now_iso(),
        "run_id": run_id,
        "command": command,
        "acceptance_target": "V2.1-C Suggestion Gate",
        "isolated": True,
        "network_used": False,
        "production_records_written": False,
        "dashboard_contract_changed": False,
        "summary": {
            "opportunity_count": len(opportunities),
            "draft_count": len(drafts),
            "allowed_count": allowed_count,
            "blocked_count": blocked_count,
            "allowed_suggestions": [draft.suggestion_id for draft in drafts if draft.action != "blocked"],
            "blocked_suggestions": [draft.suggestion_id for draft in drafts if draft.action == "blocked"],
        },
        "suggestions": [draft.model_dump() for draft in drafts],
        "safety": {
            "simulation_only": True,
            "manual_external_execution_only": True,
            "no_real_trade": True,
            "no_broker_api": True,
            "no_webhook": True,
            "no_secret_storage": True,
            "strategy_sandbox_required": True,
            "risk_veto_blocks_suggestion": True,
            "evidence_refs_required": True,
            "dashboard_contract_unchanged": True,
            "no_production_records_mutation": True,
        },
    }
