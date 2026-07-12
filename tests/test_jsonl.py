"""Phase 0 test for the only utility module allowed in this phase:
aegis/utils/jsonl.py. Round-trip only — no business logic involved."""

from __future__ import annotations

from pathlib import Path

from aegis.utils.jsonl import append_jsonl, read_jsonl, write_jsonl


def test_read_jsonl_missing_file_returns_empty(tmp_path: Path):
    missing = tmp_path / "does_not_exist.jsonl"
    assert list(read_jsonl(missing)) == []


def test_write_then_read_roundtrip(tmp_path: Path):
    path = tmp_path / "records" / "sample.jsonl"
    records = [{"a": 1}, {"a": 2, "b": "x"}]
    write_jsonl(path, records)
    assert list(read_jsonl(path)) == records


def test_append_jsonl_adds_one_line(tmp_path: Path):
    path = tmp_path / "records" / "sample.jsonl"
    append_jsonl(path, {"a": 1})
    append_jsonl(path, {"a": 2})
    assert list(read_jsonl(path)) == [{"a": 1}, {"a": 2}]
