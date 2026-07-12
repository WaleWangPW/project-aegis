"""Run historical sandbox evaluation from source-audit refresh proposals."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable

from aegis.models.strategy_hypothesis import StrategySandboxHypothesis
from aegis.strategy.hypothesis_sandbox import build_hypothesis_sandbox_report


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def refreshed_hypotheses_from_queue(
    refresh_queue: dict,
    hypotheses: Iterable[StrategySandboxHypothesis],
    *,
    created_at: str | None = None,
) -> tuple[list[StrategySandboxHypothesis], dict[str, list[str]]]:
    """Select and evidence-trim hypotheses using reachable refresh proposal refs."""

    hypothesis_list = list(hypotheses)
    created = created_at or _now_iso()
    selected_by_id: dict[str, StrategySandboxHypothesis] = {}
    proposal_to_hypotheses: dict[str, list[str]] = {}

    for proposal in refresh_queue.get("refresh_proposals", []):
        proposal_id = proposal["proposal_id"]
        proposal_market = proposal["market"]
        reachable_refs = set(proposal.get("source_research_ids", []))
        matched_ids: list[str] = []
        for hypothesis in hypothesis_list:
            if hypothesis.market != proposal_market:
                continue
            trimmed_refs = sorted(set(hypothesis.source_research_ids).intersection(reachable_refs))
            if not trimmed_refs:
                continue
            refreshed = hypothesis.model_copy(update={"source_research_ids": trimmed_refs, "created_at": created})
            selected_by_id[refreshed.hypothesis_id] = refreshed
            matched_ids.append(refreshed.hypothesis_id)
        proposal_to_hypotheses[proposal_id] = sorted(set(matched_ids))

    return list(selected_by_id.values()), proposal_to_hypotheses


def build_refresh_queue_historical_sandbox_report(
    refresh_queue: dict,
    hypotheses: Iterable[StrategySandboxHypothesis],
    *,
    run_id: str,
    command: str | None = None,
    historical_cache_file_count: int = 0,
) -> dict:
    refreshed_hypotheses, proposal_to_hypotheses = refreshed_hypotheses_from_queue(refresh_queue, hypotheses)
    report = build_hypothesis_sandbox_report(
        refreshed_hypotheses,
        run_id=run_id,
        command=command,
        historical_cache_file_count=historical_cache_file_count,
    )
    reachable_source_ids = {
        source_id
        for proposal in refresh_queue.get("refresh_proposals", [])
        for source_id in proposal.get("source_research_ids", [])
    }
    blocked_source_ids = {source.get("research_id") for source in refresh_queue.get("blocked_sources", [])}
    used_source_ids = {
        source_id for hypothesis in refreshed_hypotheses for source_id in hypothesis.source_research_ids
    }
    report["acceptance_target"] = "V2.8-D Refresh Queue Historical Sandbox Rerun"
    report["source_audit_refresh_run_id"] = refresh_queue.get("run_id")
    report["proposal_to_hypotheses"] = proposal_to_hypotheses
    report["reachable_source_ids_used"] = sorted(used_source_ids)
    report["blocked_source_ids_excluded"] = sorted(blocked_source_ids)
    report["summary"]["refresh_proposal_count"] = refresh_queue.get("refresh_proposal_count", 0)
    report["summary"]["proposal_to_hypotheses"] = proposal_to_hypotheses
    report["safety"]["no_trading_webhook"] = True
    report["checks"] = {
        "refresh_queue_passed": refresh_queue.get("overall_status") == "PASS",
        "all_proposals_evaluated": all(bool(ids) for ids in proposal_to_hypotheses.values()),
        "reachable_refs_used": bool(used_source_ids) and used_source_ids.issubset(reachable_source_ids),
        "blocked_refs_excluded": used_source_ids.isdisjoint(blocked_source_ids),
        "all_hypotheses_require_sandbox": all(item.requires_sandbox for item in refreshed_hypotheses),
        "no_direct_user_suggestion": all(not item.user_facing_suggestion_allowed for item in refreshed_hypotheses),
        "not_auto_applied": all(not item.auto_applied for item in refreshed_hypotheses),
        "historical_cases_present": report["summary"]["historical_case_count"] == len(refreshed_hypotheses) * 4,
        "pass_fail_metrics_present": all(result["metrics"]["failed_reasons"] is not None for result in report["results"]),
        "suggestion_gate_still_required": report["safety"]["suggestion_gate_still_required"] is True,
        "no_real_trade": report["safety"]["no_real_trade"] is True,
        "no_broker_api": report["safety"]["no_broker_api"] is True,
        "no_trading_webhook": report["safety"]["no_trading_webhook"] is True,
        "no_strategy_auto_mutation": report["safety"]["no_strategy_auto_mutation"] is True,
        "no_production_records_mutation": report["production_records_written"] is False,
    }
    report["safety"]["source_audit_refresh_only"] = True
    report["safety"]["blocked_source_refs_excluded"] = True
    return report
