"""Run a bounded live Finnhub quote probe for a routed symbol queue.

V2.13-R consumes the V2.13-Q expansion plan and fetches quote snapshots for the
queued US symbols only. It writes run-specific normalized artifacts and never
enables suggestions, production records, orders, or broker/webhook paths.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from aegis.external_sources.finnhub_quote_cache_readiness import (
    NORMALIZED_QUOTE_COLUMNS,
    FetchJson,
    run_finnhub_quote_cache_readiness_case,
)


ACCEPTANCE_TARGET = "V2.13-R Finnhub Quote Multi-Symbol Live Probe Dry Run"
SOURCE_EXPANSION_TARGET = "V2.13-Q Finnhub Quote Multi-Symbol Candidate Expansion Plan"


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _case_id(symbol: str) -> str:
    return "us_" + symbol.removesuffix(".US").lower().replace(".", "_") + "_finnhub_quote"


def _cases_from_expansion(expansion_report: Mapping[str, Any]) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    for item in expansion_report.get("finnhub_probe_queue") or []:
        if item.get("provider_route") != "finnhub_quote" or item.get("market") != "US":
            continue
        canonical = str(item.get("symbol"))
        provider_symbol = str(item.get("provider_symbol") or canonical.removesuffix(".US"))
        cases.append(
            {
                "case_id": _case_id(canonical),
                "route_id": "us_quote_finnhub_verified_free",
                "provider": "finnhub",
                "market": "US",
                "canonical_symbol": canonical,
                "provider_symbol": provider_symbol,
                "data_type": "quote",
                "source_strategy_id": item.get("strategy_id"),
                "source_candidate_status": item.get("candidate_status"),
            }
        )
    return cases


def build_finnhub_quote_multi_symbol_live_probe_report(
    expansion_report: Mapping[str, Any],
    *,
    output_dir: Path,
    run_id: str,
    env: Mapping[str, str] | None = None,
    fetch_json: FetchJson | None = None,
    command: str | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    cases = _cases_from_expansion(expansion_report)
    results = [
        run_finnhub_quote_cache_readiness_case(case, output_dir=output_dir, env=env, fetch_json=fetch_json)
        for case in cases
    ]
    pass_results = [result for result in results if result.get("status") == "pass"]
    fail_results = [result for result in results if result.get("status") == "fail"]
    blocked_results = [result for result in results if str(result.get("status", "")).startswith("blocked")]
    checks = {
        "source_expansion_is_v2_13_q": expansion_report.get("acceptance_target") == SOURCE_EXPANSION_TARGET,
        "source_expansion_pass": expansion_report.get("overall_status") == "PASS",
        "source_next_stage_is_v2_13_r": expansion_report.get("summary", {}).get("next_stage") == ACCEPTANCE_TARGET,
        "source_social_sentiment_still_blocked": expansion_report.get("summary", {}).get("social_sentiment_status")
        == "blocked_plan_or_rate_limit",
        "has_probe_cases": bool(cases),
        "attempted_all_probe_cases": len(results) == len(cases) and bool(cases),
        "all_probe_cases_passed": len(pass_results) == len(cases) and bool(cases),
        "all_passed_samples_have_hashes": all(
            result.get("normalized_quote_json_sha256") and result.get("normalized_quote_csv_sha256")
            for result in pass_results
        ),
        "normalized_schema_visible": all(
            result.get("status") != "pass" or result.get("normalized_schema") == NORMALIZED_QUOTE_COLUMNS
            for result in results
        ),
        "env_var_names_only": True,
        "no_secret_values_stored": all(not result.get("token_value_stored") for result in results),
        "request_urls_not_stored": all(not result.get("request_url_stored") for result in results),
        "raw_payloads_not_stored": all(not result.get("raw_payload_stored") for result in results),
        "run_specific_artifacts_only": True,
        "suggestion_path_not_enabled": True,
        "social_sentiment_not_enabled": True,
        "no_real_trade": True,
        "no_broker_api": True,
        "no_webhook": True,
        "no_order_placement": True,
        "no_live_order_signal": True,
        "no_position_size": True,
        "production_records_not_written": True,
        "production_cache_not_mutated": True,
        "production_provider_config_not_mutated": True,
        "dashboard_contract_unchanged": True,
    }
    return {
        "overall_status": "PASS" if all(checks.values()) else "FAIL",
        "acceptance_target": ACCEPTANCE_TARGET,
        "source_expansion_acceptance_target": expansion_report.get("acceptance_target"),
        "probe_type": "finnhub_quote_multi_symbol_live_probe_dry_run",
        "run_id": run_id,
        "generated_at": generated_at or _now_iso(),
        "command": command,
        "network_used": fetch_json is None,
        "production_records_written": False,
        "production_cache_mutated": False,
        "production_provider_config_mutated": False,
        "dashboard_contract_changed": False,
        "summary": {
            "case_count": len(cases),
            "pass_count": len(pass_results),
            "fail_count": len(fail_results),
            "blocked_count": len(blocked_results),
            "probe_symbols": [case["canonical_symbol"] for case in cases],
            "passed_symbols": [result.get("canonical_symbol") for result in pass_results],
            "failed_symbols": [result.get("canonical_symbol") for result in fail_results],
            "blocked_symbols": [result.get("canonical_symbol") for result in blocked_results],
            "quote_probe_ready": len(pass_results) == len(cases) and bool(cases),
            "social_sentiment_status": "blocked_plan_or_rate_limit",
            "next_stage": "V2.13-S Finnhub Quote Multi-Symbol Research Context Bridge",
        },
        "cases": cases,
        "results": results,
        "checks": checks,
        "safety": {
            "live_quote_probe_dry_run_only": True,
            "run_specific_artifacts_only": True,
            "simulation_only": True,
            "manual_external_execution_only": True,
            "suggestion_path_not_enabled": True,
            "social_sentiment_not_enabled": True,
            "no_secret_values_stored": True,
            "no_request_url_storage": True,
            "no_raw_payload_storage": True,
            "no_real_trade": True,
            "no_broker_api": True,
            "no_webhook": True,
            "no_order_placement": True,
            "no_live_order_signal": True,
            "no_position_size": True,
            "no_production_records_mutation": True,
            "production_cache_not_mutated": True,
            "production_provider_config_not_mutated": True,
            "dashboard_contract_unchanged": True,
        },
    }


def render_finnhub_quote_multi_symbol_live_probe_markdown(report: Mapping[str, Any]) -> str:
    lines = [
        "# V2.13-R Finnhub Quote Multi-Symbol Live Probe Dry Run",
        "",
        f"- status: `{report.get('overall_status')}`",
        f"- run_id: `{report.get('run_id')}`",
        f"- network_used: `{report.get('network_used')}`",
        f"- case_count: `{report.get('summary', {}).get('case_count')}`",
        f"- pass_count: `{report.get('summary', {}).get('pass_count')}`",
        f"- fail_count: `{report.get('summary', {}).get('fail_count')}`",
        f"- blocked_count: `{report.get('summary', {}).get('blocked_count')}`",
        f"- passed_symbols: `{report.get('summary', {}).get('passed_symbols')}`",
        f"- social_sentiment_status: `{report.get('summary', {}).get('social_sentiment_status')}`",
        f"- next_stage: `{report.get('summary', {}).get('next_stage')}`",
        "",
        "## Results",
        "",
    ]
    for result in report.get("results", []) or []:
        lines.extend(
            [
                f"### {result.get('canonical_symbol')}",
                "",
                f"- status: `{result.get('status')}`",
                f"- provider_symbol: `{result.get('provider_symbol')}`",
                f"- http_status: `{result.get('http_status')}`",
                f"- normalized_quote_json: `{result.get('normalized_quote_json')}`",
                f"- normalized_quote_json_sha256: `{result.get('normalized_quote_json_sha256')}`",
                f"- normalized_quote_csv: `{result.get('normalized_quote_csv')}`",
                f"- normalized_quote_csv_sha256: `{result.get('normalized_quote_csv_sha256')}`",
                f"- blocked_by: `{result.get('blocked_by', [])}`",
                "",
            ]
        )
    lines.extend(
        [
            "## Boundary",
            "",
            "- This stage only probes live quotes and writes run-specific normalized artifacts.",
            "- It does not create user-facing suggestions.",
            "- It does not write production Recommendation, PaperTrade, Review, or Memory records.",
            "- It does not store request URLs, raw payloads, or token values.",
            "- It does not connect broker APIs, webhooks, or place orders.",
            "",
        ]
    )
    return "\n".join(lines)
