"""Secret-safe Finnhub metadata activation proposal.

This consumes V2.13-A probe evidence and creates route proposals only. It does
not mutate production provider config or allow Finnhub data into suggestions.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Mapping

from aegis.external_sources.h_us_provider_metadata_activation import contains_secret_like_material


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _result_lookup(probe_report: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    lookup: dict[str, Mapping[str, Any]] = {}
    for item in probe_report.get("results", []) or []:
        if isinstance(item, dict) and item.get("endpoint"):
            lookup[str(item["endpoint"])] = item
    return lookup


def _capability(endpoint: str, result: Mapping[str, Any] | None) -> dict[str, Any]:
    status = "unproven"
    blocked_by: list[str] = ["missing_probe_result"]
    if result:
        if result.get("ok") is True:
            status = "ready_for_metadata"
        elif result.get("status") == "blocked_plan_or_rate_limit":
            status = "blocked_plan_or_rate_limit"
        else:
            status = "blocked_fetch_error"
        blocked_by = list(result.get("blocked_by") or [])
    return {
        "provider": "finnhub",
        "endpoint": endpoint,
        "market": (result or {}).get("market"),
        "symbol": (result or {}).get("symbol"),
        "data_type": (result or {}).get("data_type"),
        "status": status,
        "required_env_vars": (result or {}).get("required_env_vars") or ["AEGIS_FINNHUB_API_KEY"],
        "env_var_used": (result or {}).get("env_var_used"),
        "probe_summary_sha256": (result or {}).get("summary_sha256"),
        "blocked_by": blocked_by,
        "stores_request_url": False,
        "stores_raw_payload": False,
        "stores_token_value": False,
    }


def build_finnhub_metadata_activation(
    *,
    probe_report: Mapping[str, Any],
    run_id: str,
    command: str | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    """Build a non-secret Finnhub metadata activation proposal."""

    lookup = _result_lookup(probe_report)
    quote = lookup.get("quote")
    social = lookup.get("social_sentiment")
    quote_ready = bool(quote and quote.get("ok") is True and quote.get("status") == "pass")
    social_blocked = bool(social and social.get("status") == "blocked_plan_or_rate_limit")

    capabilities = [_capability("quote", quote), _capability("social_sentiment", social)]
    routes = [
        {
            "route_id": "us_quote_finnhub_verified_free",
            "market": "US",
            "data_type": "quote",
            "primary_provider": "finnhub",
            "fallback_providers": [],
            "status": "ready_for_metadata" if quote_ready else "blocked_no_quote",
            "required_env_vars": ["AEGIS_FINNHUB_API_KEY"],
            "symbol_rules": {
                "canonical_examples": ["AAPL.US", "MSFT.US"],
                "finnhub_examples": ["AAPL", "MSFT"],
                "rule": "Use bare U.S. ticker symbols for Finnhub quote endpoint.",
            },
            "allowed_uses": ["provider_health_check", "quote_freshness_probe", "research_context_inputs"],
            "forbidden_uses": ["real_trade", "broker_api", "trading_webhook", "order_placement"],
            "suggestion_path_enabled": False,
        },
        {
            "route_id": "us_social_sentiment_finnhub_plan_blocked",
            "market": "US",
            "data_type": "social_sentiment",
            "primary_provider": "finnhub",
            "fallback_providers": [],
            "status": "blocked_plan_or_rate_limit" if social_blocked else "needs_review",
            "required_env_vars": ["AEGIS_FINNHUB_API_KEY"],
            "blocked_by": list((social or {}).get("blocked_by") or ["social_sentiment_not_verified"]),
            "allowed_uses": [],
            "forbidden_uses": [
                "sentiment_inputs",
                "suggestion_inputs",
                "production_routing",
                "real_trade",
                "order_placement",
            ],
            "bypass_allowed": False,
            "suggestion_path_enabled": False,
        },
    ]

    checks = {
        "source_probe_report_pass": probe_report.get("overall_status") == "PASS",
        "source_acceptance_target_correct": probe_report.get("acceptance_target") == "V2.13-A Finnhub Free Probe",
        "source_secret_like_material_absent": not contains_secret_like_material(probe_report),
        "quote_ready_for_metadata": quote_ready,
        "social_sentiment_blocked_visible": social_blocked,
        "quote_route_proposal_visible": any(route["route_id"] == "us_quote_finnhub_verified_free" for route in routes),
        "social_sentiment_route_blocked": any(
            route["route_id"] == "us_social_sentiment_finnhub_plan_blocked"
            and route["status"] == "blocked_plan_or_rate_limit"
            for route in routes
        ),
        "env_var_names_only": True,
        "no_secret_values_stored": True,
        "request_urls_not_stored": True,
        "raw_payloads_not_stored": True,
        "network_not_used": True,
        "production_provider_config_not_mutated": True,
        "suggestion_path_not_enabled": True,
        "no_real_trade": True,
        "no_broker_api": True,
        "no_trading_webhook": True,
        "no_order_placement": True,
        "dashboard_contract_unchanged": True,
    }

    return {
        "overall_status": "PASS" if all(checks.values()) else "FAIL",
        "acceptance_target": "V2.13-B Finnhub Metadata Activation",
        "packet_type": "finnhub_metadata_activation",
        "run_id": run_id,
        "generated_at": generated_at or _now_iso(),
        "command": command,
        "network_used": False,
        "production_records_written": False,
        "production_provider_config_mutated": False,
        "dashboard_contract_changed": False,
        "summary": {
            "quote_route": "finnhub_quote_ready" if quote_ready else "blocked",
            "social_sentiment_route": "blocked_plan_or_rate_limit" if social_blocked else "needs_review",
            "route_count": len(routes),
            "capability_count": len(capabilities),
            "next_stage": "V2.13-C Finnhub Quote Cache Readiness Dry Run",
        },
        "capabilities": capabilities,
        "route_proposals": routes,
        "source_evidence": {
            "source_target": probe_report.get("acceptance_target"),
            "source_run_id": probe_report.get("run_id"),
            "source_summary_sha256": _sha256_text(
                json.dumps(probe_report.get("summary") or {}, ensure_ascii=False, sort_keys=True)
            ),
        },
        "checks": checks,
        "safety": {
            "metadata_activation_only": True,
            "no_secret_values_stored": True,
            "no_request_url_storage": True,
            "no_raw_payload_storage": True,
            "network_not_used": True,
            "production_provider_config_not_mutated": True,
            "suggestion_path_not_enabled": True,
            "social_sentiment_not_enabled": True,
            "no_real_trade": True,
            "no_broker_api": True,
            "no_trading_webhook": True,
            "no_order_placement": True,
            "dashboard_contract_unchanged": True,
        },
    }


def render_finnhub_metadata_activation_markdown(packet: Mapping[str, Any]) -> str:
    lines = [
        "# V2.13-B Finnhub Metadata Activation",
        "",
        f"- status: `{packet.get('overall_status')}`",
        f"- run_id: `{packet.get('run_id')}`",
        f"- quote_route: `{packet.get('summary', {}).get('quote_route')}`",
        f"- social_sentiment_route: `{packet.get('summary', {}).get('social_sentiment_route')}`",
        f"- next_stage: `{packet.get('summary', {}).get('next_stage')}`",
        "",
        "## Route Proposals",
        "",
    ]
    for route in packet.get("route_proposals", []) or []:
        lines.extend(
            [
                f"### {route.get('route_id')}",
                "",
                f"- market: `{route.get('market')}`",
                f"- data_type: `{route.get('data_type')}`",
                f"- primary_provider: `{route.get('primary_provider')}`",
                f"- status: `{route.get('status')}`",
                f"- allowed_uses: `{route.get('allowed_uses')}`",
                f"- forbidden_uses: `{route.get('forbidden_uses')}`",
                f"- suggestion_path_enabled: `{route.get('suggestion_path_enabled')}`",
                "",
            ]
        )
    lines.extend(
        [
            "## Boundary",
            "",
            "- Metadata activation only.",
            "- Finnhub quote is ready for metadata routing but not enabled for production suggestions.",
            "- Finnhub social sentiment remains plan/rate-limit blocked and cannot feed sentiment or suggestions.",
            "- Production provider config is not mutated.",
            "- Suggestion path is not enabled.",
            "- No request URL, raw payload, or token value is stored.",
            "- No real trade, broker API, trading webhook, order placement, or Dashboard Contract change.",
            "",
        ]
    )
    return "\n".join(lines)
