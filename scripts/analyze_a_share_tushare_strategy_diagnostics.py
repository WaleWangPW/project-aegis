#!/usr/bin/env python3
"""Explain why A-share Tushare source strategies are not rankable yet.

This is a no-network diagnostic layer for stock-agent. It reads existing proxy,
feature coverage, and deep sandbox reports, then emits compact next actions.
It never changes candidate ranking and never creates trading records.
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
REPORTS = ROOT / "data" / "reports"
PROCESSED = ROOT / "data" / "processed" / "a_share_tushare_strategy_diagnostics"

PROXY_JSON = REPORTS / "a_share_tushare_source_hypothesis_evaluation_latest.json"
FEATURE_JSON = REPORTS / "a_share_tushare_source_feature_coverage_latest.json"
DEEP_JSON = REPORTS / "a_share_tushare_source_deep_sandbox_latest.json"
CASES_JSON = REPORTS / "aegis_strategy_specific_historical_cases_latest.json"
OUT_JSON = REPORTS / "a_share_tushare_strategy_diagnostics_latest.json"
OUT_MD = REPORTS / "a_share_tushare_strategy_diagnostics_latest.md"
PASS_MARKER = REPORTS / "A_SHARE_TUSHARE_STRATEGY_DIAGNOSTICS_PASS.marker"

THRESHOLDS = {
    "minimum_rankable_win_rate": 0.50,
    "minimum_rankable_average_return": 0.0,
    "maximum_rankable_drawdown_floor": -0.18,
    "minimum_signal_case_count_for_tuning": 8,
}

REASON_TEXT = {
    "source_signal_win_rate_below_threshold": "源信号命中后的胜率低于门槛",
    "source_signal_average_return_below_threshold": "源信号命中后的平均收益不达标",
    "source_signal_drawdown_breached": "源信号命中后的最大回撤过深",
    "source_signal_case_count_below_threshold": "源信号命中样本不足",
}

HYPOTHESIS_LABELS = {
    "hyp_a_tushare_capital_flow_accumulation": "主力资金流向",
    "hyp_a_tushare_dragon_tiger_seat_confirmation": "龙虎榜/游资席位",
    "hyp_a_tushare_institutional_ownership_stability": "机构持仓稳定",
    "hyp_a_tushare_holder_concentration_improvement": "股东人数/筹码集中",
    "hyp_a_tushare_factor_liquidity_quality_overlay": "因子+流动性质量",
    "hyp_a_tushare_governance_reward_alignment": "治理/高管激励",
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


def pct(value: Any) -> str:
    return "N/A" if value is None else f"{float(value) * 100:.1f}%"


def reason_text(reasons: list[str]) -> list[str]:
    return [REASON_TEXT.get(reason, reason) for reason in reasons]


def metric_gaps(metrics: dict[str, Any]) -> dict[str, Any]:
    win_rate = metrics.get("source_signal_win_rate")
    average_return = metrics.get("source_signal_average_return")
    drawdown = metrics.get("source_signal_max_drawdown")
    case_count = int(metrics.get("source_signal_case_count") or 0)
    return {
        "signal_case_gap": max(0, THRESHOLDS["minimum_signal_case_count_for_tuning"] - case_count),
        "win_rate_gap": None if win_rate is None else max(0.0, THRESHOLDS["minimum_rankable_win_rate"] - float(win_rate)),
        "average_return_gap": None
        if average_return is None
        else max(0.0, THRESHOLDS["minimum_rankable_average_return"] - float(average_return)),
        "drawdown_excess": None
        if drawdown is None
        else max(0.0, THRESHOLDS["maximum_rankable_drawdown_floor"] - float(drawdown)),
    }


def next_action_for_deep_item(item: dict[str, Any]) -> tuple[str, str]:
    metrics = item.get("metrics") or {}
    count = int(metrics.get("source_signal_case_count") or 0)
    signal_rate = metrics.get("source_signal_rate")
    win_rate = metrics.get("source_signal_win_rate")
    avg = metrics.get("source_signal_average_return")
    drawdown = metrics.get("source_signal_max_drawdown")
    if count < THRESHOLDS["minimum_signal_case_count_for_tuning"]:
        return (
            "collect_more_signal_cases",
            "源信号命中样本偏少，先扩大 A股历史样本，再谈调参。",
        )
    if signal_rate is not None and float(signal_rate) > 0.70 and win_rate is not None and float(win_rate) < 0.35:
        return (
            "tighten_signal_definition",
            "信号太宽，几乎什么都能命中但胜率低，应增加趋势/估值/回撤过滤。",
        )
    if avg is not None and float(avg) < 0 and drawdown is not None and float(drawdown) < -0.25:
        return (
            "add_risk_veto_before_retest",
            "信号命中后平均收益为负且回撤深，应先叠加风险否决再重测。",
        )
    return (
        "rework_hypothesis",
        "当前源特征没有证明增益，先重写假设，不进入 ranking gate。",
    )


def feature_gap_actions(feature: dict[str, Any]) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    for item in feature.get("items", []):
        if item.get("feature_status") == "READY_FOR_DEEP_SANDBOX":
            continue
        actions.append(
            {
                "hypothesis_id": item.get("hypothesis_id"),
                "label": HYPOTHESIS_LABELS.get(item.get("hypothesis_id"), item.get("title")),
                "status": item.get("feature_status"),
                "required_endpoints": item.get("required_endpoints") or [],
                "eligible_symbol_count": len(item.get("eligible_symbols") or []),
                "recommended_action": "collect_endpoint_history",
                "why": "当前 historical cases 对这些 endpoint 没有足够覆盖，不能判断策略可行性。",
                "stock_agent_task": "扩大含 top_list/top_inst 命中的 A股样本，优先收集最近上榜且有 20 日后验价格的 case。",
            }
        )
    return actions


def summarize_deep_items(deep: dict[str, Any]) -> list[dict[str, Any]]:
    diagnostics: list[dict[str, Any]] = []
    for item in deep.get("items", []):
        metrics = item.get("metrics") or {}
        action, why = next_action_for_deep_item(item)
        diagnostics.append(
            {
                "hypothesis_id": item.get("hypothesis_id"),
                "label": HYPOTHESIS_LABELS.get(item.get("hypothesis_id"), item.get("title")),
                "disposition": item.get("disposition"),
                "plain_reasons": reason_text(item.get("reasons") or []),
                "required_endpoints": item.get("required_endpoints") or [],
                "metrics": {
                    "eligible_case_count": metrics.get("eligible_case_count"),
                    "source_signal_case_count": metrics.get("source_signal_case_count"),
                    "source_signal_rate": metrics.get("source_signal_rate"),
                    "source_signal_win_rate": metrics.get("source_signal_win_rate"),
                    "source_signal_average_return": metrics.get("source_signal_average_return"),
                    "source_signal_max_drawdown": metrics.get("source_signal_max_drawdown"),
                },
                "metric_gaps": metric_gaps(metrics),
                "recommended_action": action,
                "why": why,
                "ranking_gate_allowed": item.get("disposition") == "DEEP_SANDBOX_PASS_CANDIDATE",
                "user_facing_suggestion_allowed": False,
            }
        )
    return diagnostics


def build_report(proxy: dict[str, Any], feature: dict[str, Any], deep: dict[str, Any], cases: dict[str, Any]) -> dict[str, Any]:
    deep_diagnostics = summarize_deep_items(deep)
    gap_actions = feature_gap_actions(feature)
    ranking_allowed = any(item.get("ranking_gate_allowed") for item in deep_diagnostics)
    priority_actions = gap_actions + [
        item
        for item in sorted(
            deep_diagnostics,
            key=lambda row: (
                row["recommended_action"] != "tighten_signal_definition",
                row["recommended_action"] != "add_risk_veto_before_retest",
                row["label"] or "",
            ),
        )
        if item["recommended_action"] in {"tighten_signal_definition", "add_risk_veto_before_retest", "collect_more_signal_cases"}
    ]
    report = {
        "type": "a_share_tushare_strategy_diagnostics",
        "status": "PASS",
        "generated_at": now_iso(),
        "summary": {
            "a_share_case_count": cases.get("summary", {}).get("a_share_case_count"),
            "proxy_pass_count": proxy.get("summary", {}).get("proxy_pass_count"),
            "proxy_fail_count": proxy.get("summary", {}).get("proxy_fail_count"),
            "ready_for_deep_sandbox_count": feature.get("summary", {}).get("ready_for_deep_sandbox_count"),
            "feature_gap_count": feature.get("summary", {}).get("feature_gap_count"),
            "deep_sandbox_pass_candidate_count": deep.get("summary", {}).get("deep_sandbox_pass_candidate_count"),
            "deep_sandbox_fail_count": deep.get("summary", {}).get("deep_sandbox_fail_count"),
            "rankable_strategy_count": sum(1 for item in deep_diagnostics if item["ranking_gate_allowed"]),
            "priority_action_count": len(priority_actions),
            "ranking_impact_allowed": False,
            "user_facing_suggestion_allowed": False,
            "next_stage": "stock-agent should collect feature-gap samples first, then retest tightened signals before ranking gate.",
        },
        "priority_actions": priority_actions[:6],
        "feature_gap_actions": gap_actions,
        "deep_diagnostics": deep_diagnostics,
        "source_reports": {
            "proxy_evaluation": str(PROXY_JSON),
            "feature_coverage": str(FEATURE_JSON),
            "deep_sandbox": str(DEEP_JSON),
            "historical_cases": str(CASES_JSON),
        },
        "source_hashes": {
            "proxy_evaluation": sha256(PROXY_JSON),
            "feature_coverage": sha256(FEATURE_JSON),
            "deep_sandbox": sha256(DEEP_JSON),
            "historical_cases": sha256(CASES_JSON),
        },
        "checks": {
            "proxy_report_pass": proxy.get("status") == "PASS",
            "feature_report_pass": feature.get("status") == "PASS",
            "deep_report_pass": deep.get("status") == "PASS",
            "a_share_cases_present": (cases.get("summary", {}).get("a_share_case_count") or 0) > 0,
            "ranking_gate_blocked_when_no_pass_candidate": (
                ranking_allowed or deep.get("summary", {}).get("deep_sandbox_pass_candidate_count") == 0
            ),
            "no_network_used": True,
            "no_raw_payload_saved": True,
            "no_broker_api": True,
            "no_webhook": True,
            "no_order_placement": True,
        },
        "safety": {
            "simulation_only": True,
            "research_only": True,
            "diagnostic_only": True,
            "ranking_impact_allowed": False,
            "user_facing_suggestion_allowed": False,
            "no_broker_api": True,
            "no_order_placement": True,
            "no_trading_webhook": True,
            "real_trade_allowed": False,
        },
    }
    if not all(report["checks"].values()):
        report["status"] = "FAIL"
    return report


def render_markdown(report: dict[str, Any]) -> str:
    s = report["summary"]
    lines = [
        "# A-share Tushare Strategy Diagnostics",
        "",
        f"- Status: `{report['status']}`",
        f"- Generated At: `{report['generated_at']}`",
        f"- A-share Cases: `{s.get('a_share_case_count')}`",
        f"- Rankable Strategies: `{s.get('rankable_strategy_count')}`",
        f"- Feature Gaps: `{s.get('feature_gap_count')}`",
        f"- Deep Sandbox Fail: `{s.get('deep_sandbox_fail_count')}`",
        "- Boundary: diagnostic only; no ranking impact, no broker, no order, no trading webhook.",
        "",
        "## Priority Actions",
        "",
    ]
    for item in report["priority_actions"]:
        lines.append(
            f"- **{item.get('label')}**: `{item.get('recommended_action')}` - {item.get('why') or item.get('stock_agent_task')}"
        )
    lines.extend(
        [
            "",
            "## Deep Diagnostics",
            "",
            "| Strategy | Signal Cases | Win Rate | Avg Return | Max Drawdown | Action |",
            "| --- | ---: | ---: | ---: | ---: | --- |",
        ]
    )
    for item in report["deep_diagnostics"]:
        m = item["metrics"]
        lines.append(
            "| "
            + " | ".join(
                [
                    str(item["label"]),
                    str(m.get("source_signal_case_count")),
                    pct(m.get("source_signal_win_rate")),
                    pct(m.get("source_signal_average_return")),
                    pct(m.get("source_signal_max_drawdown")),
                    str(item["recommended_action"]),
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
    run_json = run_dir / "a_share_tushare_strategy_diagnostics.json"
    run_md = run_dir / "a_share_tushare_strategy_diagnostics.md"
    write_json(run_json, report)
    run_md.write_text(render_markdown(report), encoding="utf-8")
    write_json(OUT_JSON, report)
    OUT_MD.write_text(render_markdown(report), encoding="utf-8")
    PASS_MARKER.write_text(
        "\n".join(
            [
                f"status={report['status']}",
                f"generated_at={report['generated_at']}",
                f"report_json={OUT_JSON}",
                f"report_json_sha256={sha256(OUT_JSON)}",
                f"rankable_strategy_count={report['summary']['rankable_strategy_count']}",
                f"priority_action_count={report['summary']['priority_action_count']}",
                "ranking_impact_allowed=false",
                "user_facing_suggestion_allowed=false",
                "no_network_used=true",
                "no_real_trade=true",
                "no_broker_api=true",
                "no_webhook=true",
                "no_order_placement=true",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return {"run_json": str(run_json), "run_md": str(run_md), "latest_json": str(OUT_JSON), "latest_md": str(OUT_MD), "marker": str(PASS_MARKER)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Analyze A-share Tushare strategy diagnostics.")
    parser.add_argument("--proxy-json", type=Path, default=PROXY_JSON)
    parser.add_argument("--feature-json", type=Path, default=FEATURE_JSON)
    parser.add_argument("--deep-json", type=Path, default=DEEP_JSON)
    parser.add_argument("--cases-json", type=Path, default=CASES_JSON)
    parser.add_argument("--run-id", default=f"a_share_tushare_strategy_diagnostics_{datetime.now().strftime('%Y%m%dT%H%M%S')}")
    args = parser.parse_args(argv)
    report = build_report(
        load_json(args.proxy_json, {}),
        load_json(args.feature_json, {}),
        load_json(args.deep_json, {}),
        load_json(args.cases_json, {}),
    )
    outputs = write_outputs(report, args.run_id)
    print(json.dumps({"status": report["status"], "summary": report["summary"], "outputs": outputs}, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
