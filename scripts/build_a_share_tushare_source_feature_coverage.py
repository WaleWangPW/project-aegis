#!/usr/bin/env python3
"""Build read-only historical feature coverage for A-share Tushare hypotheses.

This script checks whether current A-share historical cases have matching
source-specific Tushare features such as moneyflow, dragon-tiger lists,
holder concentration, factor data, and governance rows. It stores coverage
metadata only. It never stores raw Tushare payloads and never creates live
recommendations, paper trades, orders, or broker/webhook calls.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aegis.data.providers import ProviderError  # noqa: E402
from aegis.data.tushare_adapter import TushareAdapter  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "data" / "reports"
PROCESSED = ROOT / "data" / "processed" / "a_share_tushare_source_feature_coverage"
QUEUE_JSON = REPORTS / "a_share_tushare_source_hypothesis_queue_latest.json"
CASES_JSON = REPORTS / "aegis_strategy_specific_historical_cases_latest.json"
EVALUATION_JSON = REPORTS / "a_share_tushare_source_hypothesis_evaluation_latest.json"
OUT_JSON = REPORTS / "a_share_tushare_source_feature_coverage_latest.json"
OUT_MD = REPORTS / "a_share_tushare_source_feature_coverage_latest.md"
PASS_MARKER = REPORTS / "A_SHARE_TUSHARE_SOURCE_FEATURE_COVERAGE_PASS.marker"
BLOCKED_MARKER = REPORTS / "A_SHARE_TUSHARE_SOURCE_FEATURE_COVERAGE_BLOCKED.marker"

RECORD_PATHS = {
    "recommendations_jsonl": ROOT / "data" / "records" / "recommendations.jsonl",
    "paper_trades_jsonl": ROOT / "data" / "records" / "paper_trades.jsonl",
    "reviews_jsonl": ROOT / "data" / "records" / "reviews.jsonl",
    "memory_jsonl": ROOT / "data" / "records" / "memory.jsonl",
    "investment_memory_jsonl": ROOT / "data" / "records" / "investment_memory.jsonl",
    "feedback_events_jsonl": ROOT / "data" / "records" / "aegis_stock_feedback_events.jsonl",
}

REQUIRED_ENDPOINTS_BY_HYPOTHESIS = {
    "hyp_a_tushare_capital_flow_accumulation": ["moneyflow"],
    "hyp_a_tushare_dragon_tiger_seat_confirmation": ["top_list", "top_inst"],
    "hyp_a_tushare_institutional_ownership_stability": ["top10_holders", "top10_floatholders"],
    "hyp_a_tushare_holder_concentration_improvement": ["stk_holdernumber"],
    "hyp_a_tushare_factor_liquidity_quality_overlay": ["stk_factor", "daily_basic"],
    "hyp_a_tushare_governance_reward_alignment": ["stk_rewards"],
}

MIN_READY_COVERAGE = 0.50


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
    return value.replace("-", "")


def lookback_start(value: str, days: int = 540) -> str:
    date = datetime.strptime(compact_date(value), "%Y%m%d").date()
    return (date - timedelta(days=days)).strftime("%Y%m%d")


def fingerprint(path: Path) -> dict[str, Any]:
    return {
        "exists": path.exists(),
        "size": path.stat().st_size if path.exists() else None,
        "sha256": sha256(path),
    }


def fingerprints() -> dict[str, dict[str, Any]]:
    return {name: fingerprint(path) for name, path in RECORD_PATHS.items()}


def dataframe_sample_hash(df: pd.DataFrame) -> str | None:
    if df.empty:
        return None
    sample = df.head(20).to_json(orient="records", force_ascii=False, date_format="iso")
    return hashlib.sha256(sample.encode("utf-8")).hexdigest()


def endpoint_status(candidate_rows: int, error: str | None = None) -> str:
    if error:
        lower = error.lower()
        if any(token in lower for token in ("权限", "积分", "permission", "forbidden", "unauthorized")):
            return "PERMISSION_BLOCKED"
        return "ERROR"
    if candidate_rows <= 0:
        return "MISSING_FOR_CASE"
    return "PASS"


def a_share_cases(cases_report: dict[str, Any]) -> list[dict[str, Any]]:
    return [case for case in cases_report.get("historical_cases", []) if case.get("market") == "A"]


def eligible_cases_for_hypothesis(hypothesis_id: str, evaluation_report: dict[str, Any], cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    item = next((row for row in evaluation_report.get("items", []) if row.get("hypothesis_id") == hypothesis_id), None)
    symbols = set(item.get("eligible_symbols") or []) if item else set()
    if not symbols:
        return cases
    return [case for case in cases if case.get("symbol") in symbols]


def _filter_ts_code(df: pd.DataFrame, ts_code: str) -> pd.DataFrame:
    if "ts_code" not in df.columns:
        return pd.DataFrame()
    return df[df["ts_code"].astype(str) == ts_code]


def _filter_disclosed_before(df: pd.DataFrame, ts_code: str, as_of: str) -> pd.DataFrame:
    rows = _filter_ts_code(df, ts_code)
    if rows.empty or "ann_date" not in rows.columns:
        return rows
    compact = compact_date(as_of)
    return rows[rows["ann_date"].astype(str) <= compact]


def collect_observations(pro: Any, cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    observations: list[dict[str, Any]] = []
    day_cache: dict[tuple[str, str], pd.DataFrame] = {}
    symbol_cache: dict[tuple[str, str, str], pd.DataFrame] = {}

    def day_df(endpoint: str, trade_date: str, call: Callable[[], pd.DataFrame]) -> pd.DataFrame:
        key = (endpoint, trade_date)
        if key not in day_cache:
            day_cache[key] = call()
        return day_cache[key]

    def symbol_df(endpoint: str, ts_code: str, as_of: str, call: Callable[[], pd.DataFrame]) -> pd.DataFrame:
        key = (endpoint, ts_code, as_of)
        if key not in symbol_cache:
            symbol_cache[key] = call()
        return symbol_cache[key]

    endpoint_calls: dict[str, Callable[[dict[str, Any]], pd.DataFrame]] = {
        "moneyflow": lambda case: _filter_ts_code(
            day_df("moneyflow", compact_date(case["entry_date"]), lambda: pro.moneyflow(trade_date=compact_date(case["entry_date"]))),
            case["ts_code"],
        ),
        "top_list": lambda case: _filter_ts_code(
            day_df("top_list", compact_date(case["entry_date"]), lambda: pro.top_list(trade_date=compact_date(case["entry_date"]))),
            case["ts_code"],
        ),
        "top_inst": lambda case: _filter_ts_code(
            day_df("top_inst", compact_date(case["entry_date"]), lambda: pro.top_inst(trade_date=compact_date(case["entry_date"]))),
            case["ts_code"],
        ),
        "daily_basic": lambda case: _filter_ts_code(
            day_df("daily_basic", compact_date(case["entry_date"]), lambda: pro.daily_basic(trade_date=compact_date(case["entry_date"]))),
            case["ts_code"],
        ),
        "stk_factor": lambda case: _filter_ts_code(
            day_df("stk_factor", compact_date(case["entry_date"]), lambda: pro.stk_factor(trade_date=compact_date(case["entry_date"]))),
            case["ts_code"],
        ),
        "top10_holders": lambda case: _filter_disclosed_before(
            symbol_df(
                "top10_holders",
                case["ts_code"],
                case["entry_date"],
                lambda: pro.top10_holders(
                    ts_code=case["ts_code"],
                    start_date=lookback_start(case["entry_date"]),
                    end_date=compact_date(case["entry_date"]),
                ),
            ),
            case["ts_code"],
            case["entry_date"],
        ),
        "top10_floatholders": lambda case: _filter_disclosed_before(
            symbol_df(
                "top10_floatholders",
                case["ts_code"],
                case["entry_date"],
                lambda: pro.top10_floatholders(
                    ts_code=case["ts_code"],
                    start_date=lookback_start(case["entry_date"]),
                    end_date=compact_date(case["entry_date"]),
                ),
            ),
            case["ts_code"],
            case["entry_date"],
        ),
        "stk_holdernumber": lambda case: _filter_disclosed_before(
            symbol_df(
                "stk_holdernumber",
                case["ts_code"],
                case["entry_date"],
                lambda: pro.stk_holdernumber(
                    ts_code=case["ts_code"],
                    start_date=lookback_start(case["entry_date"]),
                    end_date=compact_date(case["entry_date"]),
                ),
            ),
            case["ts_code"],
            case["entry_date"],
        ),
        "stk_rewards": lambda case: _filter_disclosed_before(
            symbol_df("stk_rewards", case["ts_code"], case["entry_date"], lambda: pro.stk_rewards(ts_code=case["ts_code"])),
            case["ts_code"],
            case["entry_date"],
        ),
    }

    for case in cases:
        ts_code = str(case.get("ts_code") or "")
        if not ts_code:
            continue
        for endpoint, call in endpoint_calls.items():
            error = None
            rows = pd.DataFrame()
            try:
                candidate = call(case)
                if isinstance(candidate, pd.DataFrame):
                    rows = candidate
            except Exception as exc:  # noqa: BLE001 - Tushare endpoint errors vary
                error = str(exc)
            observations.append(
                {
                    "case_id": case.get("case_id"),
                    "symbol": case.get("symbol"),
                    "ts_code": ts_code,
                    "entry_date": case.get("entry_date"),
                    "endpoint": endpoint,
                    "status": endpoint_status(len(rows.index), error),
                    "candidate_row_count": int(len(rows.index)),
                    "columns": list(map(str, rows.columns[:24])) if isinstance(rows, pd.DataFrame) else [],
                    "sample_hash": dataframe_sample_hash(rows),
                    "error_message": error[:240] if error else None,
                }
            )
    return observations


def build_feature_coverage_report(
    queue: dict[str, Any],
    cases_report: dict[str, Any],
    evaluation_report: dict[str, Any],
    observations: list[dict[str, Any]],
    *,
    run_id: str,
    network_used: bool,
    command: str,
) -> dict[str, Any]:
    before = fingerprints()
    cases = a_share_cases(cases_report)
    by_case_endpoint = {(item["case_id"], item["endpoint"]): item for item in observations}
    items: list[dict[str, Any]] = []

    for hypothesis in queue.get("hypotheses", []):
        hypothesis_id = hypothesis.get("hypothesis_id")
        required = REQUIRED_ENDPOINTS_BY_HYPOTHESIS.get(hypothesis_id, [])
        eligible = eligible_cases_for_hypothesis(hypothesis_id, evaluation_report, cases)
        endpoint_results: list[dict[str, Any]] = []
        for endpoint in required:
            endpoint_obs = [by_case_endpoint.get((case.get("case_id"), endpoint)) for case in eligible]
            endpoint_obs = [item for item in endpoint_obs if item]
            covered = sum(1 for item in endpoint_obs if item.get("status") == "PASS")
            total = len(eligible)
            endpoint_results.append(
                {
                    "endpoint": endpoint,
                    "eligible_case_count": total,
                    "covered_case_count": covered,
                    "coverage_ratio": covered / total if total else None,
                    "missing_case_count": total - covered,
                    "blocked_or_error_count": sum(1 for item in endpoint_obs if item.get("status") in {"ERROR", "PERMISSION_BLOCKED"}),
                }
            )
        ratios = [item["coverage_ratio"] for item in endpoint_results if item["coverage_ratio"] is not None]
        min_coverage = min(ratios) if ratios else 0.0
        feature_status = "READY_FOR_DEEP_SANDBOX" if required and min_coverage >= MIN_READY_COVERAGE else "FEATURE_GAPS"
        items.append(
            {
                "hypothesis_id": hypothesis_id,
                "title": hypothesis.get("title"),
                "required_endpoints": required,
                "eligible_symbols": sorted({case.get("symbol") for case in eligible}),
                "eligible_case_count": len(eligible),
                "min_endpoint_coverage": min_coverage,
                "feature_status": feature_status,
                "endpoint_results": endpoint_results,
                "allowed_next_step": "run_deep_source_specific_sandbox" if feature_status == "READY_FOR_DEEP_SANDBOX" else "collect_more_source_feature_history",
                "simulation_only": True,
                "user_facing_suggestion_allowed": False,
                "real_trade_allowed": False,
            }
        )
    after = fingerprints()
    status = "PASS" if queue.get("hypothesis_count", 0) and cases and observations else "BLOCKED_NO_FEATURE_OBSERVATIONS"
    report = {
        "type": "a_share_tushare_source_feature_coverage",
        "status": status,
        "generated_at": now_iso(),
        "run_id": run_id,
        "command": command,
        "thresholds": {"min_ready_coverage": MIN_READY_COVERAGE},
        "summary": {
            "hypothesis_count": len(items),
            "ready_for_deep_sandbox_count": sum(1 for item in items if item["feature_status"] == "READY_FOR_DEEP_SANDBOX"),
            "feature_gap_count": sum(1 for item in items if item["feature_status"] == "FEATURE_GAPS"),
            "a_share_case_count": len(cases),
            "observation_count": len(observations),
            "network_used": network_used,
            "user_facing_suggestion_allowed": False,
            "next_stage": "Deep source-specific sandbox may run only for READY_FOR_DEEP_SANDBOX hypotheses.",
        },
        "items": items,
        "observation_summary": {
            "pass_count": sum(1 for item in observations if item["status"] == "PASS"),
            "missing_count": sum(1 for item in observations if item["status"] == "MISSING_FOR_CASE"),
            "error_count": sum(1 for item in observations if item["status"] == "ERROR"),
            "permission_blocked_count": sum(1 for item in observations if item["status"] == "PERMISSION_BLOCKED"),
            "endpoints": sorted({item["endpoint"] for item in observations}),
        },
        "source_reports": {
            "source_hypothesis_queue": str(QUEUE_JSON),
            "strategy_specific_historical_cases": str(CASES_JSON),
            "source_hypothesis_evaluation": str(EVALUATION_JSON),
        },
        "source_hashes": {
            "source_hypothesis_queue": sha256(QUEUE_JSON),
            "strategy_specific_historical_cases": sha256(CASES_JSON),
            "source_hypothesis_evaluation": sha256(EVALUATION_JSON),
        },
        "checks": {
            "source_queue_present": queue.get("hypothesis_count", 0) > 0,
            "a_share_cases_present": bool(cases),
            "observations_present": bool(observations),
            "raw_payload_saved": False,
            "production_records_unchanged": before == after,
            "no_broker_api": True,
            "no_webhook": True,
            "no_order_placement": True,
            "no_position_size": True,
        },
        "safety": {
            "simulation_only": True,
            "research_only": True,
            "metadata_only": True,
            "raw_payload_saved": False,
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
    checks = report["checks"]
    pass_checks = (
        checks["source_queue_present"]
        and checks["a_share_cases_present"]
        and checks["observations_present"]
        and checks["raw_payload_saved"] is False
        and checks["production_records_unchanged"]
        and checks["no_broker_api"]
        and checks["no_webhook"]
        and checks["no_order_placement"]
        and checks["no_position_size"]
    )
    if not pass_checks:
        report["status"] = "BLOCKED_CHECK_FAILED"
    return report


def blocked_report(status: str, message: str, *, run_id: str, command: str) -> dict[str, Any]:
    return {
        "type": "a_share_tushare_source_feature_coverage",
        "status": status,
        "generated_at": now_iso(),
        "run_id": run_id,
        "command": command,
        "blocker": message,
        "summary": {
            "hypothesis_count": 0,
            "ready_for_deep_sandbox_count": 0,
            "feature_gap_count": 0,
            "a_share_case_count": 0,
            "observation_count": 0,
            "network_used": False,
            "user_facing_suggestion_allowed": False,
        },
        "items": [],
        "checks": {
            "raw_payload_saved": False,
            "no_broker_api": True,
            "no_webhook": True,
            "no_order_placement": True,
            "no_position_size": True,
        },
        "safety": {
            "simulation_only": True,
            "research_only": True,
            "metadata_only": True,
            "raw_payload_saved": False,
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
        "# A-share Tushare Source Feature Coverage",
        "",
        f"- Status: `{report['status']}`",
        f"- Generated At: `{report['generated_at']}`",
        f"- Ready For Deep Sandbox: `{report['summary']['ready_for_deep_sandbox_count']}`",
        f"- Feature Gaps: `{report['summary']['feature_gap_count']}`",
        f"- Observations: `{report['summary']['observation_count']}`",
        "- Boundary: metadata-only; no raw payload, no broker, no order, no trading webhook.",
        "",
        "## Hypotheses",
        "",
        "| Hypothesis | Feature Status | Cases | Min Coverage | Required Endpoints |",
        "| --- | --- | ---: | ---: | --- |",
    ]
    for item in report.get("items", []):
        lines.append(
            "| "
            + " | ".join(
                [
                    f"`{item['hypothesis_id']}`",
                    f"`{item['feature_status']}`",
                    str(item.get("eligible_case_count")),
                    f"{item.get('min_endpoint_coverage', 0):.2f}",
                    ", ".join(item.get("required_endpoints", [])),
                ]
            )
            + " |"
        )
    if report.get("blocker"):
        lines.extend(["", "## Blocker", "", str(report["blocker"])])
    lines.append("")
    return "\n".join(lines)


def write_outputs(report: dict[str, Any], run_id: str) -> dict[str, str]:
    REPORTS.mkdir(parents=True, exist_ok=True)
    run_dir = PROCESSED / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    run_json = run_dir / "a_share_tushare_source_feature_coverage.json"
    run_md = run_dir / "a_share_tushare_source_feature_coverage.md"
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
                f"ready_for_deep_sandbox_count={report['summary']['ready_for_deep_sandbox_count']}",
                f"feature_gap_count={report['summary']['feature_gap_count']}",
                f"observation_count={report['summary']['observation_count']}",
                f"network_used={str(report['summary'].get('network_used')).lower()}",
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
    return {"run_json": str(run_json), "run_md": str(run_md), "latest_json": str(OUT_JSON), "latest_md": str(OUT_MD), "marker": str(marker)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build read-only Tushare source feature coverage for A-share hypotheses.")
    parser.add_argument("--queue-json", type=Path, default=QUEUE_JSON)
    parser.add_argument("--cases-json", type=Path, default=CASES_JSON)
    parser.add_argument("--evaluation-json", type=Path, default=EVALUATION_JSON)
    parser.add_argument("--run-id", default=f"a_share_tushare_source_feature_coverage_{datetime.now().strftime('%Y%m%dT%H%M%S')}")
    args = parser.parse_args(argv)
    command = " ".join(sys.argv)
    queue = load_json(args.queue_json, {})
    cases_report = load_json(args.cases_json, {})
    evaluation_report = load_json(args.evaluation_json, {})
    cases = a_share_cases(cases_report)

    adapter = TushareAdapter.from_env()
    if not adapter.is_configured():
        report = blocked_report("BLOCKED_MISSING_TUSHARE_TOKEN", "TUSHARE_TOKEN is not configured.", run_id=args.run_id, command=command)
    else:
        try:
            pro = adapter._require_client()
            observations = collect_observations(pro, cases)
            report = build_feature_coverage_report(queue, cases_report, evaluation_report, observations, run_id=args.run_id, network_used=True, command=command)
        except ProviderError as exc:
            report = blocked_report("BLOCKED_TUSHARE_CLIENT_UNAVAILABLE", str(exc), run_id=args.run_id, command=command)
    outputs = write_outputs(report, args.run_id)
    print(json.dumps({"status": report["status"], "summary": report["summary"], "outputs": outputs}, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
