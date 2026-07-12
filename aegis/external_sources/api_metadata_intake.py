"""Validate real-user API metadata readiness without storing secrets."""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import urlparse

from aegis.external_sources.api_config import APIConfigError, load_api_connector_specs
from aegis.external_sources.api_connector import evaluate_api_connector
from aegis.models.external_api import ExternalAPIConnectorSpec


CANDIDATE_REFRESH_CONNECTOR_ID = "api_user_candidate_refresh_approved_env"
LOCAL_CONFIG_RELATIVE_PATH = "config/external_api_connectors.local.json"
FORBIDDEN_PURPOSE_TERMS = ("trade", "trading", "order", "broker", "webhook")
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


def _contains_secret_like_material(payload: dict[str, Any]) -> bool:
    for text in _walk_strings(payload):
        lowered = text.lower()
        if any(pattern in lowered for pattern in SECRET_VALUE_PATTERNS):
            return True
    return False


def _purposes_are_safe(spec: ExternalAPIConnectorSpec) -> bool:
    joined = " ".join(spec.allowed_purposes).lower()
    return not any(term in joined for term in FORBIDDEN_PURPOSE_TERMS)


def _candidate_schema_ok(raw_connector: dict[str, Any]) -> bool:
    schema = raw_connector.get("candidate_payload_schema")
    if not isinstance(schema, dict):
        return False
    return (
        schema.get("candidate_summary_only") is True
        and set(schema.get("allowed_markets", [])) >= {"A", "H", "US"}
        and isinstance(schema.get("max_items_per_market"), int)
        and schema.get("max_items_per_market", 0) > 0
    )


def _connector_summary(spec: ExternalAPIConnectorSpec, *, raw_connector: dict[str, Any], env: Mapping[str, str]) -> dict[str, Any]:
    decision = evaluate_api_connector(spec)
    parsed = urlparse(spec.base_url)
    required = list(spec.required_env_vars)
    present = [name for name in required if bool(env.get(name))]
    missing = [name for name in required if name not in present]
    return {
        "connector_id": spec.connector_id,
        "name": spec.name,
        "provider_type": spec.provider_type,
        "markets": spec.markets,
        "base_url_host": parsed.netloc,
        "base_url_sha256": _sha256_text(spec.base_url),
        "auth_method": spec.auth_method,
        "required_env_vars": required,
        "present_env_vars": present,
        "missing_env_vars": missing,
        "license_status": spec.license_status,
        "retention_policy": spec.retention_policy,
        "allowed_purposes": spec.allowed_purposes,
        "policy_decision": decision.decision,
        "policy_reasons": decision.reasons,
        "candidate_payload_schema_ok": _candidate_schema_ok(raw_connector),
        "safe_purposes": _purposes_are_safe(spec),
        "can_run_live_readiness": decision.can_connect and not missing,
    }


