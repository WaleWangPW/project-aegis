#!/usr/bin/env python3
"""Evaluate stock-agent proposed A-share signal-tuning experiments.

This layer consumes the derived-feature deep sandbox report. It does not call
Tushare, does not read secrets, does not save raw payloads, and does not create
recommendations. It only checks whether stricter signal definitions improve the
failed A-share source strategies enough to justify later Codex-reviewed work.
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

from scripts.evaluate_a_share_tushare_source_hypotheses import fingerprints  # noqa: E402

REPORTS = ROOT / "data" / "reports"
PROCESSED = ROOT / "data" / "processed" / "a_share_signal_tuning_experiments"
DEEP_JSON = REPORTS / "a_share_tushare_source_deep_sandbox_latest.json"
OUT_JSON = REPORTS / "a_share_signal_tuning_experiments_latest.json"
OUT_MD = REPORTS / "a_share_signal_tuning_experiments_latest.md"
PASS_MARKER = REPORTS / "A_SHARE_SIGNAL_TUNING_EXPERIMENTS_PASS.marker"
BLOCKED_MARKER = REPORTS / "A_SHARE_SIGNAL_TUNING_EXPERIMENTS_BLOCKED.marker"

THRESHOLDS = {
    "min_signal_case_count": 2,
    "min_signal_win_rate": 0.50,
    "min_signal_average_return": 0.0,
    "max_signal_drawdown_floor": -0.18,
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


def deep_maps(deep_report: dict[str, Any]) -> dict[str, dict[str, dict[str, Any]]]:
    return {
        item.get("hypothesis_id"): {
            case.get("case_id"): case
            for case in item.get("case_features", [])
            if case.get("case_id")
        }
        for item in deep_report.get("items", [])
    }


def aggregate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    returns = [float(row["raw_return"]) for row in rows]
    drawdowns = [float(row["max_drawdown"]) for row in rows]
    symbols = {str(row.get("symbol")) for row in rows if row.get("symbol")}
    entry_months = {str(row.get("entry_date"))[:7] for row in rows if row.get("entry_date")}
    return {
        "tuned_signal_case_count": len(rows),
        "tuned_signal_unique_symbol_count": len(symbols),
        "tuned_signal_entry_month_count": len(entry_months),
        "tuned_signal_win_rate": sum(1 for value in returns if value > 0) / len(returns) if returns else None,
        "tuned_signal_average_return": sum(returns) / len(returns) if returns else None,
        "tuned_signal_max_drawdown": min(drawdowns) if drawdowns else None,
        "tuned_signal_best_return": max(returns) if returns else None,
        "tuned_signal_worst_return": min(returns) if returns else None,
    }


def classify(metrics: dict[str, Any], *, ranking_candidate_allowed: bool = True) -> tuple[str, list[str]]:
    reasons: list[str] = []
    count = int(metrics.get("tuned_signal_case_count") or 0)
    win_rate = metrics.get("tuned_signal_win_rate")
    avg = metrics.get("tuned_signal_average_return")
    drawdown = metrics.get("tuned_signal_max_drawdown")
    if count < THRESHOLDS["min_signal_case_count"]:
        reasons.append("tuned_signal_case_count_below_threshold")
    if win_rate is None or win_rate < THRESHOLDS["min_signal_win_rate"]:
        reasons.append("tuned_signal_win_rate_below_threshold")
    if avg is None or avg <= THRESHOLDS["min_signal_average_return"]:
        reasons.append("tuned_signal_average_return_below_threshold")
    if drawdown is None or drawdown < THRESHOLDS["max_signal_drawdown_floor"]:
        reasons.append("tuned_signal_drawdown_breached")
    if not ranking_candidate_allowed:
        reasons.append("veto_or_diagnostic_only_not_rankable")
    if reasons:
        return "TUNED_EXPERIMENT_FAIL", reasons
    return "TUNED_EXPERIMENT_PASS_CANDIDATE", ["tuned_signal_thresholds_passed"]


def coverage_warnings(metrics: dict[str, Any]) -> list[str]:
    warnings: list[str] = []
    if int(metrics.get("tuned_signal_entry_month_count") or 0) < 2:
        warnings.append("entry_month_coverage_too_narrow_for_ranking")
    if int(metrics.get("tuned_signal_unique_symbol_count") or 0) < 3:
        warnings.append("unique_symbol_coverage_too_narrow_for_ranking")
    return warnings


def baseline_snapshot(maps: dict[str, dict[str, dict[str, Any]]], hypothesis_id: str) -> dict[str, Any]:
    rows = [
        case
        for case in maps.get(hypothesis_id, {}).values()
        if case.get("source_signal_pass")
    ]
    metrics = aggregate(rows)
    return {
        "hypothesis_id": hypothesis_id,
        "signal_case_count": metrics["tuned_signal_case_count"],
        "signal_win_rate": metrics["tuned_signal_win_rate"],
        "signal_average_return": metrics["tuned_signal_average_return"],
        "signal_max_drawdown": metrics["tuned_signal_max_drawdown"],
    }


def feature(case: dict[str, Any]) -> dict[str, Any]:
    return case.get("feature_summary") or {}


def common_case_ids(maps: dict[str, dict[str, dict[str, Any]]], required: list[str]) -> list[str]:
    if not all(hypothesis_id in maps for hypothesis_id in required):
        return []
    return sorted(set.intersection(*(set(maps[hypothesis_id]) for hypothesis_id in required)))


def make_row(primary_case: dict[str, Any], required: list[str], maps: dict[str, dict[str, dict[str, Any]]]) -> dict[str, Any]:
    return {
        "case_id": primary_case.get("case_id"),
        "symbol": primary_case.get("symbol"),
        "entry_date": primary_case.get("entry_date"),
        "raw_return": primary_case.get("raw_return"),
        "max_drawdown": primary_case.get("max_drawdown"),
        "case_result": primary_case.get("case_result"),
        "required_signal_hypotheses": required,
        "feature_hashes": {
            hypothesis_id: maps[hypothesis_id][primary_case["case_id"]].get("feature_hash")
            for hypothesis_id in required
        },
    }


def evaluate_experiments(maps: dict[str, dict[str, dict[str, Any]]]) -> list[dict[str, Any]]:
    defs = [
        {
            "experiment_id": "tuned_a_moneyflow_factor_veto",
            "label": "主力资金 + 因子风险否决",
            "primary": "hyp_a_tushare_capital_flow_accumulation",
            "required": [
                "hyp_a_tushare_capital_flow_accumulation",
                "hyp_a_tushare_factor_liquidity_quality_overlay",
            ],
            "thesis": "主力资金不再单独作为正向信号，必须同时通过流动性、估值和过热护栏。",
            "predicate": lambda cases: all(case.get("source_signal_pass") for case in cases),
            "ranking_candidate_allowed": True,
        },
        {
            "experiment_id": "tuned_a_holder_concentration_strict",
            "label": "股东人数严格下降",
            "primary": "hyp_a_tushare_holder_concentration_improvement",
            "required": ["hyp_a_tushare_holder_concentration_improvement"],
            "thesis": "把股东人数持平从正向信号中剔除，只保留真正环比下降的筹码集中改善。",
            "predicate": lambda cases: bool(cases[0].get("source_signal_pass"))
            and feature(cases[0]).get("holder_num_delta_sign") == 1,
            "ranking_candidate_allowed": True,
        },
        {
            "experiment_id": "tuned_a_institutional_factor_trend_filter",
            "label": "机构持仓净增 + 因子护栏",
            "primary": "hyp_a_tushare_institutional_ownership_stability",
            "required": [
                "hyp_a_tushare_institutional_ownership_stability",
                "hyp_a_tushare_factor_liquidity_quality_overlay",
            ],
            "thesis": "机构持仓稳定太宽，必须 top10 与流通股东同步净增，并通过因子护栏。",
            "predicate": lambda cases: bool(cases[0].get("source_signal_pass"))
            and feature(cases[0]).get("top10_hold_ratio_delta_sign") == 1
            and feature(cases[0]).get("top10_float_ratio_delta_sign") == 1
            and bool(cases[1].get("source_signal_pass")),
            "ranking_candidate_allowed": True,
        },
        {
            "experiment_id": "tuned_a_governance_veto_only",
            "label": "治理/高管激励仅作否决诊断",
            "primary": "hyp_a_tushare_governance_reward_alignment",
            "required": ["hyp_a_tushare_governance_reward_alignment"],
            "thesis": "治理/高管激励不再作为正向选股因子，只评估它是否适合作为风险否决集合。",
            "predicate": lambda cases: bool(cases[0].get("source_signal_pass")),
            "ranking_candidate_allowed": False,
        },
    ]
    items: list[dict[str, Any]] = []
    for definition in defs:
        required = definition["required"]
        selected: list[dict[str, Any]] = []
        for case_id in common_case_ids(maps, required):
            cases = [maps[hypothesis_id][case_id] for hypothesis_id in required]
            if definition["predicate"](cases):
                selected.append(make_row(cases[0], required, maps))
        metrics = aggregate(selected)
        disposition, reasons = classify(
            metrics,
            ranking_candidate_allowed=bool(definition["ranking_candidate_allowed"]),
        )
        baseline = baseline_snapshot(maps, definition["primary"])
        items.append(
            {
                "experiment_id": definition["experiment_id"],
                "label": definition["label"],
                "thesis": definition["thesis"],
                "required_signal_hypotheses": required,
                "baseline": baseline,
                "disposition": disposition,
                "reasons": reasons,
                "coverage_warnings": coverage_warnings(metrics),
                "metrics": metrics,
                "case_features": selected,
                "allowed_next_step": "candidate_for_codex_reviewed_refined_sandbox"
                if disposition == "TUNED_EXPERIMENT_PASS_CANDIDATE"
                else "do_not_rank_rework_signal_or_collect_more_cases",
                "simulation_only": True,
                "user_facing_suggestion_allowed": False,
                "ranking_impact_allowed": False,
                "real_trade_allowed": False,
            }
        )
    return items


def build_report(deep_report: dict[str, Any], *, run_id: str, command: str) -> dict[str, Any]:
    before = fingerprints()
    maps = deep_maps(deep_report)
    items = evaluate_experiments(maps)
    pass_count = sum(1 for item in items if item["disposition"] == "TUNED_EXPERIMENT_PASS_CANDIDATE")
    after = fingerprints()
    report = {
        "type": "a_share_signal_tuning_experiments",
        "status": "PASS" if deep_report.get("status") == "PASS" and items else "BLOCKED_NO_DEEP_SANDBOX",
        "generated_at": now_iso(),
        "run_id": run_id,
        "command": command,
        "thresholds": THRESHOLDS,
        "summary": {
            "tuned_experiment_count": len(items),
            "tuned_pass_candidate_count": pass_count,
            "tuned_fail_count": sum(1 for item in items if item["disposition"] == "TUNED_EXPERIMENT_FAIL"),
            "ranking_impact_allowed": False,
            "user_facing_suggestion_allowed": False,
            "network_used": False,
            "next_stage": "Pass candidates still require Codex-reviewed refined sandbox and ranking gate; no automatic recommendation impact.",
        },
        "items": items,
        "source_reports": {"source_deep_sandbox": str(DEEP_JSON)},
        "source_hashes": {"source_deep_sandbox": sha256(DEEP_JSON)},
        "checks": {
            "source_deep_sandbox_pass": deep_report.get("status") == "PASS",
            "experiments_evaluated": len(items) == 4,
            "raw_payload_saved": False,
            "network_not_used": True,
            "production_records_unchanged": before == after,
            "ranking_impact_allowed": False,
            "user_facing_suggestion_allowed": False,
            "no_broker_api": True,
            "no_webhook": True,
            "no_order_placement": True,
            "no_position_size": True,
        },
        "safety": {
            "simulation_only": True,
            "research_only": True,
            "derived_features_only": True,
            "raw_payload_saved": False,
            "network_used": False,
            "requires_separate_ranking_gate_before_ranking": True,
            "ranking_impact_allowed": False,
            "user_facing_suggestion_allowed": False,
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
        checks["source_deep_sandbox_pass"]
        and checks["experiments_evaluated"]
        and checks["raw_payload_saved"] is False
        and checks["network_not_used"]
        and checks["production_records_unchanged"]
        and checks["ranking_impact_allowed"] is False
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
        "# A-share Signal Tuning Experiments",
        "",
        f"- Status: `{report['status']}`",
        f"- Generated At: `{report['generated_at']}`",
        f"- Experiments: `{report['summary']['tuned_experiment_count']}`",
        f"- Pass Candidates: `{report['summary']['tuned_pass_candidate_count']}`",
        f"- Fail: `{report['summary']['tuned_fail_count']}`",
        "- Boundary: derived features only; no raw payload, no broker, no order, no trading webhook, no ranking impact.",
        "",
        "## Results",
        "",
        "| Experiment | Disposition | Cases | Win Rate | Avg Return | Max Drawdown | Reasons |",
        "| --- | --- | ---: | ---: | ---: | ---: | --- |",
    ]
    for item in report.get("items", []):
        metrics = item.get("metrics") or {}
        win = metrics.get("tuned_signal_win_rate")
        avg = metrics.get("tuned_signal_average_return")
        dd = metrics.get("tuned_signal_max_drawdown")
        lines.append(
            "| "
            + " | ".join(
                [
                    f"`{item['experiment_id']}`",
                    f"`{item['disposition']}`",
                    str(metrics.get("tuned_signal_case_count")),
                    "" if win is None else f"{win:.2f}",
                    "" if avg is None else f"{avg:.4f}",
                    "" if dd is None else f"{dd:.4f}",
                    ", ".join(item.get("reasons", [])),
                ]
            )
            + " |"
        )
    return "\n".join(lines) + "\n"


def write_outputs(report: dict[str, Any], run_id: str) -> dict[str, str]:
    REPORTS.mkdir(parents=True, exist_ok=True)
    run_dir = PROCESSED / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    run_json = run_dir / "a_share_signal_tuning_experiments.json"
    run_md = run_dir / "a_share_signal_tuning_experiments.md"
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
                f"tuned_experiment_count={report['summary']['tuned_experiment_count']}",
                f"tuned_pass_candidate_count={report['summary']['tuned_pass_candidate_count']}",
                f"tuned_fail_count={report['summary']['tuned_fail_count']}",
                f"network_used={str(report['summary'].get('network_used')).lower()}",
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
    return {"run_json": str(run_json), "run_md": str(run_md), "latest_json": str(OUT_JSON), "latest_md": str(OUT_MD), "marker": str(marker)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Evaluate A-share signal tuning experiments from derived features.")
    parser.add_argument("--deep-json", type=Path, default=DEEP_JSON)
    parser.add_argument("--run-id", default=f"a_share_signal_tuning_experiments_{datetime.now().strftime('%Y%m%dT%H%M%S')}")
    args = parser.parse_args(argv)
    command = " ".join(sys.argv)
    deep_report = load_json(args.deep_json, {})
    report = build_report(deep_report, run_id=args.run_id, command=command)
    outputs = write_outputs(report, args.run_id)
    print(json.dumps({"status": report["status"], "summary": report["summary"], "outputs": outputs}, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
