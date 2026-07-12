#!/usr/bin/env python3
"""Retest A-share Tushare source strategies with risk-veto combinations.

This layer consumes the derived-feature deep sandbox report and evaluates
simple combinations such as moneyflow + holder concentration. It does not call
Tushare, does not store raw payloads, and does not create user-facing
recommendations. Passing combinations are only candidates for a later ranking
gate review.
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
PROCESSED = ROOT / "data" / "processed" / "a_share_tushare_refined_strategy_sandbox"
DEEP_JSON = REPORTS / "a_share_tushare_source_deep_sandbox_latest.json"
OUT_JSON = REPORTS / "a_share_tushare_refined_strategy_sandbox_latest.json"
OUT_MD = REPORTS / "a_share_tushare_refined_strategy_sandbox_latest.md"
PASS_MARKER = REPORTS / "A_SHARE_TUSHARE_REFINED_STRATEGY_SANDBOX_PASS.marker"
BLOCKED_MARKER = REPORTS / "A_SHARE_TUSHARE_REFINED_STRATEGY_SANDBOX_BLOCKED.marker"

THRESHOLDS = {
    "min_signal_case_count": 2,
    "min_signal_win_rate": 0.50,
    "min_signal_average_return": 0.0,
    "max_signal_drawdown_floor": -0.18,
}

COMBINATIONS = [
    {
        "refined_strategy_id": "refined_a_moneyflow_holder_concentration",
        "label": "主力资金 + 筹码集中",
        "primary": "hyp_a_tushare_capital_flow_accumulation",
        "guardrails": ["hyp_a_tushare_holder_concentration_improvement"],
        "thesis": "主力资金单独信号太噪；只有同时出现股东人数/筹码集中改善时，才作为下一轮 ranking gate 候选。",
    },
    {
        "refined_strategy_id": "refined_a_moneyflow_factor_veto",
        "label": "主力资金 + 因子风险否决",
        "primary": "hyp_a_tushare_capital_flow_accumulation",
        "guardrails": ["hyp_a_tushare_factor_liquidity_quality_overlay"],
        "thesis": "资金流入必须叠加流动性、估值不过热和日内不过热，避免把追涨资金当作积累。",
    },
    {
        "refined_strategy_id": "refined_a_holder_factor_veto",
        "label": "筹码集中 + 因子风险否决",
        "primary": "hyp_a_tushare_holder_concentration_improvement",
        "guardrails": ["hyp_a_tushare_factor_liquidity_quality_overlay"],
        "thesis": "筹码集中只能作为辅助；需要流动性和估值/过热护栏确认。",
    },
    {
        "refined_strategy_id": "refined_a_institutional_factor_veto",
        "label": "机构持仓 + 因子风险否决",
        "primary": "hyp_a_tushare_institutional_ownership_stability",
        "guardrails": ["hyp_a_tushare_factor_liquidity_quality_overlay"],
        "thesis": "机构持仓稳定太宽，必须叠加因子护栏后再验证。",
    },
    {
        "refined_strategy_id": "refined_a_moneyflow_holder_factor",
        "label": "主力资金 + 筹码集中 + 因子",
        "primary": "hyp_a_tushare_capital_flow_accumulation",
        "guardrails": [
            "hyp_a_tushare_holder_concentration_improvement",
            "hyp_a_tushare_factor_liquidity_quality_overlay",
        ],
        "thesis": "最严格组合，样本可能偏少；只用于观察过拟合风险。",
    },
]


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


def case_maps(deep_report: dict[str, Any]) -> dict[str, dict[str, dict[str, Any]]]:
    maps: dict[str, dict[str, dict[str, Any]]] = {}
    for item in deep_report.get("items", []):
        maps[item.get("hypothesis_id")] = {
            case.get("case_id"): case
            for case in item.get("case_features", [])
            if case.get("case_id")
        }
    return maps


def aggregate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    returns = [float(row["raw_return"]) for row in rows]
    drawdowns = [float(row["max_drawdown"]) for row in rows]
    return {
        "refined_signal_case_count": len(rows),
        "refined_signal_win_rate": sum(1 for value in returns if value > 0) / len(returns) if returns else None,
        "refined_signal_average_return": sum(returns) / len(returns) if returns else None,
        "refined_signal_max_drawdown": min(drawdowns) if drawdowns else None,
        "refined_signal_best_return": max(returns) if returns else None,
        "refined_signal_worst_return": min(returns) if returns else None,
    }


def classify(metrics: dict[str, Any]) -> tuple[str, list[str]]:
    reasons: list[str] = []
    count = int(metrics.get("refined_signal_case_count") or 0)
    win_rate = metrics.get("refined_signal_win_rate")
    avg = metrics.get("refined_signal_average_return")
    drawdown = metrics.get("refined_signal_max_drawdown")
    if count < THRESHOLDS["min_signal_case_count"]:
        reasons.append("refined_signal_case_count_below_threshold")
    if win_rate is None or win_rate < THRESHOLDS["min_signal_win_rate"]:
        reasons.append("refined_signal_win_rate_below_threshold")
    if avg is None or avg <= THRESHOLDS["min_signal_average_return"]:
        reasons.append("refined_signal_average_return_below_threshold")
    if drawdown is None or drawdown < THRESHOLDS["max_signal_drawdown_floor"]:
        reasons.append("refined_signal_drawdown_breached")
    if reasons:
        return "REFINED_SANDBOX_FAIL", reasons
    return "REFINED_SANDBOX_PASS_CANDIDATE", ["refined_signal_thresholds_passed"]


def evaluate_combination(defn: dict[str, Any], maps: dict[str, dict[str, dict[str, Any]]]) -> dict[str, Any]:
    required = [defn["primary"], *defn.get("guardrails", [])]
    available = [hypothesis_id for hypothesis_id in required if hypothesis_id in maps]
    if len(available) != len(required):
        metrics = aggregate([])
        return {
            **defn,
            "disposition": "REFINED_SANDBOX_BLOCKED",
            "reasons": ["missing_required_deep_sandbox_features"],
            "metrics": metrics,
            "case_features": [],
            "simulation_only": True,
            "user_facing_suggestion_allowed": False,
            "real_trade_allowed": False,
        }
    common_ids = set.intersection(*(set(maps[hypothesis_id].keys()) for hypothesis_id in required))
    rows: list[dict[str, Any]] = []
    for case_id in sorted(common_ids):
        if all(maps[hypothesis_id][case_id].get("source_signal_pass") for hypothesis_id in required):
            primary_case = maps[defn["primary"]][case_id]
            rows.append(
                {
                    "case_id": case_id,
                    "symbol": primary_case.get("symbol"),
                    "entry_date": primary_case.get("entry_date"),
                    "raw_return": primary_case.get("raw_return"),
                    "max_drawdown": primary_case.get("max_drawdown"),
                    "case_result": primary_case.get("case_result"),
                    "required_signal_hypotheses": required,
                    "feature_hashes": {
                        hypothesis_id: maps[hypothesis_id][case_id].get("feature_hash")
                        for hypothesis_id in required
                    },
                }
            )
    metrics = aggregate(rows)
    disposition, reasons = classify(metrics)
    return {
        **defn,
        "required_signal_hypotheses": required,
        "disposition": disposition,
        "reasons": reasons,
        "metrics": metrics,
        "case_features": rows,
        "allowed_next_step": "candidate_for_separate_ranking_gate_review"
        if disposition == "REFINED_SANDBOX_PASS_CANDIDATE"
        else "do_not_rank_rework_or_collect_more_cases",
        "simulation_only": True,
        "user_facing_suggestion_allowed": False,
        "ranking_impact_allowed": False,
        "real_trade_allowed": False,
    }


def build_report(deep_report: dict[str, Any], *, run_id: str, command: str) -> dict[str, Any]:
    before = fingerprints()
    maps = case_maps(deep_report)
    items = [evaluate_combination(defn, maps) for defn in COMBINATIONS]
    pass_count = sum(1 for item in items if item["disposition"] == "REFINED_SANDBOX_PASS_CANDIDATE")
    after = fingerprints()
    report = {
        "type": "a_share_tushare_refined_strategy_sandbox",
        "status": "PASS" if items else "BLOCKED_NO_DEEP_SANDBOX_ITEMS",
        "generated_at": now_iso(),
        "run_id": run_id,
        "command": command,
        "thresholds": THRESHOLDS,
        "summary": {
            "refined_strategy_count": len(items),
            "refined_sandbox_pass_candidate_count": pass_count,
            "refined_sandbox_fail_count": sum(1 for item in items if item["disposition"] == "REFINED_SANDBOX_FAIL"),
            "refined_sandbox_blocked_count": sum(1 for item in items if item["disposition"] == "REFINED_SANDBOX_BLOCKED"),
            "ranking_impact_allowed": False,
            "user_facing_suggestion_allowed": False,
            "network_used": False,
            "next_stage": "Only pass candidates may be reviewed by a separate ranking gate; no automatic recommendation impact.",
        },
        "items": items,
        "source_reports": {
            "source_deep_sandbox": str(DEEP_JSON),
        },
        "source_hashes": {
            "source_deep_sandbox": sha256(DEEP_JSON),
        },
        "checks": {
            "source_deep_sandbox_pass": deep_report.get("status") == "PASS",
            "refined_strategies_evaluated": len(items) == len(COMBINATIONS),
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
        and checks["refined_strategies_evaluated"]
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
        "# A-share Tushare Refined Strategy Sandbox",
        "",
        f"- Status: `{report['status']}`",
        f"- Generated At: `{report['generated_at']}`",
        f"- Refined Strategies: `{report['summary']['refined_strategy_count']}`",
        f"- Pass Candidates: `{report['summary']['refined_sandbox_pass_candidate_count']}`",
        f"- Ranking Impact Allowed: `{report['summary']['ranking_impact_allowed']}`",
        "- Boundary: derived features only; no raw payload, no broker, no order, no trading webhook, no ranking impact.",
        "",
        "| Strategy | Disposition | Cases | Win Rate | Avg Return | Max Drawdown | Reasons |",
        "| --- | --- | ---: | ---: | ---: | ---: | --- |",
    ]
    for item in report.get("items", []):
        metrics = item.get("metrics") or {}
        win = metrics.get("refined_signal_win_rate")
        avg = metrics.get("refined_signal_average_return")
        dd = metrics.get("refined_signal_max_drawdown")
        lines.append(
            "| "
            + " | ".join(
                [
                    f"`{item['refined_strategy_id']}` {item['label']}",
                    f"`{item['disposition']}`",
                    str(metrics.get("refined_signal_case_count")),
                    "" if win is None else f"{win:.2f}",
                    "" if avg is None else f"{avg:.4f}",
                    "" if dd is None else f"{dd:.4f}",
                    ", ".join(item.get("reasons", [])),
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
    run_json = run_dir / "a_share_tushare_refined_strategy_sandbox.json"
    run_md = run_dir / "a_share_tushare_refined_strategy_sandbox.md"
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
                f"refined_strategy_count={report['summary']['refined_strategy_count']}",
                f"refined_sandbox_pass_candidate_count={report['summary']['refined_sandbox_pass_candidate_count']}",
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
    return {"run_json": str(run_json), "run_md": str(run_md), "latest_json": str(OUT_JSON), "latest_md": str(OUT_MD), "marker": str(marker)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Evaluate refined A-share Tushare source strategy combinations.")
    parser.add_argument("--deep-json", type=Path, default=DEEP_JSON)
    parser.add_argument("--run-id", default=f"a_share_tushare_refined_strategy_sandbox_{datetime.now().strftime('%Y%m%dT%H%M%S')}")
    args = parser.parse_args(argv)
    command = " ".join(sys.argv)
    deep_report = load_json(args.deep_json, {})
    report = build_report(deep_report, run_id=args.run_id, command=command)
    outputs = write_outputs(report, args.run_id)
    print(json.dumps({"status": report["status"], "summary": report["summary"], "outputs": outputs}, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
