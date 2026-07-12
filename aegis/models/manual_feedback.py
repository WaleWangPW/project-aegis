"""User-submitted manual feedback evidence.

These records describe what the user says or attaches after reviewing Aegis
simulation-only suggestions. They are evidence inputs only; they are not
orders, broker instructions, or PaperTrade mutations.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from aegis.models.common import Market

FeedbackType = Literal["review_note", "manual_watch", "manual_ignore", "external_manual_execution"]
FeedbackStatus = Literal["accepted", "blocked"]


class ManualFeedbackInput(BaseModel):
    feedback_id: str
    suggestion_id: str
    symbol: str
    market: Market
    feedback_type: FeedbackType
    user_note: str
    screenshot_paths: list[str] = Field(default_factory=list)
    external_execution_summary: str | None = None
    submitted_at: str

    @field_validator("feedback_id", "suggestion_id", "symbol", "user_note", "submitted_at")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("field must not be blank")
        return value

    @model_validator(mode="after")
    def _execution_summary_required_when_execution_claimed(self) -> "ManualFeedbackInput":
        if self.feedback_type == "external_manual_execution" and not (self.external_execution_summary or "").strip():
            raise ValueError("external manual execution feedback requires external_execution_summary")
        return self


class ManualFeedbackRecord(BaseModel):
    feedback_id: str
    suggestion_id: str
    symbol: str
    market: Market
    feedback_type: FeedbackType
    feedback_status: FeedbackStatus
    user_note_summary: str
    screenshot_evidence: list[dict] = Field(default_factory=list)
    external_execution_summary: str | None = None
    blocked_by: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    linked_brief_item_id: str | None = None
    user_submitted_evidence_only: bool = True
    simulation_only: bool = True
    manual_external_execution_only: bool = True
    no_real_trade_execution: bool = True
    no_broker_api: bool = True
    no_webhook: bool = True
    no_order_placement: bool = True
    created_at: str

    @model_validator(mode="after")
    def _status_consistency(self) -> "ManualFeedbackRecord":
        if self.feedback_status == "blocked" and not self.blocked_by:
            raise ValueError("blocked feedback requires blocked_by")
        if self.feedback_status == "accepted" and self.blocked_by:
            raise ValueError("accepted feedback must not carry blocked_by")
        if not (
            self.user_submitted_evidence_only
            and self.simulation_only
            and self.manual_external_execution_only
            and self.no_real_trade_execution
            and self.no_broker_api
            and self.no_webhook
            and self.no_order_placement
        ):
            raise ValueError("manual feedback intake must remain evidence-only and non-executing")
        return self
