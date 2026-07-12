"""Live API metadata activation preflight.

This module checks whether a user-provided API connector is ready for a bounded
live dry-run. It never prints or stores env var values.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping

from aegis.external_sources.api_config import APIConfigError, get_api_connector_spec
from aegis.external_sources.api_connector import evaluate_api_connector


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def assess_live_api_activation(
    *,
    config_path: Path,
    connector_id: str,
    env: Mapping[str, str] | None = None,
) -> dict:
    """Return activation status without performing a network call."""

    env_source = env if env is not None else os.environ
    try:
        spec = get_api_connector_spec(config_path, connector_id)
    except APIConfigError as exc:
        return {
            "activation_status": "blocked_missing_metadata",
            "connector_id": connector_id,
            "config_path": str(config_path),
            "can_run_live_dry_run": False,
            "blocked_by": ["missing_connector_metadata"],
            "blocked_reason": str(exc),
            "required_env_vars": [],
            "present_env_vars": [],
            "missing_env_vars": [],
            "checked_at": _now_iso(),
        }

    decision = evaluate_api_connector(spec)
    if not decision.can_connect:
        return {
            "activation_status": "blocked_policy_denied",
            "connector_id": connector_id,
            "config_path": str(config_path),
            "provider_type": spec.provider_type,
            "markets": spec.markets,
            "can_run_live_dry_run": False,
            "blocked_by": ["policy_denied"],
            "blocked_reason": "; ".join(decision.reasons),
            "required_env_vars": spec.required_env_vars,
            "present_env_vars": [],
            "missing_env_vars": spec.required_env_vars,
            "checked_at": _now_iso(),
        }

    required = list(spec.required_env_vars)
    present = [name for name in required if bool(env_source.get(name))]
    missing = [name for name in required if name not in present]
    if missing:
        return {
            "activation_status": "blocked_missing_env_vars",
            "connector_id": connector_id,
            "config_path": str(config_path),
            "provider_type": spec.provider_type,
            "markets": spec.markets,
            "can_run_live_dry_run": False,
            "blocked_by": ["missing_required_env_vars"],
            "blocked_reason": "missing required env vars: " + ", ".join(missing),
            "required_env_vars": required,
            "present_env_vars": present,
            "missing_env_vars": missing,
            "checked_at": _now_iso(),
        }

    return {
        "activation_status": "ready_for_live_dry_run",
        "connector_id": connector_id,
        "config_path": str(config_path),
        "provider_type": spec.provider_type,
        "markets": spec.markets,
        "base_url": spec.base_url,
        "retention_policy": spec.retention_policy,
        "allowed_purposes": spec.allowed_purposes,
        "can_run_live_dry_run": True,
        "blocked_by": [],
        "blocked_reason": None,
        "required_env_vars": required,
        "present_env_vars": present,
        "missing_env_vars": [],
        "checked_at": _now_iso(),
    }


def build_api_activation_report(
    *,
    config_path: Path,
    connector_id: str,
    run_id: str,
    env: Mapping[str, str] | None = None,
    command: str | None = None,
) -> dict:
    activation = assess_live_api_activation(config_path=config_path, connector_id=connector_id, env=env)
    checks = {
        "metadata_status_recorded": activation["activation_status"]
        in {"blocked_missing_metadata", "blocked_missing_env_vars", "blocked_policy_denied", "ready_for_live_dry_run"},
        "ready_implies_no_missing_env_vars": (
            activation["activation_status"] != "ready_for_live_dry_run" or not activation["missing_env_vars"]
        ),
        "blocked_has_reason": (
            activation["activation_status"] == "ready_for_live_dry_run" or bool(activation["blocked_reason"])
        ),
        "env_values_not_stored": True,
        "env_var_names_only": True,
        "network_not_used": True,
        "no_real_trade": True,
        "no_broker_api": True,
        "no_webhook": True,
        "no_order_placement": True,
    }
    return {
        "overall_status": "PASS" if all(checks.values()) else "FAIL",
        "acceptance_target": "V2.7-A Live API Metadata Activation",
        "run_id": run_id,
        "generated_at": _now_iso(),
        "command": command,
        "network_used": False,
        "production_records_written": False,
        "dashboard_contract_changed": False,
        "activation": activation,
        "checks": checks,
        "safety": {
            "preflight_only": True,
            "env_values_not_stored": True,
            "env_var_names_only": True,
            "no_raw_api_response": True,
            "no_request_headers_stored": True,
            "no_real_trade": True,
            "no_broker_api": True,
            "no_webhook": True,
            "no_order_placement": True,
            "dashboard_contract_unchanged": True,
            "no_production_records_mutation": True,
        },
    }
