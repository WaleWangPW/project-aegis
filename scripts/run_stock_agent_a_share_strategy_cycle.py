#!/usr/bin/env python3
"""Run the OpenClaw stock-agent A-share strategy cycle with compact evidence.

This wrapper is intended for the future stock-agent backend. It records command
exit codes, report paths, hashes, and safety status. It does not create orders,
broker calls, trading webhooks, or user-facing recommendations.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
REPORTS = ROOT / "data" / "reports"
OUT_JSON = REPORTS / "stock_agent_a_share_strategy_cycle_latest.json"
OUT_MD = REPORTS / "stock_agent_a_share_strategy_cycle_latest.md"
PASS_MARKER = REPORTS / "STOCK_AGENT_A_SHARE_STRATEGY_CYCLE_PASS.marker"
FAIL_MARKER = REPORTS / "STOCK_AGENT_A_SHARE_STRATEGY_CYCLE_FAIL.marker"
EXPANSION_PLAN = REPORTS / "a_share_strategy_sample_expansion_plan_latest.json"
DEFAULT_EXPANDED_FORWARD_DAYS = 20

COMMANDS = [
    {
        "name": "probe_a_share_tushare_strategy_sources",
        "argv": ["scripts/probe_a_share_tushare_strategy_sources.py"],
        "report": REPORTS / "a_share_tushare_strategy_source_probe_latest.json",
        "marker": REPORTS / "A_SHARE_TUSHARE_STRATEGY_SOURCE_PROBE_PASS.marker",
    },
    {
        "name": "build_a_share_tushare_source_hypothesis_queue",
        "argv": ["scripts/build_a_share_tushare_source_hypothesis_queue.py"],
        "report": REPORTS / "a_share_tushare_source_hypothesis_queue_latest.json",
        "marker": REPORTS / "A_SHARE_TUSHARE_SOURCE_HYPOTHESIS_QUEUE_PASS.marker",
    },
    {
        "name": "collect_a_share_dragon_tiger_research_samples",
        "argv": ["scripts/collect_a_share_dragon_tiger_research_samples.py"],
        "report": REPORTS / "a_share_dragon_tiger_research_samples_latest.json",
        "marker": REPORTS / "A_SHARE_DRAGON_TIGER_RESEARCH_SAMPLES_PASS.marker",
    },
    {
        "name": "build_aegis_strategy_specific_historical_cases",
        "argv": ["scripts/build_aegis_strategy_specific_historical_cases.py"],
        "report": REPORTS / "aegis_strategy_specific_historical_cases_latest.json",
        "marker": REPORTS / "AEGIS_STRATEGY_SPECIFIC_HISTORICAL_CASES_PASS.marker",
    },
    {
        "name": "evaluate_aegis_strategy_specific_cases",
        "argv": ["scripts/evaluate_aegis_strategy_specific_cases.py"],
        "report": REPORTS / "aegis_strategy_specific_case_evaluation_latest.json",
        "marker": REPORTS / "AEGIS_STRATEGY_SPECIFIC_CASE_EVALUATION_PASS.marker",
    },
    {
        "name": "evaluate_a_share_tushare_source_hypotheses",
        "argv": ["scripts/evaluate_a_share_tushare_source_hypotheses.py"],
        "report": REPORTS / "a_share_tushare_source_hypothesis_evaluation_latest.json",
        "marker": REPORTS / "A_SHARE_TUSHARE_SOURCE_HYPOTHESIS_EVALUATION_PASS.marker",
    },
    {
        "name": "build_a_share_tushare_source_feature_coverage",
        "argv": ["scripts/build_a_share_tushare_source_feature_coverage.py"],
        "report": REPORTS / "a_share_tushare_source_feature_coverage_latest.json",
        "marker": REPORTS / "A_SHARE_TUSHARE_SOURCE_FEATURE_COVERAGE_PASS.marker",
    },
    {
        "name": "evaluate_a_share_tushare_source_deep_sandbox",
        "argv": ["scripts/evaluate_a_share_tushare_source_deep_sandbox.py"],
        "report": REPORTS / "a_share_tushare_source_deep_sandbox_latest.json",
        "marker": REPORTS / "A_SHARE_TUSHARE_SOURCE_DEEP_SANDBOX_PASS.marker",
    },
    {
        "name": "evaluate_a_share_tushare_refined_strategy_sandbox",
        "argv": ["scripts/evaluate_a_share_tushare_refined_strategy_sandbox.py"],
        "report": REPORTS / "a_share_tushare_refined_strategy_sandbox_latest.json",
        "marker": REPORTS / "A_SHARE_TUSHARE_REFINED_STRATEGY_SANDBOX_PASS.marker",
    },
    {
        "name": "evaluate_a_share_signal_tuning_experiments",
        "argv": ["scripts/evaluate_a_share_signal_tuning_experiments.py"],
        "report": REPORTS / "a_share_signal_tuning_experiments_latest.json",
        "marker": REPORTS / "A_SHARE_SIGNAL_TUNING_EXPERIMENTS_PASS.marker",
    },
    {
        "name": "review_a_share_refined_strategy_ranking_gate",
        "argv": ["scripts/review_a_share_refined_strategy_ranking_gate.py"],
        "report": REPORTS / "a_share_refined_strategy_ranking_gate_latest.json",
        "marker": REPORTS / "A_SHARE_REFINED_STRATEGY_RANKING_GATE_PASS.marker",
    },
    {
        "name": "plan_a_share_strategy_sample_expansion",
        "argv": ["scripts/plan_a_share_strategy_sample_expansion.py"],
        "report": REPORTS / "a_share_strategy_sample_expansion_plan_latest.json",
        "marker": REPORTS / "A_SHARE_STRATEGY_SAMPLE_EXPANSION_PLAN_PASS.marker",
    },
    {
        "name": "analyze_a_share_tushare_strategy_diagnostics",
        "argv": ["scripts/analyze_a_share_tushare_strategy_diagnostics.py"],
        "report": REPORTS / "a_share_tushare_strategy_diagnostics_latest.json",
        "marker": REPORTS / "A_SHARE_TUSHARE_STRATEGY_DIAGNOSTICS_PASS.marker",
    },
    {
        "name": "build_a_share_full_year_coverage_plan",
        "argv": ["scripts/build_a_share_full_year_coverage_plan.py"],
        "report": REPORTS / "a_share_full_year_coverage_plan_latest.json",
        "marker": REPORTS / "A_SHARE_FULL_YEAR_COVERAGE_PLAN_PASS.marker",
    },
    {
        "name": "build_a_share_strategy_experiment_queue",
        "argv": ["scripts/build_a_share_strategy_experiment_queue.py"],
        "report": REPORTS / "a_share_strategy_experiment_queue_latest.json",
        "marker": REPORTS / "A_SHARE_STRATEGY_EXPERIMENT_QUEUE_PASS.marker",
    },
]


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


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def tail(text: str, limit: int = 2800) -> str:
    text = text.strip()
    return text[-limit:] if len(text) > limit else text


def expansion_plan_args() -> list[str]:
    plan = load_json(EXPANSION_PLAN)
    summary = plan.get("summary") or {}
    if not summary.get("expansion_task_count"):
        return []
    lookback = summary.get("next_lookback_dates")
    max_symbols = summary.get("next_max_symbols")
    max_events = summary.get("next_max_events_per_symbol")
    if not all(isinstance(value, int) and value > 0 for value in [lookback, max_symbols, max_events]):
        return []
    return [
        "--lookback-dates",
        str(lookback),
        "--forward-days",
        str(summary.get("next_forward_days") or DEFAULT_EXPANDED_FORWARD_DAYS),
        "--max-symbols",
        str(max_symbols),
        "--max-events-per-symbol",
        str(max_events),
    ]


def explicit_dragon_tiger_args(args: argparse.Namespace) -> list[str]:
    values = [
        args.dragon_tiger_lookback_dates,
        args.dragon_tiger_forward_days,
        args.dragon_tiger_max_symbols,
        args.dragon_tiger_max_events_per_symbol,
    ]
    if not any(value is not None for value in values):
        return []
    if not all(isinstance(value, int) and value > 0 for value in values):
        raise ValueError("All dragon-tiger override args must be positive integers when any override is set.")
    return [
        "--lookback-dates",
        str(args.dragon_tiger_lookback_dates),
        "--forward-days",
        str(args.dragon_tiger_forward_days),
        "--max-symbols",
        str(args.dragon_tiger_max_symbols),
        "--max-events-per-symbol",
        str(args.dragon_tiger_max_events_per_symbol),
    ]


def command_argv(
    command: dict[str, Any],
    *,
    dragon_tiger_args: list[str],
    source_probe_historical_date_scan: str | None,
) -> tuple[list[str], str | None]:
    argv = list(command["argv"])
    dynamic_source = None
    if command["name"] == "probe_a_share_tushare_strategy_sources" and source_probe_historical_date_scan:
        argv.extend(["--historical-date-scan", source_probe_historical_date_scan])
        dynamic_source = "historical_date_scan"
    if command["name"] == "collect_a_share_dragon_tiger_research_samples":
        extra = dragon_tiger_args or expansion_plan_args()
        if extra:
            argv.extend(extra)
            dynamic_source = "explicit_override" if dragon_tiger_args else "sample_expansion_plan"
    return argv, dynamic_source


def run_command(
    command: dict[str, Any],
    *,
    dragon_tiger_args: list[str],
    source_probe_historical_date_scan: str | None,
) -> dict[str, Any]:
    started = time.monotonic()
    resolved_argv, dynamic_source = command_argv(
        command,
        dragon_tiger_args=dragon_tiger_args,
        source_probe_historical_date_scan=source_probe_historical_date_scan,
    )
    argv = [sys.executable, *resolved_argv]
    proc = subprocess.run(argv, cwd=ROOT, text=True, capture_output=True, check=False)
    duration = round(time.monotonic() - started, 3)
    report = Path(command["report"])
    marker = Path(command["marker"])
    return {
        "name": command["name"],
        "command": " ".join(argv),
        "dynamic_args_source": dynamic_source,
        "exit_code": proc.returncode,
        "duration_seconds": duration,
        "stdout_tail": tail(proc.stdout),
        "stderr_tail": tail(proc.stderr),
        "report_path": str(report),
        "report_exists": report.exists(),
        "report_sha256": sha256(report),
        "marker_path": str(marker),
        "marker_exists": marker.exists(),
        "marker_sha256": sha256(marker),
    }


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Stock Agent A-share Strategy Cycle",
        "",
        f"- Status: `{report['status']}`",
        f"- Generated At: `{report['generated_at']}`",
        f"- Overall Exit Code: `{report['overall_exit_code']}`",
        f"- A-share Cases: `{report['summary'].get('a_share_case_count')}`",
        f"- Deep Sandbox Pass Candidates: `{report['summary'].get('deep_sandbox_pass_candidate_count')}`",
        f"- Ranking Impact Allowed: `{report['summary'].get('ranking_impact_allowed')}`",
        "",
        "Simulation research only. No broker API, no order placement, no trading webhook, no secrets.",
        "",
        "## Commands",
        "",
    ]
    for item in report["commands"]:
        lines.append(
            f"- `{item['name']}` exit=`{item['exit_code']}` report=`{item['report_path']}` sha256=`{item['report_sha256']}`"
        )
    if report["blockers"]:
        lines.extend(["", "## Blockers", ""])
        lines.extend(f"- {blocker}" for blocker in report["blockers"])
    lines.append("")
    return "\n".join(lines)


def build_report(command_results: list[dict[str, Any]], *, prepare_manifest: dict[str, Any] | None = None) -> dict[str, Any]:
    cases = load_json(REPORTS / "aegis_strategy_specific_historical_cases_latest.json")
    case_eval = load_json(REPORTS / "aegis_strategy_specific_case_evaluation_latest.json")
    source_eval = load_json(REPORTS / "a_share_tushare_source_hypothesis_evaluation_latest.json")
    feature = load_json(REPORTS / "a_share_tushare_source_feature_coverage_latest.json")
    deep = load_json(REPORTS / "a_share_tushare_source_deep_sandbox_latest.json")
    refined = load_json(REPORTS / "a_share_tushare_refined_strategy_sandbox_latest.json")
    tuned = load_json(REPORTS / "a_share_signal_tuning_experiments_latest.json")
    ranking_gate = load_json(REPORTS / "a_share_refined_strategy_ranking_gate_latest.json")
    expansion_plan = load_json(REPORTS / "a_share_strategy_sample_expansion_plan_latest.json")
    diagnostics = load_json(REPORTS / "a_share_tushare_strategy_diagnostics_latest.json")
    full_year = load_json(REPORTS / "a_share_full_year_coverage_plan_latest.json")
    experiment_queue = load_json(REPORTS / "a_share_strategy_experiment_queue_latest.json")
    dragon = load_json(REPORTS / "a_share_dragon_tiger_research_samples_latest.json")
    blockers = [
        f"{item['name']} exit_code={item['exit_code']}"
        for item in command_results
        if item["exit_code"] != 0
    ]
    status = "PASS" if not blockers and command_results else "FAIL"
    return {
        "type": "stock_agent_a_share_strategy_cycle",
        "status": status,
        "generated_at": now_iso(),
        "overall_exit_code": 0 if status == "PASS" else 1,
        "summary": {
            "command_count": len(command_results),
            "failed_command_count": len(blockers),
            "base_candidate_count": cases.get("summary", {}).get("base_candidate_count"),
            "candidate_count": cases.get("summary", {}).get("candidate_count"),
            "a_share_research_sample_candidate_count": cases.get("summary", {}).get(
                "a_share_research_sample_candidate_count"
            ),
            "a_share_dragon_tiger_research_sample_candidate_count": cases.get("summary", {}).get(
                "a_share_dragon_tiger_research_sample_candidate_count"
            ),
            "a_share_dragon_tiger_research_sample_case_count": cases.get("summary", {}).get(
                "a_share_dragon_tiger_research_sample_case_count"
            ),
            "dragon_tiger_sample_count": dragon.get("summary", {}).get("sample_count"),
            "dragon_tiger_event_count": dragon.get("summary", {}).get("event_count"),
            "historical_case_count": cases.get("summary", {}).get("historical_case_count"),
            "a_share_case_count": cases.get("summary", {}).get("a_share_case_count"),
            "simulation_research_candidate_count": case_eval.get("summary", {}).get(
                "simulation_research_candidate_count"
            ),
            "proxy_pass_count": source_eval.get("summary", {}).get("proxy_pass_count"),
            "proxy_fail_count": source_eval.get("summary", {}).get("proxy_fail_count"),
            "ready_for_deep_sandbox_count": feature.get("summary", {}).get("ready_for_deep_sandbox_count"),
            "feature_gap_count": feature.get("summary", {}).get("feature_gap_count"),
            "deep_sandbox_pass_candidate_count": deep.get("summary", {}).get("deep_sandbox_pass_candidate_count"),
            "deep_sandbox_fail_count": deep.get("summary", {}).get("deep_sandbox_fail_count"),
            "refined_sandbox_pass_candidate_count": refined.get("summary", {}).get(
                "refined_sandbox_pass_candidate_count"
            ),
            "refined_strategy_count": refined.get("summary", {}).get("refined_strategy_count"),
            "tuned_experiment_count": tuned.get("summary", {}).get("tuned_experiment_count"),
            "tuned_pass_candidate_count": tuned.get("summary", {}).get("tuned_pass_candidate_count"),
            "tuned_fail_count": tuned.get("summary", {}).get("tuned_fail_count"),
            "ranking_gate_reviewed_count": ranking_gate.get("summary", {}).get("ranking_gate_reviewed_count"),
            "ranking_gate_approved_count": ranking_gate.get("summary", {}).get("ranking_gate_approved_count"),
            "ranking_gate_blocked_count": ranking_gate.get("summary", {}).get("ranking_gate_blocked_count"),
            "sample_expansion_task_count": expansion_plan.get("summary", {}).get("expansion_task_count"),
            "sample_expansion_next_lookback_dates": expansion_plan.get("summary", {}).get("next_lookback_dates"),
            "sample_expansion_next_max_symbols": expansion_plan.get("summary", {}).get("next_max_symbols"),
            "rankable_strategy_count": diagnostics.get("summary", {}).get("rankable_strategy_count"),
            "strategy_priority_action_count": diagnostics.get("summary", {}).get("priority_action_count"),
            "full_year_coverage_status": full_year.get("coverage_status"),
            "full_year_coverage_answer": full_year.get("answer_label"),
            "full_year_cache_daily_file_count": full_year.get("current_cache", {}).get("daily_file_count"),
            "full_year_cache_daily_start": full_year.get("current_cache", {}).get("daily_start"),
            "full_year_cache_daily_end": full_year.get("current_cache", {}).get("daily_end"),
            "strategy_experiment_count": experiment_queue.get("summary", {}).get("experiment_count"),
            "ready_strategy_experiment_count": experiment_queue.get("summary", {}).get("ready_experiment_count"),
            "blocked_strategy_experiment_count": experiment_queue.get("summary", {}).get("blocked_experiment_count"),
            "ranking_impact_allowed": ranking_gate.get("summary", {}).get(
                "ranking_impact_allowed",
                deep.get("summary", {}).get("ranking_impact_allowed", False),
            ),
            "user_facing_suggestion_allowed": False,
        },
        "commands": command_results,
        "blockers": blockers,
        "prepare_manifest": prepare_manifest,
        "safety": {
            "simulation_research_only": True,
            "no_broker_api": True,
            "no_order_placement": True,
            "no_trading_webhook": True,
            "no_secret_values": True,
            "ranking_requires_separate_gate": True,
        },
    }


def write_report(report: dict[str, Any]) -> None:
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
                f"exit_code={report['overall_exit_code']}",
                f"report_json={OUT_JSON}",
                f"report_json_sha256={sha256(OUT_JSON)}",
                f"command_count={report['summary']['command_count']}",
                f"failed_command_count={report['summary']['failed_command_count']}",
                f"a_share_case_count={report['summary']['a_share_case_count']}",
                f"deep_sandbox_pass_candidate_count={report['summary']['deep_sandbox_pass_candidate_count']}",
                f"refined_sandbox_pass_candidate_count={report['summary'].get('refined_sandbox_pass_candidate_count')}",
                f"ranking_gate_approved_count={report['summary'].get('ranking_gate_approved_count')}",
                f"sample_expansion_task_count={report['summary'].get('sample_expansion_task_count')}",
                f"full_year_coverage_status={report['summary'].get('full_year_coverage_status')}",
                f"full_year_coverage_answer={report['summary'].get('full_year_coverage_answer')}",
                f"ranking_impact_allowed={str(report['summary']['ranking_impact_allowed']).lower()}",
                "user_facing_suggestion_allowed=false",
                "no_real_trade=true",
                "no_broker_api=true",
                "no_webhook=true",
                "no_order_placement=true",
                "no_secret_values=true",
                "",
            ]
        ),
        encoding="utf-8",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run stock-agent A-share strategy cycle.")
    parser.add_argument("--continue-on-error", action="store_true")
    parser.add_argument("--prepare-stock-agent-workspace", action="store_true")
    parser.add_argument("--dragon-tiger-lookback-dates", type=int)
    parser.add_argument("--dragon-tiger-forward-days", type=int)
    parser.add_argument("--dragon-tiger-max-symbols", type=int)
    parser.add_argument("--dragon-tiger-max-events-per-symbol", type=int)
    parser.add_argument(
        "--source-probe-historical-date-scan",
        choices=["daily_core", "moneyflow", "factor_base"],
        help="Pass historical date scan mode to the source probe step.",
    )
    args = parser.parse_args(argv)

    dragon_tiger_args = explicit_dragon_tiger_args(args)
    command_results: list[dict[str, Any]] = []
    for command in COMMANDS:
        result = run_command(
            command,
            dragon_tiger_args=dragon_tiger_args,
            source_probe_historical_date_scan=args.source_probe_historical_date_scan,
        )
        command_results.append(result)
        if result["exit_code"] != 0 and not args.continue_on_error:
            break

    prepare_manifest = None
    report = build_report(command_results)
    write_report(report)

    if args.prepare_stock_agent_workspace:
        from scripts.prepare_stock_agent_strategy_simulation_workspace import prepare

        prepare_manifest = prepare()
        report = build_report(command_results, prepare_manifest=prepare_manifest)
        write_report(report)

    print(
        json.dumps(
            {
                "status": report["status"],
                "overall_exit_code": report["overall_exit_code"],
                "summary": report["summary"],
                "report_json": str(OUT_JSON),
                "report_json_sha256": sha256(OUT_JSON),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return report["overall_exit_code"]


if __name__ == "__main__":
    raise SystemExit(main())
