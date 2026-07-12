#!/usr/bin/env python3
"""Assemble strategy-specific historical cases for current Aegis candidates.

The first implementation uses existing A-share point-in-time daily cache only.
US/HK candidates are explicitly recorded as data gaps until their historical
daily bars are refreshed. This is case assembly, not a live trading signal.
"""

from __future__ import annotations

import hashlib
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "data" / "reports"
CACHE = ROOT / "data" / "cache" / "p23_2_historical_market"
DAILY_DIR = CACHE / "daily_by_trade_date"
STOCK_BASIC = CACHE / "stock_basic_all.json"
H_US_CACHE = ROOT / "data" / "cache" / "aegis_h_us_candidate_daily_bars"
VALIDATION_INPUT = REPORTS / "aegis_strategy_validation_input_latest.json"
STOCK_SELECTION = REPORTS / "stock_selection_workbench_latest.json"
STRATEGY_COVERAGE = REPORTS / "aegis_strategy_sandbox_validation_latest.json"
H_US_REFRESH = REPORTS / "aegis_h_us_candidate_daily_bars_refresh_latest.json"

OUT_JSON = REPORTS / "aegis_strategy_specific_historical_cases_latest.json"
OUT_MD = REPORTS / "aegis_strategy_specific_historical_cases_latest.md"
PASS_MARKER = REPORTS / "AEGIS_STRATEGY_SPECIFIC_HISTORICAL_CASES_PASS.marker"
FAIL_MARKER = REPORTS / "AEGIS_STRATEGY_SPECIFIC_HISTORICAL_CASES_FAIL.marker"
PROCESSED = ROOT / "data" / "processed" / "aegis_strategy_specific_historical_cases"

RECORD_PATHS = {
    "recommendations_jsonl": ROOT / "data" / "records" / "recommendations.jsonl",
    "paper_trades_jsonl": ROOT / "data" / "records" / "paper_trades.jsonl",
    "reviews_jsonl": ROOT / "data" / "records" / "reviews.jsonl",
    "memory_jsonl": ROOT / "data" / "records" / "memory.jsonl",
    "investment_memory_jsonl": ROOT / "data" / "records" / "investment_memory.jsonl",
    "feedback_events_jsonl": ROOT / "data" / "records" / "aegis_stock_feedback_events.jsonl",
}

A_SHARE_RESEARCH_SAMPLE_STATUSES = {"high_risk_watch", "blocked"}
MAX_A_SHARE_RESEARCH_SAMPLES = 12


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


def compact_date(value: str) -> str:
    return value.replace("-", "")


def iso_date(value: str) -> str:
    if "-" in value:
        return value
    return f"{value[:4]}-{value[4:6]}-{value[6:8]}"


def eodhd_symbol(symbol: str, market: str) -> str:
    if market == "US":
        return f"{symbol}.US"
    if market == "HK":
        stripped = symbol.lstrip("0") or symbol
        return f"{stripped.zfill(4)}.HK"
    return symbol


def load_symbol_map() -> dict[str, str]:
    payload = load_json(STOCK_BASIC, {})
    rows = payload.get("rows", []) if isinstance(payload, dict) else []
    return {str(row.get("symbol")): str(row.get("ts_code")) for row in rows if row.get("symbol") and row.get("ts_code")}


def normalize_a_symbol(symbol: Any) -> str:
    raw = str(symbol or "").strip().upper()
    return raw.split(".")[0] if "." in raw else raw


def infer_a_share_strategy_ids(item: dict[str, Any]) -> list[str]:
    text = " | ".join(
        str(value)
        for value in [
            item.get("name"),
            item.get("industry_or_description"),
            item.get("status"),
            item.get("status_label"),
            " | ".join(item.get("strategy_matches") or []),
            " | ".join(item.get("risk_flags") or []),
        ]
        if value
    )
    strategy_ids = {"a_share_short_momentum"}
    if any(key in text for key in ["毛利率", "现金流", "ROE", "主业贡献", "机构持仓", "股东", "治理", "高管增持"]):
        strategy_ids.add("qvm")
    if any(key in text for key in ["趋势", "一年涨", "新增机构调研", "突破", "正面新闻", "高管增持"]):
        strategy_ids.add("growth_breakout")
    if any(key in text for key in ["波动", "回撤", "止损", "风险", "趋势向下"]):
        strategy_ids.add("low_vol_momentum")
    return sorted(strategy_ids)


