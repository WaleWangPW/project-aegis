#!/usr/bin/env python3
"""Build sandbox-only A-share hypotheses from the Tushare source probe."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aegis.strategy.a_share_tushare_source_hypotheses import (  # noqa: E402
    build_a_share_tushare_source_hypothesis_queue,
)

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "data" / "reports"
PROCESSED = ROOT / "data" / "processed" / "a_share_tushare_source_hypothesis_queue"
SOURCE_PROBE = REPORTS / "a_share_tushare_strategy_source_probe_latest.json"
LATEST_JSON = REPORTS / "a_share_tushare_source_hypothesis_queue_latest.json"
LATEST_MD = REPORTS / "a_share_tushare_source_hypothesis_queue_latest.md"
PASS_MARKER = REPORTS / "A_SHARE_TUSHARE_SOURCE_HYPOTHESIS_QUEUE_PASS.marker"
BLOCKED_MARKER = REPORTS / "A_SHARE_TUSHARE_SOURCE_HYPOTHESIS_QUEUE_BLOCKED.marker"


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def markdown_report(queue: dict[str, Any]) -> str:
    hypotheses = queue.get("hypotheses", [])
    lines = [
        "# A-share Tushare Source Hypothesis Queue",
        "",
        f"- Status: `{'PASS' if hypotheses else 'BLOCKED_NO_HYPOTHESES'}`",
        f"- Generated At: `{queue.get('generated_at')}`",
        f"- Source Probe Status: `{queue.get('source_probe_status')}`",
        f"- Latest Trade Date: `{queue.get('source_latest_trade_date')}`",
        f"- Hypothesis Count: `{queue.get('hypothesis_count')}`",
        "- Boundary: sandbox-only; no broker, no order, no trading webhook, no raw payload.",
        "",
        "## Hypotheses",
        "",
        "| ID | Title | Families | Metrics |",
        "| --- | --- | --- | --- |",
    ]
    for item in hypotheses:
        lines.append(
            "| "
            + " | ".join(
                [
                    f"`{item['hypothesis_id']}`",
                    item["title"],
                    ", ".join(item.get("strategy_families", [])),
                    ", ".join(item.get("proposed_metrics", [])[:4]),
                ]
            )
            + " |"
        )
    lines.extend(["", "## Blocked Or Skipped Sources", "", "| Module | Endpoint | Status | Reason |", "| --- | --- | --- | --- |"])
    for item in queue.get("blocked_or_skipped_sources", []):
        lines.append(
            f"| {item.get('module_name')} | `{item.get('endpoint')}` | `{item.get('status')}` | {item.get('reason') or ''} |"
        )
    lines.extend(["", "## Next", "", str(queue.get("next_step")), ""])
    return "\n".join(lines)


def write_outputs(queue: dict[str, Any], run_id: str) -> dict[str, str]:
    REPORTS.mkdir(parents=True, exist_ok=True)
    run_dir = PROCESSED / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    run_json = run_dir / "a_share_tushare_source_hypothesis_queue.json"
    run_md = run_dir / "a_share_tushare_source_hypothesis_queue.md"
    text = json.dumps(queue, ensure_ascii=False, indent=2) + "\n"
    run_json.write_text(text, encoding="utf-8")
    LATEST_JSON.write_text(text, encoding="utf-8")
    md = markdown_report(queue)
    run_md.write_text(md, encoding="utf-8")
    LATEST_MD.write_text(md, encoding="utf-8")
    status = "PASS" if queue.get("hypothesis_count", 0) > 0 else "BLOCKED_NO_HYPOTHESES"
    marker = PASS_MARKER if status == "PASS" else BLOCKED_MARKER
    marker.write_text(
        "\n".join(
            [
                f"status={status}",
                f"run_id={run_id}",
                f"generated_at={queue.get('generated_at')}",
                f"hypothesis_count={queue.get('hypothesis_count')}",
                f"latest_json_sha256={sha256(LATEST_JSON)}",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return {
        "run_json": str(run_json),
        "run_md": str(run_md),
        "latest_json": str(LATEST_JSON),
        "latest_md": str(LATEST_MD),
        "marker": str(marker),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build A-share Tushare source hypotheses from probe report.")
    parser.add_argument("--source-probe", type=Path, default=SOURCE_PROBE)
    parser.add_argument("--run-id", default=f"a_share_tushare_source_hypothesis_queue_{datetime.now().strftime('%Y%m%dT%H%M%S')}")
    args = parser.parse_args(argv)
    probe = load_json(args.source_probe)
    queue = build_a_share_tushare_source_hypothesis_queue(probe)
    outputs = write_outputs(queue, args.run_id)
    status = "PASS" if queue.get("hypothesis_count", 0) > 0 else "BLOCKED_NO_HYPOTHESES"
    print(json.dumps({"status": status, "hypothesis_count": queue.get("hypothesis_count"), "outputs": outputs}, ensure_ascii=False, indent=2))
    return 0 if status == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
