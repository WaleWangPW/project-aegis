#!/usr/bin/env python3
"""Collect research-only A-share dragon-tiger/hot-money samples.

The goal is to give stock-agent concrete historical samples for `top_list` and
`top_inst` without turning hot-money data into recommendations. The script only
uses dates already covered by the local historical price cache, so every sample
can later be checked with a 20-trading-day forward window. It stores compact
event metadata and hashes only; it never stores full Tushare payloads, creates
orders, or mutates production records.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aegis.data.providers import ProviderError  # noqa: E402
from aegis.data.tushare_adapter import TushareAdapter  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "data" / "reports"
PROCESSED = ROOT / "data" / "processed" / "a_share_dragon_tiger_research_samples"
DAILY_DIR = ROOT / "data" / "cache" / "p23_2_historical_market" / "daily_by_trade_date"
STOCK_BASIC = ROOT / "data" / "cache" / "p23_2_historical_market" / "stock_basic_all.json"

OUT_JSON = REPORTS / "a_share_dragon_tiger_research_samples_latest.json"
OUT_MD = REPORTS / "a_share_dragon_tiger_research_samples_latest.md"
PASS_MARKER = REPORTS / "A_SHARE_DRAGON_TIGER_RESEARCH_SAMPLES_PASS.marker"
BLOCKED_MARKER = REPORTS / "A_SHARE_DRAGON_TIGER_RESEARCH_SAMPLES_BLOCKED.marker"

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


def fingerprints() -> dict[str, dict[str, Any]]:
    return {name: fingerprint(path) for name, path in RECORD_PATHS.items()}


def iso_date(value: str) -> str:
    value = str(value)
    return value if "-" in value else f"{value[:4]}-{value[4:6]}-{value[6:8]}"


def compact_date(value: str) -> str:
    return str(value).replace("-", "")


def sample_hash(df: pd.DataFrame) -> str | None:
    if not isinstance(df, pd.DataFrame) or df.empty:
        return None
    payload = df.head(20).to_json(orient="records", force_ascii=False, date_format="iso")
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def daily_cache_dates() -> list[str]:
    return sorted(path.stem for path in DAILY_DIR.glob("*.json"))


def eligible_event_dates(all_dates: list[str], *, lookback_dates: int, forward_days: int) -> list[str]:
    if len(all_dates) <= forward_days:
        return []
    cutoff = len(all_dates) - forward_days - 1
    return all_dates[max(0, cutoff - lookback_dates + 1) : cutoff + 1]


def load_symbol_names() -> dict[str, str]:
    payload = load_json(STOCK_BASIC, {})
    rows = payload.get("rows", []) if isinstance(payload, dict) else []
    return {str(row.get("ts_code")): str(row.get("name") or row.get("symbol") or "") for row in rows if row.get("ts_code")}


def endpoint_error_status(message: str) -> str:
    lower = message.lower()
    if any(token in lower for token in ("权限", "积分", "permission", "forbidden", "unauthorized")):
        return "PERMISSION_BLOCKED"
    return "ERROR"


def is_usable_research_name(name: str | None) -> bool:
    text = str(name or "")
    return not ("退" in text or "ST" in text.upper())


def safe_float(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def collect_date(pro: Any, trade_date: str) -> tuple[pd.DataFrame, pd.DataFrame, list[dict[str, Any]]]:
    errors: list[dict[str, Any]] = []
    try:
        top_list = pro.top_list(trade_date=trade_date)
        if not isinstance(top_list, pd.DataFrame):
            top_list = pd.DataFrame()
    except Exception as exc:  # noqa: BLE001 - Tushare endpoint errors vary
        errors.append({"endpoint": "top_list", "trade_date": trade_date, "status": endpoint_error_status(str(exc)), "message": str(exc)[:220]})
        top_list = pd.DataFrame()
    try:
        top_inst = pro.top_inst(trade_date=trade_date)
        if not isinstance(top_inst, pd.DataFrame):
            top_inst = pd.DataFrame()
    except Exception as exc:  # noqa: BLE001
        errors.append({"endpoint": "top_inst", "trade_date": trade_date, "status": endpoint_error_status(str(exc)), "message": str(exc)[:220]})
        top_inst = pd.DataFrame()
    return top_list, top_inst, errors


def build_samples(
    date_rows: list[tuple[str, pd.DataFrame, pd.DataFrame]],
    symbol_names: dict[str, str],
    *,
    max_symbols: int,
    max_events_per_symbol: int,
) -> list[dict[str, Any]]:
    by_symbol: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for trade_date, top_list, top_inst in date_rows:
        if top_list.empty or "ts_code" not in top_list.columns:
            continue
        inst_by_symbol: dict[str, list[dict[str, Any]]] = defaultdict(list)
        if isinstance(top_inst, pd.DataFrame) and not top_inst.empty and "ts_code" in top_inst.columns:
            for row in top_inst.to_dict("records"):
                inst_by_symbol[str(row.get("ts_code"))].append(row)
        for row in top_list.to_dict("records"):
            ts_code = str(row.get("ts_code") or "")
            if not ts_code or ts_code not in symbol_names:
                continue
            if not is_usable_research_name(symbol_names.get(ts_code)):
                continue
            inst_rows = inst_by_symbol.get(ts_code, [])
            net_buy_values = [safe_float(item.get("net_buy")) for item in inst_rows]
            net_buy_values = [value for value in net_buy_values if value is not None]
            net_amount = safe_float(row.get("net_amount"))
            event = {
                "trade_date": iso_date(trade_date),
                "reason_hash": hashlib.sha256(str(row.get("reason") or "").encode("utf-8")).hexdigest() if row.get("reason") else None,
                "top_list_net_amount": net_amount,
                "top_list_pct_change": safe_float(row.get("pct_change")),
                "top_list_turnover_rate": safe_float(row.get("turnover_rate")),
                "top_inst_row_count": len(inst_rows),
                "top_inst_net_buy_sum": sum(net_buy_values) if net_buy_values else None,
                "event_hash": hashlib.sha256(
                    f"{trade_date}:{ts_code}:{row.get('reason')}:{net_amount}:{len(inst_rows)}:{sum(net_buy_values) if net_buy_values else ''}".encode("utf-8")
                ).hexdigest(),
            }
            by_symbol[ts_code].append(event)
    ranked: list[tuple[str, list[dict[str, Any]], float]] = []
    for ts_code, events in by_symbol.items():
        events = sorted(events, key=lambda item: (item.get("trade_date") or "", abs(item.get("top_list_net_amount") or 0)), reverse=True)
        score = sum(1 for event in events if (event.get("top_inst_net_buy_sum") or 0) > 0) * 2 + len(events)
        ranked.append((ts_code, events[:max_events_per_symbol], score))
    ranked.sort(key=lambda item: (item[2], len(item[1]), item[0]), reverse=True)
    samples: list[dict[str, Any]] = []
    for ts_code, events, score in ranked[:max_symbols]:
        symbol = ts_code.split(".")[0]
        samples.append(
            {
                "symbol": symbol,
                "ts_code": ts_code,
                "name": symbol_names.get(ts_code),
                "market": "A",
                "matched_strategy_ids": ["a_share_short_momentum", "growth_breakout"],
                "research_sample_only": True,
                "sample_source": "tushare_dragon_tiger_hot_money",
                "source_status": "feature_gap_sample",
                "source_status_label": "龙虎榜/游资历史样本",
                "source_score": score,
                "source_risk_flags": ["龙虎榜/游资样本只用于沙盘验证，不用于推荐"],
                "event_trade_dates": [event["trade_date"] for event in events],
                "events": events,
                "required_endpoints": ["top_list", "top_inst"],
                "user_facing_suggestion_allowed": False,
                "real_trade_allowed": False,
            }
        )
    return samples


def blocked_report(status: str, message: str, *, run_id: str, command: str) -> dict[str, Any]:
    return {
        "type": "a_share_dragon_tiger_research_samples",
        "status": status,
        "generated_at": now_iso(),
        "run_id": run_id,
        "command": command,
        "blocker": message,
        "summary": {
            "sample_count": 0,
            "event_count": 0,
            "queried_trade_date_count": 0,
            "network_used": False,
            "raw_payload_saved": False,
            "user_facing_suggestion_allowed": False,
        },
        "samples": [],
        "endpoint_errors": [],
        "safety": safety_block(),
    }


def safety_block() -> dict[str, Any]:
    return {
        "simulation_only": True,
        "research_only": True,
        "metadata_only": True,
        "raw_payload_saved": False,
        "user_facing_suggestion_allowed": False,
        "real_trade_allowed": False,
        "no_broker_api": True,
        "no_order_placement": True,
        "no_trading_webhook": True,
        "no_position_size": True,
        "no_live_order_signal": True,
    }


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    before = fingerprints()
    command = " ".join(sys.argv)
    all_dates = daily_cache_dates()
    event_dates = eligible_event_dates(all_dates, lookback_dates=args.lookback_dates, forward_days=args.forward_days)
    if not event_dates:
        return blocked_report("BLOCKED_NO_ELIGIBLE_CACHE_DATES", "No historical cache dates have enough forward window.", run_id=args.run_id, command=command)
    adapter = TushareAdapter.from_env()
    if not adapter.is_configured():
        return blocked_report("BLOCKED_MISSING_TUSHARE_TOKEN", "TUSHARE_TOKEN is not configured.", run_id=args.run_id, command=command)
    try:
        pro = adapter._require_client()
    except ProviderError as exc:
        return blocked_report("BLOCKED_TUSHARE_CLIENT_UNAVAILABLE", str(exc), run_id=args.run_id, command=command)

    endpoint_errors: list[dict[str, Any]] = []
    date_rows: list[tuple[str, pd.DataFrame, pd.DataFrame]] = []
    for trade_date in event_dates:
        top_list, top_inst, errors = collect_date(pro, trade_date)
        endpoint_errors.extend(errors)
        date_rows.append((trade_date, top_list, top_inst))
    samples = build_samples(
        date_rows,
        load_symbol_names(),
        max_symbols=args.max_symbols,
        max_events_per_symbol=args.max_events_per_symbol,
    )
    after = fingerprints()
    status = "PASS" if samples else "BLOCKED_NO_DRAGON_TIGER_SAMPLES"
    top_list_hashes = {trade_date: sample_hash(top_list) for trade_date, top_list, _ in date_rows if not top_list.empty}
    top_inst_hashes = {trade_date: sample_hash(top_inst) for trade_date, _, top_inst in date_rows if not top_inst.empty}
    report = {
        "type": "a_share_dragon_tiger_research_samples",
        "status": status,
        "generated_at": now_iso(),
        "run_id": args.run_id,
        "command": command,
        "summary": {
            "sample_count": len(samples),
            "event_count": sum(len(item.get("events") or []) for item in samples),
            "queried_trade_date_count": len(event_dates),
            "eligible_cache_date_start": iso_date(event_dates[0]) if event_dates else None,
            "eligible_cache_date_end": iso_date(event_dates[-1]) if event_dates else None,
            "network_used": True,
            "raw_payload_saved": False,
            "user_facing_suggestion_allowed": False,
            "next_stage": "historical case assembly should use event_trade_dates as entry dates for research-only samples.",
        },
        "samples": samples,
        "endpoint_errors": endpoint_errors,
        "source_hashes": {
            "daily_cache_dir": sha256_for_listing(DAILY_DIR),
            "stock_basic": sha256(STOCK_BASIC),
            "top_list_samples_by_date": top_list_hashes,
            "top_inst_samples_by_date": top_inst_hashes,
        },
        "checks": {
            "eligible_cache_dates_present": bool(event_dates),
            "samples_present": bool(samples),
            "events_have_forward_window": True,
            "research_sample_only": all(item.get("research_sample_only") is True for item in samples),
            "user_facing_suggestion_allowed_false": all(item.get("user_facing_suggestion_allowed") is False for item in samples),
            "real_trade_allowed_false": all(item.get("real_trade_allowed") is False for item in samples),
            "raw_payload_not_saved": True,
            "production_records_unchanged": before == after,
            "no_broker_api": True,
            "no_webhook": True,
            "no_order_placement": True,
        },
        "safety": safety_block(),
        "production_record_files_before": before,
        "production_record_files_after": after,
    }
    if not all(report["checks"].values()):
        report["status"] = "BLOCKED_CHECK_FAILED"
    return report


def sha256_for_listing(path: Path) -> str | None:
    if not path.exists():
        return None
    payload = "\n".join(sorted(child.name for child in path.glob("*")))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def render_markdown(report: dict[str, Any]) -> str:
    s = report["summary"]
    lines = [
        "# A-share Dragon Tiger Research Samples",
        "",
        f"- Status: `{report['status']}`",
        f"- Generated At: `{report['generated_at']}`",
        f"- Samples: `{s.get('sample_count')}`",
        f"- Events: `{s.get('event_count')}`",
        f"- Queried Dates: `{s.get('queried_trade_date_count')}`",
        f"- Cache Window: `{s.get('eligible_cache_date_start')}` to `{s.get('eligible_cache_date_end')}`",
        "- Boundary: research-only; no recommendation, no broker, no order, no trading webhook.",
        "",
        "## Samples",
        "",
    ]
    for item in report.get("samples", []):
        lines.append(
            f"- `{item.get('ts_code')}` {item.get('name')}: events={len(item.get('events') or [])}, "
            f"entry_dates={', '.join(item.get('event_trade_dates') or [])}"
        )
    if report.get("blocker"):
        lines.extend(["", "## Blocker", "", str(report["blocker"])])
    lines.append("")
    return "\n".join(lines)


def write_outputs(report: dict[str, Any], run_id: str) -> dict[str, str]:
    REPORTS.mkdir(parents=True, exist_ok=True)
    run_dir = PROCESSED / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    run_json = run_dir / "a_share_dragon_tiger_research_samples.json"
    run_md = run_dir / "a_share_dragon_tiger_research_samples.md"
    write_json(run_json, report)
    run_md.write_text(render_markdown(report), encoding="utf-8")
    write_json(OUT_JSON, report)
    OUT_MD.write_text(render_markdown(report), encoding="utf-8")
    marker = PASS_MARKER if report["status"] == "PASS" else BLOCKED_MARKER
    stale = BLOCKED_MARKER if marker == PASS_MARKER else PASS_MARKER
    if stale.exists():
        stale.unlink()
    marker.write_text(
        "\n".join(
            [
                f"status={report['status']}",
                f"generated_at={report['generated_at']}",
                f"report_json={OUT_JSON}",
                f"report_json_sha256={sha256(OUT_JSON)}",
                f"sample_count={report['summary']['sample_count']}",
                f"event_count={report['summary']['event_count']}",
                f"queried_trade_date_count={report['summary']['queried_trade_date_count']}",
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
    parser = argparse.ArgumentParser(description="Collect research-only dragon-tiger/hot-money A-share samples.")
    parser.add_argument("--run-id", default=f"a_share_dragon_tiger_research_samples_{datetime.now().strftime('%Y%m%dT%H%M%S')}")
    parser.add_argument("--lookback-dates", type=int, default=45)
    parser.add_argument("--forward-days", type=int, default=20)
    parser.add_argument("--max-symbols", type=int, default=12)
    parser.add_argument("--max-events-per-symbol", type=int, default=2)
    args = parser.parse_args(argv)
    report = build_report(args)
    outputs = write_outputs(report, args.run_id)
    print(json.dumps({"status": report["status"], "summary": report["summary"], "outputs": outputs}, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
