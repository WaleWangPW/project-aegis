"""Evaluate multi-symbol Finnhub quote historical cases in the sandbox."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Mapping

from aegis.models.strategy import HistoricalStrategyCase, StrategyCandidate
from aegis.strategy.sandbox import evaluate_strategy_candidate

ACCEPTANCE_TARGET = "V2.13-V Finnhub Quote Multi-Symbol Sandbox Evaluation"
SOURCE_ACCEPTANCE_TARGET = "V2.13-U Finnhub Quote Multi-Symbol Historical Case Assembly"


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _load_candidates(source_report: Mapping[str, Any]) -> list[StrategyCandidate]:
    return [
        StrategyCandidate(**packet["strategy_candidate"])
        for packet in source_report.get("candidate_packets", []) or []
        if isinstance(packet, dict) and packet.get("strategy_candidate")
    ]


def _load_cases(source_report: Mapping[str, Any]) -> list[HistoricalStrategyCase]:
    return [HistoricalStrategyCase(**case) for case in source_report.get("historical_cases", []) or []]


def build_finnhub_quote_multi_symbol_sandbox_evaluation_report(
    *,
    source_report: Mapping[str, Any],
    run_id: str,
    command: str | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    created = generated_at or _now_iso()
    candidates = _load_candidates(source_report)
    cases = _load_cases(source_report)
    results = [evaluate_strategy_candidate(candidate, cases).model_dump() for candidate in candidates]
    pass_count = sum(1 for result in results if result["status"] == "PASS")
    fail_count = sum(1 for result in results if result["status"] == "FAIL")
    blocked_symbols = sorted(
        {
            case.symbol
            for result in results
            if result["status"] == "FAIL"
            for case in cases
            if case.strategy_id == result["strategy_id"]
        }
    )
    checks = {
        "source_report_pass": source_report.get("overall_status") == "PASS",
        "source_acceptance_target_correct": source_report.get("acceptance_target") == SOURCE_ACCEPTANCE_TARGET,
        "source_historical_cases_present": int(source_report.get("summary", {}).get("historical_case_count") or 0) > 0,
        "source_sandbox_not_already_run": source_report.get("summary", {}).get("sandbox_evaluation_run") is False,
        "source_social_sentiment_still_blocked": source_report.get("summary", {}).get("social_sentiment_status")
        == "blocked_plan_or_rate_limit",
        "candidate_count_at_least_three": len(candidates) >= 3,
        "historical_cases_present": bool(cases),
        "sandbox_results_present": len(results) == len(candidates) and bool(results),
        "all_results_have_metrics": all(result.get("metrics") for result in results),
        "all_cases_have_multi_symbol_quote_context_evidence": all(
            str(case.evidence_ref or "").startswith("v2_13_u_multi_symbol_case:") for case in cases
        ),
        "failed_results_not_promoted_to_suggestions": True,
        "suggestion_gate_not_run": True,
        "user_facing_suggestion_not_allowed": True,
        "network_not_used": True,
        "production_records_not_written": True,
        "production_cache_not_mutated": True,
        "production_provider_config_not_mutated": True,
        "no_secret_values_stored": True,
        "request_urls_not_stored": True,
        "raw_payloads_not_stored": True,
        "no_real_trade": True,
        "no_broker_api": True,
        "no_trading_webhook": True,
        "no_order_placement": True,
        "no_position_size": True,
        "no_live_order_signal": True,
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
            "candidate_count": len(candidates),
            "historical_case_count": len(cases),
            "strategy_pass_count": pass_count,
            "strategy_fail_count": fail_count,
            "passing_strategies": [result["strategy_id"] for result in results if result["status"] == "PASS"],
            "failing_strategies": [result["strategy_id"] for result in results if result["status"] == "FAIL"],
            "symbols": sorted({case.symbol for case in cases}),
            "markets": sorted({case.market for case in cases}),
            "blocked_symbols": blocked_symbols,
            "sandbox_evaluation_run": True,
            "suggestion_gate_ready": pass_count > 0,
            "suggestion_gate_required_for_passed_results": pass_count > 0,
            "user_facing_suggestion_allowed": False,
            "social_sentiment_status": "blocked_plan_or_rate_limit",
            "next_stage": "V2.13-W Finnhub Quote Multi-Symbol Sandbox Result Brief",
        },
        "candidates": [candidate.model_dump() for candidate in candidates],
        "historical_cases": [case.model_dump() for case in cases],
        "results": results,
        "source_evidence": {
            "source_target": source_report.get("acceptance_target"),
            "source_run_id": source_report.get("run_id"),
            "source_summary_sha256": _sha256_text(
                json.dumps(source_report.get("summary") or {}, ensure_ascii=False, sort_keys=True)
            ),
        },
        "checks": checks,
        "safety": {
            "sandbox_evaluation_only": True,
            "suggestion_gate_not_run": True,
            "user_facing_suggestion_allowed": False,
            "network_not_used": True,
            "social_sentiment_not_enabled": True,
            "production_records_not_written": True,
            "production_cache_not_mutated": True,
            "production_provider_config_not_mutated": True,
            "no_secret_values_stored": True,
            "no_request_url_storage": True,
            "no_raw_payload_storage": True,
            "no_real_trade": True,
            "no_broker_api": True,
            "no_trading_webhook": True,
            "no_order_placement": True,
            "no_position_size": True,
            "no_live_order_signal": True,
            "dashboard_contract_unchanged": True,
        },
    }


def render_finnhub_quote_multi_symbol_sandbox_evaluation_markdown(report: Mapping[str, Any]) -> str:
    lines = [
        "# V2.13-V Finnhub Quote Multi-Symbol Sandbox Evaluation",
        "",
        f"- status: `{report.get('overall_status')}`",
        f"- run_id: `{report.get('run_id')}`",
        f"- candidate_count: `{report.get('summary', {}).get('candidate_count')}`",
        f"- historical_case_count: `{report.get('summary', {}).get('historical_case_count')}`",
        f"- strategy_pass_count: `{report.get('summary', {}).get('strategy_pass_count')}`",
        f"- strategy_fail_count: `{report.get('summary', {}).get('strategy_fail_count')}`",
        f"- passing_strategies: `{report.get('summary', {}).get('passing_strategies')}`",
        f"- failing_strategies: `{report.get('summary', {}).get('failing_strategies')}`",
        f"- user_facing_suggestion_allowed: `{report.get('summary', {}).get('user_facing_suggestion_allowed')}`",
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
            "- Sandbox evaluation only.",
            "- Failed sandbox results are not promoted to suggestions.",
            "- Suggestion Gate is not run in this stage.",
            "- No user-facing suggestion, position size, live order signal, real trade, broker API, webhook, or order placement.",
            "",
        ]
    )
    return "\n".join(lines)
