#!/usr/bin/env python3
"""Build a read-only readiness report for the A-share current-day retry.

This preflight does not call Tushare, does not read secrets, and does not
collect market data. It only answers whether the existing coverage report says
the current trading day retry should wait, can be attempted, is unnecessary, or
is blocked by a different condition.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "data" / "reports"
DEFAULT_COVERAGE_REPORT = REPORTS / "a_share_full_year_coverage_plan_latest.json"
OUT_JSON = REPORTS / "a_share_current_day_retry_readiness_latest.json"
OUT_MD = REPORTS / "a_share_current_day_retry_readiness_latest.md"

EXPECTED_CHAIN = [
    "make a-share-current-day-retry",
    "make build-p23-2-historical-market-cache START_DATE=20250713 END_DATE=20260713",
    "make build-a-share-full-year-coverage-plan",
    "make stock-agent-a-share-strategy-cycle-managed-expanded",
]


def now_local() -> datetime:
    return datetime.now().astimezone()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def parse_retry_clock(value: str | None, *, now: datetime) -> datetime | None:
    if not value:
        return None
    clock = value.split()[0]
    try:
        hour_text, minute_text = clock.split(":", 1)
        retry_at = now.replace(hour=int(hour_text), minute=int(minute_text), second=0, microsecond=0)
    except (ValueError, TypeError):
        return None
    return retry_at


def build_readiness(*, coverage_report: dict[str, Any] | None, now: datetime) -> dict[str, Any]:
    blockers: list[str] = []
    retry = (coverage_report or {}).get("current_day_retry", {})
    coverage_status = (coverage_report or {}).get("coverage_status")
    answer_label = (coverage_report or {}).get("answer_label")
    retry_at = parse_retry_clock(retry.get("retry_not_before_local_time"), now=now)
    if coverage_report is None:
        status = "BLOCKED"
        blockers.append("missing_coverage_report")
    elif answer_label == "YES":
        status = "NOT_NEEDED"
    elif coverage_status != "WAITING_CURRENT_TRADING_DAY_DAILY":
        status = "BLOCKED"
        blockers.append(f"coverage_status_not_waiting:{coverage_status or 'UNKNOWN'}")
    elif not retry.get("needed"):
        status = "BLOCKED"
        blockers.append("coverage_report_retry_not_marked_needed")
    elif retry_at is None:
        status = "BLOCKED"
        blockers.append("invalid_retry_time")
    elif now < retry_at:
        status = "WAITING"
    else:
        status = "READY"

    return {
        "type": "a_share_current_day_retry_readiness",
        "status": status,
        "generated_at": now.isoformat(timespec="seconds"),
        "coverage_status": coverage_status,
        "answer_label": answer_label,
        "retry_not_before_local_time": retry.get("retry_not_before_local_time"),
        "ready_to_run": status == "READY",
        "recommended_command": "make a-share-current-day-retry" if status == "READY" else None,
        "command_chain": EXPECTED_CHAIN,
        "blockers": blockers,
        "source_report": str(DEFAULT_COVERAGE_REPORT.relative_to(ROOT)),
        "source_generated_at": (coverage_report or {}).get("generated_at"),
        "safety": {
            "network_used": False,
            "secret_values_read": False,
            "simulation_only": True,
            "no_broker_api": True,
            "no_order_placement": True,
            "no_trading_webhook": True,
            "executes_retry": False,
        },
    }


def render_markdown(report: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# A-share Current-Day Retry Readiness",
            "",
            f"- status: `{report['status']}`",
            f"- ready_to_run: `{report['ready_to_run']}`",
            f"- retry_not_before_local_time: `{report.get('retry_not_before_local_time')}`",
            f"- recommended_command: `{report.get('recommended_command')}`",
            f"- blockers: `{', '.join(report.get('blockers') or []) or 'none'}`",
            "",
            "## Command Chain",
            "",
            *[f"- `{item}`" for item in report["command_chain"]],
            "",
            "## Safety",
            "",
            "- This report is read-only.",
            "- It does not call Tushare, read secrets, call brokers, place orders, or invoke trading webhooks.",
            "",
        ]
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--coverage-report", type=Path, default=DEFAULT_COVERAGE_REPORT)
    parser.add_argument("--out-json", type=Path, default=OUT_JSON)
    parser.add_argument("--out-md", type=Path, default=OUT_MD)
    args = parser.parse_args()

    coverage_report = read_json(args.coverage_report) if args.coverage_report.exists() else None
    report = build_readiness(coverage_report=coverage_report, now=now_local())
    write_json(args.out_json, report)
    args.out_md.write_text(render_markdown(report), encoding="utf-8")
    print(f"status={report['status']}")
    print(f"ready_to_run={report['ready_to_run']}")
    print(f"out_json={args.out_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
