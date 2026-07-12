#!/usr/bin/env python3
"""Evaluate strategy-specific historical cases for simulation-only research.

This produces candidate-level research dispositions from historical cases. It
does not create recommendations, paper trades, positions, broker calls, or
user-facing live order signals.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "data" / "reports"
INPUT = REPORTS / "aegis_strategy_specific_historical_cases_latest.json"
OUT_JSON = REPORTS / "aegis_strategy_specific_case_evaluation_latest.json"
OUT_MD = REPORTS / "aegis_strategy_specific_case_evaluation_latest.md"
PASS_MARKER = REPORTS / "AEGIS_STRATEGY_SPECIFIC_CASE_EVALUATION_PASS.marker"
FAIL_MARKER = REPORTS / "AEGIS_STRATEGY_SPECIFIC_CASE_EVALUATION_FAIL.marker"

RECORD_PATHS = {
    "recommendations_jsonl": ROOT / "data" / "records" / "recommendations.jsonl",
    "paper_trades_jsonl": ROOT / "data" / "records" / "paper_trades.jsonl",
    "reviews_jsonl": ROOT / "data" / "records" / "reviews.jsonl",
    "memory_jsonl": ROOT / "data" / "records" / "memory.jsonl",
    "investment_memory_jsonl": ROOT / "data" / "records" / "investment_memory.jsonl",
    "feedback_events_jsonl": ROOT / "data" / "records" / "aegis_stock_feedback_events.jsonl",
}

THRESHOLDS = {
    "min_case_count": 4,
    "min_win_rate": 0.5,
    "min_average_return": 0.0,
    "hard_worst_return": -0.20,
    "watch_average_drawdown": -0.12,
    "watch_worst_return": -0.12,
}


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def sha256(path: Path) -> str | None:
    if not path.exists():
        return None
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def fingerprint(path: Path) -> dict[str, Any]:
    return {
        "exists": path.exists(),
        "size": path.stat().st_size if path.exists() else None,
        "sha256": sha256(path),
    }


def fingerprints(paths: dict[str, Path]) -> dict[str, dict[str, Any]]:
    return {name: fingerprint(path) for name, path in paths.items()}


def classify(summary: dict[str, Any]) -> tuple[str, list[str]]:
    reasons: list[str] = []
    case_count = summary.get("case_count") or 0
    win_rate = summary.get("win_rate")
    average_return = summary.get("average_return")
    average_drawdown = summary.get("average_max_drawdown")
    worst_return = summary.get("worst_return")

    if case_count < THRESHOLDS["min_case_count"]:
        reasons.append("case_count_below_threshold")
    if win_rate is None or win_rate < THRESHOLDS["min_win_rate"]:
        reasons.append("win_rate_below_threshold")
    if average_return is None or average_return <= THRESHOLDS["min_average_return"]:
        reasons.append("average_return_below_threshold")
    if worst_return is None or worst_return <= THRESHOLDS["hard_worst_return"]:
        reasons.append("hard_worst_return_breached")

    if reasons:
        return "downgraded", reasons

    watch_reasons: list[str] = []
    if average_drawdown is not None and average_drawdown <= THRESHOLDS["watch_average_drawdown"]:
        watch_reasons.append("average_drawdown_watch")
    if worst_return is not None and worst_return <= THRESHOLDS["watch_worst_return"]:
        watch_reasons.append("worst_return_watch")
    if watch_reasons:
        return "watch_only", watch_reasons
    return "simulation_research_candidate", ["historical_case_thresholds_passed"]


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Aegis Strategy-Specific Case Evaluation",
        "",
        f"- Status: {report['status']}",
        f"- Generated At: {report['generated_at']}",
        f"- Candidate Count: {report['summary']['candidate_count']}",
        f"- Simulation Research Candidates: {report['summary']['simulation_research_candidate_count']}",
        f"- Watch Only: {report['summary']['watch_only_count']}",
        f"- Downgraded: {report['summary']['downgraded_count']}",
        "",
        "Evaluation only. No real trade, no broker API, no webhook, no order placement.",
        "",
        "## Dispositions",
        "",
    ]
    for item in report["items"]:
        s = item["summary"]
        lines.append(
            "- "
            f"{item['symbol']} {item.get('name', '')}: {item['disposition']} "
            f"cases={s.get('case_count')} win_rate={s.get('win_rate')} "
            f"avg_return={s.get('average_return')} reasons={','.join(item['reasons'])}"
        )
    lines.append("")
    return "\n".join(lines)


def build_report() -> dict[str, Any]:
    source = load_json(INPUT, {})
    before = fingerprints(RECORD_PATHS)
    items = []
    for result in source.get("candidate_results", []):
        disposition, reasons = classify(result.get("summary") or {})
        items.append(
            {
                "symbol": result.get("symbol"),
                "name": result.get("name"),
                "market": result.get("market"),
                "matched_strategy_ids": result.get("matched_strategy_ids") or [],
                "disposition": disposition,
                "reasons": reasons,
                "summary": result.get("summary") or {},
                "simulation_only": True,
                "user_facing_suggestion_allowed": False,
                "real_trade_allowed": False,
            }
        )
    after = fingerprints(RECORD_PATHS)
    report = {
        "type": "aegis_strategy_specific_case_evaluation",
        "status": "PASS" if source.get("status") == "PASS" and items else "FAIL",
        "generated_at": now_iso(),
        "thresholds": THRESHOLDS,
        "summary": {
            "candidate_count": len(items),
            "simulation_research_candidate_count": sum(
                1 for item in items if item["disposition"] == "simulation_research_candidate"
            ),
            "watch_only_count": sum(1 for item in items if item["disposition"] == "watch_only"),
            "downgraded_count": sum(1 for item in items if item["disposition"] == "downgraded"),
            "user_facing_suggestion_allowed": False,
            "next_stage": "surface dispositions in dashboard and stock assistant brief",
        },
        "items": items,
        "source_reports": {"strategy_specific_historical_cases": str(INPUT)},
        "source_hashes": {"strategy_specific_historical_cases": sha256(INPUT)},
        "checks": {
            "source_pass": source.get("status") == "PASS",
            "all_candidates_evaluated": len(items) == len(source.get("candidate_results", [])) and bool(items),
            "data_gap_count_zero": source.get("summary", {}).get("data_gap_count") == 0,
            "production_records_unchanged": before == after,
            "no_broker_api": True,
            "no_webhook": True,
            "no_order_placement": True,
            "no_position_size": True,
        },
        "safety": {
            "simulation_only": True,
            "research_only": True,
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
    if not all(report["checks"].values()):
        report["status"] = "FAIL"
    return report


def main() -> int:
    report = build_report()
    write_json(OUT_JSON, report)
    OUT_MD.write_text(render_markdown(report), encoding="utf-8")
    marker = PASS_MARKER if report["status"] == "PASS" else FAIL_MARKER
    stale = FAIL_MARKER if marker == PASS_MARKER else PASS_MARKER
    if stale.exists():
        stale.unlink()
    marker.write_text(
        "\n".join(
            [
                f"generated_at={report['generated_at']}",
                f"exit_code={0 if report['status'] == 'PASS' else 1}",
                f"report_json={OUT_JSON}",
                f"report_json_sha256={sha256(OUT_JSON)}",
                f"candidate_count={report['summary']['candidate_count']}",
                f"simulation_research_candidate_count={report['summary']['simulation_research_candidate_count']}",
                f"watch_only_count={report['summary']['watch_only_count']}",
                f"downgraded_count={report['summary']['downgraded_count']}",
                "user_facing_suggestion_allowed=false",
                "no_real_trade=true",
                "no_broker_api=true",
                "no_webhook=true",
                "no_order_placement=true",
                "no_position_size=true",
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "status": report["status"],
                "candidate_count": report["summary"]["candidate_count"],
                "simulation_research_candidate_count": report["summary"]["simulation_research_candidate_count"],
                "watch_only_count": report["summary"]["watch_only_count"],
                "downgraded_count": report["summary"]["downgraded_count"],
                "report_json": str(OUT_JSON),
            },
            ensure_ascii=False,
        )
    )
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
