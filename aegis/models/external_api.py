"""External API connector specifications.

Connector specs describe approved data/API inputs without storing credentials.
They are not provider implementations, broker integrations, or webhooks.
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

Market = Literal["A", "H", "US", "GLOBAL"]
ProviderType = Literal[
    "official_regulator",
    "official_company",
    "licensed_market_data",
    "user_provided_research_api",
    "social_official_api",
    "broker_api",
    "trading_webhook",
    "unknown",
]
AuthMethod = Literal["none", "env_var", "oauth", "api_key_value_forbidden"]
RetentionPolicy = Literal["metadata_only", "summary_only", "short_excerpt", "no_storage"]

_SECRET_PATTERNS = ("token", "secret", "api_key", "apikey", "password", "bearer ", "cookie")


class ExternalAPIConnectorSpec(BaseModel):
    connector_id: str
    name: str
    provider_type: ProviderType
    markets: list[Market] = Field(default_factory=list)
    base_url: str
    auth_method: AuthMethod
    required_env_vars: list[str] = Field(default_factory=list)
    license_status: Literal["approved", "pending", "not_required", "forbidden", "unknown"]
    retention_policy: RetentionPolicy
    allowed_purposes: list[str] = Field(default_factory=list)
    can_connect: bool
    notes: Optional[str] = None

    @field_validator("connector_id", "name", "base_url")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("field must not be blank")
        return value

    @model_validator(mode="after")
    def _safety_rules(self) -> "ExternalAPIConnectorSpec":
        joined = " ".join([self.base_url, self.notes or "", *self.required_env_vars]).lower()
        if self.auth_method == "api_key_value_forbidden":
            raise ValueError("API key values must not be stored in connector specs")
        if any(pattern in self.base_url.lower() for pattern in _SECRET_PATTERNS):
            raise ValueError("base_url must not include token, secret, api_key, password, bearer, or cookie material")
        if self.provider_type in {"broker_api", "trading_webhook"} and self.can_connect:
            raise ValueError("broker APIs and trading webhooks must not be enabled")
        if self.provider_type == "licensed_market_data" and self.license_status != "approved" and self.can_connect:
            raise ValueError("licensed market data requires approved license before connection")
        if self.auth_method == "env_var" and not self.required_env_vars:
            raise ValueError("env_var auth requires env var names")
        if "cookie" in joined and self.can_connect:
            raise ValueError("cookie-based API access is not allowed")
        return self


class ExternalAPIConnectorDecision(BaseModel):
    connector_id: str
    decision: Literal["allow", "deny"]
    can_connect: bool
    reasons: list[str] = Field(default_factory=list)
    allowed_purposes: list[str] = Field(default_factory=list)
    retention_policy: RetentionPolicy
    required_env_vars: list[str] = Field(default_factory=list)


class ExternalAPIFetchItem(BaseModel):
    connector_id: str
    retrieved_at: str
    endpoint_path: str
    status_code: int
    content_type: str
    summary: str
    content_hash: str
    raw_bytes_stored: bool = False
    auth_env_vars_used: list[str] = Field(default_factory=list)
    request_headers_stored: bool = False
    safety_notes: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _no_raw_or_headers(self) -> "ExternalAPIFetchItem":
        if self.raw_bytes_stored:
            raise ValueError("API fetch items must not store raw bytes")
        if self.request_headers_stored:
            raise ValueError("API fetch items must not store request headers")
        return self
