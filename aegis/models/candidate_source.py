"""Approved candidate source models.

Candidate sources are refresh inputs for simulation-only suggestion bindings.
They can describe fixtures or user-approved APIs, but they must never store API
keys, cookies, broker credentials, or order-routing information.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from aegis.models.common import Market

SourceType = Literal["approved_fixture", "user_provided_api", "existing_report"]
RefreshMode = Literal["fixture", "api_dry_run", "existing_file"]

_SECRET_PATTERNS = ("token", "secret", "api_key", "apikey", "password", "bearer ", "cookie")


class CandidateSourceItem(BaseModel):
    symbol: str
    market: Market
    name: str | None = None
    score: float | None = None
    status: str = "Watch"
    rationale: list[str] = Field(default_factory=list)

    @field_validator("symbol")
    @classmethod
    def _symbol_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("symbol must not be blank")
        return value


class CandidateSourceSpec(BaseModel):
    source_id: str
    source_type: SourceType
    refresh_mode: RefreshMode
    markets: list[Market]
    license_status: Literal["approved", "not_required", "pending", "forbidden", "unknown"]
    auth_env_vars: list[str] = Field(default_factory=list)
    can_refresh: bool
    retention_policy: Literal["metadata_only", "summary_only", "candidate_summary_only", "no_storage"]
    candidates: list[CandidateSourceItem] = Field(default_factory=list)
    notes: str | None = None

    @field_validator("source_id")
    @classmethod
    def _source_id_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("source_id must not be blank")
        return value

    @model_validator(mode="after")
    def _safety_rules(self) -> "CandidateSourceSpec":
        joined = " ".join([self.source_id, self.notes or ""]).lower()
        if any(pattern in joined for pattern in _SECRET_PATTERNS):
            raise ValueError("candidate source specs must not include secret-like values")
        if self.source_type == "user_provided_api" and self.refresh_mode != "api_dry_run":
            raise ValueError("user_provided_api sources must use api_dry_run refresh mode")
        if self.source_type == "user_provided_api" and not self.auth_env_vars:
            raise ValueError("user_provided_api sources require env var names")
        if self.source_type == "approved_fixture" and self.refresh_mode != "fixture":
            raise ValueError("approved_fixture sources must use fixture refresh mode")
        if self.license_status in {"forbidden", "unknown"} and self.can_refresh:
            raise ValueError("forbidden or unknown license sources cannot refresh")
        if not self.markets:
            raise ValueError("candidate source specs require at least one market")
        for candidate in self.candidates:
            if candidate.market not in self.markets:
                raise ValueError("candidate market must be covered by source markets")
        return self


class CandidateSourceRegistry(BaseModel):
    schema_version: str
    generated_at: str
    sources: list[CandidateSourceSpec]
    safety: dict[str, bool]

    @model_validator(mode="after")
    def _registry_safety(self) -> "CandidateSourceRegistry":
        if not self.sources:
            raise ValueError("candidate source registry requires at least one source")
        if not self.safety.get("no_secret_values_stored"):
            raise ValueError("candidate source registry must forbid stored secret values")
        if not self.safety.get("no_broker_api"):
            raise ValueError("candidate source registry must forbid broker API")
        return self
