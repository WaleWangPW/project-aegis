"""Policy gate for external API connector specs."""

from __future__ import annotations

from aegis.models.external_api import ExternalAPIConnectorDecision, ExternalAPIConnectorSpec


def evaluate_api_connector(spec: ExternalAPIConnectorSpec) -> ExternalAPIConnectorDecision:
    allowed = spec.can_connect
    reasons: list[str] = []

    if spec.provider_type in {"broker_api", "trading_webhook"}:
        allowed = False
        reasons.append("broker_or_trading_webhook_forbidden")
    if spec.provider_type == "licensed_market_data" and spec.license_status != "approved":
        allowed = False
        reasons.append("licensed_data_requires_approved_license")
    if spec.license_status in {"forbidden", "unknown"}:
        allowed = False
        reasons.append("license_status_not_approved")
    if spec.auth_method == "oauth":
        allowed = False
        reasons.append("oauth_not_supported_in_v2_2_a")
    if spec.auth_method == "env_var" and not spec.required_env_vars:
        allowed = False
        reasons.append("missing_env_var_names")
    if not spec.allowed_purposes:
        allowed = False
        reasons.append("allowed_purposes_required")
    if spec.retention_policy not in {"metadata_only", "summary_only", "short_excerpt", "no_storage"}:
        allowed = False
        reasons.append("unsupported_retention_policy")

    if allowed and not reasons:
        reasons.append("api_connector_policy_allow")
    elif not reasons:
        reasons.append("connector_declared_not_connectible")

    return ExternalAPIConnectorDecision(
        connector_id=spec.connector_id,
        decision="allow" if allowed else "deny",
        can_connect=allowed,
        reasons=reasons,
        allowed_purposes=spec.allowed_purposes,
        retention_policy=spec.retention_policy,
        required_env_vars=spec.required_env_vars,
    )


def evaluate_api_connector_registry(specs: list[ExternalAPIConnectorSpec]) -> dict:
    decisions = [evaluate_api_connector(spec) for spec in specs]
    allow_count = sum(1 for decision in decisions if decision.can_connect)
    deny_count = len(decisions) - allow_count
    return {
        "registry_type": "external_api_connector_policy_gate",
        "connector_count": len(specs),
        "allow_count": allow_count,
        "deny_count": deny_count,
        "decisions": [decision.model_dump() for decision in decisions],
        "safety": {
            "metadata_only_connector_specs": True,
            "no_secret_values_stored": True,
            "env_var_names_only": True,
            "no_cookie_access": True,
            "no_broker_api": True,
            "no_trading_webhook": True,
            "no_real_trade": True,
            "no_strategy_auto_mutation": True,
            "dashboard_contract_unchanged": True,
        },
    }
