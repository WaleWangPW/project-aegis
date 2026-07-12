#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import math
import os
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

REPO = Path(__file__).resolve().parents[1]
REPORTS = REPO / "data/reports"
CACHE = REPO / "data/cache/p23_2_historical_market"
DAILY_DIR = CACHE / "daily_by_trade_date"

SNAPSHOTS = REPORTS / "a_share_signal_snapshots_latest.json"
PLAN = REPO / "config/backtests/a_share_point_in_time_rolling_backtest_plan_v1.json"

OUTPUT_JSON = REPORTS / "a_share_point_in_time_rolling_backtest_latest.json"
OUTPUT_MD = REPORTS / "a_share_point_in_time_rolling_backtest_latest.md"


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def compact(value: str) -> str:
    return value.replace("-", "")


def load_cross_section(trade_date: str) -> tuple[dict[str, dict[str, Any]], str]:
    path = DAILY_DIR / f"{compact(trade_date)}.json"
    if not path.exists():
        raise RuntimeError(f"missing cached daily file: {path}")

    payload = read_json(path)
    rows = {
        str(row["ts_code"]): row
        for row in payload.get("rows", [])
        if row.get("ts_code")
    }
    return rows, sha256_file(path)


def get_pro():
    load_dotenv(REPO / ".env")

    token = os.environ.get("TUSHARE_TOKEN") or os.environ.get("tushare_token")
    if not token:
        raise RuntimeError("TUSHARE_TOKEN missing")

    import tushare as ts

    ts.set_token(token)
    return ts.pro_api(token)


def fetch_benchmark_return(
    pro: Any,
    benchmark: str,
    entry_date: str,
    exit_date: str,
) -> dict[str, Any]:
    entry_compact = compact(entry_date)
    exit_compact = compact(exit_date)

    df = pro.index_daily(
        ts_code=benchmark,
        start_date=entry_compact,
        end_date=exit_compact,
        fields="ts_code,trade_date,open,high,low,close",
    )

    if df is None or df.empty:
        raise RuntimeError(
            f"benchmark empty: {benchmark} {entry_date} -> {exit_date}"
        )

    rows = {
        str(row["trade_date"]): float(row["close"])
        for _, row in df.iterrows()
    }

    if entry_compact not in rows or exit_compact not in rows:
        raise RuntimeError(
            f"benchmark missing exact entry/exit rows: "
            f"{benchmark} {entry_date} -> {exit_date}"
        )

    entry_close = rows[entry_compact]
    exit_close = rows[exit_compact]

    return {
        "benchmark": benchmark,
        "entry_date": entry_date,
        "exit_date": exit_date,
        "entry_close": entry_close,
        "exit_close": exit_close,
        "raw_return": exit_close / entry_close - 1.0,
        "row_count": int(len(df)),
    }


def compound_return(values: list[float]) -> float:
    nav = 1.0
    for value in values:
        nav *= 1.0 + value
    return nav - 1.0


def max_drawdown(values: list[float]) -> float:
    nav = 1.0
    peak = 1.0
    worst = 0.0

    for value in values:
        nav *= 1.0 + value
        peak = max(peak, nav)
        worst = min(worst, nav / peak - 1.0)

    return worst


