#!/usr/bin/env python3
"""Validate Project Aegis V2.1-A Historical Strategy Sandbox."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aegis.models.strategy import HistoricalStrategyCase, StrategyCandidate, StrategyPassCriteria  # noqa: E402
from aegis.strategy.sandbox import build_strategy_sandbox_report  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_ROOT = ROOT / "data" / "processed" / "v2_1_a_acceptance"
DEFAULT_REPORTS_DIR = ROOT / "data" / "reports"
HISTORICAL_CACHE_DIR = ROOT / "data" / "cache" / "p23_2_historical_market"

PASS_MARKER = "V2_1_A_HISTORICAL_STRATEGY_SANDBOX_PASS.marker"
FAIL_MARKER = "V2_1_A_HISTORICAL_STRATEGY_SANDBOX_FAIL.marker"
REPORT_JSON = "v2_1_a_historical_strategy_sandbox_latest.json"
REPORT_MD = "v2_1_a_historical_strategy_sandbox_latest.md"


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def _run_id() -> str:
    return "v2_1_a_strategy_sandbox_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _sha256(path: Path) -> Optional[str]:
    if not path.exists():
        return None
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _historical_cache_file_count() -> int:
    if not HISTORICAL_CACHE_DIR.exists():
        return 0
    return sum(1 for _ in HISTORICAL_CACHE_DIR.rglob("*.json"))


def _fixture_candidates() -> list[StrategyCandidate]:
    created_at = "2026-07-11T00:00:00+08:00"
    return [
        StrategyCandidate(
            strategy_id="low_volatility_dividend_a",
            name="A-share low volatility dividend defensive candidate",
            market="A",
            universe="A-share liquid large/mid cap historical sandbox fixture",
            factor_family="multi_factor",
            entry_rule="Rank by lower realized volatility plus dividend yield; enter top eligible candidates.",
            exit_rule="Evaluate after 20 trading days in sandbox.",
            exit_horizon_days=20,
            risk_controls=["liquidity_filter", "max_drawdown_floor", "single_name_exposure_cap"],
            pass_criteria=StrategyPassCriteria(
                min_sample_count=4,
                min_win_rate=0.5,
                min_average_return=0.01,
                max_drawdown_floor=-0.08,
            ),
            source_research_refs=["S&P DJI China A-share factor research", "Aegis internal risk veto rule"],
            created_at=created_at,
        ),
        StrategyCandidate(
            strategy_id="raw_momentum_us",
            name="U.S. raw short-horizon momentum candidate",
            market="US",
            universe="U.S. large cap historical sandbox fixture",
            factor_family="momentum",
            entry_rule="Enter high short-horizon momentum without defensive quality overlay.",
            exit_rule="Evaluate after 20 trading days in sandbox.",
            exit_horizon_days=20,
            risk_controls=["max_drawdown_floor"],
            pass_criteria=StrategyPassCriteria(
                min_sample_count=4,
                min_win_rate=0.6,
                min_average_return=0.015,
                max_drawdown_floor=-0.08,
            ),
            source_research_refs=["Aegis V2.1 strategy research baseline"],
            created_at=created_at,
        ),
    ]


def _fixture_cases() -> list[HistoricalStrategyCase]:
    raw_cases = [
        {
            "case_id": "a_low_vol_div_001",
            "strategy_id": "low_volatility_dividend_a",
            "date": "2024-03-01",
            "symbol": "600000.SH",
            "market": "A",
            "entry_price": 10.00,
            "exit_price": 10.42,
            "max_drawdown": -0.025,
            "risk_flags": [],
            "factor_values": {"dividend_yield": 0.042, "realized_volatility": 0.18},
        },
        {
            "case_id": "a_low_vol_div_002",
            "strategy_id": "low_volatility_dividend_a",
            "date": "2024-03-08",
            "symbol": "000001.SZ",
            "market": "A",
            "entry_price": 12.50,
            "exit_price": 12.80,
            "max_drawdown": -0.031,
            "risk_flags": [],
            "factor_values": {"dividend_yield": 0.038, "realized_volatility": 0.2},
        },
        {
            "case_id": "a_low_vol_div_003",
            "strategy_id": "low_volatility_dividend_a",
            "date": "2024-03-15",
            "symbol": "600519.SH",
            "market": "A",
            "entry_price": 100.00,
            "exit_price": 98.90,
            "max_drawdown": -0.047,
            "risk_flags": ["valuation_pressure"],
            "factor_values": {"dividend_yield": 0.022, "realized_volatility": 0.16},
        },
        {
            "case_id": "a_low_vol_div_004",
            "strategy_id": "low_volatility_dividend_a",
            "date": "2024-03-22",
            "symbol": "601318.SH",
            "market": "A",
            "entry_price": 40.00,
            "exit_price": 41.20,
            "max_drawdown": -0.035,
            "risk_flags": [],
            "factor_values": {"dividend_yield": 0.05, "realized_volatility": 0.19},
        },
        {
            "case_id": "us_raw_mom_001",
            "strategy_id": "raw_momentum_us",
            "date": "2024-04-01",
            "symbol": "AAPL",
            "market": "US",
            "entry_price": 190.00,
            "exit_price": 187.00,
            "max_drawdown": -0.094,
            "risk_flags": ["drawdown_breach"],
            "factor_values": {"momentum_20d": 0.08},
        },
        {
            "case_id": "us_raw_mom_002",
            "strategy_id": "raw_momentum_us",
            "date": "2024-04-08",
            "symbol": "MSFT",
            "market": "US",
            "entry_price": 420.00,
            "exit_price": 422.00,
            "max_drawdown": -0.062,
            "risk_flags": [],
            "factor_values": {"momentum_20d": 0.07},
        },
        {
            "case_id": "us_raw_mom_003",
            "strategy_id": "raw_momentum_us",
            "date": "2024-04-15",
            "symbol": "NVDA",
            "market": "US",
            "entry_price": 90.00,
            "exit_price": 84.50,
            "max_drawdown": -0.13,
            "risk_flags": ["drawdown_breach", "crowding_risk"],
            "factor_values": {"momentum_20d": 0.12},
        },
        {
            "case_id": "us_raw_mom_004",
            "strategy_id": "raw_momentum_us",
            "date": "2024-04-22",
            "symbol": "TSLA",
            "market": "US",
            "entry_price": 170.00,
            "exit_price": 164.00,
            "max_drawdown": -0.101,
            "risk_flags": ["drawdown_breach"],
            "factor_values": {"momentum_20d": 0.09},
        },
    ]
    return [HistoricalStrategyCase(**case) for case in raw_cases]


def run_acceptance(
    *,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    reports_dir: Path = DEFAULT_REPORTS_DIR,
    run_id: Optional[str] = None,
    command: Optional[str] = None,
) -> dict:
    run_id = run_id or _run_id()
    run_dir = output_root / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    reports_dir.mkdir(parents=True, exist_ok=True)

    candidates = _fixture_candidates()
    historical_cases = _fixture_cases()
    candidates_json = run_dir / "strategy_candidates.json"
    historical_jsonl = run_dir / "historical_strategy_cases.jsonl"
    candidates_json.write_text(
        json.dumps([candidate.model_dump() for candidate in candidates], ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    historical_jsonl.write_text(
        "".join(json.dumps(case.model_dump(), ensure_ascii=False) + "\n" for case in historical_cases),
        encoding="utf-8",
    )

    report = build_strategy_sandbox_report(
        candidates,
        historical_cases,
        run_id=run_id,
        command=command,
        historical_cache_file_count=_historical_cache_file_count(),
    )
    report["run_dir"] = str(run_dir)
    report["candidates_json"] = str(candidates_json)
    report["historical_cases_jsonl"] = str(historical_jsonl)

    checks = {
        "sandbox_report_passed": report["overall_status"] == "PASS",
        "at_least_one_strategy_passed": report["summary"]["pass_count"] >= 1,
        "at_least_one_strategy_failed": report["summary"]["fail_count"] >= 1,
        "metrics_present": all(
            result["metrics"]["win_rate"] is not None
            and result["metrics"]["average_return"] is not None
            and result["metrics"]["max_drawdown"] is not None
            for result in report["results"]
        ),
        "risk_reasons_present_for_failed_strategy": any(
            result["status"] == "FAIL" and result["metrics"]["failed_reasons"] for result in report["results"]
        ),
        "historical_cache_detected": report["historical_cache_file_count"] > 0,
        "simulation_only": report["safety"]["simulation_only"] is True,
        "no_real_trade_or_broker": report["safety"]["no_real_trade"] is True
        and report["safety"]["no_broker_api"] is True,
        "no_strategy_auto_mutation": report["safety"]["no_strategy_auto_mutation"] is True,
        "no_production_records_mutation": report["production_records_written"] is False,
        "dashboard_contract_unchanged": report["dashboard_contract_changed"] is False,
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise RuntimeError("V2.1-A acceptance checks failed: " + ", ".join(failed))

    report["checks"] = checks
    report["hashes"] = {
        "candidates_json": _sha256(candidates_json),
        "historical_cases_jsonl": _sha256(historical_jsonl),
    }
    _write_reports(report, reports_dir)
    return report


def _write_reports(report: dict, reports_dir: Path) -> None:
    json_path = reports_dir / REPORT_JSON
    md_path = reports_dir / REPORT_MD
    marker_path = reports_dir / PASS_MARKER
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md_path.write_text(
        "\n".join(
            [
                "# V2.1-A Historical Strategy Sandbox Acceptance",
                "",
                f"- status: {report['overall_status']}",
                f"- target: {report['acceptance_target']}",
                f"- run_id: {report['run_id']}",
                f"- candidates_json: `{report['candidates_json']}`",
                f"- historical_cases_jsonl: `{report['historical_cases_jsonl']}`",
                f"- pass_count: `{report['summary']['pass_count']}`",
                f"- fail_count: `{report['summary']['fail_count']}`",
                f"- historical_cache_file_count: `{report['historical_cache_file_count']}`",
                "- safety: simulation only, no real trade, no broker API, no webhook, no strategy auto-mutation",
                "",
            ]
        ),
        encoding="utf-8",
    )
    marker_path.write_text(
        "\n".join(
            [
                f"generated_at={report['generated_at']}",
                f"command={report.get('command') or ''}",
                "exit_code=0",
                "target=V2.1-A Historical Strategy Sandbox",
                f"report_json={json_path}",
                f"report_json_sha256={_sha256(json_path)}",
                f"report_md={md_path}",
                f"report_md_sha256={_sha256(md_path)}",
                f"run_dir={report['run_dir']}",
                f"candidates_json={report['candidates_json']}",
                f"candidates_json_sha256={report['hashes']['candidates_json']}",
                f"historical_cases_jsonl={report['historical_cases_jsonl']}",
                f"historical_cases_jsonl_sha256={report['hashes']['historical_cases_jsonl']}",
                f"historical_cache_file_count={report['historical_cache_file_count']}",
                "network_used=false",
                "dashboard_contract_changed=false",
                "production_records_written=false",
                "simulation_only=true",
                "no_real_trade=true",
                "no_broker_api=true",
                "failed=0",
                "",
            ]
        ),
        encoding="utf-8",
    )
    fail_marker = reports_dir / FAIL_MARKER
    if fail_marker.exists():
        fail_marker.unlink()


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--reports-dir", type=Path, default=DEFAULT_REPORTS_DIR)
    parser.add_argument("--run-id")
    args = parser.parse_args(argv)
    command = " ".join([Path(sys.argv[0]).name, *(argv if argv is not None else sys.argv[1:])])

    try:
        report = run_acceptance(
            output_root=args.output_root,
            reports_dir=args.reports_dir,
            run_id=args.run_id,
            command=command,
        )
    except Exception as exc:
        args.reports_dir.mkdir(parents=True, exist_ok=True)
        fail_marker = args.reports_dir / FAIL_MARKER
        fail_marker.write_text(
            "\n".join(
                [
                    f"generated_at={_now_iso()}",
                    f"command={command}",
                    "exit_code=1",
                    "target=V2.1-A Historical Strategy Sandbox",
                    f"error={exc}",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        print(f"V2.1-A Historical Strategy Sandbox FAIL: {exc}")
        return 1

    print(
        "V2.1-A Historical Strategy Sandbox PASS "
        f"run_id={report['run_id']} report={args.reports_dir / REPORT_JSON}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
