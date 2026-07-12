"""InvestmentMemory — Master Spec §8.11.

A single accumulated lesson. Plain JSONL file memory for P0 — no vector
database (Master Spec §5.10 / §8.11: "P0 不做向量库").
Storage: data/records/memory.jsonl.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class InvestmentMemory(BaseModel):
    memory_id: str
    date: str
    source_type: str
    linked_recommendation_id: Optional[str] = None
    lesson_type: str
    lesson: str
    tags: list[str]
    confidence: float
    created_at: str
