#!/usr/bin/env python3
"""Evaluate external source registry policy decisions from a JSON source file."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aegis.external_sources.policy import evaluate_source_registry  # noqa: E402
from aegis.models.external_source import ExternalSourcePolicy  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = ROOT / "data" / "reports"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Evaluate Project Aegis external source policy gate.")
    parser.add_argument("--source", required=True, help="JSON file containing source policy records.")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args(argv)

    raw = json.loads(Path(args.source).read_text(encoding="utf-8"))
    sources = [ExternalSourcePolicy(**item) for item in raw.get("sources", [])]
    report = evaluate_source_registry(sources)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "external_source_policy_gate.json"
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
