#!/usr/bin/env python3
"""scripts/refresh_stock_agent_aegis_status.py — P1C.3 + P1D.1 Stock-Agent Auto Refresh.

Read-only helper that keeps the Feishu/OpenClaw stock-agent's on-disk
Project Aegis status mirror fresh, so the agent's read flow stays
strictly *file-based*:

    repo -> build_desktop_status builder -> data/desktop/aegis_status.json/html
         -> copy into ~/.openclaw/agents/stock-agent/workspace/project-aegis/
         -> stock-agent reads via its own file-read tool -> Feishu response

This script never makes the stock-agent execute shell, call
`exec`/`nodes.invoke`, or depend on a localhost `web_fetch` — it only
writes plain files to a plain directory.

What it does, in order:
1. Rebuilds `data/desktop/aegis_status.json` / `.html` by calling the
   same `build_desktop_status.build_status()` / `render_html()`
   functions the desktop page and read-only gateway already use — no
   second, divergent status implementation.
2. Creates `~/.openclaw/agents/stock-agent/workspace/project-aegis/`
   if missing.
3. Copies a fixed, small set of already-persisted, read-only files
   into that directory: `aegis_status.json`, `aegis_status.html`,
   `recommendation_details.json` (P1D.1), and (only if each already
   exists on disk) `market_snapshot_smoke_report.json`,
   `provider_router_live_report.json`, `provider_coverage_report.json`.
4. Writes `README_FOR_STOCK_AGENT.md` into the same directory,
   restating the read-only rules for whoever/whatever reads this
   mirror next.
5. Prints every file copied and the final target directory path.

This script never reads, prints, or otherwise touches `.env` or any
token/secret; never reads or writes `data/records/paper_trades.jsonl`;
never calls a broker API or constructs a real or paper trade; never
modifies `dashboard/index.html` (a completely separate file from
`data/desktop/aegis_status.html`); and never special-cases CRCL — it
is just one more row inside the holdings section of the status this
script mirrors.

Usage:
    python scripts/refresh_stock_agent_aegis_status.py
    python scripts/refresh_stock_agent_aegis_status.py --stock-agent-workspace /tmp/fake-workspace
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Any, Optional

# Allow running this file directly without having installed the package.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.build_desktop_status import (  # noqa: E402
    DEFAULT_HOLDINGS_PATH,
    DEFAULT_MARKET_SNAPSHOT_SMOKE_REPORT,
    DEFAULT_PROVIDER_COVERAGE_REPORT,
    DEFAULT_PROVIDER_ROUTER_LIVE_REPORT,
    DEFAULT_RECORDS_DIR,
    build_status,
    render_html,
)
from aegis.desktop.recommendation_details import (  # noqa: E402
    DEFAULT_RECORDS_DIR as _RD_RECORDS_DIR,
    DEFAULT_OUTPUT_PATH as DEFAULT_REC_DETAILS_PATH,
    build_recommendation_details,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_HTML = REPO_ROOT / "data" / "desktop" / "aegis_status.html"
DEFAULT_OUTPUT_JSON = REPO_ROOT / "data" / "desktop" / "aegis_status.json"

# Outside the repo, under the user's home directory — this is where the
# Feishu/OpenClaw stock-agent's own file-read tool looks for Project
# Aegis status. Never inside `data/records/` or anything treated as a
# writable trading record — this is a pure read-only mirror.
DEFAULT_STOCK_AGENT_WORKSPACE = (
    Path.home() / ".openclaw" / "agents" / "stock-agent" / "workspace" / "project-aegis"
)

README_FOR_STOCK_AGENT_TEXT = """# Project Aegis — read-only status mirror for stock-agent

This directory is a **read-only mirror**, refreshed automatically by
`scripts/refresh_stock_agent_aegis_status.py` in the Project Aegis repo.
It exists so the Feishu/OpenClaw stock-agent can answer
`aegis status` / `aegis holdings` / `aegis summary` style questions by
**reading a file** — never by executing shell, calling `exec` /
`nodes.invoke`, or depending on a localhost `web_fetch` call.

