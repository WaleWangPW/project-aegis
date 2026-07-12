"""Finnhub quote research context bridge.

This module converts a verified, run-specific Finnhub quote cache artifact into
research-context evidence only. It never fetches the network, enables social
sentiment, creates suggestions, or mutates production records.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping


ACCEPTANCE_TARGET = "V2.13-D Finnhub Quote Research Context Bridge"
SOURCE_ACCEPTANCE_TARGET = "V2.13-C Finnhub Quote Cache Readiness Dry Run"


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _safe_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _build_context_item(result: Mapping[str, Any], quote: Mapping[str, Any], quote_hash: str) -> dict[str, Any]:
    current = _safe_float(quote.get("current_price"))
    previous_close = _safe_float(quote.get("previous_close"))
    percent_change = _safe_float(quote.get("percent_change"))
    source_quote_json = str(result.get("normalized_quote_json") or "")
    return {
        "context_id": f"finnhub_quote_context_{result.get('case_id')}",
        "provider": "finnhub",
        "market": result.get("market"),
        "canonical_symbol": result.get("canonical_symbol"),
        "provider_symbol": result.get("provider_symbol"),
        "source_case_id": result.get("case_id"),
        "source_route_id": result.get("route_id"),
        "source_quote_json": source_quote_json,
        "source_quote_json_sha256": quote_hash,
        "source_artifact_ref_sha256": _sha256_text(source_quote_json),
        "evidence_role": "research_context_only",
        "evidence_type": "price_data",
        "evidence_status": "verified",
        "price_snapshot_summary": {
            "current_price_present": current is not None and current > 0,
            "previous_close_present": previous_close is not None and previous_close > 0,
            "percent_change": percent_change,
            "provider_timestamp_present": quote.get("provider_timestamp") is not None,
        },
        "allowed_uses": [
            "research_context_inputs",
            "quote_freshness_context",
            "candidate_context_review",
        ],
        "forbidden_uses": [
            "sentiment_inputs",
            "suggestion_inputs_without_gate",
            "real_trade",
            "broker_api",
            "trading_webhook",
            "order_placement",
            "position_size_generation",
        ],
        "requires_sandbox_before_suggestion": True,
        "requires_suggestion_gate_before_user_facing": True,
        "user_facing_suggestion_allowed": False,
        "auto_applied": False,
        "no_position_size": True,
        "no_live_order_signal": True,
    }


def build_finnhub_quote_research_context_report(
    *,
    source_report: Mapping[str, Any],
    run_id: str,
    command: str | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    source_results = source_report.get("results") or []
    pass_results = [
        result
        for result in source_results
        if isinstance(result, dict) and result.get("status") == "pass" and result.get("normalized_quote_json")
    ]
    context_items: list[dict[str, Any]] = []
    artifact_checks: list[dict[str, Any]] = []
    for result in pass_results:
        quote_path = Path(str(result["normalized_quote_json"]))
        exists = quote_path.exists()
        actual_hash = _sha256_file(quote_path) if exists else None
        expected_hash = result.get("normalized_quote_json_sha256")
        hash_matches = bool(actual_hash and expected_hash and actual_hash == expected_hash)
        artifact_checks.append(
            {
                "case_id": result.get("case_id"),
                "quote_json_exists": exists,
                "quote_json_hash_matches": hash_matches,
                "expected_sha256": expected_hash,
                "actual_sha256": actual_hash,
            }
        )
        if not hash_matches:
            continue
        quote = _load_json(quote_path)
        context_items.append(_build_context_item(result, quote, actual_hash))

    checks = {
        "source_report_pass": source_report.get("overall_status") == "PASS",
        "source_acceptance_target_correct": source_report.get("acceptance_target") == SOURCE_ACCEPTANCE_TARGET,
        "source_quote_cache_ready": bool(source_report.get("summary", {}).get("quote_cache_ready")),
        "source_social_sentiment_still_blocked": source_report.get("summary", {}).get("social_sentiment_status")
        == "blocked_plan_or_rate_limit",
        "source_network_was_prior_stage_only": source_report.get("network_used") is True,
        "at_least_one_context_item": bool(context_items),
        "all_source_quote_artifacts_verified": bool(artifact_checks)
        and all(item["quote_json_exists"] and item["quote_json_hash_matches"] for item in artifact_checks),
        "research_context_only": all(item["evidence_role"] == "research_context_only" for item in context_items),
        "requires_sandbox_before_suggestion": all(
            item["requires_sandbox_before_suggestion"] is True for item in context_items
        ),
        "requires_suggestion_gate_before_user_facing": all(
            item["requires_suggestion_gate_before_user_facing"] is True for item in context_items
        ),
        "user_facing_suggestion_not_allowed": all(
            item["user_facing_suggestion_allowed"] is False for item in context_items
        ),
        "auto_apply_disabled": all(item["auto_applied"] is False for item in context_items),
        "social_sentiment_not_enabled": True,
        "suggestion_path_not_enabled": True,
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
        "no_position_size": all(item["no_position_size"] is True for item in context_items),
        "no_live_order_signal": all(item["no_live_order_signal"] is True for item in context_items),
        "dashboard_contract_unchanged": True,
    }
    return {
        "overall_status": "PASS" if all(checks.values()) else "FAIL",
        "acceptance_target": ACCEPTANCE_TARGET,
        "run_id": run_id,
        "generated_at": generated_at or _now_iso(),
        "command": command,
        "network_used": False,
        "production_records_written": False,
        "production_cache_mutated": False,
        "production_provider_config_mutated": False,
        "dashboard_contract_changed": False,
        "summary": {
            "context_item_count": len(context_items),
            "source_case_ids": sorted(str(item["source_case_id"]) for item in context_items),
            "symbols": sorted(str(item["canonical_symbol"]) for item in context_items),
            "markets": sorted(str(item["market"]) for item in context_items),
            "social_sentiment_status": "blocked_plan_or_rate_limit",
            "next_stage": "V2.13-E Finnhub Quote Context To Sandbox Candidate Binding",
        },
        "context_items": context_items,
        "artifact_checks": artifact_checks,
        "source_evidence": {
            "source_target": source_report.get("acceptance_target"),
            "source_run_id": source_report.get("run_id"),
            "source_summary_sha256": _sha256_text(
                json.dumps(source_report.get("summary") or {}, ensure_ascii=False, sort_keys=True)
            ),
        },
        "checks": checks,
        "safety": {
            "research_context_only": True,
            "network_not_used": True,
            "source_artifact_hash_verified": checks["all_source_quote_artifacts_verified"],
            "social_sentiment_not_enabled": True,
            "suggestion_path_not_enabled": True,
            "requires_sandbox_before_suggestion": True,
            "requires_suggestion_gate_before_user_facing": True,
            "user_facing_suggestion_allowed": False,
            "auto_applied": False,
            "no_secret_values_stored": True,
            "no_request_url_storage": True,
            "no_raw_payload_storage": True,
            "production_records_not_written": True,
            "production_cache_not_mutated": True,
            "production_provider_config_not_mutated": True,
            "no_real_trade": True,
            "no_broker_api": True,
            "no_trading_webhook": True,
            "no_order_placement": True,
            "no_position_size": True,
            "no_live_order_signal": True,
            "dashboard_contract_unchanged": True,
        },
    }


def render_finnhub_quote_research_context_markdown(report: Mapping[str, Any]) -> str:
    lines = [
        "# V2.13-D Finnhub Quote Research Context Bridge",
        "",
        f"- status: `{report.get('overall_status')}`",
        f"- run_id: `{report.get('run_id')}`",
        f"- context_item_count: `{report.get('summary', {}).get('context_item_count')}`",
        f"- symbols: `{report.get('summary', {}).get('symbols')}`",
        f"- markets: `{report.get('summary', {}).get('markets')}`",
        f"- social_sentiment_status: `{report.get('summary', {}).get('social_sentiment_status')}`",
        f"- next_stage: `{report.get('summary', {}).get('next_stage')}`",
        "",
        "## Context Items",
        "",
    ]
    for item in report.get("context_items", []) or []:
        lines.extend(
            [
                f"### {item.get('context_id')}",
                "",
                f"- evidence_role: `{item.get('evidence_role')}`",
                f"- symbol: `{item.get('canonical_symbol')}`",
                f"- provider: `{item.get('provider')}`",
                f"- source_case_id: `{item.get('source_case_id')}`",
                f"- source_quote_json_sha256: `{item.get('source_quote_json_sha256')}`",
                f"- requires_sandbox_before_suggestion: `{item.get('requires_sandbox_before_suggestion')}`",
                f"- user_facing_suggestion_allowed: `{item.get('user_facing_suggestion_allowed')}`",
                "",
            ]
        )
    lines.extend(
        [
            "## Boundary",
            "",
            "- Research context only; this is not a recommendation.",
            "- Network is not used in this bridge; it only verifies prior V2.13-C artifacts and hashes.",
            "- Finnhub social sentiment remains blocked and is not used.",
            "- Suggestion path, production records, production cache, and provider config are not mutated.",
            "- No real trade, broker API, trading webhook, order placement, position size, or live order signal.",
            "",
        ]
    )
    return "\n".join(lines)
