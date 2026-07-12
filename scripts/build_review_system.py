#!/usr/bin/env python3
"""Build V1.5 weekly/monthly review-system reports from existing records."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aegis.review.system import build_review_system_report, render_review_system_markdown  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Build Project Aegis V1.5 review-system report.")
    parser.add_argument("--start", required=True, help="YYYY-MM-DD")
    parser.add_argument("--end", required=True, help="YYYY-MM-DD")
    parser.add_argument("--period", choices=["weekly", "monthly"], required=True)
    parser.add_argument("--format", choices=["json", "md"], default="md")
    parser.add_argument("--records-dir", default=str(ROOT / "data" / "records"))
    parser.add_argument("--output-dir", default=str(ROOT / "data" / "processed" / "review_system"))
    args = parser.parse_args(argv)

    report = build_review_system_report(
        records_dir=Path(args.records_dir),
        start=args.start,
        end=args.end,
        period=args.period,
    )
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = f"review_system_{args.period}_{args.start.replace('-', '')}_{args.end.replace('-', '')}"
    if args.format == "json":
        output_path = output_dir / f"{stem}.json"
        output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    else:
        output_path = output_dir / f"{stem}.md"
        output_path.write_text(render_review_system_markdown(report), encoding="utf-8")

    print(str(output_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
