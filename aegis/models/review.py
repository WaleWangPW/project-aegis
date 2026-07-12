"""ReviewRecord — Master Spec §8.9.

A post-hoc review of a recommendation's decision quality — not just its
return. "Decision quality" and "return" are deliberately kept separate:
a well-reasoned recommendation that loses money is not automatically a bad
decision, and a lucky guess is not automatically a good one.
Storage: data/records/reviews.jsonl.

Acceptance: a review must evaluate decision_quality, not only actual_return.
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel

Horizon = Literal["5d", "10d", "20d", "40d", "exit"]
Outcome = Literal["success", "failure", "mixed", "pending"]
DecisionQuality = Literal["good_decision", "reasonable_decision", "poor_decision", "unclear"]


class ReviewRecord(BaseModel):
    review_id: str
    recommendation_id: str
    paper_trade_id: Optional[str] = None
    review_date: str
    horizon: Horizon
    outcome: Outcome
    actual_return: Optional[float] = None
    max_drawdown: Optional[float] = None
    decision_quality: DecisionQuality
    success_reason: Optional[str] = None
    failure_reason: Optional[str] = None
    expert_contribution: dict[str, str]
    lessons: list[str]
    created_at: str
