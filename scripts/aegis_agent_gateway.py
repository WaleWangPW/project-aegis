#!/usr/bin/env python3
"""aegis_agent_gateway.py — P1C Read-Only Agent Gateway.

The **only** entry point an external agent (OpenClaw, Feishu, or any
other future automation) should ever call to query Project Aegis. See
`docs/P1C_OPENCLAW_FEISHU_BRIDGE_CONTRACT.md` for the full contract.

This gateway is strictly read-only:
- it never creates a `PaperTrade` record;
- it never calls a broker API of any kind (none exists in this repo);
- it never executes a real or simulated trade;
- it never modifies a `DecisionRecord`/`RecommendationRecord`;
- it never reads, prints, or otherwise exposes `.env` or any token
  (it never even imports a provider adapter — every command here only
  reads already-persisted JSON/JSONL/YAML files via
  `scripts/build_desktop_status.py`'s helpers);
- it never special-cases CRCL — CRCL only ever appears as an ordinary
  row in whatever holdings/recommendations/paper-trade/review data
  already exists, exactly like any other symbol.

Allowed commands: status, holdings, recommendations, paper-summary,
review-summary, provider-report, provider-router-report,
market-snapshot-smoke, data-gaps, desktop-page, summary.

Forbidden commands (buy, sell, trade, order, broker, auto-trade,
rebalance, paper-buy, paper-sell, create-paper-trade, modify-decision,
modify-recommendation) are refused with a structured JSON error and a
non-zero exit code — never silently ignored, never partially executed.

P1C.1: `desktop-page` regenerates `data/desktop/aegis_status.html` (same
as before) but now returns a flat, agent-friendly shape —
`{"ok": true, "path": ..., "absolute_path": ..., "open_command": ...}`
— instead of the earlier `{"ok": true, "command": ..., "data": {...}}`
wrapper, so an OpenClaw/Feishu adapter can point a human straight at the
file without unwrapping anything.

Usage:
    python scripts/aegis_agent_gateway.py status
    python scripts/aegis_agent_gateway.py holdings
    python scripts/aegis_agent_gateway.py summary
    python scripts/aegis_agent_gateway.py desktop-page
    python scripts/aegis_agent_gateway.py buy   # refused, exit 1
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Optional

# Allow running this file directly without having installed the package.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import scripts.build_desktop_status as build_desktop_status  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROVIDER_DIAGNOSTICS_REPORT = (
    REPO_ROOT / "data" / "processed" / "provider_diagnostics" / "provider_router_report.json"
)

ALLOWED_COMMANDS = {
    "status",
    "holdings",
    "recommendations",
    "paper-summary",
    "review-summary",
    "provider-report",
    "provider-router-report",
    "market-snapshot-smoke",
    "data-gaps",
    "desktop-page",
    "summary",
}

# Every command this gateway must refuse rather than execute, per the
# P1C task's explicit non-goals: no real trading, no broker, no
# gateway-initiated PaperTrade creation, no Decision/Recommendation
# mutation. Matched case-insensitively against the exact command name.
FORBIDDEN_COMMANDS = {
    "buy",
    "sell",
    "trade",
    "order",
    "broker",
    "auto-trade",
    "rebalance",
    "paper-buy",
    "paper-sell",
    "create-paper-trade",
    "modify-decision",
    "modify-recommendation",
}


def _refusal(command: str) -> dict[str, Any]:
    return {
        "ok": False,
        "error": "forbidden_command",
        "command": command,
        "message": (
            f"'{command}' is not a supported command. scripts/aegis_agent_gateway.py (P1C) "
            "is a strictly read-only query interface: it never creates PaperTrade records, "
            "never calls a broker, never executes a real or simulated trade, and never "
            "modifies a Decision/Recommendation record. See "
            "docs/P1C_OPENCLAW_FEISHU_BRIDGE_CONTRACT.md."
        ),
    }


def _unknown_command(command: str) -> dict[str, Any]:
    return {
        "ok": False,
        "error": "unknown_command",
        "command": command,
        "message": f"Unknown command {command!r}. Allowed commands: {sorted(ALLOWED_COMMANDS)}.",
    }


def dispatch(
    command: str,
    *,
    holdings_path: Path,
    records_dir: Path,
    provider_coverage_report: Path,
    provider_router_live_report: Path,
    market_snapshot_smoke_report: Path,
    provider_diagnostics_report: Path,
    output_html: Path,
    output_json: Path,
) -> tuple[dict[str, Any], int]:
    """Returns `(json_serializable_result, exit_code)`. Never raises —
    every failure mode (forbidden, unknown, missing data) is an honest
    structured result, never a crash or a fabricated success."""
    normalized = command.strip().lower()

    if normalized in FORBIDDEN_COMMANDS:
        return _refusal(normalized), 1
    if normalized not in ALLOWED_COMMANDS:
        return _unknown_command(command), 1

    if normalized == "status":
        data = build_desktop_status.build_status(
            holdings_path=holdings_path,
            records_dir=records_dir,
            provider_coverage_report=provider_coverage_report,
            provider_router_live_report=provider_router_live_report,
            market_snapshot_smoke_report=market_snapshot_smoke_report,
        )
        return {"ok": True, "command": normalized, "data": data}, 0

    if normalized == "holdings":
        return {"ok": True, "command": normalized, "data": build_desktop_status._holdings_summary(holdings_path)}, 0

    if normalized == "recommendations":
        return {
            "ok": True,
            "command": normalized,
            "data": build_desktop_status._recommendations_summary(records_dir),
        }, 0

    if normalized == "paper-summary":
        return {"ok": True, "command": normalized, "data": build_desktop_status._paper_summary(records_dir)}, 0

    if normalized == "review-summary":
        return {"ok": True, "command": normalized, "data": build_desktop_status._review_summary(records_dir)}, 0

    if normalized == "data-gaps":
        # Reflect the same "current vs. historical/superseded" split the
        # desktop page shows — computed from the same coverage signals,
        # never a bare, undifferentiated dump of every gap ever recorded.
        provider_coverage = build_desktop_status._provider_coverage_summary(provider_coverage_report)
        provider_router_live = build_desktop_status._provider_router_live_summary(provider_router_live_report)
        market_snapshot_smoke = build_desktop_status._market_snapshot_smoke_summary(market_snapshot_smoke_report)
        coverage = build_desktop_status._coverage_summary(provider_router_live, market_snapshot_smoke, provider_coverage)
        confirming_created_at = build_desktop_status._confirming_timestamps(
            coverage, provider_router_live, market_snapshot_smoke, provider_coverage
        )
        data = build_desktop_status._data_gaps_summary(
            records_dir, coverage=coverage, confirming_created_at=confirming_created_at
        )
        return {"ok": True, "command": normalized, "data": data}, 0

    if normalized == "provider-router-report":
        data = build_desktop_status._safe_read_json(provider_router_live_report) or {"status": "no_data"}
        return {"ok": True, "command": normalized, "data": data}, 0

    if normalized == "provider-report":
        data = build_desktop_status._safe_read_json(provider_diagnostics_report) or {"status": "no_data"}
        return {"ok": True, "command": normalized, "data": data}, 0

    if normalized == "market-snapshot-smoke":
        data = build_desktop_status._safe_read_json(market_snapshot_smoke_report) or {"status": "no_data"}
        return {
            "ok": True,
            "command": normalized,
            "data": data,
            "note": (
                "Read-only: this reports the most recently persisted smoke result on disk; "
                "it does not trigger a new run. Run scripts/run_market_snapshot_smoke.py "
                "directly (outside this gateway) to refresh it."
            ),
        }, 0

    if normalized == "desktop-page":
        status = build_desktop_status.build_status(
            holdings_path=holdings_path,
            records_dir=records_dir,
            provider_coverage_report=provider_coverage_report,
            provider_router_live_report=provider_router_live_report,
            market_snapshot_smoke_report=market_snapshot_smoke_report,
        )
        html_text = build_desktop_status.render_html(status)
        output_html.parent.mkdir(parents=True, exist_ok=True)
        output_html.write_text(html_text, encoding="utf-8")
        output_json.parent.mkdir(parents=True, exist_ok=True)
        output_json.write_text(json.dumps(status, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        # P1C.1: flat, agent-friendly shape per
        # docs/P1C1_OPENCLAW_FEISHU_READONLY_SETUP.md — no "command"/"data"
        # wrapper, so a Feishu/OpenClaw adapter can read `path`/
        # `open_command` directly.
        try:
            rel_path = output_html.resolve().relative_to(build_desktop_status.REPO_ROOT.resolve())
        except ValueError:
            rel_path = output_html
        return {
            "ok": True,
            "path": str(rel_path),
            "absolute_path": str(output_html.resolve()),
            "open_command": f"open {rel_path}",
        }, 0

    if normalized == "summary":
        status = build_desktop_status.build_status(
            holdings_path=holdings_path,
            records_dir=records_dir,
            provider_coverage_report=provider_coverage_report,
            provider_router_live_report=provider_router_live_report,
            market_snapshot_smoke_report=market_snapshot_smoke_report,
        )
        condensed = {
            "generated_at": status["generated_at"],
            "coverage": status["coverage"],
            "holdings_count": status["holdings"]["count"],
            "recommendations_count": status["recommendations"]["count"],
            "paper_trading": {
                "open": status["paper_trading"].get("open_count", 0),
                "closed": status["paper_trading"].get("closed_count", 0),
            },
            "review_count": status["review"]["count"],
            "data_gaps_count": status["data_gaps"]["count"],
            "next_operational_action": status["next_operational_action"],
        }
        return {"ok": True, "command": normalized, "data": condensed}, 0

    raise AssertionError(f"unhandled allowed command {normalized!r}")  # pragma: no cover - defensive only


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Project Aegis P1C read-only agent gateway. Never creates PaperTrade "
        "records, never calls a broker, never executes trades, never reads .env/tokens."
    )
    parser.add_argument(
        "command",
        help="Allowed: " + ", ".join(sorted(ALLOWED_COMMANDS)) + ". Forbidden commands are refused, not executed.",
    )
    parser.add_argument("--holdings-path", default=str(build_desktop_status.DEFAULT_HOLDINGS_PATH))
    parser.add_argument("--records-dir", default=str(build_desktop_status.DEFAULT_RECORDS_DIR))
    parser.add_argument(
        "--provider-coverage-report", default=str(build_desktop_status.DEFAULT_PROVIDER_COVERAGE_REPORT)
    )
    parser.add_argument(
        "--provider-router-live-report", default=str(build_desktop_status.DEFAULT_PROVIDER_ROUTER_LIVE_REPORT)
    )
    parser.add_argument(
        "--market-snapshot-smoke-report", default=str(build_desktop_status.DEFAULT_MARKET_SNAPSHOT_SMOKE_REPORT)
    )
    parser.add_argument("--provider-diagnostics-report", default=str(DEFAULT_PROVIDER_DIAGNOSTICS_REPORT))
    parser.add_argument("--output-html", default=str(build_desktop_status.DEFAULT_OUTPUT_HTML))
    parser.add_argument("--output-json", default=str(build_desktop_status.DEFAULT_OUTPUT_JSON))
    args = parser.parse_args(argv)

    result, exit_code = dispatch(
        args.command,
        holdings_path=Path(args.holdings_path),
        records_dir=Path(args.records_dir),
        provider_coverage_report=Path(args.provider_coverage_report),
        provider_router_live_report=Path(args.provider_router_live_report),
        market_snapshot_smoke_report=Path(args.market_snapshot_smoke_report),
        provider_diagnostics_report=Path(args.provider_diagnostics_report),
        output_html=Path(args.output_html),
        output_json=Path(args.output_json),
    )
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
