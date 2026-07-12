"""MemoryService — Phase 6 §5.6.

The only allowed memory loop for P0: `ReviewRecord.lessons[]` -> a plain
`InvestmentMemory` JSONL append. No vector database, no embeddings, no
semantic retrieval, no LLM rewriting/mutation of the lesson text.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from aegis.memory.repository import MemoryRepository
from aegis.models.investment_memory import InvestmentMemory
from aegis.models.review import ReviewRecord


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


_OUTCOME_CONFIDENCE = {"success": 1.0, "failure": 1.0, "mixed": 0.5, "pending": 0.0}


class MemoryService:
    def __init__(self, repository: Optional[MemoryRepository] = None):
        self.repository = repository

    def create_from_review(self, review: ReviewRecord) -> list[InvestmentMemory]:
        """No lessons -> no memory (PHASE6 doc §5.6/§7.3 rule 2) — never
        invent a lesson from an empty list."""
        if not review.lessons:
            return []

        memories: list[InvestmentMemory] = []
        for index, lesson in enumerate(review.lessons):
            memories.append(
                InvestmentMemory(
                    memory_id=f"mem_{review.review_id}_{index}",
                    date=review.review_date,
                    source_type="review",
                    linked_recommendation_id=review.recommendation_id,
                    lesson_type=review.decision_quality,
                    lesson=lesson,
                    tags=[review.horizon, review.outcome],
                    confidence=_OUTCOME_CONFIDENCE.get(review.outcome, 0.0),
                    created_at=_now_iso(),
                )
            )
        return memories

    def append_memories(self, memories: list[InvestmentMemory]) -> None:
        if not memories:
            return
        if self.repository is None:
            raise ValueError("MemoryService.append_memories requires a repository to persist to.")
        self.repository.append_all(memories)
