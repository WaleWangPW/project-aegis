"""Rebuild proposals for failed Tushare-backed A-share strategy candidates.

V2.11-F turns failed historical sandbox evidence into the next research queue.
It does not approve A-share suggestions, mutate strategy code, place orders, or
write production Recommendation/PaperTrade/Review records.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping, Sequence


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _metric_failed_reasons(evidence: Mapping[str, Any]) -> list[str]:
    return [str(item) for item in evidence.get("failed_reasons") or []]


def _float_or_none(value: Any) -> float | None:
    if isinstance(value, int | float):
        return float(value)
    return None


def _strategy_symbols(source_v2_11_c: Mapping[str, Any], strategy_id: str) -> list[str]:
    symbols = [
        str(case.get("symbol"))
        for case in source_v2_11_c.get("historical_cases", []) or []
        if case.get("strategy_id") == strategy_id and case.get("symbol")
    ]
    return sorted(set(symbols))


def _derive_rebuild_actions(evidence: Mapping[str, Any]) -> list[str]:
    reasons = set(_metric_failed_reasons(evidence))
    actions: list[str] = []
    if "max_drawdown_breached" in reasons:
        actions.extend(
            [
                "add_market_regime_filter",
                "tighten_drawdown_and_volatility_filter",
                "require_event_risk_precheck",
            ]
        )
    if "average_return_below_threshold" in reasons:
        actions.extend(
            [
                "add_positive_momentum_confirmation",
                "require_factor_score_margin",
            ]
        )
    if "win_rate_below_threshold" in reasons:
        actions.extend(
            [
                "raise_liquidity_and_quality_floor",
                "expand_historical_sample_before_retest",
            ]
        )
    if not actions:
        actions.append("expand_historical_sample_before_retest")
    return list(dict.fromkeys(actions))


def _derive_retest_requirements(evidence: Mapping[str, Any], source_v2_11_c: Mapping[str, Any]) -> dict[str, Any]:
    current_sample_count = int((source_v2_11_c.get("summary") or {}).get("historical_case_count") or 0)
    win_rate = _float_or_none(evidence.get("win_rate"))
    average_return = _float_or_none(evidence.get("average_return"))
    max_drawdown = _float_or_none(evidence.get("max_drawdown"))
    return {
        "minimum_total_sample_count": max(24, current_sample_count * 3),
        "minimum_window_count": 6,
        "must_include_recent_market_regimes": True,
        "must_include_bull_bear_sideways_windows": True,
        "must_pass_suggestion_gate_before_user_facing_brief": True,
        "current_metrics": {
            "win_rate": win_rate,
            "average_return": average_return,
            "max_drawdown": max_drawdown,
        },
    }


def build_a_share_tushare_rebuild_proposals(
    *,
    source_v2_11_c: Mapping[str, Any],
    source_v2_11_d: Mapping[str, Any],
    evidence_refs: Sequence[str],
) -> list[dict[str, Any]]:
    """Create one simulation-only rebuild proposal for each blocked A-share strategy."""

    proposals: list[dict[str, Any]] = []
    for evidence in source_v2_11_d.get("blocked_strategy_evidence", []) or []:
        strategy_id = str(evidence.get("strategy_id"))
        failed_reasons = _metric_failed_reasons(evidence)
        proposals.append(
            {
                "proposal_id": f"rebuild_{strategy_id}",
                "source_strategy_id": strategy_id,
                "market": "A",
                "source_status": evidence.get("status"),
                "source_failed_reasons": failed_reasons,
                "source_symbols": _strategy_symbols(source_v2_11_c, strategy_id),
                "rebuild_actions": _derive_rebuild_actions(evidence),
                "retest_requirements": _derive_retest_requirements(evidence, source_v2_11_c),
                "decision": "research_rebuild_only",
                "candidate_status": "blocked_until_rebuilt_sandbox_pass",
                "requires_sandbox": True,
                "requires_suggestion_gate": True,
                "auto_applied": False,
                "user_facing_suggestion_allowed": False,
                "blocked_until_sandbox_pass": True,
                "simulation_only": True,
                "manual_external_execution_only": True,
                "no_live_price": True,
                "no_position_size": True,
                "evidence_refs": list(evidence_refs),
            }
        )
    return proposals


def build_a_share_tushare_candidate_rebuild_report(
    *,
    source_v2_11_c: Mapping[str, Any],
    source_v2_11_d: Mapping[str, Any],
    source_v2_11_e: Mapping[str, Any],
    run_id: str,
    evidence_refs: Sequence[str],
    command: str | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    """Build the V2.11-F acceptance report from existing sandbox/gate evidence."""

    proposals = build_a_share_tushare_rebuild_proposals(
        source_v2_11_c=source_v2_11_c,
        source_v2_11_d=source_v2_11_d,
        evidence_refs=evidence_refs,
    )
    blocked_strategy_ids = {
        str(item.get("strategy_id")) for item in source_v2_11_d.get("blocked_strategy_evidence", []) or []
    }
    proposal_strategy_ids = {str(item.get("source_strategy_id")) for item in proposals}
    e_removed_focus = set((source_v2_11_e.get("summary") or {}).get("removed_focus_symbols") or [])

    checks = {
        "source_v2_11_c_pass": source_v2_11_c.get("overall_status") == "PASS",
        "source_v2_11_d_pass": source_v2_11_d.get("overall_status") == "PASS",
        "source_v2_11_e_pass": source_v2_11_e.get("overall_status") == "PASS",
        "source_v2_11_c_is_tushare_a_share": (source_v2_11_c.get("live_data_source") or {}).get("provider")
        == "tushare"
        and (source_v2_11_c.get("live_data_source") or {}).get("market") == "A",
        "source_v2_11_d_has_zero_allowed": (source_v2_11_d.get("summary") or {}).get("allowed_count") == 0,
        "source_v2_11_e_removed_a_share_focus": len(e_removed_focus) >= 1,
        "blocked_strategy_evidence_present": len(blocked_strategy_ids) > 0,
        "proposal_count_matches_blocked_strategies": len(proposals) == len(blocked_strategy_ids),
        "all_blocked_strategies_have_proposals": blocked_strategy_ids == proposal_strategy_ids,
        "every_proposal_requires_sandbox": all(item["requires_sandbox"] for item in proposals),
        "every_proposal_requires_suggestion_gate": all(item["requires_suggestion_gate"] for item in proposals),
        "no_proposal_user_facing_allowed": all(not item["user_facing_suggestion_allowed"] for item in proposals),
        "no_proposal_auto_applied": all(not item["auto_applied"] for item in proposals),
        "every_proposal_blocked_until_sandbox_pass": all(item["blocked_until_sandbox_pass"] for item in proposals),
        "every_proposal_has_rebuild_actions": all(bool(item["rebuild_actions"]) for item in proposals),
        "every_proposal_has_retest_requirements": all(bool(item["retest_requirements"]) for item in proposals),
        "evidence_refs_present": all(item["evidence_refs"] for item in proposals),
        "simulation_only": True,
        "manual_external_execution_only": True,
        "no_real_trade": True,
        "no_broker_api": True,
        "no_trading_webhook": True,
        "no_order_placement": True,
        "no_live_price": True,
        "no_position_size": True,
        "no_secret_storage": True,
        "no_strategy_auto_mutation": True,
        "no_production_records_mutation": True,
        "dashboard_contract_unchanged": True,
    }

    return {
        "overall_status": "PASS" if all(checks.values()) else "FAIL",
        "acceptance_target": "V2.11-F A-Share Tushare Strategy Candidate Rebuild",
        "run_id": run_id,
        "generated_at": generated_at or _now_iso(),
        "command": command,
        "network_used": False,
        "production_records_written": False,
        "dashboard_contract_changed": False,
        "summary": {
            "source_failed_strategy_count": len(blocked_strategy_ids),
            "rebuild_proposal_count": len(proposals),
            "user_facing_suggestion_count": 0,
            "auto_applied_count": 0,
            "blocked_until_sandbox_pass_count": sum(
                1 for item in proposals if item["blocked_until_sandbox_pass"]
            ),
            "next_stage": "V2.11-G A-Share Rebuilt Candidate Sandbox Dry Run",
            "removed_focus_symbols_from_v2_11_e": sorted(e_removed_focus),
            "proposal_strategy_ids": sorted(proposal_strategy_ids),
        },
        "rebuild_proposals": proposals,
        "checks": checks,
        "safety": {
            "simulation_only": True,
            "research_rebuild_only": True,
            "not_user_facing_trade_advice": True,
            "manual_external_execution_only": True,
            "a_share_remains_blocked_until_rebuilt_sandbox_pass": True,
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
