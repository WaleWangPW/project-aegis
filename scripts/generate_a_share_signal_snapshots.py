#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import math
import shutil
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
CACHE = REPO / "data/cache/p23_2_historical_market"
CALENDAR = CACHE / "trade_calendar.json"
STOCK_BASIC = CACHE / "stock_basic_all.json"
DAILY_DIR = CACHE / "daily_by_trade_date"
REPORTS = REPO / "data/reports"
SNAPSHOT_DIR = REPO / "data/snapshots/a_share_signal_snapshots"

STRATEGY_PATH = REPO / "config/strategies/a_share_historical_liquidity_trend_v1.json"
PLAN_PATH = REPO / "config/backtests/a_share_point_in_time_rolling_backtest_plan_v1.json"

LATEST_JSON = REPORTS / "a_share_signal_snapshots_latest.json"
LATEST_MD = REPORTS / "a_share_signal_snapshots_latest.md"

MONTHS = ["202401", "202402", "202403", "202404", "202405", "202406"]


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


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_sha256(value: Any) -> str:
    raw = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def dash(value: str) -> str:
    return f"{value[:4]}-{value[4:6]}-{value[6:8]}"


def max_drawdown(closes: list[float]) -> float:
    peak = -math.inf
    worst = 0.0
    for close in closes:
        peak = max(peak, close)
        if peak > 0:
            worst = min(worst, close / peak - 1.0)
    return worst


def rank_scores(
    records: list[dict[str, Any]],
    key: str,
    *,
    descending: bool,
) -> dict[str, float]:
    ordered = sorted(
        records,
        key=lambda item: (
            -float(item[key]) if descending else float(item[key]),
            item["ts_code"],
        ),
    )
    count = len(ordered)
    result = {}
    for index, item in enumerate(ordered):
        normalized = 1.0 if count == 1 else 1.0 - index / (count - 1)
        result[item["ts_code"]] = normalized
    return result


def load_daily_rows(trade_dates: list[str]) -> tuple[dict[str, list[dict[str, Any]]], list[dict[str, str]]]:
    histories: dict[str, list[dict[str, Any]]] = {}
    fingerprints = []

    for trade_date in trade_dates:
        path = DAILY_DIR / f"{trade_date}.json"
        payload = read_json(path)
        fingerprints.append(
            {
                "trade_date": trade_date,
                "path": str(path.relative_to(REPO)),
                "sha256": sha256(path),
            }
        )

        for row in payload.get("rows", []):
            ts_code = str(row.get("ts_code", ""))
            if not ts_code:
                continue
            histories.setdefault(ts_code, []).append(row)

    for rows in histories.values():
        rows.sort(key=lambda row: str(row["trade_date"]))

    return histories, fingerprints


def eligible_stock(stock: dict[str, Any], cutoff: str) -> tuple[bool, str | None]:
    ts_code = str(stock.get("ts_code") or "")
    name = str(stock.get("name") or "")
    list_date = str(stock.get("list_date") or "")
    delist_date = str(stock.get("delist_date") or "")

    if not ts_code.endswith((".SH", ".SZ")):
        return False, "unsupported_exchange"
    if ts_code.endswith(".BJ"):
        return False, "beijing_exchange"
    if "ST" in name.upper():
        return False, "st_name"
    if not list_date or list_date > cutoff:
        return False, "not_listed_as_of_cutoff"
    if delist_date and delist_date <= cutoff:
        return False, "delisted_as_of_cutoff"

    return True, None


