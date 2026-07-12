from __future__ import annotations

import hashlib
import json
import math
import os
from datetime import datetime, timedelta
from pathlib import Path
from statistics import mean, stdev
from typing import Any

REPO = Path(__file__).resolve().parents[1]
REPORTS = REPO / "data" / "reports"
REPORTS.mkdir(parents=True, exist_ok=True)

STRATEGY_JSON = REPO / "config/strategies/a_share_watchlist_strategy_v1.json"
WATCHLIST_JSON = REPORTS / "a_share_watchlist_latest.json"

BT_JSON = REPORTS / "a_share_backtest_dry_run_latest.json"
BT_MD = REPORTS / "a_share_backtest_dry_run_latest.md"
INPUT_JSON = REPORTS / "a_share_backtest_dry_run_input_latest.json"
EVIDENCE_JSON = REPORTS / "p22_2_backtest_dry_run_evidence.json"
EVIDENCE_MD = REPORTS / "p22_2_backtest_dry_run_evidence.md"

P19_TOP5 = ["600519.SH", "600036.SH", "000858.SZ", "000001.SZ", "601398.SH"]


def now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def sha12(path: Path) -> str | None:
    if not path.exists():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()[:12]


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def symbol_of(record: dict[str, Any]) -> str | None:
    for k in ("symbol", "ts_code", "code", "ticker"):
        v = record.get(k)
        if v:
            return str(v)
    return None


def collect_record_lists(obj: Any) -> list[list[dict[str, Any]]]:
    out: list[list[dict[str, Any]]] = []
    if isinstance(obj, list):
        dicts = [x for x in obj if isinstance(x, dict)]
        if dicts:
            out.append(dicts)
        for x in obj:
            out.extend(collect_record_lists(x))
    elif isinstance(obj, dict):
        for v in obj.values():
            out.extend(collect_record_lists(v))
    return out


def extract_watchlist_records(obj: Any) -> list[dict[str, Any]]:
    candidates = collect_record_lists(obj)
    if not candidates:
        return []

    def score(items: list[dict[str, Any]]) -> int:
        s = len(items) * 10
        syms = [symbol_of(x) for x in items]
        syms = [x for x in syms if x]
        s += len(syms) * 20
        if len(syms) >= 20:
            s += 1000
        if syms[:5] == P19_TOP5:
            s += 10000
        for item in items[:5]:
            keys = {str(k).lower() for k in item.keys()}
            if {"score", "status", "liquidity_ok"} & keys:
                s += 20
        return s

    return sorted(candidates, key=score, reverse=True)[0]


def to_compact_date(s: str) -> str:
    return s.replace("-", "")


def to_dash_date(s: str) -> str:
    if len(s) == 8 and s.isdigit():
        return f"{s[:4]}-{s[4:6]}-{s[6:8]}"
    return s


def fetch_tushare_daily(pro: Any, ts_code: str, start_dash: str, end_dash: str, is_index: bool = False) -> dict[str, Any]:
    start = to_compact_date(start_dash)
    end = to_compact_date(end_dash)

    try:
        if is_index:
            df = pro.index_daily(ts_code=ts_code, start_date=start, end_date=end)
        else:
            df = pro.daily(ts_code=ts_code, start_date=start, end_date=end)
    except Exception as e:
        return {
            "symbol": ts_code,
            "rows": [],
            "data_status": f"error:{type(e).__name__}",
            "error": str(e)[:160],
        }

    if df is None or len(df) == 0:
        return {
            "symbol": ts_code,
            "rows": [],
            "data_status": "empty",
        }

    df = df.sort_values("trade_date").reset_index(drop=True)
    rows = []
    for _, r in df.iterrows():
        rows.append({
            "date": to_dash_date(str(r["trade_date"])),
            "close": float(r["close"]),
            "open": float(r.get("open", r["close"])),
            "high": float(r.get("high", r["close"])),
            "low": float(r.get("low", r["close"])),
        })

    return {
        "symbol": ts_code,
        "rows": rows,
        "price_rows": len(rows),
        "first_date": rows[0]["date"],
        "last_date": rows[-1]["date"],
        "start_price": rows[0]["close"],
        "end_price": rows[-1]["close"],
        "total_return": round(rows[-1]["close"] / rows[0]["close"] - 1, 6),
        "data_status": "ok",
    }


