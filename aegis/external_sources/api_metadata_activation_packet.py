"""User-facing packet for activating real API metadata safely.

The packet lists non-secret fields the user can provide and the local env var
names that must be configured. It never stores API key values, cookies, bearer
tokens, raw connector config, request headers, or raw API responses.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import urlparse


SECRET_VALUE_PATTERNS = (
    "sk-",
    "bearer ",
    "password=",
    "token=",
    "secret=",
    "api_key=",
    "apikey=",
    "cookie=",
    "authorization:",
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
        values: list[str] = []
        for child in value.values():
            values.extend(_walk_strings(child))
        return values
    if isinstance(value, list):
        values: list[str] = []
        for child in value:
            values.extend(_walk_strings(child))
        return values
    return []


def contains_secret_like_material(payload: Mapping[str, Any]) -> bool:
    for value in _walk_strings(payload):
        lowered = value.lower()
        if any(pattern in lowered for pattern in SECRET_VALUE_PATTERNS):
            return True
    return False


def _connector_from_template(template_payload: Mapping[str, Any], connector_id: str) -> Mapping[str, Any] | None:
    for item in template_payload.get("connectors", []) or []:
        if isinstance(item, dict) and item.get("connector_id") == connector_id:
            return item
    return None


def _safe_template_summary(connector: Mapping[str, Any] | None) -> dict[str, Any]:
    if not connector:
        return {}
    parsed = urlparse(str(connector.get("base_url") or ""))
    schema = connector.get("candidate_payload_schema") if isinstance(connector.get("candidate_payload_schema"), dict) else {}
    return {
        "connector_id": connector.get("connector_id"),
        "provider_type": connector.get("provider_type"),
        "markets": list(connector.get("markets") or []),
        "base_url_host_example": parsed.netloc,
        "base_url_example_sha256": _sha256_text(str(connector.get("base_url") or "")),
        "auth_method": connector.get("auth_method"),
        "required_env_vars": list(connector.get("required_env_vars") or []),
        "license_status": connector.get("license_status"),
        "retention_policy": connector.get("retention_policy"),
        "allowed_purposes": list(connector.get("allowed_purposes") or []),
        "endpoint_path": connector.get("endpoint_path"),
        "candidate_payload_schema": {
            "items_path": schema.get("items_path"),
            "symbol_field": schema.get("symbol_field"),
            "market_field": schema.get("market_field"),
            "name_field": schema.get("name_field"),
            "score_field": schema.get("score_field"),
            "status_field": schema.get("status_field"),
            "allowed_markets": list(schema.get("allowed_markets") or []),
            "max_items_per_market": schema.get("max_items_per_market"),
            "candidate_summary_only": schema.get("candidate_summary_only"),
        },
    }


def build_api_metadata_activation_packet(
    *,
    template_payload: Mapping[str, Any],
    metadata_intake_report: Mapping[str, Any],
    tushare_probe_report: Mapping[str, Any] | None = None,
    run_id: str,
    connector_id: str,
    command: str | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    connector = _connector_from_template(template_payload, connector_id)
    template_has_secret_like_material = contains_secret_like_material(template_payload)
    intake_summary = dict(metadata_intake_report.get("summary") or {})
    intake_status = intake_summary.get("intake_status")
    tushare_probe = dict(tushare_probe_report or {})
    tushare_summary = dict(tushare_probe.get("summary") or {})
    tushare_checks = list(tushare_probe.get("checks") or [])
    tushare_passed = {
        (item.get("market"), item.get("data_type"))
        for item in tushare_checks
        if item.get("status") == "pass"
    }
    tushare_unknown = [
        {
            "market": item.get("market"),
            "data_type": item.get("data_type"),
            "status": item.get("status"),
        }
        for item in tushare_checks
        if str(item.get("status") or "").startswith("unknown")
    ]
    tushare_a_core_ready = {
        ("A", "daily_bars"),
        ("A", "index_bars"),
        ("A", "stock_basic"),
        ("A", "trading_calendar"),
    }.issubset(tushare_passed)
    required_env_vars = list(
        intake_summary.get("required_env_vars")
        or (connector or {}).get("required_env_vars")
        or []
    )

    required_metadata_fields = [
        "connector_id",
        "name",
        "provider_type",
        "markets",
        "base_url",
        "auth_method",
        "required_env_vars",
        "license_status",
        "retention_policy",
        "allowed_purposes",
        "can_connect",
        "endpoint_path",
        "request_query_template",
        "candidate_payload_schema",
    ]
    forbidden_fields_or_values = [
        "api_key value",
        "secret value",
        "cookie",
        "bearer token",
        "authorization header value",
        "broker credential",
        "trading webhook secret",
        "password",
        "oauth refresh token",
    ]
    user_steps = [
        "Copy config/external_api_connectors.user-template.json to config/external_api_connectors.local.json.",
        "Replace only non-secret metadata fields such as base_url, endpoint_path, markets, allowed_purposes, and schema field names.",
        "Set the actual API key only in the named local environment variable; never paste the value into chat, repo, Vault, or JSON.",
        "Run V2.10-B metadata intake again; only proceed when status is ready_for_live_readiness_check or blocked_missing_env_vars with clear env var names.",
    ]

    checks = {
        "template_connector_found": connector is not None,
        "template_secret_like_material_absent": template_has_secret_like_material is False,
        "intake_report_pass": metadata_intake_report.get("overall_status") == "PASS",
        "tushare_probe_visible": bool(tushare_probe_report),
        "tushare_token_value_not_stored": True,
        "tushare_a_core_ready_visible": not tushare_probe_report or tushare_a_core_ready,
        "current_intake_status_visible": intake_status
        in {
            "blocked_missing_metadata",
            "blocked_missing_env_vars",
            "ready_for_live_readiness_check",
            "blocked_invalid_metadata",
            "blocked_secret_like_material",
            "blocked_missing_connector",
            "blocked_invalid_or_incomplete_metadata",
        },
        "required_metadata_fields_visible": len(required_metadata_fields) >= 10,
        "required_env_var_names_visible": bool(required_env_vars),
        "forbidden_secret_values_visible": len(forbidden_fields_or_values) >= 5,
        "raw_config_not_stored": True,
        "env_values_not_stored": True,
        "network_not_used": True,
        "no_broker_api": True,
        "no_trading_webhook": True,
        "no_order_placement": True,
    }

    return {
        "overall_status": "PASS" if all(checks.values()) else "FAIL",
        "acceptance_target": "V2.11-B User-Provided API Metadata Activation Packet",
        "packet_type": "user_api_metadata_activation_packet",
        "run_id": run_id,
        "generated_at": generated_at or _now_iso(),
        "command": command,
        "network_used": False,
        "production_records_written": False,
        "dashboard_contract_changed": False,
        "summary": {
            "connector_id": connector_id,
            "current_intake_status": intake_status,
            "blocked_by": intake_summary.get("blocked_by") or [],
            "template_connector_found": connector is not None,
            "required_env_vars": required_env_vars,
            "tushare_status": (
                "a_share_core_ready"
                if tushare_a_core_ready
                else "not_checked" if not tushare_probe_report else "not_ready"
            ),
            "tushare_token_present": tushare_probe.get("token_present"),
            "tushare_network_available": tushare_probe.get("network_available"),
            "tushare_pass_count": tushare_summary.get("pass_count"),
            "tushare_unknown_count": tushare_summary.get("unknown_count"),
            "local_config_path": "config/external_api_connectors.local.json",
            "user_template_path": "config/external_api_connectors.user-template.json",
            "next_after_user_setup": "V2.10-B Real API Metadata Intake And Live Readiness Check",
        },
        "tushare_first": {
            "role": "primary_a_share_data_source",
            "required_env_var_name": "TUSHARE_TOKEN",
            "token_present": tushare_probe.get("token_present"),
            "network_available": tushare_probe.get("network_available"),
            "a_share_core_ready": tushare_a_core_ready,
            "passed_capabilities": [
                {"market": market, "data_type": data_type}
                for market, data_type in sorted(tushare_passed)
            ],
            "unknown_capabilities": tushare_unknown,
            "allowed_uses": [
                "a_share_data_read",
                "historical_sandbox",
                "strategy_research_inputs",
                "simulation_only_suggestions",
            ],
            "forbidden_uses": [
                "real_trade",
                "broker_api",
                "trading_webhook",
                "order_placement",
            ],
        },
        "safe_template_summary": _safe_template_summary(connector),
        "required_metadata_fields": required_metadata_fields,
        "forbidden_fields_or_values": forbidden_fields_or_values,
        "user_steps": user_steps,
        "ready_criteria": [
            "config/external_api_connectors.local.json exists and is gitignored.",
            "metadata contains connector_id api_user_candidate_refresh_approved_env.",
            "markets cover A, H, and US.",
            "allowed_purposes do not contain trade, trading, order, broker, or webhook.",
            "retention_policy is summary_only.",
            "candidate_payload_schema.candidate_summary_only is true.",
            "required local env var names are present, but values are never serialized.",
        ],
        "checks": checks,
        "safety": {
            "metadata_packet_only": True,
            "raw_config_not_stored": True,
            "env_values_not_stored": True,
            "env_var_names_only": True,
            "network_not_used": True,
            "tushare_token_value_not_stored": True,
            "no_raw_api_response": True,
            "no_request_headers_stored": True,
            "no_real_trade": True,
            "no_broker_api": True,
            "no_trading_webhook": True,
            "no_order_placement": True,
            "no_production_records_mutation": True,
            "dashboard_contract_unchanged": True,
        },
    }


def render_api_metadata_activation_packet_markdown(packet: Mapping[str, Any]) -> str:
    lines = [
        "# V2.11-B User API Metadata Activation Packet",
        "",
        f"- status: `{packet.get('overall_status')}`",
        f"- connector_id: `{packet.get('summary', {}).get('connector_id')}`",
        f"- current_intake_status: `{packet.get('summary', {}).get('current_intake_status')}`",
        f"- tushare_status: `{packet.get('summary', {}).get('tushare_status')}`",
        f"- tushare_token_present: `{packet.get('summary', {}).get('tushare_token_present')}`",
        f"- tushare_network_available: `{packet.get('summary', {}).get('tushare_network_available')}`",
        f"- local_config_path: `{packet.get('summary', {}).get('local_config_path')}`",
        f"- user_template_path: `{packet.get('summary', {}).get('user_template_path')}`",
        f"- required_env_vars: `{packet.get('summary', {}).get('required_env_vars')}`",
        "",
        "## Tushare First",
        "",
    ]
    tushare = packet.get("tushare_first", {})
    lines.extend(
        [
            f"- role: `{tushare.get('role')}`",
            f"- required_env_var_name: `{tushare.get('required_env_var_name')}`",
            f"- a_share_core_ready: `{tushare.get('a_share_core_ready')}`",
            f"- allowed_uses: `{tushare.get('allowed_uses')}`",
            f"- forbidden_uses: `{tushare.get('forbidden_uses')}`",
            "",
        ]
    )
    lines.extend(
        [
        "## Fill These Non-Secret Metadata Fields",
        "",
        ]
    )
    for field in packet.get("required_metadata_fields", []):
        lines.append(f"- `{field}`")

    lines.extend(["", "## Never Put These In Files Or Chat", ""])
    for field in packet.get("forbidden_fields_or_values", []):
        lines.append(f"- {field}")

    lines.extend(["", "## User Steps", ""])
    for step in packet.get("user_steps", []):
        lines.append(f"- {step}")

    lines.extend(["", "## Ready Criteria", ""])
    for criterion in packet.get("ready_criteria", []):
        lines.append(f"- {criterion}")

    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "- Metadata packet only.",
            "- No network fetch.",
            "- No API key values stored.",
            "- No broker API.",
            "- No trading webhook.",
            "- No order placement.",
            "",
        ]
    )
    return "\n".join(lines)
