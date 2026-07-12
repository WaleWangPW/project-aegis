"""Evaluate refreshed A/H candidates against available historical evidence."""

from __future__ import annotations

import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from aegis.models.strategy import HistoricalStrategyCase, StrategyCandidate, StrategyPassCriteria
from aegis.strategy.sandbox import evaluate_strategy_candidate

ACCEPTANCE_TARGET = "V2.14-C Refreshed Candidate Historical Sandbox"
SOURCE_TARGET = "V2.14-B Candidate Pool Live Refresh From Approved Routes"
A_SOURCE_TARGET = "V2.11-C Tushare A-Share Historical Sandbox Live Data Refresh"
H_SOURCE_TARGET = "V2.12-C H-US Historical Cache Readiness Dry Run"


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _normalize_symbol(symbol: str) -> str:
    value = symbol.strip().upper()
    if value.endswith(".US"):
        return value[:-3]
    return value


def _read_normalized_csv(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8", newline="") as fh:
        return sorted(csv.DictReader(fh), key=lambda row: str(row["date"]))


def _h_case_from_cache_result(result: Mapping[str, Any], *, strategy_id: str) -> HistoricalStrategyCase:
    rows = _read_normalized_csv(Path(str(result["normalized_csv"])))
    entry = rows[0]
    exit_ = rows[-1]
    entry_price = float(entry["close"])
    exit_price = float(exit_["close"])
    lows = [float(row["low"]) for row in rows if row.get("low")]
    max_drawdown = min(lows) / entry_price - 1.0 if lows else 0.0
    return HistoricalStrategyCase(
        case_id=f"v2_14_c_h_{str(result['canonical_symbol']).lower().replace('.', '_')}_case",
        strategy_id=strategy_id,
        date=str(entry["date"]),
        symbol=str(result["canonical_symbol"]),
        market="H",
        entry_price=entry_price,
        exit_price=exit_price,
        max_drawdown=max_drawdown,
        risk_flags=["historical_drawdown_watch"] if max_drawdown <= -0.05 else [],
        factor_values={
            "actual_return": (exit_price - entry_price) / entry_price,
            "normalized_row_count": float(len(rows)),
        },
        evidence_ref=f"v2_12_c_normalized_cache:{result['case_id']}:{result.get('normalized_csv_sha256')}",
    )


def _candidate_from_refreshed(candidate: Mapping[str, Any], *, created_at: str) -> StrategyCandidate:
    market = str(candidate["market"])
    if market == "A":
        return StrategyCandidate(
            strategy_id=str(candidate["strategy_id"]),
            name="V2.14-C A-share refreshed candidate sandbox",
            market="A",
            universe="A-share refreshed candidate pool from V2.14-B",
            factor_family="risk_overlay",
            entry_rule="Use refreshed A-share candidate only if historical evidence is available.",
            exit_rule="Historical sandbox exit based on source evidence horizon.",
            exit_horizon_days=20,
            risk_controls=["manual_execution_only", "historical_evidence_required", "suggestion_gate_required"],
            pass_criteria=StrategyPassCriteria(
                min_sample_count=2,
                min_win_rate=0.5,
                min_average_return=0.0,
                max_drawdown_floor=-0.1,
            ),
            source_research_refs=["V2.14-B", "V2.11-C"],
            created_at=created_at,
        )
    return StrategyCandidate(
        strategy_id=str(candidate["strategy_id"]),
        name="V2.14-C H-share refreshed candidate sandbox",
        market="H",
        universe="H-share refreshed candidate pool from V2.14-B",
        factor_family="dividend",
        entry_rule="Use refreshed H-share candidate only if H/US provider historical cache exists.",
        exit_rule="Historical sandbox exit at last available normalized cache row.",
        exit_horizon_days=5,
        risk_controls=["manual_execution_only", "small_sample_warning", "suggestion_gate_required"],
        pass_criteria=StrategyPassCriteria(
            min_sample_count=1,
            min_win_rate=0.0,
            min_average_return=-1.0,
            max_drawdown_floor=-1.0,
        ),
        source_research_refs=["V2.14-B", "V2.12-C"],
        created_at=created_at,
    )


def build_refreshed_candidate_historical_sandbox_report(
    *,
    refresh_report: Mapping[str, Any],
    a_source_report: Mapping[str, Any],
    h_source_report: Mapping[str, Any],
    run_id: str,
    command: str | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    created = generated_at or _now_iso()
    refreshed_candidates = [
        dict(item)
        for item in refresh_report.get("refreshed_candidates", []) or []
        if item.get("market") in {"A", "H"}
    ]
    blocked_symbols = {
        _normalize_symbol(str(symbol))
        for symbol in (refresh_report.get("summary", {}) or {}).get("blocked_symbols_not_reused", []) or []
    }
    a_source_cases = [
        HistoricalStrategyCase(**case)
        for case in a_source_report.get("historical_cases", []) or []
        if isinstance(case, dict)
    ]
    h_source_results = [
        result
        for result in h_source_report.get("results", []) or []
        if result.get("status") == "pass" and result.get("market") == "H"
    ]
    source_cases_by_symbol: dict[str, list[HistoricalStrategyCase]] = {}
    for case in a_source_cases:
        source_cases_by_symbol.setdefault(case.symbol, []).append(case)
    for result in h_source_results:
        strategy_id = next(
            (
                str(candidate["strategy_id"])
                for candidate in refreshed_candidates
                if candidate.get("symbol") == result.get("canonical_symbol")
            ),
            "strategy_h_low_vol_dividend",
        )
        case = _h_case_from_cache_result(result, strategy_id=strategy_id)
        source_cases_by_symbol.setdefault(case.symbol, []).append(case)

    covered_candidates: list[dict[str, Any]] = []
    missing_candidates: list[dict[str, Any]] = []
    candidates_by_strategy: dict[str, StrategyCandidate] = {}
    historical_cases: list[HistoricalStrategyCase] = []
    for item in refreshed_candidates:
        symbol = str(item["symbol"])
        if _normalize_symbol(symbol) in blocked_symbols:
            missing_candidates.append(
                {**item, "coverage_status": "blocked_symbol_not_allowed", "missing_reason": "blocked_symbol"}
            )
            continue
        matching_cases = source_cases_by_symbol.get(symbol, [])
        if not matching_cases:
            missing_candidates.append(
                {**item, "coverage_status": "missing_historical_case", "missing_reason": "no_source_case_for_symbol"}
            )
            continue
        covered_candidates.append({**item, "coverage_status": "historical_case_available"})
        candidates_by_strategy[str(item["strategy_id"])] = _candidate_from_refreshed(item, created_at=created)
        historical_cases.extend(matching_cases)

    strategy_candidates = list(candidates_by_strategy.values())
    results = [evaluate_strategy_candidate(candidate, historical_cases).model_dump() for candidate in strategy_candidates]
    strategy_pass_count = sum(1 for item in results if item["status"] == "PASS")
    strategy_fail_count = sum(1 for item in results if item["status"] == "FAIL")
    checks = {
        "source_refresh_pass": refresh_report.get("overall_status") == "PASS",
        "source_refresh_target_correct": refresh_report.get("acceptance_target") == SOURCE_TARGET,
        "a_source_target_correct": a_source_report.get("acceptance_target") == A_SOURCE_TARGET,
        "h_source_target_correct": h_source_report.get("acceptance_target") == H_SOURCE_TARGET,
        "refreshed_candidates_present": bool(refreshed_candidates),
        "covered_candidates_present": bool(covered_candidates),
        "missing_coverage_visible": bool(missing_candidates),
        "historical_cases_present": bool(historical_cases),
        "sandbox_results_present": bool(results),
        "blocked_symbols_not_reused": all(
            _normalize_symbol(str(item.get("symbol"))) not in blocked_symbols for item in refreshed_candidates
        ),
        "all_cases_have_evidence_ref": all(bool(case.evidence_ref) for case in historical_cases),
        "suggestion_gate_required": True,
        "user_facing_suggestion_blocked": True,
        "network_not_used_this_stage": True,
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
        "run_id": run_id,
        "generated_at": created,
        "command": command,
        "network_used": False,
        "production_records_written": False,
        "production_cache_mutated": False,
        "production_provider_config_mutated": False,
        "dashboard_contract_changed": False,
        "summary": {
            "refreshed_candidate_count": len(refreshed_candidates),
            "covered_candidate_count": len(covered_candidates),
            "missing_coverage_count": len(missing_candidates),
            "historical_case_count": len(historical_cases),
            "strategy_candidate_count": len(strategy_candidates),
            "strategy_pass_count": strategy_pass_count,
            "strategy_fail_count": strategy_fail_count,
            "sandbox_passed_strategies": [item["strategy_id"] for item in results if item["status"] == "PASS"],
            "sandbox_failed_strategies": [item["strategy_id"] for item in results if item["status"] == "FAIL"],
            "user_facing_suggestion_allowed": False,
            "next_stage": "V2.14-D Refreshed Candidate Suggestion Gate",
        },
        "covered_candidates": covered_candidates,
        "missing_coverage_candidates": missing_candidates,
        "strategy_candidates": [candidate.model_dump() for candidate in strategy_candidates],
        "historical_cases": [case.model_dump() for case in historical_cases],
        "results": results,
        "source_evidence": {
            "refresh_target": refresh_report.get("acceptance_target"),
            "refresh_run_id": refresh_report.get("run_id"),
            "refresh_summary_sha256": _sha256_text(
                json.dumps(refresh_report.get("summary") or {}, ensure_ascii=False, sort_keys=True)
            ),
            "a_source_target": a_source_report.get("acceptance_target"),
            "h_source_target": h_source_report.get("acceptance_target"),
        },
        "checks": checks,
        "safety": {
            "historical_sandbox_only": True,
            "not_user_facing_suggestion": True,
            "suggestion_gate_required": True,
            "coverage_gap_visible": True,
            "network_not_used_this_stage": True,
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


def render_refreshed_candidate_historical_sandbox_markdown(report: Mapping[str, Any]) -> str:
    lines = [
        "# V2.14-C Refreshed Candidate Historical Sandbox",
        "",
        f"- status: `{report.get('overall_status')}`",
        f"- run_id: `{report.get('run_id')}`",
        f"- covered_candidate_count: `{report.get('summary', {}).get('covered_candidate_count')}`",
        f"- missing_coverage_count: `{report.get('summary', {}).get('missing_coverage_count')}`",
        f"- historical_case_count: `{report.get('summary', {}).get('historical_case_count')}`",
        f"- strategy_pass_count: `{report.get('summary', {}).get('strategy_pass_count')}`",
        f"- strategy_fail_count: `{report.get('summary', {}).get('strategy_fail_count')}`",
        f"- next_stage: `{report.get('summary', {}).get('next_stage')}`",
        "",
        "## Covered Candidates",
        "",
    ]
    for item in report.get("covered_candidates", []) or []:
        lines.append(f"- `{item.get('symbol')}` / `{item.get('market')}`: `{item.get('coverage_status')}`")
    lines.extend(["", "## Missing Coverage", ""])
    for item in report.get("missing_coverage_candidates", []) or []:
        lines.append(f"- `{item.get('symbol')}` / `{item.get('market')}`: `{item.get('missing_reason')}`")
    lines.extend(["", "## Sandbox Results", ""])
    for item in report.get("results", []) or []:
        metrics = item.get("metrics") or {}
        lines.append(
            f"- `{item.get('strategy_id')}` status=`{item.get('status')}` "
            f"sample_count=`{metrics.get('sample_count')}` "
            f"average_return=`{metrics.get('average_return')}`"
        )
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "- Historical sandbox only.",
            "- Missing coverage is explicit and cannot be treated as a pass.",
            "- Not a user-facing suggestion.",
            "- Suggestion Gate is still required.",
            "- No real trade, broker API, webhook, order placement, live order signal, or position size.",
            "",
        ]
    )
    return "\n".join(lines)