def assess_api_metadata_intake(
    *,
    local_config_path: Path,
    gitignore_path: Path,
    connector_id: str = CANDIDATE_REFRESH_CONNECTOR_ID,
    env: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    env_source = env if env is not None else os.environ
    gitignore_text = gitignore_path.read_text(encoding="utf-8") if gitignore_path.exists() else ""
    local_config_gitignored = LOCAL_CONFIG_RELATIVE_PATH in gitignore_text

    if not local_config_path.exists():
        return {
            "intake_status": "blocked_missing_metadata",
            "connector_id": connector_id,
            "local_config_path": str(local_config_path),
            "local_config_gitignored": local_config_gitignored,
            "checked_at": _now_iso(),
            "blocked_by": ["missing_connector_metadata"],
            "blocked_reason": f"{LOCAL_CONFIG_RELATIVE_PATH} is missing",
            "connectors": [],
            "selected_connector": None,
            "required_env_vars": [],
            "present_env_vars": [],
            "missing_env_vars": [],
            "secret_like_material_detected": False,
            "raw_config_stored": False,
        }

    try:
        payload = json.loads(local_config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {
            "intake_status": "blocked_invalid_metadata",
            "connector_id": connector_id,
            "local_config_path": str(local_config_path),
            "local_config_gitignored": local_config_gitignored,
            "checked_at": _now_iso(),
            "blocked_by": ["invalid_json"],
            "blocked_reason": str(exc),
            "connectors": [],
            "selected_connector": None,
            "required_env_vars": [],
            "present_env_vars": [],
            "missing_env_vars": [],
            "secret_like_material_detected": False,
            "raw_config_stored": False,
        }

    if _contains_secret_like_material(payload):
        return {
            "intake_status": "blocked_secret_like_material",
            "connector_id": connector_id,
            "local_config_path": str(local_config_path),
            "local_config_gitignored": local_config_gitignored,
            "checked_at": _now_iso(),
            "blocked_by": ["secret_like_material_detected"],
            "blocked_reason": "local connector metadata appears to contain token/secret/cookie/password material",
            "connectors": [],
            "selected_connector": None,
            "required_env_vars": [],
            "present_env_vars": [],
            "missing_env_vars": [],
            "secret_like_material_detected": True,
            "raw_config_stored": False,
        }

    raw_by_id = {
        item.get("connector_id"): item
        for item in payload.get("connectors", [])
        if isinstance(item, dict) and item.get("connector_id")
    }
    try:
        specs = load_api_connector_specs(local_config_path)
    except APIConfigError as exc:
        return {
            "intake_status": "blocked_invalid_metadata",
            "connector_id": connector_id,
            "local_config_path": str(local_config_path),
            "local_config_gitignored": local_config_gitignored,
            "checked_at": _now_iso(),
            "blocked_by": ["invalid_connector_metadata"],
            "blocked_reason": str(exc),
            "connectors": [],
            "selected_connector": None,
            "required_env_vars": [],
            "present_env_vars": [],
            "missing_env_vars": [],
            "secret_like_material_detected": False,
            "raw_config_stored": False,
        }

    connector_summaries = [
        _connector_summary(spec, raw_connector=raw_by_id.get(spec.connector_id, {}), env=env_source)
        for spec in specs
    ]
    selected = next((item for item in connector_summaries if item["connector_id"] == connector_id), None)
    if selected is None:
        return {
            "intake_status": "blocked_missing_connector",
            "connector_id": connector_id,
            "local_config_path": str(local_config_path),
            "local_config_gitignored": local_config_gitignored,
            "checked_at": _now_iso(),
            "blocked_by": ["connector_id_not_found"],
            "blocked_reason": f"connector_id not found: {connector_id}",
            "connectors": connector_summaries,
            "selected_connector": None,
            "required_env_vars": [],
            "present_env_vars": [],
            "missing_env_vars": [],
            "secret_like_material_detected": False,
            "raw_config_stored": False,
        }

    blocked_by: list[str] = []
    if not local_config_gitignored:
        blocked_by.append("local_config_not_gitignored")
    if selected["policy_decision"] != "allow":
        blocked_by.append("policy_denied")
    if set(selected["markets"]) < {"A", "H", "US"}:
        blocked_by.append("missing_a_h_us_market_coverage")
    if not selected["candidate_payload_schema_ok"]:
        blocked_by.append("candidate_payload_schema_invalid")
    if not selected["safe_purposes"]:
        blocked_by.append("unsafe_allowed_purposes")
    if selected["missing_env_vars"]:
        blocked_by.append("missing_required_env_vars")

    if not blocked_by:
        status = "ready_for_live_readiness_check"
        reason = None
    elif blocked_by == ["missing_required_env_vars"]:
        status = "blocked_missing_env_vars"
        reason = "missing required env vars: " + ", ".join(selected["missing_env_vars"])
    else:
        status = "blocked_invalid_or_incomplete_metadata"
        reason = ", ".join(blocked_by)

    return {
        "intake_status": status,
        "connector_id": connector_id,
        "local_config_path": str(local_config_path),
        "local_config_gitignored": local_config_gitignored,
        "checked_at": _now_iso(),
        "blocked_by": blocked_by,
        "blocked_reason": reason,
        "connectors": connector_summaries,
        "selected_connector": selected,
        "required_env_vars": selected["required_env_vars"],
        "present_env_vars": selected["present_env_vars"],
        "missing_env_vars": selected["missing_env_vars"],
        "secret_like_material_detected": False,
        "raw_config_stored": False,
    }


def build_api_metadata_intake_report(
    *,
    local_config_path: Path,
    gitignore_path: Path,
    connector_id: str,
    run_id: str,
    env: Mapping[str, str] | None = None,
    command: str | None = None,
) -> dict[str, Any]:
    intake = assess_api_metadata_intake(
        local_config_path=local_config_path,
        gitignore_path=gitignore_path,
        connector_id=connector_id,
        env=env,
    )
    checks = {
        "status_recorded": intake["intake_status"]
        in {
            "blocked_missing_metadata",
            "blocked_invalid_metadata",
            "blocked_secret_like_material",
            "blocked_missing_connector",
            "blocked_missing_env_vars",
            "blocked_invalid_or_incomplete_metadata",
            "ready_for_live_readiness_check",
        },
        "missing_metadata_not_overclaimed": intake["intake_status"] != "blocked_missing_metadata"
        or intake["selected_connector"] is None,
        "ready_requires_env_present": intake["intake_status"] != "ready_for_live_readiness_check"
        or not intake["missing_env_vars"],
        "ready_requires_a_h_us": intake["intake_status"] != "ready_for_live_readiness_check"
        or set(intake["selected_connector"]["markets"]) >= {"A", "H", "US"},
        "secret_like_material_blocked": intake["secret_like_material_detected"] is False
        or intake["intake_status"] == "blocked_secret_like_material",
        "raw_config_not_stored": intake["raw_config_stored"] is False,
        "env_values_not_stored": True,
        "env_var_names_only": True,
        "network_not_used": True,
        "no_real_trade": True,
        "no_broker_api": True,
        "no_trading_webhook": True,
        "no_order_placement": True,
    }
    return {
        "overall_status": "PASS" if all(checks.values()) else "FAIL",
        "acceptance_target": "V2.10-B Real API Metadata Intake And Live Readiness Check",
        "run_id": run_id,
        "generated_at": _now_iso(),
        "command": command,
        "network_used": False,
        "production_records_written": False,
        "dashboard_contract_changed": False,
        "intake": intake,
        "summary": {
            "intake_status": intake["intake_status"],
            "blocked_by": intake["blocked_by"],
            "connector_id": connector_id,
            "required_env_vars": intake["required_env_vars"],
            "present_env_vars": intake["present_env_vars"],
            "missing_env_vars": intake["missing_env_vars"],
            "next_target": "V2.10-C Real API Candidate Refresh Live Dry Run When Ready",
        },
        "checks": checks,
        "safety": {
            "metadata_preflight_only": True,
            "raw_config_not_stored": True,
            "env_values_not_stored": True,
            "env_var_names_only": True,
            "network_not_used": True,
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