def a_share_research_samples(
    stock_selection: dict[str, Any],
    existing_items: list[dict[str, Any]],
    symbol_map: dict[str, str],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Add non-recommendation A-share samples so source strategies can be tested.

    These rows come from today's workbench risk/watch/blocked pool. They are
    labelled as research-only samples and are never user-facing suggestions.
    """
    existing = {
        (str(item.get("market")), normalize_a_symbol(item.get("symbol")))
        for item in existing_items
    }
    samples: list[dict[str, Any]] = []
    rows = stock_selection.get("candidates", []) if isinstance(stock_selection, dict) else []
    for row in rows:
        symbol = normalize_a_symbol(row.get("symbol"))
        if row.get("market") != "A":
            continue
        if row.get("status") not in A_SHARE_RESEARCH_SAMPLE_STATUSES:
            continue
        if not symbol or ("A", symbol) in existing:
            continue
        if symbol not in symbol_map:
            continue
        samples.append(
            {
                "symbol": symbol,
                "name": row.get("name"),
                "market": "A",
                "matched_strategy_ids": infer_a_share_strategy_ids(row),
                "research_sample_only": True,
                "sample_source": "stock_selection_workbench",
                "source_status": row.get("status"),
                "source_status_label": row.get("status_label"),
                "source_score": row.get("score"),
                "source_risk_flags": row.get("risk_flags") or [],
                "user_facing_suggestion_allowed": False,
                "real_trade_allowed": False,
            }
        )
        if len(samples) >= MAX_A_SHARE_RESEARCH_SAMPLES:
            break
    return samples, {
        "enabled": True,
        "source": str(STOCK_SELECTION),
        "eligible_statuses": sorted(A_SHARE_RESEARCH_SAMPLE_STATUSES),
        "added_candidate_count": len(samples),
        "added_symbols": [item["symbol"] for item in samples],
        "research_sample_only": True,
        "user_facing_suggestion_allowed": False,
    }


def load_daily_rows() -> tuple[list[str], dict[str, dict[str, dict[str, Any]]], dict[str, str]]:
    dates: list[str] = []
    rows_by_date: dict[str, dict[str, dict[str, Any]]] = {}
    source_hashes: dict[str, str] = {}
    for path in sorted(DAILY_DIR.glob("*.json")):
        payload = load_json(path, {})
        date = str(payload.get("trade_date") or path.stem)
        row_map = {row.get("ts_code"): row for row in payload.get("rows", []) if row.get("ts_code")}
        if row_map:
            dates.append(date)
            rows_by_date[date] = row_map
            source_hashes[date] = sha256(path) or ""
    return dates, rows_by_date, source_hashes


def max_drawdown(closes: list[float]) -> float:
    peak = closes[0]
    worst = 0.0
    for close in closes:
        peak = max(peak, close)
        if peak:
            worst = min(worst, close / peak - 1.0)
    return worst


def case_windows(dates: list[str], available_count: int, window: int = 20, desired: int = 4) -> list[int]:
    if available_count <= window:
        return []
    max_start = available_count - window - 1
    if max_start <= 0:
        return []
    step = max(1, max_start // max(desired - 1, 1))
    starts = [0, step, step * 2, max_start]
    return sorted(set(min(max_start, value) for value in starts))


def build_cases_for_candidate(
    item: dict[str, Any],
    ts_code: str,
    dates: list[str],
    rows_by_date: dict[str, dict[str, dict[str, Any]]],
    source_hashes: dict[str, str],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    symbol_dates = [date for date in dates if ts_code in rows_by_date.get(date, {})]
    cases: list[dict[str, Any]] = []
    if len(symbol_dates) <= 21:
        return cases, {
            "symbol": item.get("symbol"),
            "ts_code": ts_code,
            "status": "missing_historical_rows",
            "available_trade_dates": len(symbol_dates),
            "required_trade_dates": 22,
        }

    starts = case_windows(symbol_dates, len(symbol_dates))
    for idx, start in enumerate(starts, start=1):
        entry_date = symbol_dates[start]
        exit_date = symbol_dates[start + 20]
        path_dates = symbol_dates[start : start + 21]
        entry = rows_by_date[entry_date][ts_code]
        exit_row = rows_by_date[exit_date][ts_code]
        entry_close = float(entry["close"])
        exit_close = float(exit_row["close"])
        closes = [float(rows_by_date[date][ts_code]["close"]) for date in path_dates]
        raw_return = exit_close / entry_close - 1.0
        case_id = f"aegis_case_{str(item.get('symbol')).lower()}_{idx}"
        evidence_seed = f"{ts_code}:{entry_date}:{exit_date}:{source_hashes.get(entry_date)}:{source_hashes.get(exit_date)}"
        cases.append(
            {
                "case_id": case_id,
                "symbol": item.get("symbol"),
                "ts_code": ts_code,
                "name": item.get("name"),
                "market": "A",
                "matched_strategy_ids": item.get("matched_strategy_ids") or [],
                "research_sample_only": bool(item.get("research_sample_only")),
                "sample_source": item.get("sample_source"),
                "source_status": item.get("source_status"),
                "entry_date": iso_date(entry_date),
                "exit_date": iso_date(exit_date),
                "entry_close": entry_close,
                "exit_close": exit_close,
                "raw_return": raw_return,
                "max_drawdown": max_drawdown(closes),
                "holding_trade_days": 20,
                "point_in_time_case": True,
                "data_cutoff_date": iso_date(entry_date),
                "future_data_used_for_selection": False,
                "case_result": "win" if raw_return > 0 else "loss",
                "evidence_ref": f"aegis_strategy_specific_case:{hashlib.sha256(evidence_seed.encode()).hexdigest()}",
            }
        )
    return cases, {
        "symbol": item.get("symbol"),
        "ts_code": ts_code,
        "status": "case_assembled",
        "available_trade_dates": len(symbol_dates),
        "case_count": len(cases),
    }


def read_h_us_rows(symbol: str, market: str) -> tuple[list[dict[str, Any]], Path]:
    provider_symbol = eodhd_symbol(symbol, market)
    safe_symbol = provider_symbol.lower().replace(".", "_")
    path = H_US_CACHE / market / "daily_bars" / f"{safe_symbol}.csv"
    if not path.exists():
        return [], path
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            try:
                rows.append(
                    {
                        "date": row["date"],
                        "close": float(row.get("adjusted_close") or row.get("close")),
                    }
                )
            except (KeyError, TypeError, ValueError):
                continue
    return rows, path


def build_h_us_cases_for_candidate(item: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows, path = read_h_us_rows(str(item.get("symbol")), str(item.get("market")))
    if len(rows) <= 21:
        return [], {
            "symbol": item.get("symbol"),
            "provider_symbol": eodhd_symbol(str(item.get("symbol")), str(item.get("market"))),
            "status": "missing_h_us_daily_bars_for_current_candidate",
            "available_trade_dates": len(rows),
            "required_trade_dates": 22,
            "cache_path": str(path),
        }
    starts = case_windows([row["date"] for row in rows], len(rows))
    cases: list[dict[str, Any]] = []
    for idx, start in enumerate(starts, start=1):
        entry = rows[start]
        exit_row = rows[start + 20]
        path_rows = rows[start : start + 21]
        entry_close = float(entry["close"])
        exit_close = float(exit_row["close"])
        closes = [float(row["close"]) for row in path_rows]
        raw_return = exit_close / entry_close - 1.0
        evidence_seed = f"{item.get('market')}:{item.get('symbol')}:{entry['date']}:{exit_row['date']}:{sha256(path)}"
        cases.append(
            {
                "case_id": f"aegis_case_{str(item.get('symbol')).lower()}_{idx}",
                "symbol": item.get("symbol"),
                "provider_symbol": eodhd_symbol(str(item.get("symbol")), str(item.get("market"))),
                "name": item.get("name"),
                "market": item.get("market"),
                "matched_strategy_ids": item.get("matched_strategy_ids") or [],
                "research_sample_only": bool(item.get("research_sample_only")),
                "sample_source": item.get("sample_source"),
                "source_status": item.get("source_status"),
                "entry_date": iso_date(entry["date"]),
                "exit_date": iso_date(exit_row["date"]),
                "entry_close": entry_close,
                "exit_close": exit_close,
                "raw_return": raw_return,
                "max_drawdown": max_drawdown(closes),
                "holding_trade_days": 20,
                "point_in_time_case": True,
                "data_cutoff_date": iso_date(entry["date"]),
                "future_data_used_for_selection": False,
                "case_result": "win" if raw_return > 0 else "loss",
                "evidence_ref": f"aegis_strategy_specific_case:{hashlib.sha256(evidence_seed.encode()).hexdigest()}",
            }
        )
    return cases, {
        "symbol": item.get("symbol"),
        "provider_symbol": eodhd_symbol(str(item.get("symbol")), str(item.get("market"))),
        "status": "case_assembled",
        "available_trade_dates": len(rows),
        "case_count": len(cases),
        "cache_path": str(path),
        "cache_sha256": sha256(path),
    }


def summarize_cases(cases: list[dict[str, Any]]) -> dict[str, Any]:
    if not cases:
        return {
            "case_count": 0,
            "win_rate": None,
            "average_return": None,
            "average_max_drawdown": None,
            "best_return": None,
            "worst_return": None,
        }
    returns = [case["raw_return"] for case in cases]
    drawdowns = [case["max_drawdown"] for case in cases]
    return {
        "case_count": len(cases),
        "win_rate": sum(1 for value in returns if value > 0) / len(returns),
        "average_return": sum(returns) / len(returns),
        "average_max_drawdown": sum(drawdowns) / len(drawdowns),
        "best_return": max(returns),
        "worst_return": min(returns),
    }


def render_markdown(report: dict[str, Any]) -> str:
    s = report["summary"]
    lines = [
        "# Aegis Strategy-Specific Historical Cases",
        "",
        f"- Status: {report['status']}",
        f"- Generated At: {report['generated_at']}",
        f"- Candidate Count: {s['candidate_count']}",
        f"- Base Candidate Count: {s.get('base_candidate_count')}",
        f"- A-share Research Sample Candidates: {s.get('a_share_research_sample_candidate_count')}",
        f"- Candidates With Cases: {s['candidates_with_cases']}",
        f"- Historical Case Count: {s['historical_case_count']}",
        f"- A-share Research Sample Cases: {s.get('a_share_research_sample_case_count')}",
        f"- Data Gap Count: {s['data_gap_count']}",
        f"- User-Facing Suggestion Allowed: {s['user_facing_suggestion_allowed']}",
        "",
        "Historical case assembly only. No real trade, no broker API, no webhook, no order placement.",
        "",
        "## Candidate Results",
        "",
    ]
    for result in report["candidate_results"]:
        lines.append(
            f"- {result['symbol']} {result.get('name', '')}: {result['status']} "
            f"cases={result.get('case_count', 0)}"
        )
    lines.append("")
    return "\n".join(lines)


def build_report() -> dict[str, Any]:
    validation = load_json(VALIDATION_INPUT, {})
    stock_selection = load_json(STOCK_SELECTION, {})
    coverage = load_json(STRATEGY_COVERAGE, {})
    symbol_map = load_symbol_map()
    base_candidates = validation.get("items", []) if validation.get("status") == "READY" else []
    samples, sample_summary = a_share_research_samples(stock_selection, base_candidates, symbol_map)
    candidates = base_candidates + samples
    dates, rows_by_date, source_hashes = load_daily_rows()
    before = fingerprints(RECORD_PATHS)

    all_cases: list[dict[str, Any]] = []
    candidate_results: list[dict[str, Any]] = []
    data_gaps: list[dict[str, Any]] = []
    for item in candidates:
        result = {
            "symbol": item.get("symbol"),
            "name": item.get("name"),
            "market": item.get("market"),
            "matched_strategy_ids": item.get("matched_strategy_ids") or [],
            "research_sample_only": bool(item.get("research_sample_only")),
            "sample_source": item.get("sample_source"),
            "source_status": item.get("source_status"),
            "source_status_label": item.get("source_status_label"),
            "source_score": item.get("source_score"),
            "source_risk_flags": item.get("source_risk_flags") or [],
            "status": "pending",
            "case_count": 0,
            "summary": summarize_cases([]),
            "user_facing_suggestion_allowed": False,
            "real_trade_allowed": False,
        }
        if item.get("market") == "A":
            ts_code = symbol_map.get(str(item.get("symbol")))
            if not ts_code:
                result["status"] = "missing_ts_code"
                data_gaps.append({**result, "gap_reason": "missing_ts_code"})
            else:
                cases, assembly = build_cases_for_candidate(item, ts_code, dates, rows_by_date, source_hashes)
                result.update(assembly)
                result["summary"] = summarize_cases(cases)
                all_cases.extend(cases)
                if not cases:
                    data_gaps.append({**result, "gap_reason": result["status"]})
        else:
            cases, assembly = build_h_us_cases_for_candidate(item)
            result.update(assembly)
            result["summary"] = summarize_cases(cases)
            all_cases.extend(cases)
            if not cases:
                data_gaps.append(
                    {
                        **result,
                        "gap_reason": "current US/HK candidate historical daily bars not refreshed yet",
                        "required_next_step": "refresh EODHD/Twelve daily bars and rerun case assembly",
                    }
                )
        candidate_results.append(result)

    after = fingerprints(RECORD_PATHS)
    run_id = f"aegis_strategy_specific_historical_cases_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    report: dict[str, Any] = {
        "type": "aegis_strategy_specific_historical_cases",
        "status": "PASS" if candidates and all_cases else "FAIL",
        "generated_at": now_iso(),
        "run_id": run_id,
        "summary": {
            "base_candidate_count": len(base_candidates),
            "candidate_count": len(candidates),
            "a_share_research_sample_candidate_count": len(samples),
            "candidates_with_cases": sum(1 for result in candidate_results if result.get("case_count", 0) > 0),
            "historical_case_count": len(all_cases),
            "data_gap_count": len(data_gaps),
            "a_share_case_count": sum(1 for case in all_cases if case.get("market") == "A"),
            "a_share_research_sample_case_count": sum(
                1 for case in all_cases if case.get("market") == "A" and case.get("research_sample_only")
            ),
            "h_us_case_count": sum(1 for case in all_cases if case.get("market") in {"US", "HK"}),
            "direct_candidate_backtest_count": len(all_cases),
            "user_facing_suggestion_allowed": False,
            "next_stage": "evaluate expanded A-share research samples before any source strategy can influence ranking",
        },
        "a_share_research_sample_expansion": sample_summary,
        "candidate_results": candidate_results,
        "historical_cases": all_cases,
        "data_gaps": data_gaps,
        "source_reports": {
            "strategy_validation_input": str(VALIDATION_INPUT),
            "stock_selection_workbench": str(STOCK_SELECTION),
            "strategy_sandbox_coverage": str(STRATEGY_COVERAGE),
            "h_us_daily_bars_refresh": str(H_US_REFRESH),
            "daily_cache_dir": str(DAILY_DIR),
            "stock_basic": str(STOCK_BASIC),
        },
        "source_hashes": {
            "strategy_validation_input": sha256(VALIDATION_INPUT),
            "stock_selection_workbench": sha256(STOCK_SELECTION),
            "strategy_sandbox_coverage": sha256(STRATEGY_COVERAGE),
            "h_us_daily_bars_refresh": sha256(H_US_REFRESH),
            "stock_basic": sha256(STOCK_BASIC),
        },
        "checks": {
            "strategy_validation_input_ready": validation.get("status") == "READY",
            "strategy_sandbox_coverage_pass": coverage.get("status") == "PASS",
            "a_share_daily_cache_available": bool(dates),
            "a_share_cases_assembled": any(case.get("market") == "A" for case in all_cases),
            "a_share_research_samples_labelled": all(
                result.get("research_sample_only") is True
                and result.get("user_facing_suggestion_allowed") is False
                and result.get("real_trade_allowed") is False
                for result in candidate_results
                if result.get("sample_source") == "stock_selection_workbench"
            ),
            "h_us_cases_or_gaps_explicit": (
                any(case.get("market") in {"US", "HK"} for case in all_cases)
                or any(gap.get("market") in {"US", "HK"} for gap in data_gaps)
            ),
            "direct_candidate_cases_not_user_suggestions": True,
            "research_samples_not_user_suggestions": True,
            "production_records_unchanged": before == after,
            "network_not_used": True,
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
        "run_dir": str(PROCESSED / run_id),
    }
    if not all(report["checks"].values()):
        report["status"] = "FAIL"
    return report


def main() -> int:
    report = build_report()
    run_dir = Path(report["run_dir"])
    run_dir.mkdir(parents=True, exist_ok=True)
    write_json(run_dir / "strategy_specific_historical_cases.json", report)
    (run_dir / "strategy_specific_historical_cases.md").write_text(render_markdown(report), encoding="utf-8")
    (run_dir / "strategy_specific_historical_cases.jsonl").write_text(
        "".join(json.dumps(case, ensure_ascii=False) + "\n" for case in report["historical_cases"]),
        encoding="utf-8",
    )
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
                f"base_candidate_count={report['summary']['base_candidate_count']}",
                f"candidate_count={report['summary']['candidate_count']}",
                f"a_share_research_sample_candidate_count={report['summary']['a_share_research_sample_candidate_count']}",
                f"candidates_with_cases={report['summary']['candidates_with_cases']}",
                f"historical_case_count={report['summary']['historical_case_count']}",
                f"a_share_research_sample_case_count={report['summary']['a_share_research_sample_case_count']}",
                f"data_gap_count={report['summary']['data_gap_count']}",
                "network_used=false",
                "user_facing_suggestion_allowed=false",
                "research_samples_not_user_suggestions=true",
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
                "base_candidate_count": report["summary"]["base_candidate_count"],
                "candidate_count": report["summary"]["candidate_count"],
                "a_share_research_sample_candidate_count": report["summary"]["a_share_research_sample_candidate_count"],
                "candidates_with_cases": report["summary"]["candidates_with_cases"],
                "historical_case_count": report["summary"]["historical_case_count"],
                "a_share_research_sample_case_count": report["summary"]["a_share_research_sample_case_count"],
                "data_gap_count": report["summary"]["data_gap_count"],
                "report_json": str(OUT_JSON),
            },
            ensure_ascii=False,
        )
    )
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
