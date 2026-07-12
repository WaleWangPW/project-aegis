#!/usr/bin/env python3
"""Plan the next A-share research-sample expansion for stock-agent.

This script turns ranking-gate blockers into concrete low-token stock-agent
tasks. It does not call Tushare, does not mutate strategy thresholds, and does
not create recommendations. The goal is to tell OpenClaw what to expand next
so Codex does not need to manually inspect every failed gate.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.collect_a_share_dragon_tiger_research_samples import daily_cache_dates  # noqa: E402
from scripts.evaluate_a_share_tushare_source_hypotheses import fingerprints  # noqa: E402

REPORTS = ROOT / "data" / "reports"
PROCESSED = ROOT / "data" / "processed" / "a_share_strategy_sample_expansion_plan"
RANKING_GATE = REPORTS / "a_share_refined_strategy_ranking_gate_latest.json"
DRAGON_TIGER = REPORTS / "a_share_dragon_tiger_research_samples_latest.json"
HISTORICAL_CASES = REPORTS / "aegis_strategy_specific_historical_cases_latest.json"
OUT_JSON = REPORTS / "a_share_strategy_sample_expansion_plan_latest.json"
OUT_MD = REPORTS / "a_share_strategy_sample_expansion_plan_latest.md"
PASS_MARKER = REPORTS / "A_SHARE_STRATEGY_SAMPLE_EXPANSION_PLAN_PASS.marker"
BLOCKED_MARKER = REPORTS / "A_SHARE_STRATEGY_SAMPLE_EXPANSION_PLAN_BLOCKED.marker"

DEFAULT_NEXT_PARAMS = {
    "lookback_dates": 90,
    "forward_days": 20,
    "max_symbols": 24,
    "max_events_per_symbol": 3,
}


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def sha256(path: Path) -> str | None:
    if not path.exists():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def compact_date(value: str) -> str:
    return str(value).replace("-", "")


def iso_date(value: str) -> str:
    value = str(value)
    return value if "-" in value else f"{value[:4]}-{value[4:6]}-{value[6:8]}"


def eligible_window(*, lookback_dates: int, forward_days: int) -> dict[str, Any]:
    dates = daily_cache_dates()
    if len(dates) <= forward_days:
        return {
            "eligible": False,
            "available_cache_date_count": len(dates),
            "lookback_dates": lookback_dates,
            "forward_days": forward_days,
            "eligible_date_count": 0,
            "eligible_start": None,
            "eligible_end": None,
        }
    cutoff = len(dates) - forward_days - 1
    selected = dates[max(0, cutoff - lookback_dates + 1) : cutoff + 1]
    return {
        "eligible": bool(selected),
        "available_cache_date_count": len(dates),
        "lookback_dates": lookback_dates,
        "forward_days": forward_days,
        "eligible_date_count": len(selected),
        "eligible_start": iso_date(selected[0]) if selected else None,
        "eligible_end": iso_date(selected[-1]) if selected else None,
    }


def gate_shortfalls(item: dict[str, Any]) -> list[dict[str, Any]]:
    blockers = set(item.get("ranking_gate_blockers") or [])
    obs = item.get("observations") or {}
    mapping = [
        (
            "ranking_gate_case_count_below_threshold",
            "increase_case_count",
            f"当前 case={obs.get('case_count')}，需要扩大事件日期和每股事件数。",
        ),
        (
            "ranking_gate_unique_symbol_count_below_threshold",
            "increase_unique_symbol_coverage",
            f"当前唯一股票={obs.get('unique_symbol_count')}，需要扩大 max_symbols 并避免重复同一股票。",
        ),
        (
            "ranking_gate_single_symbol_concentration_too_high",
            "reduce_single_symbol_concentration",
            f"当前最大单股占比={obs.get('max_single_symbol_case_share')}，需要更多不同股票的有效事件。",
        ),
        (
            "ranking_gate_entry_month_coverage_below_threshold",
            "increase_entry_month_coverage",
            f"当前月份={obs.get('entry_month_count')}，需要扩大 lookback_dates。",
        ),
    ]
    return [
        {"blocker": blocker, "task": task, "why": why}
        for blocker, task, why in mapping
        if blocker in blockers
    ]


def build_report(
    ranking_gate: dict[str, Any],
    dragon_tiger: dict[str, Any],
    historical_cases: dict[str, Any],
    *,
    run_id: str,
    command: str,
) -> dict[str, Any]:
    before = fingerprints()
    gate_items = ranking_gate.get("items") or []
    blocked_items = [
        item for item in gate_items if item.get("ranking_gate_disposition") == "RANKING_GATE_BLOCKED"
    ]
    current_dt_summary = dragon_tiger.get("summary") or {}
    current_case_summary = historical_cases.get("summary") or {}
    current_window = {
        "lookback_dates": current_dt_summary.get("queried_trade_date_count"),
        "eligible_start": current_dt_summary.get("eligible_cache_date_start"),
        "eligible_end": current_dt_summary.get("eligible_cache_date_end"),
        "sample_count": current_dt_summary.get("sample_count"),
        "event_count": current_dt_summary.get("event_count"),
        "event_aligned_case_count": current_case_summary.get("a_share_dragon_tiger_research_sample_case_count"),
    }
    next_window = eligible_window(
        lookback_dates=DEFAULT_NEXT_PARAMS["lookback_dates"],
        forward_days=DEFAULT_NEXT_PARAMS["forward_days"],
    )
    tasks: list[dict[str, Any]] = []
    for item in blocked_items:
        tasks.append(
            {
                "refined_strategy_id": item.get("refined_strategy_id"),
                "label": item.get("label"),
                "current_observations": item.get("observations") or {},
                "shortfalls": gate_shortfalls(item),
                "recommended_collect_command": (
                    ".venv/bin/python scripts/collect_a_share_dragon_tiger_research_samples.py "
                    f"--lookback-dates {DEFAULT_NEXT_PARAMS['lookback_dates']} "
                    f"--forward-days {DEFAULT_NEXT_PARAMS['forward_days']} "
                    f"--max-symbols {DEFAULT_NEXT_PARAMS['max_symbols']} "
                    f"--max-events-per-symbol {DEFAULT_NEXT_PARAMS['max_events_per_symbol']}"
                ),
                "then_run": [
                    "make stock-agent-a-share-strategy-cycle-managed",
                    "inspect data/reports/a_share_refined_strategy_ranking_gate_latest.json",
                ],
                "done_when": [
                    "ranking_gate_approved_count increases above 0",
                    "or blocker evidence shows no improvement after expanded sample collection",
                ],
                "ranking_impact_allowed": False,
                "user_facing_suggestion_allowed": False,
            }
        )
    after = fingerprints()
    report = {
        "type": "a_share_strategy_sample_expansion_plan",
        "status": "PASS" if ranking_gate.get("status") == "PASS" else "BLOCKED_MISSING_RANKING_GATE",
        "generated_at": now_iso(),
        "run_id": run_id,
        "command": command,
        "summary": {
            "blocked_ranking_gate_item_count": len(blocked_items),
            "expansion_task_count": len(tasks),
            "current_sample_count": current_window.get("sample_count"),
            "current_event_count": current_window.get("event_count"),
            "current_event_aligned_case_count": current_window.get("event_aligned_case_count"),
            "next_lookback_dates": DEFAULT_NEXT_PARAMS["lookback_dates"],
            "next_forward_days": DEFAULT_NEXT_PARAMS["forward_days"],
            "next_max_symbols": DEFAULT_NEXT_PARAMS["max_symbols"],
            "next_max_events_per_symbol": DEFAULT_NEXT_PARAMS["max_events_per_symbol"],
            "network_used": False,
            "ranking_impact_allowed": False,
            "user_facing_suggestion_allowed": False,
        },
        "current_window": current_window,
        "next_window": next_window,
        "tasks": tasks,
        "source_reports": {
            "ranking_gate": str(RANKING_GATE),
            "dragon_tiger": str(DRAGON_TIGER),
            "historical_cases": str(HISTORICAL_CASES),
        },
        "source_hashes": {
            "ranking_gate": sha256(RANKING_GATE),
            "dragon_tiger": sha256(DRAGON_TIGER),
            "historical_cases": sha256(HISTORICAL_CASES),
        },
        "checks": {
            "ranking_gate_loaded": ranking_gate.get("status") == "PASS",
            "blocked_items_have_tasks": len(tasks) == len(blocked_items),
            "raw_payload_saved": False,
            "network_not_used": True,
            "production_records_unchanged": before == after,
            "ranking_impact_allowed": False,
            "user_facing_suggestion_allowed": False,
            "no_broker_api": True,
            "no_webhook": True,
            "no_order_placement": True,
        },
        "safety": {
            "planning_only": True,
            "simulation_research_only": True,
            "raw_payload_saved": False,
            "network_used": False,
            "ranking_impact_allowed": False,
            "user_facing_suggestion_allowed": False,
            "no_broker_api": True,
            "no_order_placement": True,
            "no_trading_webhook": True,
            "real_trade_allowed": False,
        },
        "production_record_files_before": before,
        "production_record_files_after": after,
    }
    checks = report["checks"]
    if not (
        checks["ranking_gate_loaded"]
        and checks["blocked_items_have_tasks"]
        and checks["raw_payload_saved"] is False
        and checks["network_not_used"]
        and checks["production_records_unchanged"]
        and checks["ranking_impact_allowed"] is False
        and checks["user_facing_suggestion_allowed"] is False
        and checks["no_broker_api"]
        and checks["no_webhook"]
        and checks["no_order_placement"]
    ):
        report["status"] = "BLOCKED_CHECK_FAILED"
    return report


def markdown_report(report: dict[str, Any]) -> str:
    s = report["summary"]
    lines = [
        "# A-share Strategy Sample Expansion Plan",
        "",
        f"- Status: `{report['status']}`",
        f"- Generated At: `{report['generated_at']}`",
        f"- Blocked Gate Items: `{s.get('blocked_ranking_gate_item_count')}`",
        f"- Expansion Tasks: `{s.get('expansion_task_count')}`",
        f"- Current Samples / Events / Event Cases: `{s.get('current_sample_count')}` / `{s.get('current_event_count')}` / `{s.get('current_event_aligned_case_count')}`",
        f"- Next Lookback / Symbols / Events Per Symbol: `{s.get('next_lookback_dates')}` / `{s.get('next_max_symbols')}` / `{s.get('next_max_events_per_symbol')}`",
        "- Boundary: planning only; no network, no recommendation, no broker, no order, no trading webhook.",
        "",
        "## Tasks",
        "",
    ]
    for task in report.get("tasks", []):
        lines.append(f"### {task.get('label')} (`{task.get('refined_strategy_id')}`)")
        lines.append("")
        lines.append(f"- Command: `{task.get('recommended_collect_command')}`")
        lines.append("- Shortfalls:")
        for shortfall in task.get("shortfalls", []):
            lines.append(f"  - `{shortfall.get('task')}`: {shortfall.get('why')}")
        lines.append("")
    return "\n".join(lines)


def write_outputs(report: dict[str, Any], run_id: str) -> dict[str, str]:
    REPORTS.mkdir(parents=True, exist_ok=True)
    run_dir = PROCESSED / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    run_json = run_dir / "a_share_strategy_sample_expansion_plan.json"
    run_md = run_dir / "a_share_strategy_sample_expansion_plan.md"
    write_json(run_json, report)
    run_md.write_text(markdown_report(report), encoding="utf-8")
    write_json(OUT_JSON, report)
    OUT_MD.write_text(markdown_report(report), encoding="utf-8")
    marker = PASS_MARKER if report["status"] == "PASS" else BLOCKED_MARKER
    stale = BLOCKED_MARKER if marker == PASS_MARKER else PASS_MARKER
    if stale.exists():
        stale.unlink()
    marker.write_text(
        "\n".join(
            [
                f"status={report['status']}",
                f"run_id={run_id}",
                f"generated_at={report['generated_at']}",
                f"report_json={OUT_JSON}",
                f"report_json_sha256={sha256(OUT_JSON)}",
                f"expansion_task_count={report['summary']['expansion_task_count']}",
                f"next_lookback_dates={report['summary']['next_lookback_dates']}",
                f"next_max_symbols={report['summary']['next_max_symbols']}",
                "network_used=false",
                "raw_payload_saved=false",
                "ranking_impact_allowed=false",
                "user_facing_suggestion_allowed=false",
                "no_real_trade=true",
                "no_broker_api=true",
                "no_webhook=true",
                "no_order_placement=true",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return {
        "run_json": str(run_json),
        "run_md": str(run_md),
        "latest_json": str(OUT_JSON),
        "latest_md": str(OUT_MD),
        "marker": str(marker),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Plan A-share strategy sample expansion for stock-agent.")
    parser.add_argument("--ranking-gate-json", type=Path, default=RANKING_GATE)
    parser.add_argument("--dragon-tiger-json", type=Path, default=DRAGON_TIGER)
    parser.add_argument("--historical-cases-json", type=Path, default=HISTORICAL_CASES)
    parser.add_argument("--run-id", default=f"a_share_strategy_sample_expansion_plan_{datetime.now().strftime('%Y%m%dT%H%M%S')}")
    args = parser.parse_args(argv)
    command = " ".join(sys.argv)
    report = build_report(
        load_json(args.ranking_gate_json, {}),
        load_json(args.dragon_tiger_json, {}),
        load_json(args.historical_cases_json, {}),
        run_id=args.run_id,
        command=command,
    )
    outputs = write_outputs(report, args.run_id)
    print(json.dumps({"status": report["status"], "summary": report["summary"], "outputs": outputs}, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
