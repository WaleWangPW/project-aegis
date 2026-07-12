"""Bridge API research summaries into sandbox candidate update proposals."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable

from aegis.models.external_api import ExternalAPIFetchItem
from aegis.models.strategy import StrategyCandidate
from aegis.models.strategy_update import StrategyCandidateUpdateProposal


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def _market_overlap(candidate: StrategyCandidate, fetch_item: ExternalAPIFetchItem) -> list[str]:
    text = f"{fetch_item.summary} {fetch_item.endpoint_path}".lower()
    marker = f"market={candidate.market.lower()}"
    return [candidate.market] if marker in text else []


def build_strategy_update_proposals(
    *,
    fetch_items: Iterable[ExternalAPIFetchItem],
    candidates: Iterable[StrategyCandidate],
    source_fetch_ref: str,
    created_at: str | None = None,
) -> list[StrategyCandidateUpdateProposal]:
    created = created_at or _now_iso()
    proposals: list[StrategyCandidateUpdateProposal] = []
    for fetch_item in fetch_items:
        for candidate in candidates:
            markets = _market_overlap(candidate, fetch_item)
            if not markets:
                continue
            proposals.append(
                StrategyCandidateUpdateProposal(
                    proposal_id=f"proposal_{fetch_item.connector_id}_{candidate.strategy_id}",
                    target_strategy_id=candidate.strategy_id,
                    source_connector_id=fetch_item.connector_id,
                    source_fetch_ref=source_fetch_ref,
                    markets=markets,
                    proposed_research_refs=[fetch_item.content_hash],
                    proposed_risk_controls=["api_research_requires_sandbox_confirmation"],
                    rationale=[
                        f"API summary available for connector {fetch_item.connector_id}.",
                        "Proposal is review-only and must pass sandbox before strategy changes.",
                    ],
                    requires_sandbox=True,
                    auto_applied=False,
                    user_facing_suggestion_allowed=False,
                    created_at=created,
                )
            )
    return proposals


def build_research_bridge_report(
    *,
    fetch_items: Iterable[ExternalAPIFetchItem],
    candidates: Iterable[StrategyCandidate],
    source_fetch_ref: str,
    run_id: str,
    command: str | None = None,
) -> dict:
    proposals = build_strategy_update_proposals(
        fetch_items=fetch_items,
        candidates=candidates,
        source_fetch_ref=source_fetch_ref,
    )
    return {
        "overall_status": "PASS" if proposals else "FAIL",
        "generated_at": _now_iso(),
        "run_id": run_id,
        "command": command,
        "acceptance_target": "V2.2-C API Research To Sandbox Candidate Bridge",
        "isolated": True,
        "network_used": False,
        "production_records_written": False,
        "dashboard_contract_changed": False,
        "summary": {
            "proposal_count": len(proposals),
            "target_strategy_ids": sorted({proposal.target_strategy_id for proposal in proposals}),
            "source_connector_ids": sorted({proposal.source_connector_id for proposal in proposals}),
            "next_target": "V2.3-A Real User API Configuration Handoff",
        },
        "proposals": [proposal.model_dump() for proposal in proposals],
        "safety": {
            "proposal_only": True,
            "requires_sandbox": True,
            "auto_applied": False,
            "user_facing_suggestion_allowed": False,
            "no_real_trade": True,
            "no_broker_api": True,
            "no_trading_webhook": True,
            "no_secret_storage": True,
            "dashboard_contract_unchanged": True,
            "no_production_records_mutation": True,
        },
    }
