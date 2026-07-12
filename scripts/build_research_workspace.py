#!/usr/bin/env python3
"""Build a bounded per-symbol research workspace from a JSON source file."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aegis.models.research import ResearchEvidenceLink, ResearchNote  # noqa: E402
from aegis.research.workspace import build_research_workspace, render_research_workspace_markdown  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = ROOT / "data" / "reports"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build a V2.0-C research workspace.")
    parser.add_argument("--source", required=True, help="JSON file containing symbol, market, notes, evidence, created_at.")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--format", choices=["json", "md"], default="json")
    args = parser.parse_args(argv)

    raw = json.loads(Path(args.source).read_text(encoding="utf-8"))
    notes = [ResearchNote(**item) for item in raw.get("notes", [])]
    evidence = [ResearchEvidenceLink(**item) for item in raw.get("evidence", [])]
    report = build_research_workspace(
        symbol=raw["symbol"],
        market=raw["market"],
        notes=notes,
        evidence=evidence,
        created_at=raw["created_at"],
    )

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    suffix = "json" if args.format == "json" else "md"
    output_path = output_dir / f"research_workspace_{raw['market']}_{raw['symbol']}.{suffix}"
    if args.format == "json":
        output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    else:
        output_path.write_text(render_research_workspace_markdown(report), encoding="utf-8")
    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
