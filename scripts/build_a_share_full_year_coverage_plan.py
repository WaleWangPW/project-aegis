#!/usr/bin/env python3
"""Build an auditable A-share full-year coverage status and overnight plan.

This script is intentionally read-only. It does not call Tushare, does not read
secrets, and does not collect market data. It answers a narrower but important
question for the Dashboard and stock-agent: do we already have a current
past-year full A-share daily-bar universe materialized locally?
"""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "data" / "reports"
DEFAULT_CACHE = ROOT / "data" / "cache" / "p23_2_historical_market"
OUT_JSON = REPORTS / "a_share_full_year_coverage_plan_latest.json"
OUT_MD = REPORTS / "a_share_full_year_coverage_plan_latest.md"
PASS_MARKER = REPORTS / "A_SHARE_FULL_YEAR_COVERAGE_PLAN_PASS.marker"


@dataclass(frozen=True)
class CacheStats:
    cache_dir: Path
    calendar_exists: bool
    stock_basic_exists: bool
    daily_dir_exists: bool
    open_date_count: int
    stock_basic_row_count: int
    daily_file_count: int
    daily_start: str | None
    daily_end: str | None
    open_dates: tuple[str, ...]
    min_daily_row_count: int | None
    max_daily_row_count: int | None
    avg_daily_row_count: int | None
    total_daily_rows: int
    source_hashes: dict[str, str | None]


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def sha256(path: Path) -> str | None:
    if not path.exists() or not path.is_file():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def compact(value: date) -> str:
    return value.strftime("%Y%m%d")


