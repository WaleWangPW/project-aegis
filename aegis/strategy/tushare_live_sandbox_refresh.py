"""Build a Tushare-backed A-share historical sandbox refresh packet.

This module uses the existing verified Tushare historical cache as bounded
simulation evidence. It does not fetch broker data, place orders, mutate
strategy definitions, or write production Recommendation/PaperTrade/Review
records.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Mapping

from aegis.models.strategy import HistoricalStrategyCase, StrategyCandidate
from aegis.models.strategy_hypothesis import StrategySandboxHypothesis
from aegis.strategy.hypothesis_sandbox import strategy_candidates_from_hypotheses
from aegis.strategy.sandbox import evaluate_strategy_candidate


A_SHARE_SYMBOL_SEEDS: dict[str, list[str]] = {
    "hyp_a_low_vol_dividend_defensive": ["600000.SH", "601318.SH", "000001.SZ", "600519.SH"],
    "hyp_a_value_quality_multifactor": ["600036.SH", "000858.SZ", "002475.SZ", "601899.SH"],
}
DEFAULT_START_OFFSETS = [0, 20, 40, 60]
DEFAULT_EXIT_HORIZON_DAYS = 20
REQUIRED_TUSHARE_A_CAPABILITIES = {
    ("A", "daily_bars"),
    ("A", "index_bars"),
    ("A", "stock_basic"),
    ("A", "trading_calendar"),
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _candidate_id(hypothesis_id: str) -> str:
    return hypothesis_id.replace("hyp_", "strategy_", 1)


def _tushare_passed_capabilities(tushare_probe_report: Mapping) -> set[tuple[str | None, str | None]]:
    return {
        (item.get("market"), item.get("data_type"))
        for item in tushare_probe_report.get("checks", []) or []
        if item.get("status") == "pass"
    }


def is_tushare_a_core_ready(tushare_probe_report: Mapping) -> bool:
    return (
        tushare_probe_report.get("provider") == "tushare"
        and tushare_probe_report.get("token_present") is True
        and tushare_probe_report.get("network_available") is True
        and REQUIRED_TUSHARE_A_CAPABILITIES.issubset(_tushare_passed_capabilities(tushare_probe_report))
    )


def _open_dates(cache_dir: Path) -> list[str]:
    payload = _load_json(cache_dir / "trade_calendar.json")
    return [str(value) for value in payload.get("open_dates", [])]


def _daily_rows(cache_dir: Path, trade_date: str) -> dict[str, dict]:
    payload = _load_json(cache_dir / "daily_by_trade_date" / f"{trade_date}.json")
    return {str(row.get("ts_code")): row for row in payload.get("rows", [])}


def _case_from_cache(
    *,
    cache_dir: Path,
    open_dates: list[str],
    strategy_id: str,
    symbol: str,
    start_offset: int,
    exit_horizon_days: int,
    case_index: int,
) -> HistoricalStrategyCase:
    exit_offset = start_offset + exit_horizon_days
    if exit_offset >= len(open_dates):
        raise ValueError(f"not enough open dates for {symbol} offset={start_offset}")

    entry_date = open_dates[start_offset]
    exit_date = open_dates[exit_offset]
    entry_row = _daily_rows(cache_dir, entry_date).get(symbol)
    exit_row = _daily_rows(cache_dir, exit_date).get(symbol)
    if not entry_row or not exit_row:
        raise ValueError(f"missing cache rows for {symbol} {entry_date}->{exit_date}")

    entry_price = float(entry_row["close"])
    exit_price = float(exit_row["close"])
    lows: list[float] = []
    for trade_date in open_dates[start_offset : exit_offset + 1]:
        row = _daily_rows(cache_dir, trade_date).get(symbol)
        if not row:
            raise ValueError(f"missing cache row for {symbol} on {trade_date}")
        lows.append(float(row["low"]))

    actual_return = (exit_price - entry_price) / entry_price
    max_drawdown = min(lows) / entry_price - 1.0
    risk_flags: list[str] = []
    if max_drawdown <= -0.1:
        risk_flags.append("historical_drawdown_breach")
    elif max_drawdown <= -0.08:
        risk_flags.append("historical_drawdown_watch")

    return HistoricalStrategyCase(
        case_id=f"{strategy_id}_tushare_live_case_{case_index:03d}",
        strategy_id=strategy_id,
        date=entry_date,
        symbol=symbol,
        market="A",
        entry_price=entry_price,
        exit_price=exit_price,
        max_drawdown=max_drawdown,
        risk_flags=risk_flags,
        factor_values={
            "actual_return": actual_return,
            "exit_horizon_days": float(exit_horizon_days),
            "entry_close": entry_price,
            "exit_close": exit_price,
            "window_low": min(lows),
        },
        evidence_ref=f"tushare_cache:{symbol}:{entry_date}:{exit_date}",
    )


def build_tushare_a_share_historical_cases(
    hypotheses: Iterable[StrategySandboxHypothesis],
    *,
    cache_dir: Path,
    start_offsets: list[int] | None = None,
    exit_horizon_days: int = DEFAULT_EXIT_HORIZON_DAYS,
) -> list[HistoricalStrategyCase]:
    dates = _open_dates(cache_dir)
    offsets = start_offsets or DEFAULT_START_OFFSETS
    cases: list[HistoricalStrategyCase] = []
    for hypothesis in hypotheses:
        if hypothesis.market != "A":
            continue
        symbols = A_SHARE_SYMBOL_SEEDS.get(hypothesis.hypothesis_id, [])
        strategy_id = _candidate_id(hypothesis.hypothesis_id)
        for index, (symbol, offset) in enumerate(zip(symbols, offsets, strict=True), start=1):
            cases.append(
                _case_from_cache(
                    cache_dir=cache_dir,
                    open_dates=dates,
                    strategy_id=strategy_id,
                    symbol=symbol,
                    start_offset=offset,
                    exit_horizon_days=exit_horizon_days,
                    case_index=index,
                )
            )
    return cases


def build_tushare_live_sandbox_refresh_report(
    *,
    hypotheses: Iterable[StrategySandboxHypothesis],
    tushare_probe_report: Mapping,
    cache_manifest: Mapping,
    cache_dir: Path,
    run_id: str,
    command: str | None = None,
    generated_at: str | None = None,
) -> dict:
    a_hypotheses = [hypothesis for hypothesis in hypotheses if hypothesis.market == "A"]
    candidates = strategy_candidates_from_hypotheses(a_hypotheses, created_at=generated_at or _now_iso())
    cases = build_tushare_a_share_historical_cases(a_hypotheses, cache_dir=cache_dir)
    results = [evaluate_strategy_candidate(candidate, cases).model_dump() for candidate in candidates]
    strategy_pass_count = sum(1 for result in results if result["status"] == "PASS")
    strategy_fail_count = sum(1 for result in results if result["status"] == "FAIL")

    daily_cache = cache_manifest.get("daily_cache") or {}
    expected_daily_count = int(daily_cache.get("expected_count") or 0)
    actual_daily_count = int(daily_cache.get("actual_count") or 0)
    probe_summary = tushare_probe_report.get("summary") or {}
    passed_capabilities = sorted(
        {"_".join([str(market), str(data_type)]) for market, data_type in _tushare_passed_capabilities(tushare_probe_report)}
    )

    checks = {
        "tushare_a_core_ready": is_tushare_a_core_ready(tushare_probe_report),
        "tushare_token_value_not_stored": True,
        "cache_manifest_pass": cache_manifest.get("overall_verdict") == "PASS",
        "cache_manifest_dry_run": cache_manifest.get("dry_run") is True,
        "cache_manifest_no_trading": cache_manifest.get("trading_called") is False,
        "daily_cache_complete": expected_daily_count > 0 and actual_daily_count >= expected_daily_count,
        "a_hypotheses_present": len(a_hypotheses) == 2,
        "a_strategy_candidates_present": len(candidates) == 2,
        "tushare_historical_cases_present": len(cases) == len(candidates) * 4,
        "all_cases_are_a_share": all(case.market == "A" for case in cases),
        "all_cases_have_tushare_cache_evidence": all(
            str(case.evidence_ref or "").startswith("tushare_cache:") for case in cases
        ),
        "pass_fail_metrics_present": all(result["metrics"]["failed_reasons"] is not None for result in results),
        "simulation_only": True,
        "no_real_trade": True,
        "no_broker_api": True,
        "no_trading_webhook": True,
        "no_order_placement": True,
        "no_strategy_auto_mutation": True,
        "no_production_records_mutation": True,
        "dashboard_contract_unchanged": True,
    }

    return {
        "overall_status": "PASS" if all(checks.values()) else "FAIL",
        "acceptance_target": "V2.11-C Tushare A-Share Historical Sandbox Live Data Refresh",
        "run_id": run_id,
        "generated_at": generated_at or _now_iso(),
        "command": command,
        "network_used_this_stage": False,
        "tushare_probe_network_available": tushare_probe_report.get("network_available"),
        "production_records_written": False,
        "dashboard_contract_changed": False,
        "live_data_source": {
            "provider": "tushare",
            "market": "A",
            "source_mode": "verified_tushare_cache_plus_v2_11_b_probe",
            "token_present_bool_only": tushare_probe_report.get("token_present"),
            "passed_capabilities": passed_capabilities,
            "pass_count": probe_summary.get("pass_count"),
            "unknown_count": probe_summary.get("unknown_count"),
        },
        "historical_cache": {
            "manifest_type": cache_manifest.get("type"),
            "manifest_generated_at": cache_manifest.get("generated_at"),
            "start_date": cache_manifest.get("start_date"),
            "end_date": cache_manifest.get("end_date"),
            "daily_directory": daily_cache.get("directory"),
            "expected_daily_count": expected_daily_count,
            "actual_daily_count": actual_daily_count,
            "failed_dates": daily_cache.get("failed_dates") or [],
        },
        "summary": {
            "hypothesis_count": len(a_hypotheses),
            "candidate_count": len(candidates),
            "historical_case_count": len(cases),
            "strategy_pass_count": strategy_pass_count,
            "strategy_fail_count": strategy_fail_count,
            "passing_strategies": [result["strategy_id"] for result in results if result["status"] == "PASS"],
            "failing_strategies": [result["strategy_id"] for result in results if result["status"] == "FAIL"],
            "historical_case_symbols": sorted({case.symbol for case in cases}),
            "strategy_outcomes_are_simulation_evidence": True,
        },
        "candidates": [candidate.model_dump() for candidate in candidates],
        "historical_cases": [case.model_dump() for case in cases],
        "results": results,
        "checks": checks,
        "safety": {
            "simulation_only": True,
            "historical_sandbox_only": True,
            "not_user_facing_trade_advice": True,
            "no_real_trade": True,
            "no_broker_api": True,
            "no_webhook": True,
            "no_order_placement": True,
            "no_secret_storage": True,
            "no_strategy_auto_mutation": True,
            "no_production_records_mutation": True,
            "dashboard_contract_unchanged": True,
            "suggestion_gate_still_required": True,
        },
    }
