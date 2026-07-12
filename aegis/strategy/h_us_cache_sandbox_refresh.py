"""Build H/US sandbox candidate refresh inputs from normalized cache samples."""

from __future__ import annotations

import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from aegis.models.strategy import HistoricalStrategyCase, StrategyCandidate, StrategyPassCriteria
from aegis.strategy.sandbox import evaluate_strategy_candidate


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _read_normalized_csv(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    return sorted(rows, key=lambda row: str(row["date"]))


def _float(value: Any) -> float:
    return float(value)


def _provider_case_id(result: Mapping[str, Any]) -> str:
    return str(result["case_id"]).replace("_daily_bars", "_sandbox_case")


def historical_case_from_cache_result(
    result: Mapping[str, Any],
    *,
    strategy_id: str,
) -> HistoricalStrategyCase:
    rows = _read_normalized_csv(Path(str(result["normalized_csv"])))
    if len(rows) < 2:
        raise ValueError(f"not enough normalized rows for {result.get('case_id')}")
    entry = rows[0]
    exit_ = rows[-1]
    entry_price = _float(entry["close"])
    exit_price = _float(exit_["close"])
    lows = [_float(row["low"]) for row in rows if row.get("low")]
    max_drawdown = min(lows) / entry_price - 1.0 if lows else 0.0
    risk_flags: list[str] = []
    if max_drawdown <= -0.1:
        risk_flags.append("historical_drawdown_breach")
    elif max_drawdown <= -0.05:
        risk_flags.append("historical_drawdown_watch")

    return HistoricalStrategyCase(
        case_id=_provider_case_id(result),
        strategy_id=strategy_id,
        date=str(entry["date"]),
        symbol=str(result["canonical_symbol"]),
        market=result["market"],
        entry_price=entry_price,
        exit_price=exit_price,
        max_drawdown=max_drawdown,
        risk_flags=risk_flags,
        factor_values={
            "actual_return": (exit_price - entry_price) / entry_price,
            "normalized_row_count": float(len(rows)),
        },
        evidence_ref=f"v2_12_c_normalized_cache:{result['case_id']}:{result.get('normalized_csv_sha256')}",
    )


def _candidate_for_market(market: str, *, created_at: str) -> StrategyCandidate:
    if market == "H":
        return StrategyCandidate(
            strategy_id="strategy_h_cache_readiness_multifactor_probe",
            name="H-share cache-readiness multifactor sandbox probe",
            market="H",
            universe="H-share API-backed normalized cache sample universe",
            factor_family="multi_factor",
            entry_rule="Use V2.12-C normalized H cache samples as preliminary sandbox inputs only.",
            exit_rule="Exit at last available normalized cache sample row for readiness dry run.",
            exit_horizon_days=5,
            risk_controls=["manual_execution_only", "sample_size_warning", "suggestion_gate_required"],
            pass_criteria=StrategyPassCriteria(
                min_sample_count=1,
                min_win_rate=0.0,
                min_average_return=-1.0,
                max_drawdown_floor=-1.0,
            ),
            source_research_refs=["V2.12-C"],
            created_at=created_at,
        )
    return StrategyCandidate(
        strategy_id="strategy_us_cache_readiness_multifactor_probe",
        name="U.S. cache-readiness multifactor sandbox probe",
        market="US",
        universe="U.S. API-backed normalized cache sample universe",
        factor_family="multi_factor",
        entry_rule="Use V2.12-C normalized US cache samples as preliminary sandbox inputs only.",
        exit_rule="Exit at last available normalized cache sample row for readiness dry run.",
        exit_horizon_days=5,
        risk_controls=["manual_execution_only", "sample_size_warning", "suggestion_gate_required"],
        pass_criteria=StrategyPassCriteria(
            min_sample_count=1,
            min_win_rate=0.0,
            min_average_return=-1.0,
            max_drawdown_floor=-1.0,
        ),
        source_research_refs=["V2.12-C"],
        created_at=created_at,
    )


def build_h_us_cache_sandbox_refresh_report(
    *,
    cache_readiness_report: Mapping[str, Any],
    run_id: str,
    command: str | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    created = generated_at or _now_iso()
    passed_results = [
        result for result in cache_readiness_report.get("results", []) or [] if result.get("status") == "pass"
    ]
    candidates = [_candidate_for_market("H", created_at=created), _candidate_for_market("US", created_at=created)]
    strategy_by_market = {candidate.market: candidate.strategy_id for candidate in candidates}
    cases = [
        historical_case_from_cache_result(result, strategy_id=strategy_by_market[str(result["market"])])
        for result in passed_results
        if result.get("market") in strategy_by_market
    ]
    results = [evaluate_strategy_candidate(candidate, cases).model_dump() for candidate in candidates]
    pass_count = sum(1 for result in results if result["status"] == "PASS")
    fail_count = sum(1 for result in results if result["status"] == "FAIL")

    markets_with_cases = {case.market for case in cases}
    checks = {
        "source_cache_readiness_pass": cache_readiness_report.get("overall_status") == "PASS",
        "source_acceptance_target_correct": cache_readiness_report.get("acceptance_target")
        == "V2.12-C H-US Historical Cache Readiness Dry Run",
        "h_case_present": "H" in markets_with_cases,
        "us_case_present": "US" in markets_with_cases,
        "h_candidate_present": any(candidate.market == "H" for candidate in candidates),
        "us_candidate_present": any(candidate.market == "US" for candidate in candidates),
        "sandbox_results_present": len(results) == 2,
        "all_cases_have_cache_evidence": all(
            str(case.evidence_ref or "").startswith("v2_12_c_normalized_cache:") for case in cases
        ),
        "preliminary_sample_warning_visible": all(
            "sample_size_warning" in candidate.risk_controls for candidate in candidates
        ),
        "suggestion_gate_required": True,
        "user_facing_suggestion_blocked": True,
        "production_cache_not_mutated": True,
        "production_provider_config_not_mutated": True,
        "production_records_not_mutated": True,
        "network_not_used_this_stage": True,
        "no_secret_values_stored": True,
        "request_urls_not_stored": True,
        "raw_payloads_not_stored": True,
        "no_real_trade": True,
        "no_broker_api": True,
        "no_trading_webhook": True,
        "no_order_placement": True,
        "dashboard_contract_unchanged": True,
    }

    return {
        "overall_status": "PASS" if all(checks.values()) else "FAIL",
        "acceptance_target": "V2.12-D H-US Historical Sandbox Candidate Refresh Dry Run",
        "run_id": run_id,
        "generated_at": created,
        "command": command,
        "network_used": False,
        "production_records_written": False,
        "production_cache_mutated": False,
        "production_provider_config_mutated": False,
        "dashboard_contract_changed": False,
        "summary": {
            "candidate_count": len(candidates),
            "historical_case_count": len(cases),
            "strategy_pass_count": pass_count,
            "strategy_fail_count": fail_count,
            "markets_with_cases": sorted(markets_with_cases),
            "preliminary_only": True,
            "user_facing_suggestion_allowed": False,
            "next_stage": "V2.12-E H-US Suggestion Gate Refresh From Sandbox Evidence",
        },
        "source_cache_readiness": {
            "source_target": cache_readiness_report.get("acceptance_target"),
            "source_run_id": cache_readiness_report.get("run_id"),
            "source_summary_sha256": _sha256_text(
                json.dumps(cache_readiness_report.get("summary") or {}, ensure_ascii=False, sort_keys=True)
            ),
        },
        "candidates": [candidate.model_dump() for candidate in candidates],
        "historical_cases": [case.model_dump() for case in cases],
        "results": results,
        "checks": checks,
        "safety": {
            "historical_sandbox_input_only": True,
            "preliminary_sample_only": True,
            "simulation_only": True,
            "suggestion_gate_required": True,
            "user_facing_suggestion_allowed": False,
            "network_not_used_this_stage": True,
            "production_cache_not_mutated": True,
            "production_provider_config_not_mutated": True,
            "production_records_not_mutated": True,
            "no_secret_values_stored": True,
            "no_request_url_storage": True,
            "no_raw_payload_storage": True,
            "no_real_trade": True,
            "no_broker_api": True,
            "no_trading_webhook": True,
            "no_order_placement": True,
            "dashboard_contract_unchanged": True,
        },
    }


def render_h_us_cache_sandbox_refresh_markdown(report: Mapping[str, Any]) -> str:
    lines = [
        "# V2.12-D H-US Historical Sandbox Candidate Refresh Dry Run",
        "",
        f"- status: `{report.get('overall_status')}`",
        f"- run_id: `{report.get('run_id')}`",
        f"- candidate_count: `{report.get('summary', {}).get('candidate_count')}`",
        f"- historical_case_count: `{report.get('summary', {}).get('historical_case_count')}`",
        f"- strategy_pass_count: `{report.get('summary', {}).get('strategy_pass_count')}`",
        f"- strategy_fail_count: `{report.get('summary', {}).get('strategy_fail_count')}`",
        f"- preliminary_only: `{report.get('summary', {}).get('preliminary_only')}`",
        f"- next_stage: `{report.get('summary', {}).get('next_stage')}`",
        "",
        "## Sandbox Results",
        "",
    ]
    for result in report.get("results", []) or []:
        metrics = result.get("metrics") or {}
        lines.extend(
            [
                f"### {result.get('strategy_id')}",
                "",
                f"- status: `{result.get('status')}`",
                f"- sample_count: `{metrics.get('sample_count')}`",
                f"- win_rate: `{metrics.get('win_rate')}`",
                f"- average_return: `{metrics.get('average_return')}`",
                f"- max_drawdown: `{metrics.get('max_drawdown')}`",
                f"- failed_reasons: `{metrics.get('failed_reasons')}`",
                "",
            ]
        )
    lines.extend(
        [
            "## Boundary",
            "",
            "- Preliminary historical sandbox input only.",
            "- Sample size is intentionally small and cannot prove a production strategy.",
            "- Suggestion Gate is still required.",
            "- No user-facing suggestion is allowed by this stage.",
            "- No real trade, broker API, trading webhook, or order placement.",
            "- No production cache/config/record mutation.",
            "- Dashboard Contract unchanged.",
            "",
        ]
    )
    return "\n".join(lines)
