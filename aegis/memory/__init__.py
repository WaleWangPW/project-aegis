"""InvestmentMemory — Phase 6 §5.6.

Minimal memory loop: `ReviewRecord.lessons[]` -> `InvestmentMemory` JSONL
append. Deliberately no vector database, no embeddings, no semantic
retrieval, no LLM memory rewriting, no automatic strategy mutation
(Master Spec §5.10/§8.11 — "P0 不做向量库").
"""

from __future__ import annotations

from aegis.memory.repository import MemoryRepository
from aegis.memory.service import MemoryService

__all__ = ["MemoryRepository", "MemoryService"]
