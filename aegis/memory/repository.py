"""MemoryRepository — Phase 6 §5.6.

Plain append-only JSONL storage, same pattern as every other repository in
this project. No database, no vector index.
"""

from __future__ import annotations

from pathlib import Path

from aegis.models.investment_memory import InvestmentMemory
from aegis.utils.jsonl import append_jsonl, read_jsonl

MEMORY_FILENAME = "memory.jsonl"


class MemoryRepository:
    def __init__(self, records_dir: str | Path):
        self.records_dir = Path(records_dir)
        self.path = self.records_dir / MEMORY_FILENAME

    def append(self, memory: InvestmentMemory) -> None:
        append_jsonl(self.path, memory.model_dump())

    def append_all(self, memories: list[InvestmentMemory]) -> None:
        for memory in memories:
            self.append(memory)

    def list_all(self) -> list[InvestmentMemory]:
        return [InvestmentMemory(**row) for row in read_jsonl(self.path)]

    def find_by_recommendation_id(self, recommendation_id: str) -> list[InvestmentMemory]:
        return [m for m in self.list_all() if m.linked_recommendation_id == recommendation_id]
