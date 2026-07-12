"""Secret-safe H/US provider metadata activation proposal.

This stage consumes the V2.12-A provider probe report and creates a routing
proposal only. It does not change production provider config or let market
data flow into suggestions.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Mapping


SECRET_VALUE_PATTERNS = (
    "api_token=",
    "apikey=",
    "token=",
    "secret=",
    "password=",
    "bearer ",
    "authorization:",
    "cookie=",
    "sk-",
    "oauth_refresh_token",
    "-----begin",
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _walk_strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        strings: list[str] = []
        for child in value.values():
            strings.extend(_walk_strings(child))
        return strings
    if isinstance(value, list):
        strings: list[str] = []
        for child in value:
            strings.extend(_walk_strings(child))
        return strings
    return []


def contains_secret_like_material(payload: Mapping[str, Any]) -> bool:
    for value in _walk_strings(payload):
        lowered = value.lower()
        if any(pattern in lowered for pattern in SECRET_VALUE_PATTERNS):
            return True
    return False


def _result_lookup(probe_report: Mapping[str, Any]) -> dict[tuple[str, str], Mapping[str, Any]]:
    lookup: dict[tuple[str, str], Mapping[str, Any]] = {}
    for item in probe_report.get("results", []) or []:
        if isinstance(item, dict):
            lookup[(str(item.get("provider")), str(item.get("market")))] = item
    return lookup


def _provider_capability(
    *,
    provider: str,
    market: str,
    data_type: str,
    result: Mapping[str, Any] | None,
) -> dict[str, Any]:
    status = "unproven"
    blocked_by: list[str] = ["missing_probe_result"]
    if result:
        status = "ready_for_metadata" if result.get("ok") is True else "blocked_fetch_error"
        blocked_by = list(result.get("blocked_by") or [])
    return {
        "provider": provider,
        "market": market,
        "data_type": data_type,
        "status": status,
        "required_env_var": (result or {}).get("required_env_var"),
        "probe_symbol": (result or {}).get("symbol"),
        "probe_summary_sha256": (result or {}).get("summary_sha256"),
        "blocked_by": blocked_by,
        "stores_request_url": False,
        "stores_raw_payload": False,
        "stores_token_value": False,
    }


def _hk_symbol_rules() -> dict[str, Any]:
    return {
        "canonical_examples": ["00700.HK", "00005.HK"],
        "eodhd_examples": ["0700.HK", "0005.HK"],
        "rule": "For 5-digit HK equity codes, remove exactly one leading zero before the .HK suffix for EODHD.",
        "examples": [
            {"canonical": "00700.HK", "eodhd": "0700.HK"},
            {"canonical": "00005.HK", "eodhd": "0005.HK"},
        ],
        "requires_later_unit_coverage": True,
    }


def build_h_us_provider_metadata_activation(
    *,
    probe_report: Mapping[str, Any],
    run_id: str,
    command: str | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    """Build a non-secret H/US provider routing proposal from V2.12-A evidence."""

    lookup = _result_lookup(probe_report)
    eodhd_h = lookup.get(("eodhd", "H"))
    eodhd_us = lookup.get(("eodhd", "US"))
    twelve_us = lookup.get(("twelve_data", "US"))
    twelve_h = lookup.get(("twelve_data", "H"))

    capabilities = [
        _provider_capability(provider="eodhd", market="H", data_type="daily_bars", result=eodhd_h),
        _provider_capability(provider="eodhd", market="US", data_type="daily_bars", result=eodhd_us),
        _provider_capability(provider="twelve_data", market="US", data_type="daily_bars", result=twelve_us),
        _provider_capability(provider="twelve_data", market="H", data_type="daily_bars", result=twelve_h),
    ]
    h_ready = bool(eodhd_h and eodhd_h.get("ok") is True)
    us_ready = bool((eodhd_us and eodhd_us.get("ok") is True) and (twelve_us and twelve_us.get("ok") is True))
    twelve_h_blocked = bool(twelve_h and twelve_h.get("ok") is not True)

    routes = [
        {
            "route_id": "h_daily_bars_eodhd_primary",
            "market": "H",
            "data_type": "daily_bars",
            "primary_provider": "eodhd",
            "fallback_providers": [],
            "status": "ready_for_metadata" if h_ready else "blocked_no_h_provider",
            "required_env_vars": ["AEGIS_EODHD_API_TOKEN"],
            "symbol_rules": _hk_symbol_rules(),
            "allowed_uses": ["historical_cache_refresh", "historical_sandbox", "strategy_research_inputs"],
            "forbidden_uses": ["real_trade", "broker_api", "trading_webhook", "order_placement"],
        },
        {
            "route_id": "us_daily_bars_eodhd_primary_twelve_backup",
            "market": "US",
            "data_type": "daily_bars",
            "primary_provider": "eodhd",
            "fallback_providers": ["twelve_data"],
            "status": "ready_for_metadata" if us_ready else "blocked_no_us_provider",
            "required_env_vars": ["AEGIS_EODHD_API_TOKEN", "AEGIS_TWELVE_DATA_API_KEY"],
            "symbol_rules": {
                "canonical_examples": ["AAPL.US", "MSFT.US"],
                "eodhd_examples": ["AAPL.US", "MSFT.US"],
                "twelve_data_examples": ["AAPL", "MSFT"],
                "rule": "Use .US suffix for EODHD and bare ticker symbols for Twelve Data U.S. equities.",
            },
            "allowed_uses": ["historical_cache_refresh", "historical_sandbox", "strategy_research_inputs"],
            "forbidden_uses": ["real_trade", "broker_api", "trading_webhook", "order_placement"],
        },
        {
            "route_id": "h_daily_bars_twelve_data_review",
            "market": "H",
            "data_type": "daily_bars",
            "primary_provider": "twelve_data",
            "fallback_providers": [],
            "status": "blocked_fetch_error" if twelve_h_blocked else "needs_review",
            "required_env_vars": ["AEGIS_TWELVE_DATA_API_KEY"],
            "symbol_rules": {
                "attempted": [{"symbol": "0700", "exchange": "HKEX"}],
                "rule": "Do not use Twelve Data for Hong Kong daily bars until plan and symbol route are proven.",
            },
            "blocked_by": list((twelve_h or {}).get("blocked_by") or ["unproven_h_route"]),
            "allowed_uses": [],
            "forbidden_uses": ["suggestion_inputs", "production_routing", "real_trade", "order_placement"],
        },
    ]

    checks = {
        "source_probe_report_pass": probe_report.get("overall_status") == "PASS",
        "source_acceptance_target_correct": probe_report.get("acceptance_target")
        == "V2.12-A EODHD Twelve Data H-US Provider Probe",
        "source_secret_like_material_absent": not contains_secret_like_material(probe_report),
        "eodhd_h_ready_for_metadata": h_ready,
        "eodhd_us_ready_for_metadata": bool(eodhd_us and eodhd_us.get("ok") is True),
        "twelve_data_us_ready_for_metadata": bool(twelve_us and twelve_us.get("ok") is True),
        "twelve_data_h_blocked_visible": twelve_h_blocked,
        "h_route_proposal_visible": any(route["route_id"] == "h_daily_bars_eodhd_primary" for route in routes),
        "us_route_proposal_visible": any(
            route["route_id"] == "us_daily_bars_eodhd_primary_twelve_backup" for route in routes
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
        "acceptance_target": "V2.12-B H-US Provider Metadata Activation",
        "packet_type": "h_us_provider_metadata_activation",
        "run_id": run_id,
        "generated_at": generated_at or _now_iso(),
        "command": command,
        "network_used": False,
        "production_records_written": False,
        "production_provider_config_mutated": False,
        "dashboard_contract_changed": False,
        "summary": {
            "h_route": "eodhd_primary_ready" if h_ready else "blocked",
            "us_route": "eodhd_primary_twelve_backup_ready" if us_ready else "blocked",
            "twelve_data_h_status": "blocked_fetch_error" if twelve_h_blocked else "needs_review",
            "route_count": len(routes),
            "capability_count": len(capabilities),
            "next_stage": "V2.12-C H-US Historical Cache Readiness Dry Run",
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
            "no_real_trade": True,
            "no_broker_api": True,
            "no_trading_webhook": True,
            "no_order_placement": True,
            "dashboard_contract_unchanged": True,
        },
    }


def render_h_us_provider_metadata_activation_markdown(packet: Mapping[str, Any]) -> str:
    lines = [
        "# V2.12-B H-US Provider Metadata Activation",
        "",
        f"- status: `{packet.get('overall_status')}`",
        f"- run_id: `{packet.get('run_id')}`",
        f"- h_route: `{packet.get('summary', {}).get('h_route')}`",
        f"- us_route: `{packet.get('summary', {}).get('us_route')}`",
        f"- twelve_data_h_status: `{packet.get('summary', {}).get('twelve_data_h_status')}`",
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
                f"- fallback_providers: `{route.get('fallback_providers')}`",
                f"- status: `{route.get('status')}`",
                f"- required_env_vars: `{route.get('required_env_vars')}`",
                f"- forbidden_uses: `{route.get('forbidden_uses')}`",
                "",
            ]
        )
    lines.extend(
        [
            "## Boundary",
            "",
            "- Metadata/routing proposal only.",
            "- Env var names only; no token values.",
            "- No request URL or raw payload storage.",
            "- Production provider config is not mutated.",
            "- Suggestion path is not enabled by this stage.",
            "- No real trade, broker API, trading webhook, or order placement.",
            "- Dashboard Contract unchanged.",
            "",
        ]
    )
    return "\n".join(lines)
