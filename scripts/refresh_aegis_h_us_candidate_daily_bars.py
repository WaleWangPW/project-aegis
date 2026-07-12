#!/usr/bin/env python3
"""Refresh H/US daily bars for current Aegis research candidates via EODHD.

This script only fetches historical market data for simulation research. It
does not place trades, call brokers, write paper trades, or store secrets.
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "data" / "reports"
INPUT = REPORTS / "aegis_strategy_validation_input_latest.json"
CACHE_ROOT = ROOT / "data" / "cache" / "aegis_h_us_candidate_daily_bars"
OUT_JSON = REPORTS / "aegis_h_us_candidate_daily_bars_refresh_latest.json"
OUT_MD = REPORTS / "aegis_h_us_candidate_daily_bars_refresh_latest.md"
PASS_MARKER = REPORTS / "AEGIS_H_US_CANDIDATE_DAILY_BARS_REFRESH_PASS.marker"
FAIL_MARKER = REPORTS / "AEGIS_H_US_CANDIDATE_DAILY_BARS_REFRESH_FAIL.marker"

RECORD_PATHS = {
    "recommendations_jsonl": ROOT / "data" / "records" / "recommendations.jsonl",
    "paper_trades_jsonl": ROOT / "data" / "records" / "paper_trades.jsonl",
    "reviews_jsonl": ROOT / "data" / "records" / "reviews.jsonl",
    "memory_jsonl": ROOT / "data" / "records" / "memory.jsonl",
    "investment_memory_jsonl": ROOT / "data" / "records" / "investment_memory.jsonl",
    "feedback_events_jsonl": ROOT / "data" / "records" / "aegis_stock_feedback_events.jsonl",
}


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


def get_token() -> str | None:
    for name in ("AEGIS_EODHD_API_TOKEN", "EODHD_API_TOKEN", "AEGIS_EODHD_API_KEY", "EODHD_API_KEY"):
        value = os.environ.get(name)
        if value:
            return value
    return None


def get_twelve_token() -> str | None:
    for name in ("AEGIS_TWELVE_DATA_API_KEY", "TWELVE_DATA_API_KEY", "AEGIS_TWELVE_DATA_API_TOKEN"):
        value = os.environ.get(name)
        if value:
            return value
    return None


def eodhd_symbol(symbol: str, market: str) -> str:
    if market == "US":
        return f"{symbol}.US"
    if market == "HK":
        stripped = symbol.lstrip("0") or symbol
        return f"{stripped.zfill(4)}.HK"
    return symbol


def candidate_items() -> list[dict[str, Any]]:
    payload = load_json(INPUT, {})
    return [
        item
        for item in payload.get("items", [])
        if item.get("market") in {"US", "HK"} and item.get("status") == "research_candidate"
    ]


def fetch_eodhd_daily_bars(code: str, token: str, start: str, end: str) -> tuple[int, Any]:
    query = urllib.parse.urlencode({"from": start, "to": end, "period": "d", "api_token": token, "fmt": "json"})
    url = f"https://eodhd.com/api/eod/{urllib.parse.quote(code)}?{query}"
    request = urllib.request.Request(url, headers={"User-Agent": "Project-Aegis/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except Exception as exc:  # noqa: BLE001 - report sanitized provider failures.
        return 0, {"error": exc.__class__.__name__, "message": str(exc)[:160]}


def twelve_symbols(symbol: str, market: str) -> list[str]:
    if market == "US":
        return [symbol]
    if market == "HK":
        stripped = symbol.lstrip("0") or symbol
        padded = stripped.zfill(4)
        return [f"{padded}.HK", f"{padded}:HKEX", padded]
    return [symbol]


def yahoo_symbol(symbol: str, market: str) -> str:
    if market == "US":
        return symbol
    if market == "HK":
        stripped = symbol.lstrip("0") or symbol
        return f"{stripped.zfill(4)}.HK"
    return symbol


def fetch_twelve_daily_bars(symbol: str, market: str, token: str, start: str, end: str) -> tuple[int, Any, str | None]:
    last_payload: Any = None
    last_status = 0
    for candidate in twelve_symbols(symbol, market):
        query = urllib.parse.urlencode(
            {
                "symbol": candidate,
                "interval": "1day",
                "start_date": start,
                "end_date": end,
                "outputsize": 5000,
                "apikey": token,
                "format": "JSON",
            }
        )
        url = f"https://api.twelvedata.com/time_series?{query}"
        try:
            with urllib.request.urlopen(
                urllib.request.Request(url, headers={"User-Agent": "Project-Aegis/1.0"}),
                timeout=30,
            ) as response:
                payload = json.loads(response.read().decode("utf-8"))
                values = payload.get("values") if isinstance(payload, dict) else None
                if response.status == 200 and values:
                    return response.status, payload, candidate
                last_status = response.status
                last_payload = payload
        except Exception as exc:  # noqa: BLE001
            last_status = 0
            last_payload = {"error": exc.__class__.__name__, "message": str(exc)[:160]}
        time.sleep(8 if market == "HK" else 1)
    return last_status, last_payload or {}, None


def fetch_yahoo_daily_bars(symbol: str, market: str, start: str, end: str) -> tuple[int, Any, str]:
    provider_symbol = yahoo_symbol(symbol, market)
    start_ts = int(datetime.fromisoformat(start).replace(tzinfo=timezone.utc).timestamp())
    end_ts = int(datetime.fromisoformat(end).replace(tzinfo=timezone.utc).timestamp()) + 86400
    query = urllib.parse.urlencode(
        {
            "period1": start_ts,
            "period2": end_ts,
            "interval": "1d",
            "events": "history",
            "includeAdjustedClose": "true",
        }
    )
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(provider_symbol)}?{query}"
    try:
        with urllib.request.urlopen(
            urllib.request.Request(url, headers={"User-Agent": "Project-Aegis/1.0"}),
            timeout=30,
        ) as response:
            return response.status, json.loads(response.read().decode("utf-8")), provider_symbol
    except Exception as exc:  # noqa: BLE001
        return 0, {"error": exc.__class__.__name__, "message": str(exc)[:160]}, provider_symbol


def normalize_rows(payload: Any) -> list[dict[str, Any]]:
    if not isinstance(payload, list):
        return []
    rows = []
    for row in payload:
        if not isinstance(row, dict) or not row.get("date"):
            continue
        try:
            rows.append(
                {
                    "date": str(row.get("date")),
                    "open": float(row.get("open")),
                    "high": float(row.get("high")),
                    "low": float(row.get("low")),
                    "close": float(row.get("close")),
                    "adjusted_close": float(row.get("adjusted_close", row.get("close"))),
                    "volume": float(row.get("volume", 0) or 0),
                }
            )
        except (TypeError, ValueError):
            continue
    return rows


def normalize_twelve_rows(payload: Any) -> list[dict[str, Any]]:
    if not isinstance(payload, dict) or not isinstance(payload.get("values"), list):
        return []
    rows = []
    for row in reversed(payload["values"]):
        try:
            close = float(row["close"])
            rows.append(
                {
                    "date": str(row["datetime"]),
                    "open": float(row["open"]),
                    "high": float(row["high"]),
                    "low": float(row["low"]),
                    "close": close,
                    "adjusted_close": close,
                    "volume": float(row.get("volume", 0) or 0),
                }
            )
        except (KeyError, TypeError, ValueError):
            continue
    return rows


def normalize_yahoo_rows(payload: Any) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        return []
    chart = payload.get("chart") if isinstance(payload.get("chart"), dict) else {}
    results = chart.get("result") if isinstance(chart.get("result"), list) else []
    if not results:
        return []
    result = results[0] or {}
    timestamps = result.get("timestamp") if isinstance(result.get("timestamp"), list) else []
    quote_list = result.get("indicators", {}).get("quote", [])
    adj_list = result.get("indicators", {}).get("adjclose", [])
    quote = quote_list[0] if quote_list else {}
    adjclose = adj_list[0].get("adjclose", []) if adj_list else []
    rows = []
    for idx, ts in enumerate(timestamps):
        try:
            open_value = quote.get("open", [])[idx]
            high_value = quote.get("high", [])[idx]
            low_value = quote.get("low", [])[idx]
            close_value = quote.get("close", [])[idx]
            if open_value is None or high_value is None or low_value is None or close_value is None:
                continue
            adjusted_close = adjclose[idx] if idx < len(adjclose) and adjclose[idx] is not None else close_value
            rows.append(
                {
                    "date": datetime.fromtimestamp(int(ts), tz=timezone.utc).date().isoformat(),
                    "open": float(open_value),
                    "high": float(high_value),
                    "low": float(low_value),
                    "close": float(close_value),
                    "adjusted_close": float(adjusted_close),
                    "volume": float((quote.get("volume", [0]) or [0])[idx] or 0),
                }
            )
        except (IndexError, TypeError, ValueError):
            continue
    return rows


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=["date", "open", "high", "low", "close", "adjusted_close", "volume"],
        )
        writer.writeheader()
        writer.writerows(rows)


def render_markdown(report: dict[str, Any]) -> str:
    s = report["summary"]
    lines = [
        "# Aegis H/US Candidate Daily Bars Refresh",
        "",
        f"- Status: {report['status']}",
        f"- Generated At: {report['generated_at']}",
        f"- Candidate Count: {s['candidate_count']}",
        f"- Refreshed Count: {s['refreshed_count']}",
        f"- Blocked Count: {s['blocked_count']}",
        "",
        "Historical data refresh only. No broker API, no webhook, no order placement.",
        "",
    ]
    for item in report["items"]:
        lines.append(f"- {item['symbol']} {item['market']}: {item['status']} rows={item.get('row_count', 0)}")
    lines.append("")
    return "\n".join(lines)


def build_report() -> dict[str, Any]:
    token = get_token()
    twelve_token = get_twelve_token()
    items = candidate_items()
    before = fingerprints(RECORD_PATHS)
    start = "2024-01-01"
    end = date.today().isoformat()
    results = []
    for item in items:
        code = eodhd_symbol(str(item["symbol"]), str(item["market"]))
        result: dict[str, Any] = {
            "symbol": item.get("symbol"),
            "name": item.get("name"),
            "market": item.get("market"),
            "provider": "eodhd",
            "provider_symbol": code,
            "status": "blocked_missing_env" if not token else "pending",
            "request_window": {"from": start, "to": end},
            "request_url_stored": False,
            "token_stored": False,
            "real_trade_allowed": False,
        }
        if not token and not twelve_token:
            results.append(result)
            continue
        if token:
            status_code, payload = fetch_eodhd_daily_bars(code, token, start, end)
            rows = normalize_rows(payload)
        else:
            status_code, payload, rows = 0, {"error": "missing_eodhd_env"}, []
        provider_used = "eodhd"
        provider_symbol_used = code
        fallback_status: dict[str, Any] | None = None
        if not rows and twelve_token:
            twelve_status, twelve_payload, twelve_symbol = fetch_twelve_daily_bars(
                str(item["symbol"]),
                str(item["market"]),
                twelve_token,
                start,
                end,
            )
            twelve_rows = normalize_twelve_rows(twelve_payload)
            fallback_status = {
                "provider": "twelve_data",
                "http_status": twelve_status,
                "symbol": twelve_symbol,
                "row_count": len(twelve_rows),
                "error_type": twelve_payload.get("error") if isinstance(twelve_payload, dict) else None,
                "api_status": twelve_payload.get("status") if isinstance(twelve_payload, dict) else None,
            }
            if twelve_rows:
                rows = twelve_rows
                provider_used = "twelve_data"
                provider_symbol_used = twelve_symbol or str(item["symbol"])
        if not rows:
            yahoo_status, yahoo_payload, yahoo_provider_symbol = fetch_yahoo_daily_bars(
                str(item["symbol"]),
                str(item["market"]),
                start,
                end,
            )
            yahoo_rows = normalize_yahoo_rows(yahoo_payload)
            yahoo_status_report = {
                "provider": "yahoo_chart",
                "http_status": yahoo_status,
                "symbol": yahoo_provider_symbol,
                "row_count": len(yahoo_rows),
                "error_type": yahoo_payload.get("error") if isinstance(yahoo_payload, dict) else None,
                "api_status": yahoo_payload.get("chart", {}).get("error") if isinstance(yahoo_payload, dict) else None,
                "request_url_stored": False,
                "token_required": False,
                "token_stored": False,
            }
            if fallback_status:
                fallback_status["next_fallback_status"] = yahoo_status_report
            else:
                fallback_status = yahoo_status_report
            if yahoo_rows:
                rows = yahoo_rows
                provider_used = "yahoo_chart"
                provider_symbol_used = yahoo_provider_symbol
        if rows:
            safe_symbol = code.lower().replace(".", "_")
            csv_path = CACHE_ROOT / str(item["market"]) / "daily_bars" / f"{safe_symbol}.csv"
            write_csv(csv_path, rows)
            result.update(
                {
                    "status": "refreshed",
                    "http_status": status_code,
                    "provider_used": provider_used,
                    "provider_symbol_used": provider_symbol_used,
                    "row_count": len(rows),
                    "first_date": rows[0]["date"],
                    "last_date": rows[-1]["date"],
                    "csv_path": str(csv_path),
                    "csv_sha256": sha256(csv_path),
                }
            )
            if fallback_status:
                result["fallback_status"] = fallback_status
        else:
            result.update(
                {
                    "status": "fetch_failed_or_empty",
                    "http_status": status_code,
                    "row_count": 0,
                    "error_type": payload.get("error") if isinstance(payload, dict) else "unexpected_payload",
                    "fallback_status": fallback_status,
                }
            )
        results.append(result)
    after = fingerprints(RECORD_PATHS)
    refreshed = sum(1 for item in results if item["status"] == "refreshed")
    report: dict[str, Any] = {
        "type": "aegis_h_us_candidate_daily_bars_refresh",
        "status": "PASS" if items and refreshed > 0 else "BLOCKED",
        "generated_at": now_iso(),
        "summary": {
            "candidate_count": len(items),
            "refreshed_count": refreshed,
            "blocked_count": sum(1 for item in results if item["status"] != "refreshed"),
            "network_used": bool(token),
            "fallback_provider_available": bool(twelve_token),
            "user_facing_suggestion_allowed": False,
            "next_stage": "rerun strategy-specific historical case assembly",
        },
        "items": results,
        "source_reports": {"strategy_validation_input": str(INPUT)},
        "source_hashes": {"strategy_validation_input": sha256(INPUT)},
        "checks": {
            "strategy_validation_input_exists": INPUT.exists(),
            "token_not_stored": True,
            "request_urls_not_stored": True,
            "fallback_provider_supported": True,
            "production_records_unchanged": before == after,
            "no_broker_api": True,
            "no_webhook": True,
            "no_order_placement": True,
            "no_position_size": True,
        },
        "safety": {
            "historical_data_refresh_only": True,
            "simulation_only": True,
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
    return report


def main() -> int:
    report = build_report()
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
                f"exit_code={0 if report['status'] == 'PASS' else 2}",
                f"report_json={OUT_JSON}",
                f"report_json_sha256={sha256(OUT_JSON)}",
                f"candidate_count={report['summary']['candidate_count']}",
                f"refreshed_count={report['summary']['refreshed_count']}",
                f"blocked_count={report['summary']['blocked_count']}",
                f"network_used={str(report['summary']['network_used']).lower()}",
                "user_facing_suggestion_allowed=false",
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
                "candidate_count": report["summary"]["candidate_count"],
                "refreshed_count": report["summary"]["refreshed_count"],
                "blocked_count": report["summary"]["blocked_count"],
                "network_used": report["summary"]["network_used"],
                "report_json": str(OUT_JSON),
            },
            ensure_ascii=False,
        )
    )
    return 0 if report["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
