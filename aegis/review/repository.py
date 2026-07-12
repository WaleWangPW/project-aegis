"""ReviewRepository — Phase 6 §5.5.

Append-only JSONL persistence, same pattern as `PaperTradeRepository`/
`RecommendationRepository`. Guards against duplicate reviews for the same
`recommendation_id + horizon` pair — `ReviewService` also checks this before
building a review, but the repository re-checks independently so a
duplicate can never slip in through a different call path.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from aegis.models.review import ReviewRecord
from aegis.utils.jsonl import append_jsonl, read_jsonl

REVIEWS_FILENAME = "reviews.jsonl"


class ReviewRepository:
    def __init__(self, records_dir: str | Path):
        self.records_dir = Path(records_dir)
        self.path = self.records_dir / REVIEWS_FILENAME

    def append(self, review: ReviewRecord) -> None:
        if self.exists_for(review.recommendation_id, review.horizon):
            return  # never create a duplicate recommendation_id+horizon review
        append_jsonl(self.path, review.model_dump())

    def list_all(self) -> list[ReviewRecord]:
        return [ReviewRecord(**row) for row in read_jsonl(self.path)]

    def find_by_id(self, review_id: str) -> Optional[ReviewRecord]:
        for review in self.list_all():
            if review.review_id == review_id:
                return review
        return None

    def find_by_recommendation_id(self, recommendation_id: str) -> list[ReviewRecord]:
        return [r for r in self.list_all() if r.recommendation_id == recommendation_id]

    def exists_for(self, recommendation_id: str, horizon: str) -> bool:
        return any(
            r.recommendation_id == recommendation_id and r.horizon == horizon for r in self.list_all()
        )
