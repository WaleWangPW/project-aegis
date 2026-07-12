"""External source registry models for V2.0-E."""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator

SourceType = Literal[
    "licensed_financial_data",
    "official_company",
    "regulator",
    "public_web",
    "reddit",
    "x_twitter",
    "social_public_figure",
    "unknown",
]
AccessMethod = Literal["licensed_api", "official_api", "public_page", "manual_input", "unauthorized_scrape"]
LicenseStatus = Literal["approved", "pending", "not_required", "forbidden", "unknown"]
EvidenceLevel = Literal[
    "verified_primary",
    "licensed_provider",
    "verified_social_statement",
    "community_discussion",
    "llm_summary",
    "unverified_web",
]
RetentionPolicy = Literal["metadata_only", "summary_only", "short_excerpt", "no_storage"]


class ExternalSourcePolicy(BaseModel):
    source_id: str
    name: str
    source_type: SourceType
    access_method: AccessMethod
    license_status: LicenseStatus
    evidence_level: EvidenceLevel
    retention_policy: RetentionPolicy
    allowed_fields: list[str] = Field(default_factory=list)
    requires_api_key: bool = False
    paywalled: bool = False
    can_collect: bool
    notes: Optional[str] = None

    @model_validator(mode="after")
    def _forbid_unsafe_collection(self) -> "ExternalSourcePolicy":
        if self.access_method == "unauthorized_scrape" and self.can_collect:
            raise ValueError("unauthorized_scrape sources must not be collectible")
        if self.paywalled and self.license_status != "approved" and self.can_collect:
            raise ValueError("paywalled sources require approved license before collection")
        if self.evidence_level in {"community_discussion", "llm_summary", "unverified_web"} and self.retention_policy not in {
            "metadata_only",
            "summary_only",
            "no_storage",
        }:
            raise ValueError("low-trust sources must not use long-form retention")
        return self


class SourcePolicyDecision(BaseModel):
    source_id: str
    can_collect: bool
    decision: Literal["allow", "deny"]
    reasons: list[str] = Field(default_factory=list)
    evidence_level: EvidenceLevel
    retention_policy: RetentionPolicy
    allowed_fields: list[str] = Field(default_factory=list)
