"""JSONL read/write helpers — Master Spec §19 (Storage).

All core records (RecommendationRecord, ExpertOpinion, DecisionRecord,
PaperTrade, ReviewRecord, InvestmentMemory, MarketSnapshot, ...) are stored
as JSONL: one JSON object per line, append-only. These three functions are
the only thing Phase 0 provides — no business logic, no schema validation
beyond "is this valid JSON", no locking/concurrency handling yet.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterator


def read_jsonl(path: str | Path) -> Iterator[dict[str, Any]]:
    """Yield each record (as a dict) from a JSONL file.

    Returns an empty iterator if the file does not exist yet — reading from
    a not-yet-created records file is a normal P0 state, not an error.
    """
    p = Path(path)
    if not p.exists():
        return
    with p.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            yield json.loads(line)


def append_jsonl(path: str | Path, record: dict[str, Any]) -> None:
    """Append a single record as one JSON line. Creates parent dirs if needed."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def write_jsonl(path: str | Path, records: list[dict[str, Any]]) -> None:
    """Overwrite a JSONL file with the given records (one per line)."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
