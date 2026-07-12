#!/usr/bin/env python3
"""Fetch one approved official/regulator/company source item."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aegis.external_sources.fetcher import fetch_official_source_item  # noqa: E402
from aegis.models.external_source import ExternalSourcePolicy  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = ROOT / "data" / "reports"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Fetch an approved official source item.")
    parser.add_argument("--source-policy", required=True)
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--market", required=True)
    parser.add_argument("--url", required=True)
    parser.add_argument("--publisher", required=True)
    parser.add_argument("--user-agent", required=True)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args(argv)

    source = ExternalSourcePolicy(**json.loads(Path(args.source_policy).read_text(encoding="utf-8")))
    item = fetch_official_source_item(
        source=source,
        symbol=args.symbol,
        market=args.market,
        url=args.url,
        publisher=args.publisher,
        user_agent=args.user_agent,
    )
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"official_source_item_{args.market}_{args.symbol}.json"
    output_path.write_text(json.dumps(item.model_dump(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