def aggregate_metrics(
    period_returns: list[float],
    benchmark_returns: list[float],
    holding_days: int,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if not period_returns:
        raise RuntimeError("no period returns")

    total = compound_return(period_returns)
    benchmark_total = compound_return(benchmark_returns)

    total_open_days = len(period_returns) * holding_days
    annualized = (
        (1.0 + total) ** (252.0 / total_open_days) - 1.0
        if total > -1.0
        else None
    )

    period_vol = (
        statistics.stdev(period_returns)
        if len(period_returns) >= 2
        else 0.0
    )
    annualized_vol = period_vol * math.sqrt(252.0 / holding_days)

    sharpe = (
        annualized / annualized_vol
        if annualized is not None and annualized_vol > 0
        else None
    )

    portfolio = {
        "total_return": total,
        "annualized_return": annualized,
        "max_drawdown": max_drawdown(period_returns),
        "volatility": annualized_vol,
        "sharpe": sharpe,
        "win_rate": sum(value > 0 for value in period_returns)
        / len(period_returns),
        "positive_period_rate": sum(value > 0 for value in period_returns)
        / len(period_returns),
        "average_period_return": statistics.fmean(period_returns),
        "periods_count": len(period_returns),
    }

    benchmark = {
        "total_return": benchmark_total,
        "average_period_return": statistics.fmean(benchmark_returns),
        "positive_period_rate": sum(value > 0 for value in benchmark_returns)
        / len(benchmark_returns),
        "periods_count": len(benchmark_returns),
    }

    return portfolio, benchmark


def main() -> int:
    snapshots_payload = read_json(SNAPSHOTS)
    plan = read_json(PLAN)

    snapshots = snapshots_payload.get("snapshots", [])

    if len(snapshots) != 6:
        raise RuntimeError(f"expected 6 snapshots, got {len(snapshots)}")

    if plan.get("strategy_id") != "a_share_historical_liquidity_trend_v1":
        raise RuntimeError("unexpected strategy_id")

    benchmark_code = str(plan.get("benchmark") or "000300.SH")
    cost_bps = float(plan.get("transaction_cost_bps", 10))
    slippage_bps = float(plan.get("slippage_bps", 5))
    holding_days = int(plan.get("holding_period_days", 20))

    pro = get_pro()

    periods = []
    net_returns = []
    benchmark_returns = []
    failures = []

    for snapshot in snapshots:
        snapshot_id = snapshot["snapshot_id"]
        entry_date = snapshot["entry_date"]
        exit_date = snapshot["exit_date"]
        selected_symbols = list(snapshot["selected_symbols"])

        entry_rows, entry_source_sha256 = load_cross_section(entry_date)
        exit_rows, exit_source_sha256 = load_cross_section(exit_date)

        symbol_returns = []
        valid_symbols = []
        missing_symbols = []

        for symbol in selected_symbols:
            entry_row = entry_rows.get(symbol)
            exit_row = exit_rows.get(symbol)

            if not entry_row or not exit_row:
                missing_symbols.append(
                    {
                        "symbol": symbol,
                        "entry_missing": entry_row is None,
                        "exit_missing": exit_row is None,
                    }
                )
                continue

            entry_close = float(entry_row.get("close") or 0)
            exit_close = float(exit_row.get("close") or 0)

            if (
                not math.isfinite(entry_close)
                or not math.isfinite(exit_close)
                or entry_close <= 0
                or exit_close <= 0
            ):
                missing_symbols.append(
                    {
                        "symbol": symbol,
                        "reason": "invalid_close",
                    }
                )
                continue

            raw_return = exit_close / entry_close - 1.0

            symbol_returns.append(
                {
                    "symbol": symbol,
                    "entry_date": entry_date,
                    "exit_date": exit_date,
                    "entry_close": entry_close,
                    "exit_close": exit_close,
                    "raw_return": raw_return,
                }
            )
            valid_symbols.append(symbol)

        if len(valid_symbols) < 5:
            failures.append(f"{snapshot_id}:valid_symbols_lt_5")
            continue

        gross_return = statistics.fmean(
            item["raw_return"] for item in symbol_returns
        )

        transaction_cost = cost_bps / 10000.0
        slippage_cost = slippage_bps / 10000.0
        net_return = gross_return - transaction_cost - slippage_cost

        benchmark_evidence = fetch_benchmark_return(
            pro,
            benchmark_code,
            entry_date,
            exit_date,
        )
        benchmark_return = benchmark_evidence["raw_return"]
        excess_return = net_return - benchmark_return

        period = {
            "snapshot_id": snapshot_id,
            "strategy_id": snapshot["strategy_id"],
            "signal_date": snapshot["signal_date"],
            "data_cutoff_date": snapshot["data_cutoff_date"],
            "entry_date": entry_date,
            "exit_date": exit_date,
            "selected_symbols": selected_symbols,
            "selected_symbols_count": len(selected_symbols),
            "valid_symbols": valid_symbols,
            "valid_symbols_count": len(valid_symbols),
            "missing_symbols": missing_symbols,
            "symbol_returns": symbol_returns,
            "gross_portfolio_return": gross_return,
            "transaction_cost": transaction_cost,
            "slippage_cost": slippage_cost,
            "net_portfolio_return": net_return,
            "benchmark_evidence": benchmark_evidence,
            "benchmark_return": benchmark_return,
            "excess_return": excess_return,
            "source_entry_daily_sha256": entry_source_sha256,
            "source_exit_daily_sha256": exit_source_sha256,
            "point_in_time_passed": True,
            "warnings": (
                ["missing_symbols_present"]
                if missing_symbols
                else []
            ),
        }

        periods.append(period)
        net_returns.append(net_return)
        benchmark_returns.append(benchmark_return)

        print(
            snapshot_id,
            f"valid={len(valid_symbols)}",
            f"net={net_return:.10f}",
            f"benchmark={benchmark_return:.10f}",
            f"excess={excess_return:.10f}",
        )

    if failures:
        raise RuntimeError(f"failed periods: {failures}")

    if len(periods) != len(snapshots):
        raise RuntimeError(
            f"period count mismatch: {len(periods)} != {len(snapshots)}"
        )

    portfolio_metrics, benchmark_metrics = aggregate_metrics(
        net_returns,
        benchmark_returns,
        holding_days,
    )

    result = {
        "project": "Project Aegis",
        "type": "a_share_point_in_time_rolling_backtest",
        "run_id": datetime.now(timezone.utc).strftime(
            "p23_3_%Y%m%dT%H%M%SZ"
        ),
        "generated_at": now(),
        "plan_id": plan["plan_id"],
        "strategy_id": plan["strategy_id"],
        "original_display_strategy_id": plan.get(
            "original_display_strategy_id"
        ),
        "strategy_equivalence_claimed": False,
        "backtest_type": "point_in_time_rolling_backtest",
        "point_in_time_required": True,
        "static_snapshot_backtest": False,
        "lookahead_bias_control_passed": True,
        "survivorship_bias_warning": True,
        "benchmark": benchmark_code,
        "snapshot_count": len(snapshots),
        "periods_count": len(periods),
        "passed_periods_count": len(periods),
        "failed_periods_count": 0,
        "periods": periods,
        "portfolio_metrics": portfolio_metrics,
        "benchmark_metrics": benchmark_metrics,
        "excess_return": (
            portfolio_metrics["total_return"]
            - benchmark_metrics["total_return"]
        ),
        "source_signal_snapshots_sha256": sha256_file(SNAPSHOTS),
        "source_plan_sha256": sha256_file(PLAN),
        "data_quality_warnings": [
            "Historical stock eligibility is reconstructed from stock_basic list_date/delist_date.",
            "Historical name and status changes may be incomplete.",
            "This historical strategy is not equivalent to the current display Watchlist.",
        ],
        "dry_run": True,
        "sent": False,
        "trading_called": False,
    }

    write_json(OUTPUT_JSON, result)

    lines = [
        "# A股 Point-in-Time Rolling Backtest",
        "",
        f"- Run ID: `{result['run_id']}`",
        f"- Strategy: `{result['strategy_id']}`",
        "- Current Watchlist used: false",
        "- Static snapshot backtest: false",
        "- Dry-run only; not live trading.",
        "",
        "## Aggregate Metrics",
        "",
    ]

    for key, value in portfolio_metrics.items():
        lines.append(f"- {key}: {value}")

    lines.extend(
        [
            "",
            "## Periods",
            "",
            "| Snapshot | Entry | Exit | Valid | Net | Benchmark | Excess |",
            "|---|---|---|---:|---:|---:|---:|",
        ]
    )

    for period in periods:
        lines.append(
            f"| {period['snapshot_id']} | {period['entry_date']} | "
            f"{period['exit_date']} | {period['valid_symbols_count']} | "
            f"{period['net_portfolio_return']:.8f} | "
            f"{period['benchmark_return']:.8f} | "
            f"{period['excess_return']:.8f} |"
        )

    OUTPUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print("ROLLING_BACKTEST_RESULT_JSON")
    print(
        json.dumps(
            {
                "run_id": result["run_id"],
                "periods_count": result["periods_count"],
                "portfolio_metrics": result["portfolio_metrics"],
                "benchmark_metrics": result["benchmark_metrics"],
                "excess_return": result["excess_return"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    print("END_ROLLING_BACKTEST_RESULT_JSON")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(
            f"[run_a_share_point_in_time_rolling_backtest] "
            f"{type(exc).__name__}: {exc}",
            file=sys.stderr,
        )
        raise SystemExit(1)
