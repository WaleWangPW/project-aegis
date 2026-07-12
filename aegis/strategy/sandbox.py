"""Historical strategy sandbox.

The sandbox evaluates explicit strategy candidates against historical cases.
It is not a live recommendation path, does not mutate strategy definitions,
and does not write production Recommendation/PaperTrade/Review records.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Sequence

from aegis.models.strategy import (
    HistoricalStrategyCase,
    StrategyCandidate,
    StrategySandboxMetrics,
    StrategySandboxResult,
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def _return_pct(case: HistoricalStrategyCase) -> float:
    return (case.exit_price - case.entry_price) / case.entry_price


def _risk_flag_counts(cases: Sequence[HistoricalStrategyCase]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for case in cases:
        for flag in case.risk_flags:
            counts[flag] = counts.get(flag, 0) + 1
    return counts


def evaluate_strategy_candidate(
    candidate: StrategyCandidate,
    historical_cases: Sequence[HistoricalStrategyCase],
) -> StrategySandboxResult:
    relevant_cases = [case for case in historical_cases if case.strategy_id == candidate.strategy_id]
    eligible_cases = [case for case in relevant_cases if case.eligible]
    returns = [_return_pct(case) for case in eligible_cases]
    win_rate = (sum(1 for value in returns if value > 0) / len(returns)) if returns else None
    average_return = (sum(returns) / len(returns)) if returns else None
    max_drawdown = min((case.max_drawdown for case in eligible_cases), default=None)
    turnover_proxy = len(eligible_cases) / len({case.date for case in eligible_cases}) if eligible_cases else None

    criteria = candidate.pass_criteria
    failed_reasons: list[str] = []
    if len(eligible_cases) < criteria.min_sample_count:
        failed_reasons.append("sample_count_below_minimum")
    if win_rate is None or win_rate < criteria.min_win_rate:
        failed_reasons.append("win_rate_below_threshold")
    if average_return is None or average_return < criteria.min_average_return:
        failed_reasons.append("average_return_below_threshold")
    if max_drawdown is None or max_drawdown < criteria.max_drawdown_floor:
        failed_reasons.append("max_drawdown_breached")

    metrics = StrategySandboxMetrics(
        strategy_id=candidate.strategy_id,
        sample_count=len(relevant_cases),
        eligible_case_count=len(eligible_cases),
        win_rate=win_rate,
        average_return=average_return,
        max_drawdown=max_drawdown,
        turnover_proxy=turnover_proxy,
        exposure_count=len({(case.market, case.symbol) for case in eligible_cases}),
        risk_flag_counts=_risk_flag_counts(eligible_cases),
        failed_reasons=failed_reasons,
    )

    return StrategySandboxResult(
        strategy_id=candidate.strategy_id,
        status="PASS" if not failed_reasons else "FAIL",
        metrics=metrics,
        safety={
            "simulation_only": True,
            "no_real_trade": True,
            "no_broker_api": True,
            "no_webhook": True,
            "no_strategy_auto_mutation": True,
            "no_production_records_mutation": True,
        },
        notes=[
            "Historical sandbox result only; user-facing suggestions still require recommendation and risk gates.",
            "Evidence is based on supplied historical cases, not future prediction.",
        ],
    )


def build_strategy_sandbox_report(
    candidates: Sequence[StrategyCandidate],
    historical_cases: Sequence[HistoricalStrategyCase],
    *,
    run_id: str,
    command: str | None = None,
    historical_cache_file_count: int = 0,
) -> dict:
    results = [evaluate_strategy_candidate(candidate, historical_cases) for candidate in candidates]
    pass_count = sum(1 for result in results if result.status == "PASS")
    fail_count = sum(1 for result in results if result.status == "FAIL")

    return {
        "overall_status": "PASS" if pass_count >= 1 and fail_count >= 1 else "FAIL",
        "generated_at": _now_iso(),
        "run_id": run_id,
        "command": command,
        "acceptance_target": "V2.1-A Historical Strategy Sandbox",
        "isolated": True,
        "network_used": False,
        "production_records_written": False,
        "dashboard_contract_changed": False,
        "historical_cache_file_count": historical_cache_file_count,
        "summary": {
            "candidate_count": len(candidates),
            "historical_case_count": len(historical_cases),
            "pass_count": pass_count,
            "fail_count": fail_count,
            "passing_strategies": [result.strategy_id for result in results if result.status == "PASS"],
            "failing_strategies": [result.strategy_id for result in results if result.status == "FAIL"],
        },
        "results": [result.model_dump() for result in results],
        "safety": {
            "simulation_only": True,
            "no_real_trade": True,
            "no_broker_api": True,
            "no_webhook": True,
            "no_secret_storage": True,
            "no_strategy_auto_mutation": True,
            "no_production_records_mutation": True,
            "dashboard_contract_unchanged": True,
            "suggestion_gate_still_required": True,
        },
    }