def main() -> int:
    REPORTS.mkdir(parents=True, exist_ok=True)
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)

    required = [CALENDAR, STOCK_BASIC, STRATEGY_PATH, PLAN_PATH]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise RuntimeError(f"missing required files: {missing}")

    calendar_payload = read_json(CALENDAR)
    stock_payload = read_json(STOCK_BASIC)
    strategy = read_json(STRATEGY_PATH)
    plan = read_json(PLAN_PATH)

    if strategy.get("strategy_id") != "a_share_historical_liquidity_trend_v1":
        raise RuntimeError("historical strategy_id mismatch")
    if plan.get("strategy_id") != strategy.get("strategy_id"):
        raise RuntimeError("plan strategy_id mismatch")

    open_dates = sorted(str(value) for value in calendar_payload.get("open_dates", []))
    if len(open_dates) < 100:
        raise RuntimeError("insufficient trade calendar")

    open_index = {value: index for index, value in enumerate(open_dates)}
    stocks = stock_payload.get("rows", [])

    old_dir = REPORTS / "backups/p23_2_real_cache_generation"
    old_dir.mkdir(parents=True, exist_ok=True)

    for path in (LATEST_JSON, LATEST_MD):
        if path.exists():
            shutil.copy2(path, old_dir / path.name)

    for old_snapshot in SNAPSHOT_DIR.glob("*.json"):
        old_snapshot.unlink()

    snapshots = []

    for month in MONTHS:
        month_open_dates = [date for date in open_dates if date.startswith(month)]
        if not month_open_dates:
            raise RuntimeError(f"no open date for month {month}")

        signal_date = month_open_dates[0]
        signal_index = open_index[signal_date]

        if signal_index < 60:
            raise RuntimeError(f"insufficient lookback for {signal_date}")
        if signal_index + 21 >= len(open_dates):
            raise RuntimeError(f"insufficient forward calendar for {signal_date}")

        data_cutoff_date = signal_date
        rebalance_date = open_dates[signal_index + 1]
        entry_date = rebalance_date
        entry_index = open_index[entry_date]
        exit_date = open_dates[entry_index + 20]

        lookback_dates = open_dates[signal_index - 59 : signal_index + 1]
        histories, daily_fingerprints = load_daily_rows(lookback_dates)

        candidate_records = []
        exclusions = []

        for stock in stocks:
            ok, reason = eligible_stock(stock, data_cutoff_date)
            ts_code = str(stock.get("ts_code") or "")

            if not ok:
                if ts_code:
                    exclusions.append({"ts_code": ts_code, "reason": reason})
                continue

            rows = histories.get(ts_code, [])
            valid_rows = [
                row
                for row in rows
                if float(row.get("close") or 0) > 0
                and row.get("amount") is not None
            ]

            if len(valid_rows) < 40:
                exclusions.append({"ts_code": ts_code, "reason": "valid_price_rows_lt_40"})
                continue

            closes = [float(row["close"]) for row in valid_rows]
            amounts = [float(row.get("amount") or 0) for row in valid_rows]

            if len(closes) < 20 or closes[-20] <= 0:
                exclusions.append({"ts_code": ts_code, "reason": "insufficient_trend_rows"})
                continue

            returns = [
                closes[index] / closes[index - 1] - 1.0
                for index in range(1, len(closes))
                if closes[index - 1] > 0
            ]

            if not returns:
                exclusions.append({"ts_code": ts_code, "reason": "no_valid_returns"})
                continue

            avg_amount = statistics.fmean(amounts)
            if avg_amount <= 1.0:
                exclusions.append({"ts_code": ts_code, "reason": "avg_amount_too_low"})
                continue

            candidate_records.append(
                {
                    "ts_code": ts_code,
                    "name": stock.get("name"),
                    "valid_price_rows": len(valid_rows),
                    "avg_amount_60d": avg_amount,
                    "trend_20d": closes[-1] / closes[-20] - 1.0,
                    "volatility_60d": statistics.pstdev(returns),
                    "max_drawdown_60d": max_drawdown(closes),
                    "last_close": closes[-1],
                }
            )

        if len(candidate_records) < 20:
            raise RuntimeError(
                f"only {len(candidate_records)} valid candidates for {signal_date}"
            )

        liquidity = rank_scores(candidate_records, "avg_amount_60d", descending=True)
        trend = rank_scores(candidate_records, "trend_20d", descending=True)
        volatility = rank_scores(candidate_records, "volatility_60d", descending=False)
        drawdown = rank_scores(candidate_records, "max_drawdown_60d", descending=True)

        for item in candidate_records:
            symbol = item["ts_code"]
            item["composite_rank_score"] = (
                0.35 * liquidity[symbol]
                + 0.35 * trend[symbol]
                + 0.15 * volatility[symbol]
                + 0.15 * drawdown[symbol]
            )

        ranked = sorted(
            candidate_records,
            key=lambda item: (-item["composite_rank_score"], item["ts_code"]),
        )

        selected_records = ranked[:20]
        selected_symbols = [item["ts_code"] for item in selected_records]

        bundle_payload = {
            "calendar_sha256": sha256(CALENDAR),
            "stock_basic_sha256": sha256(STOCK_BASIC),
            "daily_files": daily_fingerprints,
            "strategy_sha256": sha256(STRATEGY_PATH),
            "plan_sha256": sha256(PLAN_PATH),
        }

        snapshot = {
            "snapshot_id": f"snapshot_{signal_date}",
            "strategy_id": strategy["strategy_id"],
            "strategy_version": strategy["version"],
            "original_display_strategy_id": plan.get("original_display_strategy_id"),
            "strategy_equivalence_claimed": False,
            "signal_date": dash(signal_date),
            "data_cutoff_date": dash(data_cutoff_date),
            "rebalance_date": dash(rebalance_date),
            "entry_date": dash(entry_date),
            "exit_date": dash(exit_date),
            "holding_period_open_days": 20,
            "selected_symbols": selected_symbols,
            "selected_symbols_count": len(selected_symbols),
            "selected_records": selected_records,
            "top_n": 20,
            "candidate_count": len(candidate_records),
            "ranking_inputs": strategy["ranking_inputs"],
            "risk_filters": {
                "min_valid_price_rows": 40,
                "exclude_st": True,
                "exclude_bj_exchange": True,
            },
            "liquidity_filters": {
                "min_avg_amount": 1.0,
            },
            "exclusions_count": len(exclusions),
            "exclusions": exclusions,
            "source_data_hashes": {
                "trade_calendar_sha256": sha256(CALENDAR),
                "stock_basic_sha256": sha256(STOCK_BASIC),
                "strategy_sha256": sha256(STRATEGY_PATH),
                "plan_sha256": sha256(PLAN_PATH),
                "daily_bundle_sha256": canonical_sha256(bundle_payload),
            },
            "source_daily_files": daily_fingerprints,
            "trade_calendar_source": "Tushare trade_cal cached cross-section",
            "universe_source": "Tushare stock_basic L/D/P reconstructed by list_date/delist_date",
            "date_alignment_method": "first_open_day_monthly_and_open_day_index",
            "generated_at": now(),
            "dry_run": True,
            "sent": False,
            "trading_called": False,
            "current_watchlist_used": False,
            "point_in_time": True,
            "lookahead_bias_control_passed": True,
            "survivorship_bias_warning": True,
            "warnings": [
                "Historical name/status changes may be incomplete.",
                "This historical strategy is not equivalent to a_share_watchlist_v1.",
            ],
        }

        snapshots.append(snapshot)
        write_json(SNAPSHOT_DIR / f"{snapshot['snapshot_id']}.json", snapshot)

        print(
            f"{snapshot['snapshot_id']} "
            f"candidates={len(candidate_records)} selected={len(selected_symbols)} "
            f"entry={snapshot['entry_date']} exit={snapshot['exit_date']}"
        )

    output = {
        "project": "Project Aegis",
        "type": "a_share_signal_snapshots",
        "generated_at": now(),
        "plan_id": plan["plan_id"],
        "strategy_id": strategy["strategy_id"],
        "original_display_strategy_id": plan.get("original_display_strategy_id"),
        "strategy_equivalence_claimed": False,
        "snapshot_count": len(snapshots),
        "snapshots": snapshots,
        "dry_run": True,
        "sent": False,
        "trading_called": False,
    }

    write_json(LATEST_JSON, output)

    lines = [
        "# A股 Point-in-Time Signal Snapshots",
        "",
        f"- Strategy: `{strategy['strategy_id']}`",
        f"- Snapshot count: {len(snapshots)}",
        "- Current Watchlist used: false",
        "- Strategy equivalent to display Watchlist: false",
        "- Dry-run only; no trading.",
        "",
        "| Snapshot | Signal | Entry | Exit | Candidates | Selected |",
        "|---|---|---|---|---:|---:|",
    ]

    for snapshot in snapshots:
        lines.append(
            f"| {snapshot['snapshot_id']} | {snapshot['signal_date']} | "
            f"{snapshot['entry_date']} | {snapshot['exit_date']} | "
            f"{snapshot['candidate_count']} | {snapshot['selected_symbols_count']} |"
        )

    LATEST_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"generated={len(snapshots)}")
    print(f"latest_json={LATEST_JSON.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(
            f"[generate_a_share_signal_snapshots] "
            f"{type(exc).__name__}: {exc}",
            file=sys.stderr,
        )
        raise SystemExit(1)