## Files in this directory

- `aegis_status.json` — the full machine-readable status payload
  (coverage, holdings, recommendations, paper trading, review, data
  gaps). This is the file the stock-agent should read for high-level
  status.
- `aegis_status.html` — the human-readable desktop status page,
  same data as the JSON above.
- `recommendation_details.json` — sanitized, read-only recommendation
  detail bundle (P1D.1). Stock Agent may read this file to answer
  questions about support reasons, oppose reasons, risks, invalidation
  conditions, why_not_action, and expert opinions. This file is a
  pre-processed mirror — **never read raw `data/records/*.jsonl`
  directly**.
- `market_snapshot_smoke_report.json`, `provider_router_live_report.json`,
  `provider_coverage_report.json` — the underlying validation reports
  the status above is derived from, mirrored only when they already
  exist in the repo.

## Rules for whoever/whatever reads this mirror

- **Read-only.** Nothing in this directory is an instruction to take
  any action — not a buy/sell, not a paper trade, not a broker call,
  not a rebalance. It is a status snapshot, nothing more.
- **Never construct a PaperTrade from this data.** Paper trades are
  only ever created through the repo's own recommendation -> paper
  trading workflow, never from a Feishu message, an OpenClaw command,
  or anything read from this mirror.
- **Never connect to a real broker or execute real trades** based on
  anything in this directory.
- **Do not edit these files directly** — they are overwritten every
  time the refresh script runs in the repo; edits here are silently
  lost and never reflected back into Project Aegis.
- **CRCL is not special-cased anywhere in this data** — it is simply
  one row in the holdings section, like any other holding.
- **Do not access raw `data/records/*.jsonl` files** — use
  `recommendation_details.json` for recommendation explanations
  instead; it is a sanitized read-only artifact built from those
  records and safe for direct agent consumption.
- To get a fresh snapshot, re-run
  `python scripts/refresh_stock_agent_aegis_status.py` in the Project
  Aegis repo (or wait for its scheduled refresh, if one is configured).
