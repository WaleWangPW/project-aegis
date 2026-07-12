"""Research workspace models for V2.0-C.

Research notes are decision-support material, not trading instructions. A
note may contain a thesis, risks, and open questions, but every
decision-relevant claim must point to evidence links. Unverified LLM output
is allowed only as a note draft/source label and must never be promoted to
accepted evidence.
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator

from aegis.models.common import Market

EvidenceType = Literal[
    "system_report",
    "user_submitted",
    "manual_note",
    "filing",
    "news",
    "price_data",
    "llm_unverified",
]
EvidenceStatus = Literal["verified", "pending", "rejected"]


class ResearchEvidenceLink(BaseModel):
    evidence_id: str
    evidence_type: EvidenceType
    title: str
    source: str
    path_or_url: Optional[str] = None
    captured_at: str
    status: EvidenceStatus
    summary: str

    @model_validator(mode="after")
    def _llm_unverified_cannot_be_verified(self) -> "ResearchEvidenceLink":
        if self.evidence_type == "llm_unverified" and self.status == "verified":
            raise ValueError("llm_unverified evidence must not be marked verified")
        return self


class ResearchNote(BaseModel):
    note_id: str
    symbol: str
    market: Market
    title: str
    thesis: str
    risks: list[str] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    decision_relevance: str
    created_at: str
    updated_at: str

    @model_validator(mode="after")
    def _requires_evidence(self) -> "ResearchNote":
        if not self.evidence_ids:
            raise ValueError("ResearchNote requires at least one evidence_id")
        return self


class ResearchWorkspace(BaseModel):
    workspace_id: str
    symbol: str
    market: Market
    notes: list[ResearchNote]
    evidence: list[ResearchEvidenceLink]
    decision_summary: str
    unresolved_questions: list[str] = Field(default_factory=list)
    created_at: str
    updated_at: str
