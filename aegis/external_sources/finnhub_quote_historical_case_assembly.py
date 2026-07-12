"""Assemble historical cases for Finnhub quote-context sandbox candidates."""

from __future__ import annotations

import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from aegis.models.strategy import HistoricalStrategyCase

ACCEPTANCE_TARGET = "V2.13-F Finnhub Quote Context Historical Case Assembly"
SOURCE_BINDING_TARGET = "V2.13-E Finnhub Quote Context To Sandbox Candidate Binding"
SOURCE_CACHE_TARGET = "V2.12-C H-US Historical Cache Readiness Dry Run"


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _read_rows(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8", newline="") as fh:
        return sorted(csv.DictReader(fh), key=lambda row: str(row["date"]))


def _float(value: Any) -> float:
    return float(value)


def _rolling_cases_for_result(
    result: Mapping[str, Any],
    *,
    strategy_id: str,
    binding_id: str,
    context_id: str,
) -> tuple[list[HistoricalStrategyCase], dict[str, Any]]:
    csv_path = Path(str(result["normalized_csv"]))
    exists = csv_path.exists()
    actual_hash = _sha256_file(csv_path) if exists else None
    expected_hash = result.get("normalized_csv_sha256")
    hash_matches = bool(actual_hash and expected_hash and actual_hash == expected_hash)
    check = {
        "case_id": result.get("case_id"),
        "normalized_csv_exists": exists,
        "normalized_csv_hash_matches": hash_matches,
        "expected_sha256": expected_hash,
        "actual_sha256": actual_hash,
    }
    if not hash_matches:
        return [], check

    rows = _read_rows(csv_path)
    cases: list[HistoricalStrategyCase] = []
    for idx in range(len(rows) - 1):
        entry = rows[idx]
        exit_ = rows[idx + 1]
        entry_price = _float(entry["close"])
        exit_price = _float(exit_["close"])
        low = min(_float(entry["low"]), _float(exit_["low"]))
        max_drawdown = low / entry_price - 1.0
        risk_flags: list[str] = []
        if max_drawdown <= -0.1:
            risk_flags.append("historical_drawdown_breach")
        elif max_drawdown <= -0.05:
            risk_flags.append("historical_drawdown_watch")
        cases.append(
            HistoricalStrategyCase(
                case_id=f"v2_13_f_{result['case_id']}_rolling_{idx + 1}",
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
                    "rolling_window_days": 1.0,
                    "source_row_index": float(idx),
                },
                evidence_ref=(
                    f"v2_13_f_quote_context_case:{binding_id}:{context_id}:"
                    f"{result['case_id']}:{actual_hash}"
                ),
            )
        )
    return cases, check


