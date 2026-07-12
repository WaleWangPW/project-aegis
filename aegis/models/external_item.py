"""External market-intelligence item model for V2.0-F."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from aegis.models.common import Market
from aegis.models.external_source import EvidenceLevel, LicenseStatus, RetentionPolicy, SourceType


class ExternalMarketItem(BaseModel):
    source_id: str
    source_type: SourceType
    symbol: str
    market: Market
    retrieved_at: str
    published_at: Optional[str] = None
    author_or_publisher: str
    url_or_external_id: str
    license_status: LicenseStatus
    evidence_level: EvidenceLevel
    summary: str
    quoted_excerpt: Optional[str] = None
    content_hash: str
    retention_policy: RetentionPolicy
    raw_bytes_stored: bool = False
    safety_notes: list[str] = Field(default_factory=list)
