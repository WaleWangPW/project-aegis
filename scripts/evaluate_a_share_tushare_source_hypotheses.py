#!/usr/bin/env python3
"""Evaluate A-share Tushare source hypotheses with existing historical cases.

This is a proxy sandbox layer. It answers: "Do the current A-share historical
cases support spending more sandbox work on this source hypothesis?" It does
not prove the source signal itself works yet, because source-specific feature
history is not assembled here. No network, raw payload, broker, order, webhook,
or production record mutation is allowed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "data" / "reports"
PROCESSED = ROOT / "data" / "processed" / "a_share_tushare_source_hypothesis_evaluation"
QUEUE_JSON = REPORTS / "a_share_tushare_source_hypothesis_queue_latest.json"
CASES_JSON = REPORTS / "aegis_strategy_specific_historical_cases_latest.json"
OUT_JSON = REPORTS / "a_share_tushare_source_hypothesis_evaluation_latest.json"
OUT_MD = REPORTS / "a_share_tushare_source_hypothesis_evaluation_latest.md"
PASS_MARKER = REPORTS / "A_SHARE_TUSHARE_SOURCE_HYPOTHESIS_EVALUATION_PASS.marker"
FAIL_MARKER = REPORTS / "A_SHARE_TUSHARE_SOURCE_HYPOTHESIS_EVALUATION_FAIL.marker"

RECORD_PATHS = {
    "recommendations_jsonl": ROOT / "data" / "records" / "recommendations.jsonl",
    "paper_trades_jsonl": ROOT / "data" / "records" / "paper_trades.jsonl",
    "reviews_jsonl": ROOT / "data" / "records" / "reviews.jsonl",
    "memory_jsonl": ROOT / "data" / "records" / "memory.jsonl",
    "investment_memory_jsonl": ROOT / "data" / "records" / "investment_memory.jsonl",
    "feedback_events_jsonl": ROOT / "data" / "records" / "aegis_stock_feedback_events.jsonl",
}

THRESHOLDS = {
    "min_proxy_case_count": 4,
    "min_proxy_win_rate": 0.50,
    "min_proxy_average_return": 0.0,
    "max_proxy_average_drawdown": -0.14,
    "min_a_share_candidate_count_for_confident_eval": 5,
}

FAMILY_TO_STRATEGY_HINTS = {
    "capital_flow": {"a_share_short_momentum", "growth_breakout", "low_vol_momentum"},
    "hot_money": {"a_share_short_momentum", "growth_breakout"},
    "institutional_ownership": {"qvm", "low_vol_momentum"},
    "holder_concentration": {"qvm", "a_share_short_momentum"},
    "governance": {"qvm"},
    "multi_factor": {"qvm", "a_share_short_momentum", "low_vol_momentum"},
    "quality": {"qvm", "low_vol_momentum"},
    "momentum": {"a_share_short_momentum", "growth_breakout", "low_vol_momentum"},
    "risk_overlay": {"qvm", "low_vol_momentum", "a_share_short_momentum"},
}


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def sha256(path: Path) -> str | None:
    if not path.exists():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
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


def fingerprints() -> dict[str, dict[str, Any]]:
    return {name: fingerprint(path) for name, path in RECORD_PATHS.items()}


def strategy_hints_for(hypothesis: dict[str, Any]) -> set[str]:
    hints: set[str] = set()
    families = list(hypothesis.get("strategy_families", []))
    routed_families = [family for family in families if family != "risk_overlay"] or families
    for family in routed_families:
        hints.update(FAMILY_TO_STRATEGY_HINTS.get(family, set()))
    return hints


def eligible_a_share_results(hypothesis: dict[str, Any], cases_report: dict[str, Any]) -> list[dict[str, Any]]:
    hints = strategy_hints_for(hypothesis)
    results: list[dict[str, Any]] = []
    for item in cases_report.get("candidate_results", []):
        if item.get("market") != "A":
            continue
        matched = set(item.get("matched_strategy_ids") or [])
        if not hints or matched.intersection(hints):
            results.append(item)
    return results


def aggregate(results: list[dict[str, Any]]) -> dict[str, Any]:
    total_cases = sum(int((item.get("summary") or {}).get("case_count") or 0) for item in results)
    if not total_cases:
        return {
            "candidate_count": len(results),
            "proxy_case_count": 0,
            "proxy_win_rate": None,
            "proxy_average_return": None,
            "proxy_average_drawdown": None,
            "proxy_best_return": None,
            "proxy_worst_return": None,
        }
    wins = 0.0
    weighted_return = 0.0
    weighted_drawdown = 0.0
    best: float | None = None
    worst: float | None = None
    for item in results:
        summary = item.get("summary") or {}
        count = int(summary.get("case_count") or 0)
        if not count:
            continue
        win_rate = float(summary.get("win_rate") or 0.0)
        avg_return = float(summary.get("average_return") or 0.0)
        avg_drawdown = float(summary.get("average_max_drawdown") or 0.0)
        wins += win_rate * count
        weighted_return += avg_return * count
        weighted_drawdown += avg_drawdown * count
        if summary.get("best_return") is not None:
            best = max(best, float(summary["best_return"])) if best is not None else float(summary["best_return"])
        if summary.get("worst_return") is not None:
            worst = min(worst, float(summary["worst_return"])) if worst is not None else float(summary["worst_return"])
    return {
        "candidate_count": len(results),
        "proxy_case_count": total_cases,
        "proxy_win_rate": wins / total_cases,
        "proxy_average_return": weighted_return / total_cases,
        "proxy_average_drawdown": weighted_drawdown / total_cases,
        "proxy_best_return": best,
        "proxy_worst_return": worst,
    }


def classify(metrics: dict[str, Any]) -> tuple[str, list[str], str]:
    reasons: list[str] = []
    case_count = int(metrics.get("proxy_case_count") or 0)
    candidate_count = int(metrics.get("candidate_count") or 0)
    win_rate = metrics.get("proxy_win_rate")
    average_return = metrics.get("proxy_average_return")
    average_drawdown = metrics.get("proxy_average_drawdown")

    if case_count < THRESHOLDS["min_proxy_case_count"]:
        reasons.append("proxy_case_count_below_threshold")
    if win_rate is None or win_rate < THRESHOLDS["min_proxy_win_rate"]:
        reasons.append("proxy_win_rate_below_threshold")
    if average_return is None or average_return <= THRESHOLDS["min_proxy_average_return"]:
        reasons.append("proxy_average_return_below_threshold")
    if average_drawdown is not None and average_drawdown <= THRESHOLDS["max_proxy_average_drawdown"]:
        reasons.append("proxy_average_drawdown_too_deep")

    if candidate_count < THRESHOLDS["min_a_share_candidate_count_for_confident_eval"]:
        confidence = "LOW_SAMPLE_PROXY"
    else:
        confidence = "PROXY"

    if reasons:
        return "proxy_fail", reasons, confidence
    if confidence == "LOW_SAMPLE_PROXY":
        return "needs_more_a_share_cases", ["proxy_thresholds_passed_but_sample_is_small"], confidence
    return "proxy_pass", ["proxy_thresholds_passed"], confidence


def build_report(queue: dict[str, Any], cases_report: dict[str, Any], *, run_id: str, command: str) -> dict[str, Any]:
    before = fingerprints()
    items: list[dict[str, Any]] = []
    for hypothesis in queue.get("hypotheses", []):
        eligible = eligible_a_share_results(hypothesis, cases_report)
        metrics = aggregate(eligible)
        disposition, reasons, confidence = classify(metrics)
        items.append(
            {
                "hypothesis_id": hypothesis.get("hypothesis_id"),
                "title": hypothesis.get("title"),
                "strategy_families": hypothesis.get("strategy_families") or [],
                "source_research_ids": hypothesis.get("source_research_ids") or [],
                "proxy_strategy_hints": sorted(strategy_hints_for(hypothesis)),
                "eligible_symbols": [item.get("symbol") for item in eligible],
                "metrics": metrics,
                "disposition": disposition,
                "confidence": confidence,
                "reasons": reasons,
                "feature_history_status": "source_specific_feature_history_not_yet_assembled",
                "allowed_next_step": "deep_source_specific_sandbox" if disposition != "proxy_fail" else "collect_more_cases_or_rework_hypothesis",
                "simulation_only": True,
                "user_facing_suggestion_allowed": False,
                "real_trade_allowed": False,
            }
        )
    after = fingerprints()
    status = "PASS" if queue.get("hypothesis_count", 0) and items and cases_report.get("status") == "PASS" else "FAIL"
    report = {
        "type": "a_share_tushare_source_hypothesis_evaluation",
        "status": status,
        "generated_at": now_iso(),
        "run_id": run_id,
        "command": command,
        "thresholds": THRESHOLDS,
        "summary": {
            "hypothesis_count": len(items),
            "proxy_pass_count": sum(1 for item in items if item["disposition"] == "proxy_pass"),
            "needs_more_a_share_cases_count": sum(1 for item in items if item["disposition"] == "needs_more_a_share_cases"),
            "proxy_fail_count": sum(1 for item in items if item["disposition"] == "proxy_fail"),
            "a_share_candidate_count": len(
                {item.get("symbol") for item in cases_report.get("candidate_results", []) if item.get("market") == "A"}
            ),
            "a_share_proxy_case_count": cases_report.get("summary", {}).get("a_share_case_count", 0),
            "user_facing_suggestion_allowed": False,
            "next_stage": "OpenClaw stock-agent should collect deeper source-specific historical features before any ranking impact.",
        },
        "items": items,
        "source_reports": {
            "source_hypothesis_queue": str(QUEUE_JSON),
            "strategy_specific_historical_cases": str(CASES_JSON),
        },
        "source_hashes": {
            "source_hypothesis_queue": sha256(QUEUE_JSON),
            "strategy_specific_historical_cases": sha256(CASES_JSON),
        },
        "checks": {
            "source_queue_present": queue.get("hypothesis_count", 0) > 0,
            "strategy_specific_cases_pass": cases_report.get("status") == "PASS",
            "all_hypotheses_evaluated": len(items) == queue.get("hypothesis_count", 0),
            "a_share_cases_present": cases_report.get("summary", {}).get("a_share_case_count", 0) > 0,
            "feature_history_limitation_explicit": all(
                item["feature_history_status"] == "source_specific_feature_history_not_yet_assembled" for item in items
            ),
            "production_records_unchanged": before == after,
            "network_not_used": True,
            "no_raw_tushare_payload": True,
            "no_broker_api": True,
            "no_webhook": True,
            "no_order_placement": True,
            "no_position_size": True,
        },
        "safety": {
            "simulation_only": True,
            "research_only": True,
            "proxy_sandbox_only": True,
            "requires_deep_source_specific_sandbox_before_ranking": True,
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


def markdown_report(report: dict[str, Any]) -> str:
    lines = [
        "# A-share Tushare Source Hypothesis Evaluation",
        "",
        f"- Status: `{report['status']}`",
        f"- Generated At: `{report['generated_at']}`",
        f"- Hypothesis Count: `{report['summary']['hypothesis_count']}`",
        f"- Proxy Pass: `{report['summary']['proxy_pass_count']}`",
        f"- Needs More A-share Cases: `{report['summary']['needs_more_a_share_cases_count']}`",
        f"- Proxy Fail: `{report['summary']['proxy_fail_count']}`",
        "- Boundary: proxy sandbox only; no broker, no order, no trading webhook, no ranking impact.",
        "",
        "## Results",
        "",
        "| Hypothesis | Disposition | Confidence | Cases | Avg Return | Reasons |",
        "| --- | --- | --- | ---: | ---: | --- |",
    ]
    for item in report.get("items", []):
        metrics = item.get("metrics") or {}
        avg = metrics.get("proxy_average_return")
        lines.append(
            "| "
            + " | ".join(
                [
                    f"`{item['hypothesis_id']}`",
                    f"`{item['disposition']}`",
                    f"`{item['confidence']}`",
                    str(metrics.get("proxy_case_count")),
                    "" if avg is None else f"{avg:.4f}",
                    ", ".join(item.get("reasons", [])),
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Limitation",
            "",
            "This report uses current A-share historical candidate cases as proxy evidence. "
            "Source-specific historical features such as historical moneyflow, top-list seats, "
            "holder concentration changes, and governance events still need deeper assembly before "
            "any strategy can affect ranking.",
            "",
        ]
    )
    return "\n".join(lines)


def write_outputs(report: dict[str, Any], run_id: str) -> dict[str, str]:
    REPORTS.mkdir(parents=True, exist_ok=True)
    run_dir = PROCESSED / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    run_json = run_dir / "a_share_tushare_source_hypothesis_evaluation.json"
    run_md = run_dir / "a_share_tushare_source_hypothesis_evaluation.md"
    write_json(run_json, report)
    run_md.write_text(markdown_report(report), encoding="utf-8")
    write_json(OUT_JSON, report)
    OUT_MD.write_text(markdown_report(report), encoding="utf-8")
    marker = PASS_MARKER if report["status"] == "PASS" else FAIL_MARKER
    stale = FAIL_MARKER if marker == PASS_MARKER else PASS_MARKER
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
                f"hypothesis_count={report['summary']['hypothesis_count']}",
                f"proxy_pass_count={report['summary']['proxy_pass_count']}",
                f"needs_more_a_share_cases_count={report['summary']['needs_more_a_share_cases_count']}",
                f"proxy_fail_count={report['summary']['proxy_fail_count']}",
                "network_used=false",
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
    return {"run_json": str(run_json), "run_md": str(run_md), "latest_json": str(OUT_JSON), "latest_md": str(OUT_MD), "marker": str(marker)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Evaluate A-share Tushare source hypotheses using proxy historical cases.")
    parser.add_argument("--queue-json", type=Path, default=QUEUE_JSON)
    parser.add_argument("--cases-json", type=Path, default=CASES_JSON)
    parser.add_argument("--run-id", default=f"a_share_tushare_source_hypothesis_evaluation_{datetime.now().strftime('%Y%m%dT%H%M%S')}")
    args = parser.parse_args(argv)
    queue = load_json(args.queue_json)
    cases = load_json(args.cases_json)
    command = " ".join(sys.argv)
    report = build_report(queue, cases, run_id=args.run_id, command=command)
    outputs = write_outputs(report, args.run_id)
    print(json.dumps({"status": report["status"], "summary": report["summary"], "outputs": outputs}, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
