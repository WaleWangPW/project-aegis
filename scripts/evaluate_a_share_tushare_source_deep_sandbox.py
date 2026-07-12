#!/usr/bin/env python3
"""Evaluate ready A-share Tushare source hypotheses with derived features.

This is the first source-specific sandbox layer. It re-reads approved Tushare
endpoints in memory, converts rows into small derived feature summaries, and
stores only derived metadata/hashes. It never stores raw payloads and never
creates live recommendations, paper trades, orders, broker calls, or webhooks.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aegis.data.providers import ProviderError  # noqa: E402
from aegis.data.tushare_adapter import TushareAdapter  # noqa: E402
from scripts.build_a_share_tushare_source_feature_coverage import (  # noqa: E402
    REQUIRED_ENDPOINTS_BY_HYPOTHESIS,
    collect_observations,
    compact_date,
    lookback_start,
)
from scripts.evaluate_a_share_tushare_source_hypotheses import fingerprints  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "data" / "reports"
PROCESSED = ROOT / "data" / "processed" / "a_share_tushare_source_deep_sandbox"
QUEUE_JSON = REPORTS / "a_share_tushare_source_hypothesis_queue_latest.json"
CASES_JSON = REPORTS / "aegis_strategy_specific_historical_cases_latest.json"
FEATURE_COVERAGE_JSON = REPORTS / "a_share_tushare_source_feature_coverage_latest.json"
OUT_JSON = REPORTS / "a_share_tushare_source_deep_sandbox_latest.json"
OUT_MD = REPORTS / "a_share_tushare_source_deep_sandbox_latest.md"
PASS_MARKER = REPORTS / "A_SHARE_TUSHARE_SOURCE_DEEP_SANDBOX_PASS.marker"
BLOCKED_MARKER = REPORTS / "A_SHARE_TUSHARE_SOURCE_DEEP_SANDBOX_BLOCKED.marker"

THRESHOLDS = {
    "min_feature_coverage": 0.50,
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


def stable_hash(payload: Any) -> str:
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")).hexdigest()


def load_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def a_share_cases(cases_report: dict[str, Any]) -> list[dict[str, Any]]:
    return [case for case in cases_report.get("historical_cases", []) if case.get("market") == "A"]


def ready_hypotheses(queue: dict[str, Any], coverage: dict[str, Any]) -> list[dict[str, Any]]:
    ready_ids = {
        item.get("hypothesis_id")
        for item in coverage.get("items", [])
        if item.get("feature_status") == "READY_FOR_DEEP_SANDBOX"
        and float(item.get("min_endpoint_coverage") or 0.0) >= THRESHOLDS["min_feature_coverage"]
    }
    return [item for item in queue.get("hypotheses", []) if item.get("hypothesis_id") in ready_ids]


def eligible_cases_for_hypothesis(hypothesis_id: str, coverage: dict[str, Any], cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    coverage_item = next((item for item in coverage.get("items", []) if item.get("hypothesis_id") == hypothesis_id), None)
    symbols = set(coverage_item.get("eligible_symbols") or []) if coverage_item else set()
    if not symbols:
        return cases
    return [case for case in cases if case.get("symbol") in symbols]


def to_float(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def sum_columns(row: pd.Series, columns: list[str]) -> float:
    total = 0.0
    for column in columns:
        value = to_float(row.get(column))
        if value is not None:
            total += value
    return total


def latest_by(df: pd.DataFrame, column: str) -> list[pd.DataFrame]:
    if df.empty or column not in df.columns:
        return []
    work = df.copy()
    work[column] = work[column].astype(str)
    groups = []
    for _, part in work.groupby(column, sort=True):
        groups.append(part)
    return groups[-2:]


def fetch_endpoint_rows(pro: Any, case: dict[str, Any], endpoint: str) -> pd.DataFrame:
    ts_code = case["ts_code"]
    entry = compact_date(case["entry_date"])
    if endpoint == "moneyflow":
        df = pro.moneyflow(trade_date=entry)
    elif endpoint == "daily_basic":
        df = pro.daily_basic(trade_date=entry)
    elif endpoint == "stk_factor":
        df = pro.stk_factor(trade_date=entry)
    elif endpoint == "top10_holders":
        df = pro.top10_holders(ts_code=ts_code, start_date=lookback_start(case["entry_date"]), end_date=entry)
    elif endpoint == "top10_floatholders":
        df = pro.top10_floatholders(ts_code=ts_code, start_date=lookback_start(case["entry_date"]), end_date=entry)
    elif endpoint == "stk_holdernumber":
        df = pro.stk_holdernumber(ts_code=ts_code, start_date=lookback_start(case["entry_date"]), end_date=entry)
    elif endpoint == "stk_rewards":
        df = pro.stk_rewards(ts_code=ts_code)
    else:
        return pd.DataFrame()
    if not isinstance(df, pd.DataFrame) or df.empty or "ts_code" not in df.columns:
        return pd.DataFrame()
    rows = df[df["ts_code"].astype(str) == ts_code]
    if endpoint in {"top10_holders", "top10_floatholders", "stk_holdernumber", "stk_rewards"} and "ann_date" in rows.columns:
        rows = rows[rows["ann_date"].astype(str) <= entry]
    return rows


def feature_for_moneyflow(rows: dict[str, pd.DataFrame]) -> dict[str, Any]:
    row = rows.get("moneyflow", pd.DataFrame()).head(1)
    if row.empty:
        return {"signal_pass": False, "reasons": ["moneyflow_missing"]}
    item = row.iloc[0]
    net = to_float(item.get("net_mf_amount")) or 0.0
    large_net = sum_columns(item, ["buy_lg_amount", "buy_elg_amount"]) - sum_columns(item, ["sell_lg_amount", "sell_elg_amount"])
    return {
        "signal_pass": net > 0 and large_net > 0,
        "reasons": ["net_moneyflow_positive", "large_order_net_positive"] if net > 0 and large_net > 0 else ["moneyflow_not_confirmed"],
        "net_mf_amount_sign": 1 if net > 0 else -1 if net < 0 else 0,
        "large_order_net_sign": 1 if large_net > 0 else -1 if large_net < 0 else 0,
    }


def feature_for_institutional(rows: dict[str, pd.DataFrame]) -> dict[str, Any]:
    holders = rows.get("top10_holders", pd.DataFrame())
    floats = rows.get("top10_floatholders", pd.DataFrame())
    latest_sets = latest_by(holders, "end_date")
    float_sets = latest_by(floats, "end_date")
    latest_ratio = sum(to_float(value) or 0.0 for value in (latest_sets[-1]["hold_ratio"] if latest_sets else []))
    previous_ratio = sum(to_float(value) or 0.0 for value in (latest_sets[0]["hold_ratio"] if len(latest_sets) > 1 else []))
    latest_float_ratio = sum(to_float(value) or 0.0 for value in (float_sets[-1]["hold_float_ratio"] if float_sets else []))
    previous_float_ratio = sum(to_float(value) or 0.0 for value in (float_sets[0]["hold_float_ratio"] if len(float_sets) > 1 else []))
    stable = latest_ratio >= previous_ratio or latest_float_ratio >= previous_float_ratio
    return {
        "signal_pass": bool(latest_sets and float_sets and stable),
        "reasons": ["ownership_stable_or_improving"] if stable and latest_sets and float_sets else ["ownership_not_confirmed"],
        "top10_hold_ratio_delta_sign": 1 if latest_ratio > previous_ratio else -1 if latest_ratio < previous_ratio else 0,
        "top10_float_ratio_delta_sign": 1 if latest_float_ratio > previous_float_ratio else -1 if latest_float_ratio < previous_float_ratio else 0,
    }


def feature_for_holder_concentration(rows: dict[str, pd.DataFrame]) -> dict[str, Any]:
    groups = latest_by(rows.get("stk_holdernumber", pd.DataFrame()), "end_date")
    if len(groups) < 2:
        return {"signal_pass": False, "reasons": ["holdernumber_history_missing"]}
    previous = to_float(groups[0].iloc[-1].get("holder_num"))
    latest = to_float(groups[-1].iloc[-1].get("holder_num"))
    improving = previous is not None and latest is not None and latest <= previous
    return {
        "signal_pass": improving,
        "reasons": ["holder_count_decreasing_or_stable"] if improving else ["holder_count_expanding"],
        "holder_num_delta_sign": 1 if latest is not None and previous is not None and latest < previous else -1 if latest is not None and previous is not None and latest > previous else 0,
    }


def feature_for_factor(rows: dict[str, pd.DataFrame]) -> dict[str, Any]:
    daily = rows.get("daily_basic", pd.DataFrame()).head(1)
    factor = rows.get("stk_factor", pd.DataFrame()).head(1)
    if daily.empty or factor.empty:
        return {"signal_pass": False, "reasons": ["factor_or_daily_basic_missing"]}
    d = daily.iloc[0]
    f = factor.iloc[0]
    turnover = to_float(d.get("turnover_rate")) or 0.0
    pe_ttm = to_float(d.get("pe_ttm"))
    pct_change = to_float(f.get("pct_change")) or 0.0
    rsi_6 = to_float(f.get("rsi_6"))
    liquid = turnover > 0.5
    valuation_not_extreme = pe_ttm is None or pe_ttm < 120
    not_overheated = pct_change < 9.5 and (rsi_6 is None or rsi_6 < 85)
    passed = liquid and valuation_not_extreme and not_overheated
    reasons = []
    if liquid:
        reasons.append("liquidity_present")
    if valuation_not_extreme:
        reasons.append("valuation_not_extreme")
    if not_overheated:
        reasons.append("not_intraday_overheated")
    if not passed:
        reasons.append("factor_overlay_not_confirmed")
    return {
        "signal_pass": passed,
        "reasons": reasons,
        "turnover_bucket": "liquid" if liquid else "thin",
        "valuation_bucket": "not_extreme" if valuation_not_extreme else "extreme",
        "overheat_flag": not not_overheated,
    }


def feature_for_governance(rows: dict[str, pd.DataFrame]) -> dict[str, Any]:
    rewards = rows.get("stk_rewards", pd.DataFrame())
    if rewards.empty:
        return {"signal_pass": False, "reasons": ["reward_rows_missing"]}
    total_reward = sum(to_float(value) or 0.0 for value in rewards.get("reward", []))
    has_hold = any((to_float(value) or 0.0) > 0 for value in rewards.get("hold_vol", []))
    passed = total_reward > 0 or has_hold
    return {
        "signal_pass": passed,
        "reasons": ["management_reward_or_holding_present"] if passed else ["governance_reward_not_confirmed"],
        "reward_row_count": int(len(rewards.index)),
        "has_management_hold_vol": bool(has_hold),
    }


FEATURE_BUILDERS = {
    "hyp_a_tushare_capital_flow_accumulation": feature_for_moneyflow,
    "hyp_a_tushare_institutional_ownership_stability": feature_for_institutional,
    "hyp_a_tushare_holder_concentration_improvement": feature_for_holder_concentration,
    "hyp_a_tushare_factor_liquidity_quality_overlay": feature_for_factor,
    "hyp_a_tushare_governance_reward_alignment": feature_for_governance,
}


def derive_case_feature(pro: Any, case: dict[str, Any], hypothesis_id: str) -> dict[str, Any]:
    endpoints = REQUIRED_ENDPOINTS_BY_HYPOTHESIS.get(hypothesis_id, [])
    rows: dict[str, pd.DataFrame] = {}
    errors: list[str] = []
    for endpoint in endpoints:
        try:
            rows[endpoint] = fetch_endpoint_rows(pro, case, endpoint)
        except Exception as exc:  # noqa: BLE001 - Tushare endpoint errors vary
            rows[endpoint] = pd.DataFrame()
            errors.append(f"{endpoint}:{str(exc)[:120]}")
    feature = FEATURE_BUILDERS[hypothesis_id](rows)
    feature["errors"] = errors
    feature["covered_endpoints"] = [endpoint for endpoint, frame in rows.items() if not frame.empty]
    feature["feature_hash"] = stable_hash(feature)
    return feature


def aggregate_case_features(case_features: list[dict[str, Any]]) -> dict[str, Any]:
    signal_cases = [item for item in case_features if item["source_signal_pass"]]
    returns = [float(item["raw_return"]) for item in signal_cases]
    drawdowns = [float(item["max_drawdown"]) for item in signal_cases]
    return {
        "eligible_case_count": len(case_features),
        "source_signal_case_count": len(signal_cases),
        "source_signal_rate": len(signal_cases) / len(case_features) if case_features else None,
        "source_signal_win_rate": sum(1 for value in returns if value > 0) / len(returns) if returns else None,
        "source_signal_average_return": sum(returns) / len(returns) if returns else None,
        "source_signal_max_drawdown": min(drawdowns) if drawdowns else None,
        "source_signal_best_return": max(returns) if returns else None,
        "source_signal_worst_return": min(returns) if returns else None,
    }


def classify(metrics: dict[str, Any]) -> tuple[str, list[str]]:
    reasons: list[str] = []
    count = int(metrics.get("source_signal_case_count") or 0)
    win_rate = metrics.get("source_signal_win_rate")
    avg = metrics.get("source_signal_average_return")
    drawdown = metrics.get("source_signal_max_drawdown")
    if count < THRESHOLDS["min_signal_case_count"]:
        reasons.append("source_signal_case_count_below_threshold")
    if win_rate is None or win_rate < THRESHOLDS["min_signal_win_rate"]:
        reasons.append("source_signal_win_rate_below_threshold")
    if avg is None or avg <= THRESHOLDS["min_signal_average_return"]:
        reasons.append("source_signal_average_return_below_threshold")
    if drawdown is None or drawdown < THRESHOLDS["max_signal_drawdown_floor"]:
        reasons.append("source_signal_drawdown_breached")
    if reasons:
        return "DEEP_SANDBOX_FAIL", reasons
    return "DEEP_SANDBOX_PASS_CANDIDATE", ["source_signal_thresholds_passed"]


def build_report(
    queue: dict[str, Any],
    cases_report: dict[str, Any],
    coverage: dict[str, Any],
    pro: Any,
    *,
    run_id: str,
    command: str,
) -> dict[str, Any]:
    before = fingerprints()
    cases = a_share_cases(cases_report)
    ready = ready_hypotheses(queue, coverage)
    items: list[dict[str, Any]] = []
    case_feature_count = 0
    for hypothesis in ready:
        hypothesis_id = hypothesis["hypothesis_id"]
        case_features: list[dict[str, Any]] = []
        for case in eligible_cases_for_hypothesis(hypothesis_id, coverage, cases):
            feature = derive_case_feature(pro, case, hypothesis_id)
            case_features.append(
                {
                    "case_id": case["case_id"],
                    "symbol": case["symbol"],
                    "entry_date": case["entry_date"],
                    "source_signal_pass": bool(feature.get("signal_pass")),
                    "feature_reasons": feature.get("reasons") or [],
                    "covered_endpoints": feature.get("covered_endpoints") or [],
                    "feature_hash": feature["feature_hash"],
                    "raw_return": case["raw_return"],
                    "max_drawdown": case["max_drawdown"],
                    "case_result": case["case_result"],
                }
            )
        case_feature_count += len(case_features)
        metrics = aggregate_case_features(case_features)
        disposition, reasons = classify(metrics)
        items.append(
            {
                "hypothesis_id": hypothesis_id,
                "title": hypothesis.get("title"),
                "required_endpoints": REQUIRED_ENDPOINTS_BY_HYPOTHESIS.get(hypothesis_id, []),
                "disposition": disposition,
                "reasons": reasons,
                "metrics": metrics,
                "case_features": case_features,
                "allowed_next_step": "candidate_for_ranking_gate_review" if disposition == "DEEP_SANDBOX_PASS_CANDIDATE" else "do_not_rank_collect_more_cases_or_rework_signal",
                "simulation_only": True,
                "user_facing_suggestion_allowed": False,
                "real_trade_allowed": False,
            }
        )
    after = fingerprints()
    blocked_ids = [
        item.get("hypothesis_id")
        for item in coverage.get("items", [])
        if item.get("feature_status") != "READY_FOR_DEEP_SANDBOX"
    ]
    report = {
        "type": "a_share_tushare_source_deep_sandbox",
        "status": "PASS" if ready and items else "BLOCKED_NO_READY_HYPOTHESES",
        "generated_at": now_iso(),
        "run_id": run_id,
        "command": command,
        "thresholds": THRESHOLDS,
        "summary": {
            "ready_hypothesis_count": len(ready),
            "evaluated_hypothesis_count": len(items),
            "deep_sandbox_pass_candidate_count": sum(1 for item in items if item["disposition"] == "DEEP_SANDBOX_PASS_CANDIDATE"),
            "deep_sandbox_fail_count": sum(1 for item in items if item["disposition"] == "DEEP_SANDBOX_FAIL"),
            "blocked_feature_gap_count": len(blocked_ids),
            "case_feature_count": case_feature_count,
            "network_used": True,
            "user_facing_suggestion_allowed": False,
            "ranking_impact_allowed": False,
            "next_stage": "Only DEEP_SANDBOX_PASS_CANDIDATE hypotheses may be reviewed by a separate ranking gate; no automatic ranking impact.",
        },
        "items": items,
        "blocked_feature_gap_hypotheses": blocked_ids,
        "source_reports": {
            "source_hypothesis_queue": str(QUEUE_JSON),
            "strategy_specific_historical_cases": str(CASES_JSON),
            "source_feature_coverage": str(FEATURE_COVERAGE_JSON),
        },
        "source_hashes": {
            "source_hypothesis_queue": sha256(QUEUE_JSON),
            "strategy_specific_historical_cases": sha256(CASES_JSON),
            "source_feature_coverage": sha256(FEATURE_COVERAGE_JSON),
        },
        "checks": {
            "feature_coverage_pass": coverage.get("status") == "PASS",
            "ready_hypotheses_present": bool(ready),
            "all_ready_hypotheses_evaluated": len(items) == len(ready),
            "case_features_present": case_feature_count > 0,
            "raw_payload_saved": False,
            "production_records_unchanged": before == after,
            "no_broker_api": True,
            "no_webhook": True,
            "no_order_placement": True,
            "no_position_size": True,
            "ranking_impact_allowed": False,
        },
        "safety": {
            "simulation_only": True,
            "research_only": True,
            "derived_features_only": True,
            "raw_payload_saved": False,
            "requires_separate_ranking_gate_before_ranking": True,
            "user_facing_suggestion_allowed": False,
            "ranking_impact_allowed": False,
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
    pass_checks = (
        checks["feature_coverage_pass"]
        and checks["ready_hypotheses_present"]
        and checks["all_ready_hypotheses_evaluated"]
        and checks["case_features_present"]
        and checks["raw_payload_saved"] is False
        and checks["production_records_unchanged"]
        and checks["no_broker_api"]
        and checks["no_webhook"]
        and checks["no_order_placement"]
        and checks["no_position_size"]
        and checks["ranking_impact_allowed"] is False
    )
    if not pass_checks:
        report["status"] = "BLOCKED_CHECK_FAILED"
    return report


def blocked_report(status: str, message: str, *, run_id: str, command: str) -> dict[str, Any]:
    return {
        "type": "a_share_tushare_source_deep_sandbox",
        "status": status,
        "generated_at": now_iso(),
        "run_id": run_id,
        "command": command,
        "blocker": message,
        "summary": {
            "ready_hypothesis_count": 0,
            "evaluated_hypothesis_count": 0,
            "deep_sandbox_pass_candidate_count": 0,
            "deep_sandbox_fail_count": 0,
            "blocked_feature_gap_count": 0,
            "case_feature_count": 0,
            "network_used": False,
            "user_facing_suggestion_allowed": False,
            "ranking_impact_allowed": False,
        },
        "items": [],
        "checks": {
            "raw_payload_saved": False,
            "no_broker_api": True,
            "no_webhook": True,
            "no_order_placement": True,
            "no_position_size": True,
            "ranking_impact_allowed": False,
        },
        "safety": {
            "simulation_only": True,
            "research_only": True,
            "derived_features_only": True,
            "raw_payload_saved": False,
            "user_facing_suggestion_allowed": False,
            "ranking_impact_allowed": False,
            "no_broker_api": True,
            "no_order_placement": True,
            "no_trading_webhook": True,
            "no_position_size": True,
            "no_live_order_signal": True,
            "real_trade_allowed": False,
        },
    }


def markdown_report(report: dict[str, Any]) -> str:
    lines = [
        "# A-share Tushare Source Deep Sandbox",
        "",
        f"- Status: `{report['status']}`",
        f"- Generated At: `{report['generated_at']}`",
        f"- Ready Hypotheses: `{report['summary']['ready_hypothesis_count']}`",
        f"- Pass Candidates: `{report['summary']['deep_sandbox_pass_candidate_count']}`",
        f"- Fail: `{report['summary']['deep_sandbox_fail_count']}`",
        f"- Feature Gap Blocked: `{report['summary']['blocked_feature_gap_count']}`",
        "- Boundary: derived features only; no raw payload, no broker, no order, no trading webhook, no ranking impact.",
        "",
        "## Results",
        "",
        "| Hypothesis | Disposition | Signal Cases | Win Rate | Avg Return | Max Drawdown | Reasons |",
        "| --- | --- | ---: | ---: | ---: | ---: | --- |",
    ]
    for item in report.get("items", []):
        metrics = item.get("metrics") or {}
        win = metrics.get("source_signal_win_rate")
        avg = metrics.get("source_signal_average_return")
        dd = metrics.get("source_signal_max_drawdown")
        lines.append(
            "| "
            + " | ".join(
                [
                    f"`{item['hypothesis_id']}`",
                    f"`{item['disposition']}`",
                    str(metrics.get("source_signal_case_count")),
                    "" if win is None else f"{win:.2f}",
                    "" if avg is None else f"{avg:.4f}",
                    "" if dd is None else f"{dd:.4f}",
                    ", ".join(item.get("reasons", [])),
                ]
            )
            + " |"
        )
    if report.get("blocked_feature_gap_hypotheses"):
        lines.extend(["", "## Blocked By Feature Gaps", "", ", ".join(f"`{item}`" for item in report["blocked_feature_gap_hypotheses"])])
    if report.get("blocker"):
        lines.extend(["", "## Blocker", "", str(report["blocker"])])
    lines.append("")
    return "\n".join(lines)


def write_outputs(report: dict[str, Any], run_id: str) -> dict[str, str]:
    REPORTS.mkdir(parents=True, exist_ok=True)
    run_dir = PROCESSED / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    run_json = run_dir / "a_share_tushare_source_deep_sandbox.json"
    run_md = run_dir / "a_share_tushare_source_deep_sandbox.md"
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
                f"ready_hypothesis_count={report['summary']['ready_hypothesis_count']}",
                f"deep_sandbox_pass_candidate_count={report['summary']['deep_sandbox_pass_candidate_count']}",
                f"deep_sandbox_fail_count={report['summary']['deep_sandbox_fail_count']}",
                f"case_feature_count={report['summary']['case_feature_count']}",
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
    parser = argparse.ArgumentParser(description="Evaluate ready A-share Tushare source hypotheses with derived features.")
    parser.add_argument("--queue-json", type=Path, default=QUEUE_JSON)
    parser.add_argument("--cases-json", type=Path, default=CASES_JSON)
    parser.add_argument("--feature-coverage-json", type=Path, default=FEATURE_COVERAGE_JSON)
    parser.add_argument("--run-id", default=f"a_share_tushare_source_deep_sandbox_{datetime.now().strftime('%Y%m%dT%H%M%S')}")
    args = parser.parse_args(argv)
    command = " ".join(sys.argv)
    queue = load_json(args.queue_json, {})
    cases = load_json(args.cases_json, {})
    coverage = load_json(args.feature_coverage_json, {})
    adapter = TushareAdapter.from_env()
    if not adapter.is_configured():
        report = blocked_report("BLOCKED_MISSING_TUSHARE_TOKEN", "TUSHARE_TOKEN is not configured.", run_id=args.run_id, command=command)
    else:
        try:
            pro = adapter._require_client()
            # Run the coverage collector once as a cheap sanity check that endpoint access still works.
            collect_observations(pro, a_share_cases(cases)[:1])
            report = build_report(queue, cases, coverage, pro, run_id=args.run_id, command=command)
        except ProviderError as exc:
            report = blocked_report("BLOCKED_TUSHARE_CLIENT_UNAVAILABLE", str(exc), run_id=args.run_id, command=command)
    outputs = write_outputs(report, args.run_id)
    print(json.dumps({"status": report["status"], "summary": report["summary"], "outputs": outputs}, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
