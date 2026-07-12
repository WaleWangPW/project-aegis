"""Recommendation — Phase 4 §8-9.

`RecommendationService` maps a `DecisionRecord` + supporting context into
the canonical `RecommendationRecord` (Master Spec ADR-001), with a full
evidence trace back to the ExpertOpinions that produced it.
`RecommendationRepository` persists both records to JSONL — append-only,
no database.
"""

from .repository import RecommendationRepository
from .service import RecommendationService

__all__ = ["RecommendationService", "RecommendationRepository"]
