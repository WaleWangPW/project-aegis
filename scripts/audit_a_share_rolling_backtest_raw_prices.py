#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import math
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
REPORTS = REPO / "data/reports"
CACHE = REPO / "data/cache/p23_2_historical_market"
DAILY_DIR = CACHE / "daily_by_trade_date"

SNAPSHOTS = REPORTS / "a_share_signal_snapshots_latest.json"
ROLLING = REPORTS / "a_share_point_in_time_rolling_backtest_latest.json"
OUTPUT_JSON = REPORTS / "a_share_rolling_backtest_raw_price_audit_latest.json"
OUTPUT_MD = REPORTS / "a_share_rolling_backtest_raw_price_audit_latest.md"

TOLERANCE = 1e-12


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def canonical_sha256(value: Any) -> str:
    raw = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def compact(value: str) -> str:
    return value.replace("-", "")


def load_cross_section(trade_date: str) -> tuple[dict[str, dict[str, Any]], Path]:
    path = DAILY_DIR / f"{compact(trade_date)}.json"
    payload = read_json(path)
    rows = {
        str(row["ts_code"]): row
        for row in payload.get("rows", [])
        if row.get("ts_code")
    }
    return rows, path


def compound(values: list[float]) -> float:
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


def main() -> int:
    snapshots_payload = read_json(SNAPSHOTS)
    rolling = read_json(ROLLING)

    snapshots_by_id = {
        item["snapshot_id"]: item
        for item in snapshots_payload.get("snapshots", [])
    }

    symbol_price_evidence = []
    benchmark_price_evidence = []
    recomputed_periods = []
    failures = []

    transaction_cost = 10 / 10000.0
    slippage_cost = 5 / 10000.0

    for period in rolling.get("periods", []):
        snapshot_id = period["snapshot_id"]
        snapshot = snapshots_by_id.get(snapshot_id)

        if snapshot is None:
            failures.append(f"{snapshot_id}:snapshot_missing")
            continue

        entry_date = snapshot["entry_date"]
        exit_date = snapshot["exit_date"]
        entry_rows, entry_path = load_cross_section(entry_date)
        exit_rows, exit_path = load_cross_section(exit_date)

        raw_returns = []

        for symbol in snapshot["selected_symbols"]:
            entry_row = entry_rows.get(symbol)
            exit_row = exit_rows.get(symbol)

            if not entry_row or not exit_row:
                failures.append(f"{snapshot_id}:{symbol}:price_missing")
                continue

            entry_close = float(entry_row["close"])
            exit_close = float(exit_row["close"])

            if (
                entry_close <= 0
                or exit_close <= 0
                or not math.isfinite(entry_close)
                or not math.isfinite(exit_close)
            ):
                failures.append(f"{snapshot_id}:{symbol}:invalid_price")
                continue

            raw_return = exit_close / entry_close - 1.0
            raw_returns.append(raw_return)

            evidence_payload = {
                "snapshot_id": snapshot_id,
                "symbol": symbol,
                "entry_date": entry_date,
                "entry_close": entry_close,
                "exit_date": exit_date,
                "exit_close": exit_close,
                "raw_return": raw_return,
                "source_entry_file_sha256": file_sha256(entry_path),
                "source_exit_file_sha256": file_sha256(exit_path),
            }

            symbol_price_evidence.append(
                {
                    **evidence_payload,
                    "raw_price_evidence_sha256": canonical_sha256(
                        evidence_payload
                    ),
                }
            )

        gross = statistics.fmean(raw_returns)
        net = gross - transaction_cost - slippage_cost

        benchmark = period["benchmark_evidence"]
        benchmark_raw = (
            float(benchmark["exit_close"])
            / float(benchmark["entry_close"])
            - 1.0
        )

        benchmark_payload = {
            "snapshot_id": snapshot_id,
            "benchmark": benchmark["benchmark"],
            "entry_date": benchmark["entry_date"],
            "entry_close": float(benchmark["entry_close"]),
            "exit_date": benchmark["exit_date"],
            "exit_close": float(benchmark["exit_close"]),
            "raw_return": benchmark_raw,
        }

        benchmark_price_evidence.append(
            {
                **benchmark_payload,
                "benchmark_evidence_sha256": canonical_sha256(
                    benchmark_payload
                ),
            }
        )

        differences = {
            "gross_difference": gross
            - float(period["gross_portfolio_return"]),
            "net_difference": net
            - float(period["net_portfolio_return"]),
            "benchmark_difference": benchmark_raw
            - float(period["benchmark_return"]),
            "excess_difference": (
                net - benchmark_raw
            ) - float(period["excess_return"]),
        }

        passed = all(
            abs(value) <= TOLERANCE
            for value in differences.values()
        )

        if not passed:
            failures.append(f"{snapshot_id}:return_mismatch")

        recomputed_periods.append(
            {
                "snapshot_id": snapshot_id,
                "symbol_count": len(raw_returns),
                "reported_gross_return": period[
                    "gross_portfolio_return"
                ],
                "recomputed_gross_return": gross,
                "reported_net_return": period[
                    "net_portfolio_return"
                ],
                "recomputed_net_return": net,
                "reported_benchmark_return": period[
                    "benchmark_return"
                ],
                "recomputed_benchmark_return": benchmark_raw,
                "differences": differences,
                "passed": passed,
            }
        )

    recomputed_net_returns = [
        item["recomputed_net_return"]
        for item in recomputed_periods
    ]

    reported_metrics = rolling["portfolio_metrics"]

    total_return = compound(recomputed_net_returns)
    annualized_return = (
        (1.0 + total_return)
        ** (252.0 / (20.0 * len(recomputed_net_returns)))
        - 1.0
    )

    period_vol = (
        statistics.stdev(recomputed_net_returns)
        if len(recomputed_net_returns) >= 2
        else 0.0
    )
    volatility = period_vol * math.sqrt(252.0 / 20.0)
    sharpe = (
        annualized_return / volatility
        if volatility > 0
        else None
    )

    recomputed_metrics = {
        "total_return": total_return,
        "annualized_return": annualized_return,
        "max_drawdown": max_drawdown(recomputed_net_returns),
        "volatility": volatility,
        "sharpe": sharpe,
        "win_rate": sum(value > 0 for value in recomputed_net_returns)
        / len(recomputed_net_returns),
    }

    metric_differences = {}
    for key, recomputed_value in recomputed_metrics.items():
        reported_value = reported_metrics.get(key)

        if recomputed_value is None and reported_value is None:
            difference = 0.0
        elif recomputed_value is None or reported_value is None:
            difference = math.inf
        else:
            difference = float(recomputed_value) - float(reported_value)

        metric_differences[key] = difference

        if not math.isfinite(difference) or abs(difference) > TOLERANCE:
            failures.append(f"aggregate_metric_mismatch:{key}")

    expected_symbol_evidence = sum(
        int(period["valid_symbols_count"])
        for period in rolling.get("periods", [])
    )

    if len(symbol_price_evidence) != expected_symbol_evidence:
        failures.append("symbol_evidence_count_mismatch")

    if len(benchmark_price_evidence) != len(rolling.get("periods", [])):
        failures.append("benchmark_evidence_count_mismatch")

    result = {
        "project": "Project Aegis",
        "type": "a_share_rolling_backtest_raw_price_audit",
        "generated_at": now(),
        "tolerance": TOLERANCE,
        "source_signal_snapshots_sha256": file_sha256(SNAPSHOTS),
        "source_rolling_backtest_sha256": file_sha256(ROLLING),
        "symbol_price_evidence_count": len(symbol_price_evidence),
        "benchmark_price_evidence_count": len(
            benchmark_price_evidence
        ),
        "period_evidence_count": len(recomputed_periods),
        "symbol_price_evidence": symbol_price_evidence,
        "benchmark_price_evidence": benchmark_price_evidence,
        "recomputed_periods": recomputed_periods,
        "reported_aggregate_metrics": reported_metrics,
        "recomputed_aggregate_metrics": recomputed_metrics,
        "aggregate_metric_differences": metric_differences,
        "failures": failures,
        "overall_verdict": "PASS" if not failures else "FAIL",
    }

    OUTPUT_JSON.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    lines = [
        "# A股 Rolling Backtest Raw Price Audit",
        "",
        f"- Verdict: **{result['overall_verdict']}**",
        f"- Symbol evidence: {len(symbol_price_evidence)}",
        f"- Benchmark evidence: {len(benchmark_price_evidence)}",
        f"- Period evidence: {len(recomputed_periods)}",
        "",
        "| Snapshot | Symbols | Reported Net | Recomputed Net | Result |",
        "|---|---:|---:|---:|---|",
    ]

    for item in recomputed_periods:
        lines.append(
            f"| {item['snapshot_id']} | {item['symbol_count']} | "
            f"{item['reported_net_return']:.10f} | "
            f"{item['recomputed_net_return']:.10f} | "
            f"{'PASS' if item['passed'] else 'FAIL'} |"
        )

    OUTPUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print("RAW_PRICE_AUDIT_VERDICT_JSON")
    print(
        json.dumps(
            {
                "symbol_price_evidence_count": len(
                    symbol_price_evidence
                ),
                "benchmark_price_evidence_count": len(
                    benchmark_price_evidence
                ),
                "period_evidence_count": len(recomputed_periods),
                "failures": failures,
                "overall_verdict": result["overall_verdict"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    print("END_RAW_PRICE_AUDIT_VERDICT_JSON")

    return 0 if not failures else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(
            f"[audit_a_share_rolling_backtest_raw_prices] "
            f"{type(exc).__name__}: {exc}",
            file=sys.stderr,
        )
        raise SystemExit(1)
