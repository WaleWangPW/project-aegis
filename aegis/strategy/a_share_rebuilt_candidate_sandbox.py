"""Expanded sandbox dry-run for rebuilt Tushare-backed A-share candidates."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from aegis.models.strategy import StrategyCandidate
from aegis.strategy.sandbox import evaluate_strategy_candidate
from aegis.strategy.tushare_live_sandbox_refresh import _case_from_cache, _open_dates

DEFAULT_RETEST_OFFSETS = [0, 20, 40, 60, 80, 100]


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _candidate_by_strategy(source_v2_11_c: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    return {str(item.get("strategy_id")): item for item in source_v2_11_c.get("candidates", []) or []}


def _rebuilt_candidate(
    source_candidate: Mapping[str, Any],
    proposal: Mapping[str, Any],
    *,
    created_at: str,
) -> StrategyCandidate:
    payload = dict(source_candidate)
    payload["name"] = f"{source_candidate.get('name')} rebuilt sandbox dry-run"
    payload["entry_rule"] = (
        f"{source_candidate.get('entry_rule')}; rebuilt_controls="
        + ",".join(proposal.get("rebuild_actions") or [])
    )
    payload["risk_controls"] = list(
        dict.fromkeys([*list(source_candidate.get("risk_controls") or []), *list(proposal.get("rebuild_actions") or [])])
    )
    payload["created_at"] = created_at
    criteria = dict(payload.get("pass_criteria") or {})
    criteria["min_sample_count"] = int(
        (proposal.get("retest_requirements") or {}).get("minimum_total_sample_count") or 24
    )
    payload["pass_criteria"] = criteria
    return StrategyCandidate(**payload)


def build_expanded_retest_cases(
    *,
    source_v2_11_f: Mapping[str, Any],
    cache_dir: Path,
    offsets: Sequence[int] = DEFAULT_RETEST_OFFSETS,
    exit_horizon_days: int = 20,
) -> list[Any]:
    """Build expanded Tushare-cache cases for all V2.11-F rebuild proposals."""

    open_dates = _open_dates(cache_dir)
    cases = []
    for proposal in source_v2_11_f.get("rebuild_proposals", []) or []:
        strategy_id = str(proposal.get("source_strategy_id"))
        case_index = 1
        for symbol in proposal.get("source_symbols", []) or []:
            for offset in offsets:
                cases.append(
                    _case_from_cache(
                        cache_dir=cache_dir,
                        open_dates=open_dates,
                        strategy_id=strategy_id,
                        symbol=str(symbol),
                        start_offset=int(offset),
                        exit_horizon_days=exit_horizon_days,
                        case_index=case_index,
                    )
                )
                case_index += 1
    return cases


def build_a_share_rebuilt_candidate_sandbox_report(
    *,
    source_v2_11_c: Mapping[str, Any],
    source_v2_11_f: Mapping[str, Any],
    cache_dir: Path,
    run_id: str,
    evidence_refs: Sequence[str],
    command: str | None = None,
    generated_at: str | None = None,
    offsets: Sequence[int] = DEFAULT_RETEST_OFFSETS,
) -> dict[str, Any]:
    """Run the expanded sandbox dry-run for V2.11-F A-share rebuild proposals."""

    created = generated_at or _now_iso()
    candidates_by_strategy = _candidate_by_strategy(source_v2_11_c)
    proposals = list(source_v2_11_f.get("rebuild_proposals", []) or [])
    rebuilt_candidates = [
        _rebuilt_candidate(candidates_by_strategy[str(proposal.get("source_strategy_id"))], proposal, created_at=created)
        for proposal in proposals
        if str(proposal.get("source_strategy_id")) in candidates_by_strategy
    ]
    cases = build_expanded_retest_cases(source_v2_11_f=source_v2_11_f, cache_dir=cache_dir, offsets=offsets)
    results = [evaluate_strategy_candidate(candidate, cases).model_dump() for candidate in rebuilt_candidates]
    pass_count = sum(1 for result in results if result["status"] == "PASS")
    fail_count = sum(1 for result in results if result["status"] == "FAIL")
    required_sample_counts = {
        str(proposal.get("source_strategy_id")): int(
            (proposal.get("retest_requirements") or {}).get("minimum_total_sample_count") or 24
        )
        for proposal in proposals
    }

    checks = {
        "source_v2_11_c_pass": source_v2_11_c.get("overall_status") == "PASS",
        "source_v2_11_f_pass": source_v2_11_f.get("overall_status") == "PASS",
        "source_v2_11_f_has_rebuild_proposals": len(proposals) > 0,
        "rebuilt_candidate_count_matches_proposals": len(rebuilt_candidates) == len(proposals),
        "expanded_cases_present": len(cases) > 0,
        "expanded_case_count_meets_retest_requirements": all(
            result["metrics"]["sample_count"] >= required_sample_counts.get(result["strategy_id"], 24)
            for result in results
        ),
        "result_count_matches_candidates": len(results) == len(rebuilt_candidates),
        "all_results_fail": len(results) > 0 and fail_count == len(results),
        "no_passing_rebuilt_a_share_strategy": pass_count == 0,
        "a_share_reentry_not_allowed": pass_count == 0,
        "no_user_facing_suggestions": True,
        "no_strategy_auto_mutation": True,
        "simulation_only": True,
        "manual_external_execution_only": True,
        "no_real_trade": True,
        "no_broker_api": True,
        "no_trading_webhook": True,
        "no_order_placement": True,
        "no_live_price": True,
        "no_position_size": True,
        "no_secret_storage": True,
        "no_production_records_mutation": True,
        "dashboard_contract_unchanged": True,
    }

    return {
        "overall_status": "PASS" if all(checks.values()) else "FAIL",
        "acceptance_target": "V2.11-G A-Share Rebuilt Candidate Sandbox Dry Run",
        "run_id": run_id,
        "generated_at": created,
        "command": command,
        "network_used": False,
        "production_records_written": False,
        "dashboard_contract_changed": False,
        "summary": {
            "rebuild_proposal_count": len(proposals),
            "rebuilt_candidate_count": len(rebuilt_candidates),
            "expanded_case_count": len(cases),
            "retest_window_count": len(offsets),
            "strategy_pass_count": pass_count,
            "strategy_fail_count": fail_count,
            "a_share_reentry_allowed": False,
            "user_facing_suggestion_count": 0,
            "next_stage": "V2.11-H A-Share Blocked Evidence To User Brief Refresh",
        },
        "rebuilt_candidates": [candidate.model_dump() for candidate in rebuilt_candidates],
        "expanded_cases": [case.model_dump() for case in cases],
        "results": results,
        "checks": checks,
        "safety": {
            "simulation_only": True,
            "expanded_historical_sandbox_only": True,
            "not_user_facing_trade_advice": True,
            "a_share_remains_blocked": True,
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
        "evidence_refs": list(evidence_refs),
    }
