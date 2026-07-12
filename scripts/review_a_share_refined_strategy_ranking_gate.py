#!/usr/bin/env python3
"""Review refined A-share strategies before any ranking impact is allowed.

This gate is deliberately stricter than the refined sandbox. A refined sandbox
pass means "worth reviewing"; this script decides whether the evidence is broad
enough to affect simulation ranking. It never calls the network, never stores
raw payloads, and never creates user-facing recommendations.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.evaluate_a_share_tushare_source_hypotheses import fingerprints  # noqa: E402

REPORTS = ROOT / "data" / "reports"
PROCESSED = ROOT / "data" / "processed" / "a_share_refined_strategy_ranking_gate"
REFINED_JSON = REPORTS / "a_share_tushare_refined_strategy_sandbox_latest.json"
OUT_JSON = REPORTS / "a_share_refined_strategy_ranking_gate_latest.json"
OUT_MD = REPORTS / "a_share_refined_strategy_ranking_gate_latest.md"
PASS_MARKER = REPORTS / "A_SHARE_REFINED_STRATEGY_RANKING_GATE_PASS.marker"
BLOCKED_MARKER = REPORTS / "A_SHARE_REFINED_STRATEGY_RANKING_GATE_BLOCKED.marker"

THRESHOLDS = {
    "min_case_count": 6,
    "min_unique_symbols": 4,
    "max_single_symbol_case_share": 0.50,
    "min_entry_month_count": 3,
    "min_win_rate": 0.55,
    "min_average_return": 0.03,
    "max_drawdown_floor": -0.18,
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


def entry_month(entry_date: str | None) -> str | None:
    if not entry_date or len(entry_date) < 7:
        return None
    return entry_date[:7]


def case_source(case_id: str) -> str:
    if "tushare_dragon_tiger" in case_id:
        return "dragon_tiger_event_sample"
    if "stock_selection_workbench" in case_id:
        return "stock_selection_workbench_sample"
    return "unknown_case_source"


def review_item(item: dict[str, Any]) -> dict[str, Any]:
    cases = item.get("case_features") or []
    symbols = [str(case.get("symbol")) for case in cases if case.get("symbol")]
    months = [month for month in (entry_month(case.get("entry_date")) for case in cases) if month]
    source_counts = Counter(case_source(str(case.get("case_id", ""))) for case in cases)
    symbol_counts = Counter(symbols)
    count = len(cases)
    max_symbol_count = max(symbol_counts.values()) if symbol_counts else 0
    metrics = item.get("metrics") or {}
    win_rate = metrics.get("refined_signal_win_rate")
    avg = metrics.get("refined_signal_average_return")
    drawdown = metrics.get("refined_signal_max_drawdown")
    concentration = max_symbol_count / count if count else None
    observations = {
        "case_count": count,
        "unique_symbol_count": len(symbol_counts),
        "entry_month_count": len(set(months)),
        "max_single_symbol_case_share": concentration,
        "case_source_counts": dict(source_counts),
        "symbol_case_counts": dict(symbol_counts),
        "win_rate": win_rate,
        "average_return": avg,
        "max_drawdown": drawdown,
    }
    blockers: list[str] = []
    if item.get("disposition") != "REFINED_SANDBOX_PASS_CANDIDATE":
        blockers.append("not_refined_sandbox_pass_candidate")
    if count < THRESHOLDS["min_case_count"]:
        blockers.append("ranking_gate_case_count_below_threshold")
    if len(symbol_counts) < THRESHOLDS["min_unique_symbols"]:
        blockers.append("ranking_gate_unique_symbol_count_below_threshold")
    if concentration is None or concentration > THRESHOLDS["max_single_symbol_case_share"]:
        blockers.append("ranking_gate_single_symbol_concentration_too_high")
    if len(set(months)) < THRESHOLDS["min_entry_month_count"]:
        blockers.append("ranking_gate_entry_month_coverage_below_threshold")
    if win_rate is None or win_rate < THRESHOLDS["min_win_rate"]:
        blockers.append("ranking_gate_win_rate_below_threshold")
    if avg is None or avg < THRESHOLDS["min_average_return"]:
        blockers.append("ranking_gate_average_return_below_threshold")
    if drawdown is None or drawdown < THRESHOLDS["max_drawdown_floor"]:
        blockers.append("ranking_gate_drawdown_breached")
    disposition = "RANKING_GATE_APPROVED_FOR_SIMULATION_SORT" if not blockers else "RANKING_GATE_BLOCKED"
    return {
        "refined_strategy_id": item.get("refined_strategy_id"),
        "label": item.get("label"),
        "source_disposition": item.get("disposition"),
        "ranking_gate_disposition": disposition,
        "ranking_gate_blockers": blockers,
        "observations": observations,
        "required_next_evidence": []
        if disposition == "RANKING_GATE_APPROVED_FOR_SIMULATION_SORT"
        else [
            "collect_more_event_months",
            "increase_unique_symbol_coverage",
            "rerun_managed_cycle_before_ranking_impact",
        ],
        "ranking_impact_allowed": disposition == "RANKING_GATE_APPROVED_FOR_SIMULATION_SORT",
        "user_facing_suggestion_allowed": False,
        "real_trade_allowed": False,
        "simulation_only": True,
    }


def build_report(refined_report: dict[str, Any], *, run_id: str, command: str) -> dict[str, Any]:
    before = fingerprints()
    candidates = [
        item
        for item in refined_report.get("items", [])
        if item.get("disposition") == "REFINED_SANDBOX_PASS_CANDIDATE"
    ]
    items = [review_item(item) for item in candidates]
    approved = [
        item
        for item in items
        if item["ranking_gate_disposition"] == "RANKING_GATE_APPROVED_FOR_SIMULATION_SORT"
    ]
    after = fingerprints()
    report = {
        "type": "a_share_refined_strategy_ranking_gate",
        "status": "PASS" if refined_report.get("status") == "PASS" else "BLOCKED_REFINED_SANDBOX_NOT_PASS",
        "generated_at": now_iso(),
        "run_id": run_id,
        "command": command,
        "thresholds": THRESHOLDS,
        "summary": {
            "refined_pass_candidate_count": len(candidates),
            "ranking_gate_reviewed_count": len(items),
            "ranking_gate_approved_count": len(approved),
            "ranking_gate_blocked_count": len(items) - len(approved),
            "ranking_impact_allowed": bool(approved),
            "user_facing_suggestion_allowed": False,
            "network_used": False,
            "next_stage": "Only approved items may affect simulation sort; blocked items require more evidence.",
        },
        "items": items,
        "source_reports": {
            "refined_strategy_sandbox": str(REFINED_JSON),
        },
        "source_hashes": {
            "refined_strategy_sandbox": sha256(REFINED_JSON),
        },
        "checks": {
            "refined_sandbox_pass": refined_report.get("status") == "PASS",
            "only_refined_pass_candidates_reviewed": all(
                item.get("source_disposition") == "REFINED_SANDBOX_PASS_CANDIDATE"
                for item in items
            ),
            "raw_payload_saved": False,
            "network_not_used": True,
            "production_records_unchanged": before == after,
            "user_facing_suggestion_allowed": False,
            "no_broker_api": True,
            "no_webhook": True,
            "no_order_placement": True,
            "no_position_size": True,
        },
        "safety": {
            "simulation_only": True,
            "review_only": True,
            "raw_payload_saved": False,
            "network_used": False,
            "no_broker_api": True,
            "no_order_placement": True,
            "no_trading_webhook": True,
            "no_position_size": True,
            "no_live_order_signal": True,
            "real_trade_allowed": False,
        },
        "production_record_files_before": before,
        "production_record_files_after": after,
    }
    checks = report["checks"]
    if not (
        checks["refined_sandbox_pass"]
        and checks["only_refined_pass_candidates_reviewed"]
        and checks["raw_payload_saved"] is False
        and checks["network_not_used"]
        and checks["production_records_unchanged"]
        and checks["user_facing_suggestion_allowed"] is False
        and checks["no_broker_api"]
        and checks["no_webhook"]
        and checks["no_order_placement"]
        and checks["no_position_size"]
    ):
        report["status"] = "BLOCKED_CHECK_FAILED"
    return report


def markdown_report(report: dict[str, Any]) -> str:
    lines = [
        "# A-share Refined Strategy Ranking Gate",
        "",
        f"- Status: `{report['status']}`",
        f"- Generated At: `{report['generated_at']}`",
        f"- Reviewed: `{report['summary']['ranking_gate_reviewed_count']}`",
        f"- Approved For Simulation Sort: `{report['summary']['ranking_gate_approved_count']}`",
        f"- Blocked: `{report['summary']['ranking_gate_blocked_count']}`",
        f"- Ranking Impact Allowed: `{report['summary']['ranking_impact_allowed']}`",
        "- Boundary: review only; no raw payload, no broker, no order, no trading webhook, no user-facing suggestion.",
        "",
        "| Strategy | Gate | Cases | Symbols | Months | Max Symbol Share | Win Rate | Avg Return | Max Drawdown | Blockers |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for item in report.get("items", []):
        obs = item.get("observations") or {}
        share = obs.get("max_single_symbol_case_share")
        win = obs.get("win_rate")
        avg = obs.get("average_return")
        drawdown = obs.get("max_drawdown")
        lines.append(
            "| "
            + " | ".join(
                [
                    f"`{item['refined_strategy_id']}` {item.get('label')}",
                    f"`{item['ranking_gate_disposition']}`",
                    str(obs.get("case_count")),
                    str(obs.get("unique_symbol_count")),
                    str(obs.get("entry_month_count")),
                    "" if share is None else f"{share:.2f}",
                    "" if win is None else f"{win:.2f}",
                    "" if avg is None else f"{avg:.4f}",
                    "" if drawdown is None else f"{drawdown:.4f}",
                    ", ".join(item.get("ranking_gate_blockers", [])) or "none",
                ]
            )
            + " |"
        )
    lines.append("")
    return "\n".join(lines)


def write_outputs(report: dict[str, Any], run_id: str) -> dict[str, str]:
    REPORTS.mkdir(parents=True, exist_ok=True)
    run_dir = PROCESSED / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    run_json = run_dir / "a_share_refined_strategy_ranking_gate.json"
    run_md = run_dir / "a_share_refined_strategy_ranking_gate.md"
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
                f"ranking_gate_reviewed_count={report['summary']['ranking_gate_reviewed_count']}",
                f"ranking_gate_approved_count={report['summary']['ranking_gate_approved_count']}",
                f"ranking_gate_blocked_count={report['summary']['ranking_gate_blocked_count']}",
                f"ranking_impact_allowed={str(report['summary']['ranking_impact_allowed']).lower()}",
                "network_used=false",
                "raw_payload_saved=false",
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
    parser = argparse.ArgumentParser(description="Review refined A-share strategies before ranking impact.")
    parser.add_argument("--refined-json", type=Path, default=REFINED_JSON)
    parser.add_argument("--run-id", default=f"a_share_refined_strategy_ranking_gate_{datetime.now().strftime('%Y%m%dT%H%M%S')}")
    args = parser.parse_args(argv)
    command = " ".join(sys.argv)
    refined_report = load_json(args.refined_json, {})
    report = build_report(refined_report, run_id=args.run_id, command=command)
    outputs = write_outputs(report, args.run_id)
    print(json.dumps({"status": report["status"], "summary": report["summary"], "outputs": outputs}, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
