"""Policy gate for external market-intelligence sources."""

from __future__ import annotations

from aegis.models.external_source import ExternalSourcePolicy, SourcePolicyDecision

_DEFAULT_ALLOWED_FIELDS = ["source_id", "title", "url_or_external_id", "published_at", "summary", "hash"]


def evaluate_source_policy(source: ExternalSourcePolicy) -> SourcePolicyDecision:
    reasons: list[str] = []
    allowed = source.can_collect

    if source.access_method == "unauthorized_scrape":
        allowed = False
        reasons.append("unauthorized_scrape_forbidden")
    if source.paywalled and source.license_status != "approved":
        allowed = False
        reasons.append("paywalled_requires_approved_license")
    if source.source_type == "licensed_financial_data" and source.license_status != "approved":
        allowed = False
        reasons.append("licensed_financial_data_requires_approved_license")
    if source.source_type in {"reddit", "x_twitter"} and source.access_method != "official_api":
        allowed = False
        reasons.append("social_source_requires_official_api")
    if source.source_type in {"reddit", "x_twitter"} and source.license_status not in {"approved", "not_required"}:
        allowed = False
        reasons.append("social_source_requires_terms_approval")
    if source.evidence_level in {"llm_summary", "unverified_web"}:
        allowed = False
        reasons.append("evidence_level_not_allowed_for_collection")

    if allowed and not reasons:
        reasons.append("policy_gate_allow")
    elif not reasons:
        reasons.append("source_declared_not_collectible")

    return SourcePolicyDecision(
        source_id=source.source_id,
        can_collect=allowed,
        decision="allow" if allowed else "deny",
        reasons=reasons,
        evidence_level=source.evidence_level,
        retention_policy=source.retention_policy,
        allowed_fields=source.allowed_fields or _DEFAULT_ALLOWED_FIELDS,
    )


def evaluate_source_registry(sources: list[ExternalSourcePolicy]) -> dict:
    decisions = [evaluate_source_policy(source) for source in sources]
    allow_count = sum(1 for decision in decisions if decision.can_collect)
    deny_count = len(decisions) - allow_count
    return {
        "registry_type": "external_source_policy_gate",
        "source_count": len(sources),
        "allow_count": allow_count,
        "deny_count": deny_count,
        "decisions": [decision.model_dump() for decision in decisions],
        "safety": {
            "no_live_fetch": True,
            "no_cookie_access": True,
            "no_secret_storage": True,
            "no_paywall_bypass": True,
            "no_real_trade": True,
            "no_broker_api": True,
            "no_webhook": True,
            "no_strategy_mutation": True,
            "dashboard_contract_unchanged": True,
        },
    }
