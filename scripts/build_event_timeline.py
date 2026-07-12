#!/usr/bin/env python3
"""Build a V2.0-D event timeline and scenario report from a JSON source file."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aegis.events.timeline import build_event_timeline_report, render_event_timeline_markdown  # noqa: E402
from aegis.models.event_timeline import EventRecord, ScenarioRecord  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = ROOT / "data" / "reports"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build a V2.0-D event timeline report.")
    parser.add_argument("--source", required=True, help="JSON file containing symbol, market, events, scenarios.")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--format", choices=["json", "md"], default="json")
    args = parser.parse_args(argv)

    raw = json.loads(Path(args.source).read_text(encoding="utf-8"))
    events = [EventRecord(**item) for item in raw.get("events", [])]
    scenarios = [ScenarioRecord(**item) for item in raw.get("scenarios", [])]
    report = build_event_timeline_report(
        symbol=raw["symbol"],
        market=raw["market"],
        events=events,
        scenarios=scenarios,
    )

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    suffix = "json" if args.format == "json" else "md"
    output_path = output_dir / f"event_timeline_{raw['market']}_{raw['symbol']}.{suffix}"
    if args.format == "json":
        output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    else:
        output_path.write_text(render_event_timeline_markdown(report), encoding="utf-8")
    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
