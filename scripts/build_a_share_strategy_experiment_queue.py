#!/usr/bin/env python3
"""Build the next stock-agent A-share strategy experiment queue.

This report converts current sandbox failures into bounded experiments for the
OpenClaw stock-agent. It is planning metadata only: no recommendations, no
paper trades, no broker calls, no webhooks, and no raw Tushare payloads.
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
PROCESSED = ROOT / "data" / "processed" / "a_share_strategy_experiment_queue"

SOURCE_PROBE = REPORTS / "a_share_tushare_strategy_source_probe_latest.json"
DRAGON_TIGER = REPORTS / "a_share_dragon_tiger_research_samples_latest.json"
CASES = REPORTS / "aegis_strategy_specific_historical_cases_latest.json"
FEATURE = REPORTS / "a_share_tushare_source_feature_coverage_latest.json"
DEEP = REPORTS / "a_share_tushare_source_deep_sandbox_latest.json"
REFINED = REPORTS / "a_share_tushare_refined_strategy_sandbox_latest.json"
TUNED = REPORTS / "a_share_signal_tuning_experiments_latest.json"
RANKING_GATE = REPORTS / "a_share_refined_strategy_ranking_gate_latest.json"
DIAGNOSTICS = REPORTS / "a_share_tushare_strategy_diagnostics_latest.json"

OUT_JSON = REPORTS / "a_share_strategy_experiment_queue_latest.json"
OUT_MD = REPORTS / "a_share_strategy_experiment_queue_latest.md"
PASS_MARKER = REPORTS / "A_SHARE_STRATEGY_EXPERIMENT_QUEUE_PASS.marker"


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


def module_rows(probe: dict[str, Any], module_id: str) -> list[dict[str, Any]]:
    return [item for item in probe.get("modules", []) if item.get("module_id") == module_id]


def module_status(probe: dict[str, Any], module_id: str) -> dict[str, Any]:
    rows = module_rows(probe, module_id)
    statuses = {str(item.get("endpoint")): item.get("status") for item in rows}
    return {
        "module_id": module_id,
        "endpoints": statuses,
        "pass_count": sum(1 for status in statuses.values() if status == "PASS"),
        "empty_count": sum(1 for status in statuses.values() if status == "EMPTY"),
        "error_count": sum(1 for status in statuses.values() if status == "ERROR"),
    }


def first_deep_item(deep: dict[str, Any], hypothesis_id: str) -> dict[str, Any] | None:
    return next((item for item in deep.get("items", []) if item.get("hypothesis_id") == hypothesis_id), None)


def metric_snapshot(item: dict[str, Any] | None) -> dict[str, Any]:
    if not item:
        return {}
    metrics = item.get("metrics") or {}
    return {
        "disposition": item.get("disposition"),
        "reasons": item.get("reasons") or [],
        "signal_cases": metrics.get("source_signal_case_count"),
        "signal_win_rate": metrics.get("source_signal_win_rate"),
        "signal_average_return": metrics.get("source_signal_average_return"),
        "signal_max_drawdown": metrics.get("source_signal_max_drawdown"),
    }


def base_task(
    *,
    experiment_id: str,
    label: str,
    priority: int,
    status: str,
    trigger: str,
    target: str,
    evidence: dict[str, Any],
    success_metric: str,
    next_command: str | None = None,
    proposed_command: str | None = None,
) -> dict[str, Any]:
    return {
        "experiment_id": experiment_id,
        "label": label,
        "priority": priority,
        "status": status,
        "runner": "openclaw_stock_agent",
        "trigger": trigger,
        "target": target,
        "evidence": evidence,
        "next_command": next_command,
        "proposed_command_if_implemented": proposed_command,
        "success_metric": success_metric,
        "ranking_impact_allowed": False,
        "user_facing_suggestion_allowed": False,
        "real_trade_allowed": False,
    }


def build_tasks(
    probe: dict[str, Any],
    dragon: dict[str, Any],
    cases: dict[str, Any],
    feature: dict[str, Any],
    deep: dict[str, Any],
    refined: dict[str, Any],
    tuned: dict[str, Any],
    ranking_gate: dict[str, Any],
    diagnostics: dict[str, Any],
) -> list[dict[str, Any]]:
    tasks: list[dict[str, Any]] = []
    dragon_summary = dragon.get("summary") or {}
    case_summary = cases.get("summary") or {}
    feature_summary = feature.get("summary") or {}
    refined_summary = refined.get("summary") or {}
    tuned_summary = tuned.get("summary") or {}
    ranking_summary = ranking_gate.get("summary") or {}

    tasks.append(
        base_task(
            experiment_id="exp_a_dragon_tiger_event_signal_split",
            label="龙虎榜/游资事件分型",
            priority=1,
            status="READY_EXISTING_DATA",
            trigger="已有扩样本进入 managed cycle，但还没有把净买入、换手、席位拥挤拆成独立策略假设。",
            target="把 24 个样本 / 72 个事件 / 36 个事件对齐 case 拆成正净买入、负净买入、机构席位、拥挤换手等子实验。",
            evidence={
                "dragon_tiger_sample_count": dragon_summary.get("sample_count"),
                "dragon_tiger_event_count": dragon_summary.get("event_count"),
                "event_aligned_case_count": case_summary.get("a_share_dragon_tiger_research_sample_case_count"),
            },
            next_command="make stock-agent-a-share-strategy-cycle-managed-expanded",
            success_metric="生成至少 2 个可单独评估的龙虎榜子策略，并继续保持 ranking_gate_approved_count=0 直到单独 gate 通过。",
        )
    )

    holder_item = next(
        (item for item in feature.get("items", []) if item.get("hypothesis_id") == "hyp_a_tushare_holder_concentration_improvement"),
        {},
    )
    tasks.append(
        base_task(
            experiment_id="exp_a_holder_concentration_coverage_backfill",
            label="股东人数/筹码集中覆盖补齐",
            priority=2,
            status="READY_BACKFILL",
            trigger="股东人数覆盖率刚过 ready 门槛，但缺口仍大，组合策略缺稳定 guardrail。",
            target="提高 stk_holdernumber 在 A股 historical cases 上的覆盖率，减少 missing/blocked cases。",
            evidence={
                "eligible_case_count": holder_item.get("eligible_case_count"),
                "min_endpoint_coverage": holder_item.get("min_endpoint_coverage"),
                "endpoint_results": holder_item.get("endpoint_results"),
            },
            next_command="make stock-agent-a-share-strategy-cycle-managed-expanded",
            success_metric="stk_holdernumber coverage > 0.70，并能为 refined 组合提供非空 case_features。",
        )
    )

    for hypothesis_id, label in [
        ("hyp_a_tushare_institutional_ownership_stability", "机构持仓稳定信号收窄"),
        ("hyp_a_tushare_governance_reward_alignment", "治理/高管激励改为否决信号"),
    ]:
        snapshot = metric_snapshot(first_deep_item(deep, hypothesis_id))
        tasks.append(
            base_task(
                experiment_id=f"exp_a_{hypothesis_id.replace('hyp_a_tushare_', '')}_tighten",
                label=label,
                priority=3,
                status="READY_SIGNAL_REWORK",
                trigger="deep sandbox 失败，胜率和平均收益不达标，最大回撤过深。",
                target="不要继续把宽信号当正向因子；改成更严格的趋势/估值/回撤过滤，或只作为风险否决。",
                evidence=snapshot,
                next_command="make stock-agent-a-share-strategy-cycle-managed-expanded",
                success_metric="重测后 signal_case_count 仍 >= 8，且 win_rate/average_return/drawdown 至少一项明显改善。",
            )
        )

    for module_id, label, proposed in [
        (
            "capital_flow",
            "主力资金历史日期探测",
            ".venv/bin/python scripts/probe_a_share_tushare_strategy_sources.py --historical-date-scan moneyflow",
        ),
        (
            "factor_base",
            "因子/流动性历史日期探测",
            ".venv/bin/python scripts/probe_a_share_tushare_strategy_sources.py --historical-date-scan factor_base",
        ),
    ]:
        status = module_status(probe, module_id)
        if status["empty_count"]:
            tasks.append(
                base_task(
                    experiment_id=f"exp_a_{module_id}_historical_date_probe",
                    label=label,
                    priority=4,
                    status="BLOCKED_NEEDS_PROBE_IMPLEMENTATION",
                    trigger="latest_trade_date probe 返回 EMPTY，不能判断历史日期是否可用。",
                    target="新增历史交易日扫描，不要只探最新日期；优先扫描本地 historical case entry dates。",
                    evidence=status,
                    proposed_command=proposed,
                    success_metric="找到可覆盖 historical cases 的 PASS 日期，或明确证明该 endpoint 当前不可用于沙盘。",
                )
            )

    if refined_summary.get("refined_sandbox_blocked_count"):
        tasks.append(
            base_task(
                experiment_id="exp_a_refined_combination_unblock",
                label="组合策略解除 blocked",
                priority=5,
                status="BLOCKED_BY_MISSING_DEEP_FEATURES",
                trigger="refined sandbox 全部 blocked，原因是 moneyflow/factor 等 required deep sandbox features 缺失。",
                target="先让 moneyflow/factor/holder guardrails 进入 deep sandbox，再重测 refined combinations。",
                evidence={
                    "refined_sandbox_blocked_count": refined_summary.get("refined_sandbox_blocked_count"),
                    "ranking_gate_approved_count": ranking_summary.get("ranking_gate_approved_count"),
                    "feature_ready_count": feature_summary.get("ready_for_deep_sandbox_count"),
                },
                next_command="make stock-agent-a-share-strategy-cycle-managed-expanded",
                success_metric="至少 1 个 refined strategy 从 BLOCKED 变成 FAIL 或 PASS_CANDIDATE；PASS_CANDIDATE 仍需 ranking gate。",
            )
        )

    if tuned_summary.get("tuned_experiment_count") is not None:
        tuned_pass = int(tuned_summary.get("tuned_pass_candidate_count") or 0)
        tasks.append(
            base_task(
                experiment_id="exp_a_signal_tuning_result_review",
                label="信号调优结果复核",
                priority=5,
                status="READY_TUNING_REVIEW" if tuned_pass else "READY_TUNING_REWORK",
                trigger="stock-agent 提出的调优方案已进入独立实验层，需要比较 baseline 与 tuned metrics。",
                target="复核主力资金、筹码集中、机构持仓、治理 veto-only 等调优实验是否改善；即便通过也不能直接进推荐。",
                evidence={
                    "tuned_experiment_count": tuned_summary.get("tuned_experiment_count"),
                    "tuned_pass_candidate_count": tuned_summary.get("tuned_pass_candidate_count"),
                    "tuned_fail_count": tuned_summary.get("tuned_fail_count"),
                    "source_report": str(TUNED),
                },
                next_command="make stock-agent-a-share-strategy-cycle-managed-expanded",
                success_metric="至少 1 个 tuned experiment 指标改善且后续通过 Codex-reviewed refined/ranking gate；在此之前 ranking_impact_allowed=false。",
            )
        )

    # Diagnostics are copied into evidence so stock-agent can compare its next run.
    if diagnostics.get("priority_actions"):
        tasks.append(
            base_task(
                experiment_id="exp_a_diagnostics_regression_check",
                label="诊断动作回归检查",
                priority=6,
                status="READY_REGRESSION_CHECK",
                trigger="已有 diagnostics priority_actions，需要下一轮确认动作数量是否下降。",
                target="每次 managed cycle 后比较 priority_action_count、deep fail 和 blocked refined count。",
                evidence={
                    "priority_action_count": diagnostics.get("summary", {}).get("priority_action_count"),
                    "priority_actions": diagnostics.get("priority_actions", [])[:4],
                },
                next_command="make stock-agent-a-share-strategy-cycle-managed-expanded",
                success_metric="priority_action_count 下降或阻断原因更具体；不允许仅凭 PASS marker 宣称改善。",
            )
        )
    return tasks


def build_report(
    probe: dict[str, Any],
    dragon: dict[str, Any],
    cases: dict[str, Any],
    feature: dict[str, Any],
    deep: dict[str, Any],
    refined: dict[str, Any],
    tuned: dict[str, Any],
    ranking_gate: dict[str, Any],
    diagnostics: dict[str, Any],
    *,
    run_id: str,
    command: str,
) -> dict[str, Any]:
    tasks = sorted(
        build_tasks(probe, dragon, cases, feature, deep, refined, tuned, ranking_gate, diagnostics),
        key=lambda item: (item["priority"], item["experiment_id"]),
    )
    ready_count = sum(1 for item in tasks if item["status"].startswith("READY"))
    blocked_count = sum(1 for item in tasks if item["status"].startswith("BLOCKED"))
    return {
        "type": "a_share_strategy_experiment_queue",
        "status": "PASS",
        "generated_at": now_iso(),
        "run_id": run_id,
        "command": command,
        "summary": {
            "experiment_count": len(tasks),
            "ready_experiment_count": ready_count,
            "blocked_experiment_count": blocked_count,
            "dragon_tiger_sample_count": (dragon.get("summary") or {}).get("sample_count"),
            "dragon_tiger_event_count": (dragon.get("summary") or {}).get("event_count"),
            "a_share_case_count": (cases.get("summary") or {}).get("a_share_case_count"),
            "ranking_gate_approved_count": (ranking_gate.get("summary") or {}).get("ranking_gate_approved_count"),
            "rankable_strategy_count": (diagnostics.get("summary") or {}).get("rankable_strategy_count"),
            "tuned_experiment_count": (tuned.get("summary") or {}).get("tuned_experiment_count"),
            "tuned_pass_candidate_count": (tuned.get("summary") or {}).get("tuned_pass_candidate_count"),
            "ranking_impact_allowed": False,
            "user_facing_suggestion_allowed": False,
            "next_stage": "stock-agent should run ready experiments and report whether each blocker moved, not only rerun PASS markers.",
        },
        "experiments": tasks,
        "source_reports": {
            "source_probe": str(SOURCE_PROBE),
            "dragon_tiger": str(DRAGON_TIGER),
            "historical_cases": str(CASES),
            "feature_coverage": str(FEATURE),
            "deep_sandbox": str(DEEP),
            "refined_sandbox": str(REFINED),
            "signal_tuning": str(TUNED),
            "ranking_gate": str(RANKING_GATE),
            "diagnostics": str(DIAGNOSTICS),
        },
        "source_hashes": {
            "source_probe": sha256(SOURCE_PROBE),
            "dragon_tiger": sha256(DRAGON_TIGER),
            "historical_cases": sha256(CASES),
            "feature_coverage": sha256(FEATURE),
            "deep_sandbox": sha256(DEEP),
            "refined_sandbox": sha256(REFINED),
            "signal_tuning": sha256(TUNED),
            "ranking_gate": sha256(RANKING_GATE),
            "diagnostics": sha256(DIAGNOSTICS),
        },
        "checks": {
            "has_experiments": bool(tasks),
            "has_ready_experiments": ready_count > 0,
            "ranking_impact_allowed": False,
            "user_facing_suggestion_allowed": False,
            "no_network_used": True,
            "no_raw_payload_saved": True,
            "no_broker_api": True,
            "no_webhook": True,
            "no_order_placement": True,
        },
        "safety": {
            "simulation_only": True,
            "experiment_queue_only": True,
            "ranking_impact_allowed": False,
            "user_facing_suggestion_allowed": False,
            "real_trade_allowed": False,
            "no_broker_api": True,
            "no_order_placement": True,
            "no_trading_webhook": True,
            "no_secret_values": True,
        },
    }


def markdown_report(report: dict[str, Any]) -> str:
    s = report["summary"]
    lines = [
        "# A-share Strategy Experiment Queue",
        "",
        f"- Status: `{report['status']}`",
        f"- Generated At: `{report['generated_at']}`",
        f"- Experiments: `{s['experiment_count']}`",
        f"- Ready: `{s['ready_experiment_count']}`",
        f"- Blocked: `{s['blocked_experiment_count']}`",
        f"- Ranking Gate Approved: `{s['ranking_gate_approved_count']}`",
        "- Boundary: experiment planning only; no broker, no order, no trading webhook, no recommendation ranking impact.",
        "",
        "## Experiments",
        "",
        "| Priority | ID | Status | Target | Success Metric |",
        "| ---: | --- | --- | --- | --- |",
    ]
    for item in report["experiments"]:
        lines.append(
            "| "
            + " | ".join(
                [
                    str(item["priority"]),
                    f"`{item['experiment_id']}`",
                    f"`{item['status']}`",
                    item["target"],
                    item["success_metric"],
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
    run_json = run_dir / "a_share_strategy_experiment_queue.json"
    run_md = run_dir / "a_share_strategy_experiment_queue.md"
    write_json(run_json, report)
    run_md.write_text(markdown_report(report), encoding="utf-8")
    write_json(OUT_JSON, report)
    OUT_MD.write_text(markdown_report(report), encoding="utf-8")
    PASS_MARKER.write_text(
        "\n".join(
            [
                f"status={report['status']}",
                f"run_id={run_id}",
                f"generated_at={report['generated_at']}",
                f"report_json={OUT_JSON}",
                f"report_json_sha256={sha256(OUT_JSON)}",
                f"experiment_count={report['summary']['experiment_count']}",
                f"ready_experiment_count={report['summary']['ready_experiment_count']}",
                f"blocked_experiment_count={report['summary']['blocked_experiment_count']}",
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
    return {"run_json": str(run_json), "run_md": str(run_md), "latest_json": str(OUT_JSON), "latest_md": str(OUT_MD), "marker": str(PASS_MARKER)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build stock-agent A-share strategy experiment queue.")
    parser.add_argument("--source-probe-json", type=Path, default=SOURCE_PROBE)
    parser.add_argument("--dragon-tiger-json", type=Path, default=DRAGON_TIGER)
    parser.add_argument("--cases-json", type=Path, default=CASES)
    parser.add_argument("--feature-json", type=Path, default=FEATURE)
    parser.add_argument("--deep-json", type=Path, default=DEEP)
    parser.add_argument("--refined-json", type=Path, default=REFINED)
    parser.add_argument("--tuned-json", type=Path, default=TUNED)
    parser.add_argument("--ranking-gate-json", type=Path, default=RANKING_GATE)
    parser.add_argument("--diagnostics-json", type=Path, default=DIAGNOSTICS)
    parser.add_argument("--run-id", default=f"a_share_strategy_experiment_queue_{datetime.now().strftime('%Y%m%dT%H%M%S')}")
    args = parser.parse_args(argv)
    command = " ".join(sys.argv)
    report = build_report(
        load_json(args.source_probe_json, {}),
        load_json(args.dragon_tiger_json, {}),
        load_json(args.cases_json, {}),
        load_json(args.feature_json, {}),
        load_json(args.deep_json, {}),
        load_json(args.refined_json, {}),
        load_json(args.tuned_json, {}),
        load_json(args.ranking_gate_json, {}),
        load_json(args.diagnostics_json, {}),
        run_id=args.run_id,
        command=command,
    )
    outputs = write_outputs(report, args.run_id)
    print(json.dumps({"status": report["status"], "summary": report["summary"], "outputs": outputs}, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
