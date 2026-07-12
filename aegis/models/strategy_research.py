"""Structured strategy research ingestion models."""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

Market = Literal["A", "H", "US", "GLOBAL"]
StrategyFamily = Literal[
    "value",
    "quality",
    "momentum",
    "low_volatility",
    "dividend",
    "size",
    "multi_factor",
    "risk_overlay",
]
ResearchSourceType = Literal["academic", "index_provider", "asset_manager", "regulator", "official_company", "public_web"]
EvidenceLevel = Literal["primary_research", "institutional_research", "verified_primary", "context_only"]
RetentionPolicy = Literal["metadata_only", "summary_only", "short_excerpt", "no_storage"]


class StrategyResearchRecord(BaseModel):
    research_id: str
    title: str
    source_type: ResearchSourceType
    publisher: str
    url: str
    published_at: Optional[str] = None
    markets: list[Market]
    strategy_families: list[StrategyFamily]
    evidence_level: EvidenceLevel
    retention_policy: RetentionPolicy = "summary_only"
    summary: str
    implications: list[str] = Field(default_factory=list)
    raw_text_stored: bool = False

    @field_validator("research_id", "title", "publisher", "url", "summary")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("field must not be blank")
        return value

    @model_validator(mode="after")
    def _retention_rules(self) -> "StrategyResearchRecord":
        if self.raw_text_stored:
            raise ValueError("strategy research ingestion must not store raw full text")
        if self.evidence_level == "context_only" and self.retention_policy not in {"metadata_only", "summary_only"}:
            raise ValueError("context-only research cannot retain excerpts")
        if not self.markets:
            raise ValueError("at least one market is required")
        if not self.strategy_families:
            raise ValueError("at least one strategy family is required")
        return self


class StrategyResearchCorpus(BaseModel):
    schema_version: str
    generated_at: str
    record_count: int
    market_coverage: dict[str, int]
    strategy_family_coverage: dict[str, int]
    records: list[StrategyResearchRecord]
    safety: dict[str, bool]