"""

# Fixed, small set of already-persisted report files considered for
# mirroring, beyond the two rebuilt status files. Each is only copied
# if it already exists — a missing optional report is never an error,
# never fabricated.
_OPTIONAL_REPORT_KEYS = (
    "market_snapshot_smoke_report",
    "provider_router_live_report",
    "provider_coverage_report",
)


def _mirror_file(src: Path, dest_dir: Path) -> Optional[Path]:
    """Copies `src` into `dest_dir` if it exists; returns the destination
    path, or None if there was nothing to copy. Never raises for a
    missing optional source file."""
    if not src.exists():
        return None
    dest = dest_dir / src.name
    shutil.copyfile(src, dest)
    return dest


def refresh(
    *,
    holdings_path: Path = DEFAULT_HOLDINGS_PATH,
    records_dir: Path = DEFAULT_RECORDS_DIR,
    output_html: Path = DEFAULT_OUTPUT_HTML,
    output_json: Path = DEFAULT_OUTPUT_JSON,
    rec_details_path: Path = DEFAULT_REC_DETAILS_PATH,
    provider_coverage_report: Path = DEFAULT_PROVIDER_COVERAGE_REPORT,
    provider_router_live_report: Path = DEFAULT_PROVIDER_ROUTER_LIVE_REPORT,
    market_snapshot_smoke_report: Path = DEFAULT_MARKET_SNAPSHOT_SMOKE_REPORT,
    stock_agent_workspace: Path = DEFAULT_STOCK_AGENT_WORKSPACE,
) -> dict[str, Any]:
    """Rebuilds the desktop status (JSON + HTML) and recommendation_details.json
    via the shared builders, then mirrors a fixed set of read-only files plus a
    README into `stock_agent_workspace`. Returns a summary of what was written —
    never raises for a missing *optional* report file."""
    status = build_status(
        holdings_path=holdings_path,
        records_dir=records_dir,
        provider_coverage_report=provider_coverage_report,
        provider_router_live_report=provider_router_live_report,
        market_snapshot_smoke_report=market_snapshot_smoke_report,
    )
    html_text = render_html(status)

    output_html.parent.mkdir(parents=True, exist_ok=True)
    output_html.write_text(html_text, encoding="utf-8")

    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(
        json.dumps(status, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
    )

    # P1D.1 — build recommendation_details.json
    build_recommendation_details(records_dir=records_dir, output_path=rec_details_path)

    stock_agent_workspace.mkdir(parents=True, exist_ok=True)

    optional_reports = {
        "market_snapshot_smoke_report": market_snapshot_smoke_report,
        "provider_router_live_report": provider_router_live_report,
        "provider_coverage_report": provider_coverage_report,
    }

    copied: list[str] = []
    skipped: list[str] = []
    # Core status files always copied
    for src in (output_json, output_html):
        dest = _mirror_file(src, stock_agent_workspace)
        if dest is not None:
            copied.append(str(dest))

    # P1D.1 recommendation_details.json — always copied (just built above)
    rd_dest = _mirror_file(rec_details_path, stock_agent_workspace)
    if rd_dest is not None:
        copied.append(str(rd_dest))

    for key in _OPTIONAL_REPORT_KEYS:
        src = optional_reports[key]
        dest = _mirror_file(src, stock_agent_workspace)
        if dest is not None:
            copied.append(str(dest))
        else:
            skipped.append(str(src))

    readme_path = stock_agent_workspace / "README_FOR_STOCK_AGENT.md"
    readme_path.write_text(README_FOR_STOCK_AGENT_TEXT, encoding="utf-8")
    copied.append(str(readme_path))

    return {
        "target_dir": str(stock_agent_workspace),
        "copied_files": copied,
        "skipped_missing_optional_reports": skipped,
    }


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Rebuild the Project Aegis desktop status and mirror read-only "
        "files into the Feishu/OpenClaw stock-agent's workspace. Never reads a "
        "token, never touches paper_trades.jsonl, never calls a broker."
    )
    parser.add_argument("--holdings-path", default=str(DEFAULT_HOLDINGS_PATH))
    parser.add_argument("--records-dir", default=str(DEFAULT_RECORDS_DIR))
    parser.add_argument("--output-html", default=str(DEFAULT_OUTPUT_HTML))
    parser.add_argument("--output-json", default=str(DEFAULT_OUTPUT_JSON))
    parser.add_argument("--rec-details-path", default=str(DEFAULT_REC_DETAILS_PATH))
    parser.add_argument("--provider-coverage-report", default=str(DEFAULT_PROVIDER_COVERAGE_REPORT))
    parser.add_argument("--provider-router-live-report", default=str(DEFAULT_PROVIDER_ROUTER_LIVE_REPORT))
    parser.add_argument("--market-snapshot-smoke-report", default=str(DEFAULT_MARKET_SNAPSHOT_SMOKE_REPORT))
    parser.add_argument("--stock-agent-workspace", default=str(DEFAULT_STOCK_AGENT_WORKSPACE))
    args = parser.parse_args(argv)

    result = refresh(
        holdings_path=Path(args.holdings_path),
        records_dir=Path(args.records_dir),
        output_html=Path(args.output_html),
        output_json=Path(args.output_json),
        rec_details_path=Path(args.rec_details_path),
        provider_coverage_report=Path(args.provider_coverage_report),
        provider_router_live_report=Path(args.provider_router_live_report),
        market_snapshot_smoke_report=Path(args.market_snapshot_smoke_report),
        stock_agent_workspace=Path(args.stock_agent_workspace),
    )

    print("Rebuilt data/desktop/aegis_status.json and aegis_status.html.")
    print(f"Mirrored {len(result['copied_files'])} file(s) into {result['target_dir']}:")
    for f in result["copied_files"]:
        print(f"  - {f}")
    if result["skipped_missing_optional_reports"]:
        print("Skipped (not present in repo yet):")
        for f in result["skipped_missing_optional_reports"]:
            print(f"  - {f}")
    print(f"Target: {result['target_dir']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