def parse_compact(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y%m%d").date()
    except ValueError:
        return None


def load_cache_stats(cache_dir: Path) -> CacheStats:
    calendar = cache_dir / "trade_calendar.json"
    stock_basic = cache_dir / "stock_basic_all.json"
    daily_dir = cache_dir / "daily_by_trade_date"
    calendar_payload = read_json(calendar, {})
    stock_payload = read_json(stock_basic, {})
    open_dates = sorted(str(item) for item in calendar_payload.get("open_dates", []))
    stock_rows = stock_payload.get("rows", [])
    daily_files = sorted(daily_dir.glob("*.json")) if daily_dir.exists() else []
    row_counts: list[int] = []
    total_rows = 0
    for path in daily_files:
        payload = read_json(path, {})
        count = int(payload.get("row_count") or len(payload.get("rows", [])))
        row_counts.append(count)
        total_rows += count
    return CacheStats(
        cache_dir=cache_dir,
        calendar_exists=calendar.exists(),
        stock_basic_exists=stock_basic.exists(),
        daily_dir_exists=daily_dir.exists(),
        open_date_count=len(open_dates),
        stock_basic_row_count=len(stock_rows),
        daily_file_count=len(daily_files),
        daily_start=daily_files[0].stem if daily_files else None,
        daily_end=daily_files[-1].stem if daily_files else None,
        open_dates=tuple(open_dates),
        min_daily_row_count=min(row_counts) if row_counts else None,
        max_daily_row_count=max(row_counts) if row_counts else None,
        avg_daily_row_count=int(statistics.mean(row_counts)) if row_counts else None,
        total_daily_rows=total_rows,
        source_hashes={
            "trade_calendar": sha256(calendar),
            "stock_basic_all": sha256(stock_basic),
        },
    )


def previous_open_date(open_dates: tuple[str, ...], target: date) -> str | None:
    target_compact = compact(target)
    previous = [item for item in open_dates if item < target_compact]
    return previous[-1] if previous else None


def materialization_status(stats: CacheStats, target_start: date, target_end: date) -> tuple[str, list[str]]:
    blockers: list[str] = []
    if not stats.calendar_exists:
        blockers.append("missing_trade_calendar_cache")
    if not stats.stock_basic_exists:
        blockers.append("missing_stock_basic_cache")
    if not stats.daily_dir_exists or stats.daily_file_count == 0:
        blockers.append("missing_daily_by_trade_date_cache")
    cache_start = parse_compact(stats.daily_start)
    cache_end = parse_compact(stats.daily_end)
    waiting_for_current_trade_day = False
    if cache_start is None or cache_end is None:
        blockers.append("missing_daily_date_range")
    else:
        if cache_start > target_start:
            blockers.append("daily_cache_starts_after_target_start")
        if cache_end < target_end:
            target_compact = compact(target_end)
            previous_open = previous_open_date(stats.open_dates, target_end)
            if target_compact in stats.open_dates and stats.daily_end == previous_open:
                waiting_for_current_trade_day = True
                blockers.append("current_trading_day_daily_not_yet_available")
            else:
                blockers.append("daily_cache_ends_before_target_end")
        if cache_end < target_start:
            blockers.append("daily_cache_is_stale_for_current_past_year")
    if stats.stock_basic_row_count < 4000:
        blockers.append("stock_basic_row_count_below_full_universe_floor")
    if stats.daily_file_count < 200:
        blockers.append("daily_trade_date_count_below_one_year_floor")
    if blockers:
        if waiting_for_current_trade_day and blockers == ["current_trading_day_daily_not_yet_available"]:
            return "WAITING_CURRENT_TRADING_DAY_DAILY", blockers
        if stats.daily_file_count >= 200 and stats.stock_basic_row_count >= 4000:
            return "PARTIAL_STALE_FULL_CROSS_SECTION_CACHE", blockers
        return "NOT_MATERIALIZED", blockers
    return "MATERIALIZED_CURRENT_FULL_YEAR_CANDIDATE", []


def build_plan(*, cache_dir: Path, as_of: date, run_id: str, command: str) -> dict[str, Any]:
    target_end = as_of
    target_start = as_of - timedelta(days=365)
    stats = load_cache_stats(cache_dir)
    status, blockers = materialization_status(stats, target_start, target_end)
    estimated_trading_days = 244
    expected_rows_floor = max(stats.stock_basic_row_count, 5000) * estimated_trading_days
    batch_size = 20
    batch_count = (estimated_trading_days + batch_size - 1) // batch_size
    current_case_report = read_json(REPORTS / "aegis_strategy_specific_historical_cases_latest.json", {})
    stock_agent_cycle = read_json(REPORTS / "stock_agent_a_share_strategy_cycle_latest.json", {})
    return {
        "type": "a_share_full_year_coverage_plan",
        "status": "PASS",
        "coverage_status": status,
        "generated_at": now_iso(),
        "run_id": run_id,
        "command": command,
        "question": "Do we currently have materialized past-year daily records for the full A-share universe?",
        "answer": status == "MATERIALIZED_CURRENT_FULL_YEAR_CANDIDATE",
        "answer_label": "YES" if status == "MATERIALIZED_CURRENT_FULL_YEAR_CANDIDATE" else "NO",
        "target": {
            "as_of_date": as_of.isoformat(),
            "target_start": target_start.isoformat(),
            "target_end": target_end.isoformat(),
            "target_days": 365,
            "estimated_trading_days": estimated_trading_days,
            "expected_full_universe_row_floor": expected_rows_floor,
        },
        "current_cache": {
            "cache_dir": display_path(stats.cache_dir),
            "calendar_exists": stats.calendar_exists,
            "stock_basic_exists": stats.stock_basic_exists,
            "daily_dir_exists": stats.daily_dir_exists,
            "open_date_count": stats.open_date_count,
            "stock_basic_row_count": stats.stock_basic_row_count,
            "daily_file_count": stats.daily_file_count,
            "daily_start": stats.daily_start,
            "daily_end": stats.daily_end,
            "latest_expected_trade_date": compact(as_of) if compact(as_of) in stats.open_dates else None,
            "previous_open_date_before_as_of": previous_open_date(stats.open_dates, as_of),
            "min_daily_row_count": stats.min_daily_row_count,
            "max_daily_row_count": stats.max_daily_row_count,
            "avg_daily_row_count": stats.avg_daily_row_count,
            "total_daily_rows": stats.total_daily_rows,
        },
        "current_strategy_validation": {
            "historical_case_count": current_case_report.get("summary", {}).get("historical_case_count"),
            "a_share_case_count": current_case_report.get("summary", {}).get("a_share_case_count"),
            "candidate_count": current_case_report.get("summary", {}).get("candidate_count"),
            "ranking_gate_approved_count": stock_agent_cycle.get("summary", {}).get("ranking_gate_approved_count"),
            "user_facing_suggestion_allowed": False,
        },
        "blockers": blockers,
        "overnight_openclaw_plan": {
            "owner": "stock-agent",
            "mode": "bounded_read_or_simulation_only",
            "phase_1": "verify current cache/report coverage and hashes",
            "phase_2": "collect or validate target-year A-share daily_by_trade_date batches only after Tushare env is available",
            "phase_3": "run strategy validation on collected batches and publish reports; do not change ranking unless gate approves",
            "recommended_batch_size_trade_dates": batch_size,
            "estimated_batch_count": batch_count,
            "stop_conditions": [
                "missing_tushare_token_or_client",
                "daily_batch_exit_code_nonzero",
                "daily_row_count_below_4000_for_any_open_day",
                "hash_or_date_range_mismatch",
                "attempt_to_read_or_print_secret",
                "attempt_to_trade_or_call_broker_or_webhook",
            ],
            "expected_reports": [
                "data/reports/a_share_full_year_coverage_plan_latest.json",
                "data/reports/a_share_full_year_collection_manifest_latest.json",
                "data/reports/a_share_full_year_strategy_validation_latest.json",
            ],
        },
        "safety": {
            "network_used": False,
            "secret_read": False,
            "raw_payload_saved": False,
            "simulation_only": True,
            "no_broker_api": True,
            "no_order_placement": True,
            "no_trading_webhook": True,
            "ranking_impact_allowed": False,
            "user_facing_suggestion_allowed": False,
        },
        "source_hashes": stats.source_hashes,
    }


def markdown(report: dict[str, Any]) -> str:
    cache = report["current_cache"]
    plan = report["overnight_openclaw_plan"]
    lines = [
        "# A-share Full-Year Coverage Plan",
        "",
        f"- Status: `{report['coverage_status']}`",
        f"- Answer: `{report['answer_label']}` — current past-year full A-share records are not considered materialized unless status is `MATERIALIZED_CURRENT_FULL_YEAR_CANDIDATE`.",
        f"- Target: `{report['target']['target_start']}` to `{report['target']['target_end']}`",
        f"- Current cache range: `{cache['daily_start']}` to `{cache['daily_end']}`",
        f"- Current daily files: `{cache['daily_file_count']}`",
        f"- Stock basic rows: `{cache['stock_basic_row_count']}`",
        f"- Total cached daily rows: `{cache['total_daily_rows']}`",
        f"- Current A-share strategy cases: `{report['current_strategy_validation']['a_share_case_count']}`",
        f"- Ranking gate approved: `{report['current_strategy_validation']['ranking_gate_approved_count']}`",
        "",
        "## Blockers",
        "",
    ]
    if report["coverage_status"] == "WAITING_CURRENT_TRADING_DAY_DAILY":
        lines.append("- Note: cache is current through the previous open date; today's daily cross-section is not available yet.")
    lines.extend(f"- `{item}`" for item in report["blockers"]) if report["blockers"] else lines.append("- None")
    lines.extend(
        [
            "",
            "## Overnight OpenClaw Plan",
            "",
            f"- Owner: `{plan['owner']}`",
            f"- Mode: `{plan['mode']}`",
            f"- Batch size: `{plan['recommended_batch_size_trade_dates']}` trade dates",
            f"- Estimated batches: `{plan['estimated_batch_count']}`",
            "- Stop on non-zero exit, row-count anomaly, hash/date mismatch, secret exposure, broker/webhook/order attempt.",
            "",
            "## Safety",
            "",
            "- Simulation only.",
            "- No broker API.",
            "- No order placement.",
            "- No trading webhook.",
            "- No user-facing ranking impact from this plan.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE)
    parser.add_argument("--as-of", default=date.today().isoformat())
    parser.add_argument("--run-id", default=f"a_share_full_year_coverage_plan_{datetime.now().strftime('%Y%m%dT%H%M%S')}")
    args = parser.parse_args()
    as_of = date.fromisoformat(args.as_of)
    command = " ".join(["scripts/build_a_share_full_year_coverage_plan.py", "--as-of", args.as_of])
    report = build_plan(cache_dir=args.cache_dir, as_of=as_of, run_id=args.run_id, command=command)
    write_json(OUT_JSON, report)
    OUT_MD.write_text(markdown(report), encoding="utf-8")
    PASS_MARKER.write_text(f"{report['generated_at']} {report['coverage_status']}\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "coverage_status": report["coverage_status"], "answer": report["answer_label"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