def get_tushare_pro() -> Any:
    import tushare as ts

    token = os.environ.get("TUSHARE_TOKEN") or os.environ.get("tushare_token")
    if not token:
        try:
            token = ts.get_token()
        except Exception:
            token = None

    if token:
        ts.set_token(token)

    return ts.pro_api()


def metrics_from_prices(prices: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not prices or len(prices) < 2:
        return None

    closes = [float(p["close"]) for p in prices]
    returns = []
    for i in range(1, len(closes)):
        if closes[i - 1] == 0:
            continue
        returns.append(closes[i] / closes[i - 1] - 1)

    if not returns:
        return None

    total_return = closes[-1] / closes[0] - 1
    n = len(returns)
    annualized_return = (1 + total_return) ** (252 / max(n, 1)) - 1 if total_return > -1 else None
    vol = stdev(returns) * math.sqrt(252) if len(returns) >= 2 else 0.0
    sharpe = annualized_return / vol if annualized_return is not None and vol not in (0, None) else None
    win_rate = sum(1 for x in returns if x > 0) / len(returns)

    nav = 1.0
    peak = 1.0
    max_dd = 0.0
    for r in returns:
        nav *= 1 + r
        peak = max(peak, nav)
        dd = nav / peak - 1
        max_dd = min(max_dd, dd)

    return {
        "total_return": round(total_return, 6),
        "annualized_return": round(annualized_return, 6) if annualized_return is not None else None,
        "max_drawdown": round(max_dd, 6),
        "volatility": round(vol, 6),
        "sharpe": round(sharpe, 6) if sharpe is not None else None,
        "win_rate": round(win_rate, 6),
        "n_days": len(closes),
        "first_date": prices[0]["date"],
        "last_date": prices[-1]["date"],
    }


def build_portfolio_series(symbol_rows: dict[str, list[dict[str, Any]]], cost_bps: float, slippage_bps: float) -> list[dict[str, Any]]:
    maps = {
        sym: {r["date"]: float(r["close"]) for r in rows}
        for sym, rows in symbol_rows.items()
    }
    common_dates = None
    for m in maps.values():
        dates = set(m.keys())
        common_dates = dates if common_dates is None else common_dates & dates

    dates_sorted = sorted(common_dates or [])
    if len(dates_sorted) < 2:
        return []

    nav = 1.0
    nav *= 1 - (cost_bps + slippage_bps) / 10000.0
    out = [{"date": dates_sorted[0], "close": nav}]

    for i in range(1, len(dates_sorted)):
        d0 = dates_sorted[i - 1]
        d1 = dates_sorted[i]
        daily_returns = []
        for sym, m in maps.items():
            prev = m[d0]
            cur = m[d1]
            if prev:
                daily_returns.append(cur / prev - 1)
        if not daily_returns:
            continue
        nav *= 1 + mean(daily_returns)
        out.append({"date": d1, "close": nav})

    return out


def main() -> int:
    warnings: list[str] = []
    risk_events: list[str] = []

    strategy = load_json(STRATEGY_JSON)
    watch = load_json(WATCHLIST_JSON)

    records = extract_watchlist_records(watch)
    symbols = [symbol_of(r) for r in records]
    symbols = [s for s in symbols if s]

    selected = symbols[:20]
    top5 = selected[:5]

    if top5 != P19_TOP5:
        warnings.append(f"top5_mismatch:{top5}")

    today_dt = datetime.now()
    start_dt = today_dt - timedelta(days=120)
    start_dash = start_dt.strftime("%Y-%m-%d")
    end_dash = today_dt.strftime("%Y-%m-%d")

    input_obj = {
        "strategy_id": strategy.get("strategy_id", "a_share_watchlist_v1"),
        "strategy_version": strategy.get("version", "1.0.0"),
        "market": "A_SHARE",
        "universe_file": "data/reports/a_share_watchlist_latest.json",
        "price_data_source": "tushare_or_cache",
        "start_date": start_dash,
        "end_date": end_dash,
        "rebalance_frequency": "none",
        "holding_period_days": 60,
        "top_n": 20,
        "benchmark": "000300.SH",
        "transaction_cost_bps": 10,
        "slippage_bps": 5,
        "max_positions": 20,
        "allow_short": False,
        "allow_real_trade": False,
        "weight_method": "equal_weight",
        "selected_symbols": selected,
    }
    write_json(INPUT_JSON, input_obj)
    input_hash = hashlib.sha256(INPUT_JSON.read_bytes()).hexdigest()

    try:
        pro = get_tushare_pro()
    except Exception as e:
        err = {
            "project": "Project Aegis",
            "strategy_id": input_obj["strategy_id"],
            "strategy_version": input_obj["strategy_version"],
            "run_id": "bt_run_FAIL",
            "generated_at": now(),
            "error": f"tushare_init_failed:{type(e).__name__}",
            "warnings": warnings + [str(e)[:160]],
            "valid_price_series_count": 0,
            "selected_symbols_count": len(selected),
            "dry_run": True,
            "sent": False,
            "trading_called": False,
            "allow_real_trade": False,
            "allow_short": False,
            "static_snapshot_backtest": True,
            "lookahead_bias_warning": True,
        }
        write_json(BT_JSON, err)
        BT_MD.write_text("# A股 Backtest Dry-run\n\n## FAIL\n\nTushare init failed.\n", encoding="utf-8")
        return 1

    symbol_status = {}
    symbol_rows = {}
    missing = []

    for sym in selected:
        fetched = fetch_tushare_daily(pro, sym, start_dash, end_dash, is_index=False)
        symbol_status[sym] = {k: v for k, v in fetched.items() if k != "rows"}
        rows = fetched.get("rows") or []
        if len(rows) >= 2:
            symbol_rows[sym] = rows
        else:
            missing.append(sym)
            warnings.append(f"price_data_unavailable:{sym}")

    valid_count = len(symbol_rows)

    benchmark = "000300.SH"
    bench = fetch_tushare_daily(pro, benchmark, start_dash, end_dash, is_index=True)
    benchmark_metrics = metrics_from_prices(bench.get("rows") or [])
    if benchmark_metrics is None:
        warnings.append("benchmark_unavailable:000300.SH")

    if valid_count < 5:
        err = {
            "project": "Project Aegis",
            "strategy_id": input_obj["strategy_id"],
            "strategy_version": input_obj["strategy_version"],
            "run_id": "bt_run_FAIL",
            "generated_at": now(),
            "error": f"valid_price_series_count={valid_count}<5",
            "warnings": warnings,
            "missing_price_symbols": missing,
            "valid_price_series_count": valid_count,
            "selected_symbols_count": len(selected),
            "selected_symbols": selected,
            "dry_run": True,
            "sent": False,
            "trading_called": False,
            "allow_real_trade": False,
            "allow_short": False,
            "static_snapshot_backtest": True,
            "lookahead_bias_warning": True,
            "data_status": symbol_status,
        }
        write_json(BT_JSON, err)
        BT_MD.write_text(
            "# A股 Backtest Dry-run\n\n"
            "## FAIL\n\n"
            f"valid_price_series_count={valid_count}, need >=5\n\n"
            "## Missing\n\n"
            + ", ".join(missing)
            + "\n\n## Warnings\n\n"
            + "\n".join(warnings)
            + "\n",
            encoding="utf-8",
        )
        return 1

    portfolio_prices = build_portfolio_series(
        symbol_rows,
        cost_bps=input_obj["transaction_cost_bps"],
        slippage_bps=input_obj["slippage_bps"],
    )
    portfolio_metrics = metrics_from_prices(portfolio_prices)

    if portfolio_metrics is None:
        warnings.append("portfolio_metrics_unavailable")
        return 1

    excess_return = None
    if benchmark_metrics and benchmark_metrics.get("total_return") is not None:
        excess_return = round(portfolio_metrics["total_return"] - benchmark_metrics["total_return"], 6)

    run_id = "bt_run_" + datetime.now().strftime("%Y%m%d_%H%M%S")

    result = {
        "project": "Project Aegis",
        "strategy_id": input_obj["strategy_id"],
        "strategy_version": input_obj["strategy_version"],
        "run_id": run_id,
        "generated_at": now(),
        "input_hash": input_hash,
        "period": {
            "start_date": portfolio_metrics["first_date"],
            "end_date": portfolio_metrics["last_date"],
        },
        "start_date": portfolio_metrics["first_date"],
        "end_date": portfolio_metrics["last_date"],
        "benchmark": benchmark,
        "static_snapshot_backtest": True,
        "lookahead_bias_warning": True,
        "lookahead_bias_note": "当前 Watchlist 静态快照回测，不是 point-in-time 历史选股回测；后续 P22.4/P22.5 再做滚动历史选股记录。",
        "selected_symbols": selected,
        "selected_symbols_count": len(selected),
        "selected_symbols_by_period": [
            {
                "date": portfolio_metrics["first_date"],
                "symbols": selected,
            }
        ],
        "valid_price_series_count": valid_count,
        "missing_price_symbols": missing,
        "portfolio_metrics": portfolio_metrics,
        "benchmark_metrics": benchmark_metrics,
        "excess_return": excess_return,
        "rebalance_records": [
            {
                "date": portfolio_metrics["first_date"],
                "action": "dry_run_static_buy",
                "symbols": selected,
                "weights": {s: round(1.0 / len(selected), 6) for s in selected},
            }
        ],
        "symbol_metrics": {sym: metrics_from_prices(rows) for sym, rows in symbol_rows.items()},
        "data_status": symbol_status,
        "risk_events": risk_events,
        "warnings": warnings,
        "dry_run": True,
        "sent": False,
        "trading_called": False,
        "allow_real_trade": False,
        "allow_short": False,
        "transaction_cost_bps": input_obj["transaction_cost_bps"],
        "slippage_bps": input_obj["slippage_bps"],
    }

    write_json(BT_JSON, result)

    md = [
        "# A股 Watchlist 单次历史回测 Dry-run",
        "",
        "## 口径",
        "- backtest_type: static_snapshot_backtest",
        "- dry_run: true",
        "- sent: false",
        "- trading_called: false",
        "- allow_real_trade: false",
        "- allow_short: false",
        "- lookahead_bias_warning: true",
        "",
        "说明：这是当前 Watchlist 静态快照回测，不是 point-in-time 历史选股回测，存在 lookahead bias。",
        "",
        "## 输入",
        f"- selected_count: {len(selected)}",
        f"- top5: {', '.join(top5)}",
        f"- valid_price_series_count: {valid_count}",
        f"- period: {portfolio_metrics['first_date']} to {portfolio_metrics['last_date']}",
        "",
        "## 组合指标",
    ]
    for k, v in portfolio_metrics.items():
        md.append(f"- {k}: {v}")
    md += [
        "",
        "## Benchmark",
        f"- benchmark: {benchmark}",
        f"- benchmark_total_return: {benchmark_metrics.get('total_return') if benchmark_metrics else None}",
        f"- excess_return: {excess_return}",
        "",
        "## Warnings",
    ]
    md += [f"- {w}" for w in warnings] if warnings else ["- None"]
    BT_MD.write_text("\n".join(md) + "\n", encoding="utf-8")

    evidence = {
        "project": "Project Aegis",
        "type": "p22_2_backtest_dry_run_evidence",
        "generated_at": now(),
        "backtest_json": str(BT_JSON.relative_to(REPO)),
        "backtest_md": str(BT_MD.relative_to(REPO)),
        "input_json": str(INPUT_JSON.relative_to(REPO)),
        "strategy_json_sha256_12": sha12(STRATEGY_JSON),
        "watchlist_json_sha256_12": sha12(WATCHLIST_JSON),
        "backtest_json_sha256_12": sha12(BT_JSON),
        "valid_price_series_count": valid_count,
        "selected_symbols_count": len(selected),
        "top5": top5,
        "metrics": portfolio_metrics,
        "warnings": warnings,
        "safety": {
            "dry_run": True,
            "sent": False,
            "webhook_called": False,
            "trading_called": False,
            "cron_modified": False,
        },
    }
    write_json(EVIDENCE_JSON, evidence)
    EVIDENCE_MD.write_text(
        "# P22.2 Backtest Dry-run Evidence\n\n"
        f"- valid_price_series_count: {valid_count}\n"
        f"- selected_symbols_count: {len(selected)}\n"
        f"- top5: {', '.join(top5)}\n"
        f"- total_return: {portfolio_metrics.get('total_return')}\n"
        f"- max_drawdown: {portfolio_metrics.get('max_drawdown')}\n"
        f"- volatility: {portfolio_metrics.get('volatility')}\n"
        f"- win_rate: {portfolio_metrics.get('win_rate')}\n"
        "- dry_run: true\n"
        "- sent: false\n"
        "- trading_called: false\n",
        encoding="utf-8",
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
