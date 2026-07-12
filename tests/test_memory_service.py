"""Phase 6 tests for MemoryService — PHASE6 doc §5.6/§7.3.

No vector database, no embeddings — just ReviewRecord.lessons[] ->
InvestmentMemory JSONL append.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from aegis.memory.repository import MemoryRepository
from aegis.memory.service import MemoryService
from aegis.models.review import ReviewRecord


def _review(*, lessons=None, outcome="success", decision_quality="good_decision") -> ReviewRecord:
    return ReviewRecord(
        review_id="rev_rec_1_5d",
        recommendation_id="rec_1",
        review_date="2026-07-06",
        horizon="5d",
        outcome=outcome,
        actual_return=0.05,
        max_drawdown=-0.01,
        decision_quality=decision_quality,
        expert_contribution={"TrendAgent": "support"},
        lessons=lessons if lessons is not None else [],
        created_at="2026-07-06T00:00:00+00:00",
    )


def test_review_lessons_create_investment_memory_records():
    service = MemoryService()
    review = _review(lessons=["证据充分且结果兑现，支持理由/失效条件设计可复用。"])

    memories = service.create_from_review(review)

    assert len(memories) == 1
    assert memories[0].linked_recommendation_id == "rec_1"
    assert memories[0].lesson == "证据充分且结果兑现，支持理由/失效条件设计可复用。"
    assert memories[0].lesson_type == "good_decision"


def test_empty_lessons_create_no_memory():
    service = MemoryService()
    review = _review(lessons=[])

    memories = service.create_from_review(review)

    assert memories == []


def test_no_vector_or_embedding_dependency_introduced():
    import aegis.memory.service as memory_service_module

    # Check actual import lines, not the module's own prose docstring
    # (which legitimately explains what is NOT used, e.g. "no embeddings").
    source_lines = open(memory_service_module.__file__, encoding="utf-8").read().splitlines()
    import_lines = "\n".join(line for line in source_lines if line.strip().startswith(("import ", "from ")))
    for banned in ("faiss", "chromadb", "pinecone", "embedding", "vector_store", "qdrant", "openai"):
        assert banned not in import_lines.lower()


def test_append_memories_persists_via_repository(tmp_path: Path):
    records_dir = tmp_path / "records"
    repository = MemoryRepository(records_dir)
    service = MemoryService(repository=repository)
    review = _review(lessons=["lesson one", "lesson two"])

    memories = service.create_from_review(review)
    service.append_memories(memories)

    persisted = repository.list_all()
    assert len(persisted) == 2
    assert {m.lesson for m in persisted} == {"lesson one", "lesson two"}


def test_append_memories_without_repository_raises(tmp_path: Path):
    service = MemoryService()  # no repository injected
    review = _review(lessons=["lesson one"])
    memories = service.create_from_review(review)

    with pytest.raises(ValueError):
        service.append_memories(memories)


def test_append_memories_with_empty_list_is_a_no_op(tmp_path: Path):
    service = MemoryService()  # no repository — must not raise since there's nothing to persist
    service.append_memories([])
