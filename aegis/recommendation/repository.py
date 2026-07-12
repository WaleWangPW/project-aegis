"""RecommendationRepository — Phase 4 §9.

Append-only JSONL persistence, no database, reusing the existing
`aegis/utils/jsonl.py` helpers exactly like `DataGapRegistry` (Phase 1) and
`scripts/run_pre_market.py` (Phase 2/3) already do.
"""

from __future__ import annotations

from pathlib import Path

from aegis.models.decision import DecisionRecord
from aegis.models.recommendation import RecommendationRecord
from aegis.utils.jsonl import append_jsonl, read_jsonl

DECISIONS_FILENAME = "decisions.jsonl"
RECOMMENDATIONS_FILENAME = "recommendations.jsonl"


class RecommendationRepository:
    def __init__(self, records_dir: str | Path):
        self.records_dir = Path(records_dir)

    def append_decision(self, decision: DecisionRecord) -> None:
        append_jsonl(self.records_dir / DECISIONS_FILENAME, decision.model_dump())

    def append_recommendation(self, record: RecommendationRecord) -> None:
        append_jsonl(self.records_dir / RECOMMENDATIONS_FILENAME, record.model_dump())

    def list_decisions(self) -> list[DecisionRecord]:
        return [DecisionRecord(**row) for row in read_jsonl(self.records_dir / DECISIONS_FILENAME)]

    def list_recommendations(self) -> list[RecommendationRecord]:
        return [RecommendationRecord(**row) for row in read_jsonl(self.records_dir / RECOMMENDATIONS_FILENAME)]