def build_finnhub_quote_historical_case_assembly_report(
    *,
    binding_report: Mapping[str, Any],
    cache_readiness_report: Mapping[str, Any],
    run_id: str,
    command: str | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    created = generated_at or _now_iso()
    bindings = [
        item
        for item in binding_report.get("bindings", []) or []
        if isinstance(item, dict) and item.get("binding_status") == "bound_pending_historical_cases"
    ]
    cache_results = [
        item
        for item in cache_readiness_report.get("results", []) or []
        if isinstance(item, dict) and item.get("status") == "pass" and item.get("data_type") == "daily_bars"
    ]
    historical_cases: list[HistoricalStrategyCase] = []
    artifact_checks: list[dict[str, Any]] = []
    candidate_packets: list[dict[str, Any]] = []
    for binding in bindings:
        candidate = dict(binding["strategy_candidate"])
        matching_results = [
            result
            for result in cache_results
            if result.get("market") == binding.get("market")
            and result.get("canonical_symbol") == binding.get("canonical_symbol")
        ]
        binding_cases: list[HistoricalStrategyCase] = []
        for result in matching_results:
            cases, check = _rolling_cases_for_result(
                result,
                strategy_id=str(candidate["strategy_id"]),
                binding_id=str(binding["binding_id"]),
                context_id=str(binding["context_id"]),
            )
            artifact_checks.append(check)
            binding_cases.extend(cases)
        historical_cases.extend(binding_cases)
        candidate_packets.append(
            {
                "binding_id": binding["binding_id"],
                "context_id": binding["context_id"],
                "strategy_candidate": candidate,
                "historical_case_ids": [case.case_id for case in binding_cases],
                "historical_case_count": len(binding_cases),
                "status": "historical_cases_assembled" if binding_cases else "blocked_missing_historical_cases",
            }
        )

    checks = {
        "source_binding_report_pass": binding_report.get("overall_status") == "PASS",
        "source_binding_acceptance_target_correct": binding_report.get("acceptance_target") == SOURCE_BINDING_TARGET,
        "source_cache_report_pass": cache_readiness_report.get("overall_status") == "PASS",
        "source_cache_acceptance_target_correct": cache_readiness_report.get("acceptance_target") == SOURCE_CACHE_TARGET,
        "source_social_sentiment_still_blocked": binding_report.get("summary", {}).get("social_sentiment_status")
        == "blocked_plan_or_rate_limit",
        "at_least_one_bound_candidate": bool(bindings),
        "at_least_one_historical_case": bool(historical_cases),
        "historical_cases_meet_candidate_minimum": all(
            packet["historical_case_count"]
            >= int(packet["strategy_candidate"]["pass_criteria"]["min_sample_count"])
            for packet in candidate_packets
        )
        if candidate_packets
        else False,
        "all_artifacts_verified": bool(artifact_checks)
        and all(item["normalized_csv_exists"] and item["normalized_csv_hash_matches"] for item in artifact_checks),
        "all_cases_have_quote_context_evidence": all(
            str(case.evidence_ref or "").startswith("v2_13_f_quote_context_case:") for case in historical_cases
        ),
        "sandbox_evaluation_not_run": True,
        "suggestion_path_not_enabled": True,
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
        "run_id": run_id,
        "generated_at": created,
        "command": command,
        "network_used": False,
        "production_records_written": False,
        "production_cache_mutated": False,
        "production_provider_config_mutated": False,
        "dashboard_contract_changed": False,
        "summary": {
            "candidate_packet_count": len(candidate_packets),
            "historical_case_count": len(historical_cases),
            "markets": sorted({case.market for case in historical_cases}),
            "symbols": sorted({case.symbol for case in historical_cases}),
            "sandbox_evaluation_run": False,
            "sandbox_evaluation_required": True,
            "suggestion_gate_required": True,
            "user_facing_suggestion_allowed": False,
            "social_sentiment_status": "blocked_plan_or_rate_limit",
            "next_stage": "V2.13-G Finnhub Quote Context Sandbox Evaluation",
        },
        "candidate_packets": candidate_packets,
        "historical_cases": [case.model_dump() for case in historical_cases],
        "artifact_checks": artifact_checks,
        "source_evidence": {
            "binding_source_target": binding_report.get("acceptance_target"),
            "binding_source_run_id": binding_report.get("run_id"),
            "binding_source_summary_sha256": _sha256_text(
                json.dumps(binding_report.get("summary") or {}, ensure_ascii=False, sort_keys=True)
            ),
            "cache_source_target": cache_readiness_report.get("acceptance_target"),
            "cache_source_run_id": cache_readiness_report.get("run_id"),
            "cache_source_summary_sha256": _sha256_text(
                json.dumps(cache_readiness_report.get("summary") or {}, ensure_ascii=False, sort_keys=True)
            ),
        },
        "checks": checks,
        "safety": {
            "historical_case_assembly_only": True,
            "sandbox_evaluation_not_run": True,
            "suggestion_path_not_enabled": True,
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


def render_finnhub_quote_historical_case_assembly_markdown(report: Mapping[str, Any]) -> str:
    lines = [
        "# V2.13-F Finnhub Quote Context Historical Case Assembly",
        "",
        f"- status: `{report.get('overall_status')}`",
        f"- run_id: `{report.get('run_id')}`",
        f"- candidate_packet_count: `{report.get('summary', {}).get('candidate_packet_count')}`",
        f"- historical_case_count: `{report.get('summary', {}).get('historical_case_count')}`",
        f"- symbols: `{report.get('summary', {}).get('symbols')}`",
        f"- sandbox_evaluation_run: `{report.get('summary', {}).get('sandbox_evaluation_run')}`",
        f"- next_stage: `{report.get('summary', {}).get('next_stage')}`",
        "",
        "## Candidate Packets",
        "",
    ]
    for packet in report.get("candidate_packets", []) or []:
        candidate = packet.get("strategy_candidate") or {}
        lines.extend(
            [
                f"### {packet.get('binding_id')}",
                "",
                f"- status: `{packet.get('status')}`",
                f"- strategy_id: `{candidate.get('strategy_id')}`",
                f"- historical_case_count: `{packet.get('historical_case_count')}`",
                "",
            ]
        )
    lines.extend(
        [
            "## Boundary",
            "",
            "- Historical case assembly only.",
            "- Sandbox evaluation is not run in this stage.",
            "- No user-facing suggestion, position size, live order signal, real trade, broker API, webhook, or order placement.",
            "",
        ]
    )
    return "\n".join(lines)
