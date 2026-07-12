#!/usr/bin/env python3
"""Read-only probe for A-share Tushare strategy data sources.

This script checks whether the next A-share strategy modules have usable
Tushare data. It stores metadata only: status, row counts, columns, date ranges,
and hashes. It never writes raw payloads, never prints tokens, never changes
strategy ranking, and never creates recommendations or trades.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aegis.data.providers import ProviderError  # noqa: E402
from aegis.data.tushare_adapter import TushareAdapter  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = ROOT / "data" / "reports"
PROCESSED_DIR = ROOT / "data" / "processed" / "a_share_tushare_strategy_source_probe"
LATEST_JSON = REPORTS_DIR / "a_share_tushare_strategy_source_probe_latest.json"
LATEST_MD = REPORTS_DIR / "a_share_tushare_strategy_source_probe_latest.md"
PASS_MARKER = REPORTS_DIR / "A_SHARE_TUSHARE_STRATEGY_SOURCE_PROBE_PASS.marker"
BLOCKED_MARKER = REPORTS_DIR / "A_SHARE_TUSHARE_STRATEGY_SOURCE_PROBE_BLOCKED.marker"
CASES_JSON = REPORTS_DIR / "aegis_strategy_specific_historical_cases_latest.json"


@dataclass(frozen=True)
class ProbeSpec:
    module_id: str
    module_name: str
    endpoint: str
    priority: int
    description: str
    call: Callable[[Any, str, str, str], pd.DataFrame]


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def compact_date(value: datetime) -> str:
    return value.strftime("%Y%m%d")


def date_window(days: int) -> tuple[str, str]:
    end = datetime.now().date()
    start = end - timedelta(days=days)
    return start.strftime("%Y%m%d"), end.strftime("%Y%m%d")


def dataframe_hash(df: pd.DataFrame) -> str | None:
    if df.empty:
        return None
    sample = df.head(20).to_json(orient="records", force_ascii=False, date_format="iso")
    return hashlib.sha256(sample.encode("utf-8")).hexdigest()


def endpoint_status(row_count: int, error: str | None) -> str:
    if error:
        lower = error.lower()
        if any(token in lower for token in ("权限", "积分", "permission", "forbidden", "unauthorized")):
            return "PERMISSION_BLOCKED"
        return "ERROR"
    if row_count <= 0:
        return "EMPTY"
    return "PASS"


def load_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def historical_entry_dates(path: Path = CASES_JSON, *, limit: int = 30) -> list[str]:
    report = load_json(path, {})
    dates = {
        str(case.get("entry_date")).replace("-", "")
        for case in report.get("historical_cases", [])
        if case.get("market") == "A" and case.get("entry_date")
    }
    return sorted(dates, reverse=True)[:limit]


def historical_scan_modules(value: str | None) -> set[str]:
    if not value:
        return set()
    mapping = {
        "all": {"capital_flow", "dragon_tiger_hot_money", "factor_base"},
        "daily_core": {"capital_flow", "factor_base"},
        "moneyflow": {"capital_flow"},
        "capital_flow": {"capital_flow"},
        "dragon_tiger": {"dragon_tiger_hot_money"},
        "dragon_tiger_hot_money": {"dragon_tiger_hot_money"},
        "factor_base": {"factor_base"},
    }
    return mapping.get(value, {value})


def historical_scan_endpoint(
    pro: Any,
    spec: ProbeSpec,
    dates: list[str],
    start_date: str,
    end_date: str,
) -> dict[str, Any]:
    checked = 0
    errors = 0
    last_error = None
    for trade_date in dates:
        checked += 1
        try:
            candidate = spec.call(pro, trade_date, start_date, end_date)
            df = candidate if isinstance(candidate, pd.DataFrame) else pd.DataFrame()
        except Exception as exc:  # noqa: BLE001 - provider endpoint errors vary
            errors += 1
            last_error = str(exc)[:240]
            continue
        row_count = int(len(df.index))
        if row_count > 0:
            return {
                "matched": True,
                "trade_date": trade_date,
                "row_count": row_count,
                "columns": list(map(str, df.columns[:30])),
                "sample_hash": dataframe_hash(df),
                "checked_count": checked,
                "error_count": errors,
                "last_error": last_error,
            }
    return {
        "matched": False,
        "trade_date": None,
        "row_count": 0,
        "columns": [],
        "sample_hash": None,
        "checked_count": checked,
        "error_count": errors,
        "last_error": last_error,
    }


def latest_open_trade_date(pro: Any, fallback_end: str) -> str:
    start, end = date_window(20)
    try:
        df = pro.trade_cal(exchange="", start_date=start, end_date=end, is_open="1")
    except Exception:
        return fallback_end
    if not isinstance(df, pd.DataFrame) or df.empty or "cal_date" not in df.columns:
        return fallback_end
    dates = [str(value) for value in df["cal_date"].dropna().tolist()]
    return max(dates) if dates else fallback_end


def first_sample_symbol(pro: Any) -> str:
    try:
        df = pro.stock_basic(exchange="", list_status="L", fields="ts_code,symbol,name")
    except Exception:
        return "600519.SH"
    if isinstance(df, pd.DataFrame) and not df.empty and "ts_code" in df.columns:
        preferred = df[df["ts_code"].astype(str).str.startswith(("600519", "000001", "300059"))]
        source = preferred if not preferred.empty else df
        return str(source.iloc[0]["ts_code"])
    return "600519.SH"


def specs(sample_symbol: str) -> list[ProbeSpec]:
    return [
        ProbeSpec(
            "capital_flow",
            "主力资金流向",
            "moneyflow",
            1,
            "大单/中单/小单资金结构",
            lambda pro, latest, start, end: pro.moneyflow(trade_date=latest),
        ),
        ProbeSpec(
            "dragon_tiger_hot_money",
            "龙虎榜 / 游资席位",
            "top_list",
            1,
            "龙虎榜上榜原因和异动标的",
            lambda pro, latest, start, end: pro.top_list(trade_date=latest),
        ),
        ProbeSpec(
            "dragon_tiger_hot_money",
            "龙虎榜 / 游资席位",
            "top_inst",
            1,
            "龙虎榜席位买卖结构",
            lambda pro, latest, start, end: pro.top_inst(trade_date=latest),
        ),
        ProbeSpec(
            "institutional_ownership",
            "机构持仓与股东变化",
            "top10_holders",
            2,
            "十大股东变化，需披露日防前视偏差",
            lambda pro, latest, start, end: pro.top10_holders(ts_code=sample_symbol, start_date=start, end_date=end),
        ),
        ProbeSpec(
            "institutional_ownership",
            "机构持仓与股东变化",
            "top10_floatholders",
            2,
            "十大流通股东变化，需披露日防前视偏差",
            lambda pro, latest, start, end: pro.top10_floatholders(ts_code=sample_symbol, start_date=start, end_date=end),
        ),
        ProbeSpec(
            "holder_concentration",
            "股东人数 / 筹码集中",
            "stk_holdernumber",
            2,
            "股东人数变化，用于筹码集中度线索",
            lambda pro, latest, start, end: pro.stk_holdernumber(ts_code=sample_symbol, start_date=start, end_date=end),
        ),
        ProbeSpec(
            "factor_base",
            "A 股因子与日线基础池",
            "stk_factor",
            3,
            "因子基础池，用于估值、动量、波动率输入",
            lambda pro, latest, start, end: pro.stk_factor(trade_date=latest),
        ),
        ProbeSpec(
            "factor_base",
            "A 股因子与日线基础池",
            "daily_basic",
            3,
            "日线基本面、换手率、市值、估值输入",
            lambda pro, latest, start, end: pro.daily_basic(trade_date=latest),
        ),
        ProbeSpec(
            "governance",
            "高管薪酬 / 治理",
            "stk_rewards",
            4,
            "高管薪酬与持股信息，只作治理线索",
            lambda pro, latest, start, end: pro.stk_rewards(ts_code=sample_symbol),
        ),
        ProbeSpec(
            "institutional_research",
            "机构调研热度",
            "stk_survey",
            4,
            "机构调研热度，可能需要额外权限",
            lambda pro, latest, start, end: pro.stk_survey(ts_code=sample_symbol, start_date=start, end_date=end),
        ),
    ]


def run_probe(window_days: int, *, historical_date_scan: str | None = None, historical_scan_limit: int = 30) -> dict[str, Any]:
    generated_at = now_iso()
    adapter = TushareAdapter.from_env()
    start_date, end_date = date_window(window_days)
    if not adapter.is_configured():
        return {
            "overall_status": "BLOCKED_MISSING_TUSHARE_TOKEN",
            "generated_at": generated_at,
            "provider": "tushare",
            "market": "A",
            "network_used": False,
            "raw_payload_saved": False,
            "secret_values_saved": False,
            "sample_symbol": None,
            "latest_trade_date": None,
            "date_window": {"start_date": start_date, "end_date": end_date},
            "summary": {"endpoint_count": 0, "pass_count": 0, "empty_count": 0, "blocked_count": 1},
            "modules": [],
            "safety": safety_block(),
        }

    try:
        pro = adapter._require_client()
    except ProviderError as exc:
        return {
            "overall_status": "BLOCKED_TUSHARE_CLIENT_UNAVAILABLE",
            "generated_at": generated_at,
            "provider": "tushare",
            "market": "A",
            "network_used": False,
            "raw_payload_saved": False,
            "secret_values_saved": False,
            "sample_symbol": None,
            "latest_trade_date": None,
            "date_window": {"start_date": start_date, "end_date": end_date},
            "summary": {"endpoint_count": 0, "pass_count": 0, "empty_count": 0, "blocked_count": 1},
            "modules": [],
            "blocker": str(exc),
            "safety": safety_block(),
        }

    latest = latest_open_trade_date(pro, end_date)
    sample_symbol = first_sample_symbol(pro)
    results: list[dict[str, Any]] = []
    scan_modules = historical_scan_modules(historical_date_scan)
    scan_dates = historical_entry_dates(limit=historical_scan_limit) if scan_modules else []
    for spec in specs(sample_symbol):
        error = None
        df = pd.DataFrame()
        try:
            candidate = spec.call(pro, latest, start_date, end_date)
            if isinstance(candidate, pd.DataFrame):
                df = candidate
        except Exception as exc:  # noqa: BLE001 - provider errors differ by endpoint/package
            error = str(exc)
        row_count = int(len(df.index)) if isinstance(df, pd.DataFrame) else 0
        status = endpoint_status(row_count, error)
        historical_scan_used = False
        historical_scan = None
        if status == "EMPTY" and spec.module_id in scan_modules and scan_dates:
            historical_scan_used = True
            historical_scan = historical_scan_endpoint(pro, spec, scan_dates, start_date, end_date)
            if historical_scan["matched"]:
                status = "PASS"
                row_count = historical_scan["row_count"]
                error = None
                df = pd.DataFrame(columns=historical_scan["columns"])
        results.append(
            {
                "module_id": spec.module_id,
                "module_name": spec.module_name,
                "endpoint": spec.endpoint,
                "priority": spec.priority,
                "description": spec.description,
                "status": status,
                "row_count": row_count,
                "columns": historical_scan["columns"] if historical_scan and historical_scan["matched"] else list(map(str, df.columns[:30])) if isinstance(df, pd.DataFrame) else [],
                "sample_hash": historical_scan["sample_hash"] if historical_scan and historical_scan["matched"] else dataframe_hash(df),
                "error_type": type(error).__name__ if error else None,
                "error_message": error[:240] if error else None,
                "latest_trade_date": latest,
                "sample_symbol": sample_symbol,
                "historical_scan_used": historical_scan_used,
                "historical_scan_target": historical_date_scan,
                "historical_probe_dates_checked": historical_scan["checked_count"] if historical_scan else 0,
                "historical_matched_trade_date": historical_scan["trade_date"] if historical_scan else None,
                "historical_scan_error_count": historical_scan["error_count"] if historical_scan else 0,
                "historical_scan_last_error": historical_scan["last_error"] if historical_scan else None,
            }
        )

    pass_count = sum(1 for item in results if item["status"] == "PASS")
    empty_count = sum(1 for item in results if item["status"] == "EMPTY")
    blocked_count = sum(1 for item in results if item["status"] in {"ERROR", "PERMISSION_BLOCKED"})
    overall = "PASS" if pass_count else "BLOCKED_NO_USABLE_STRATEGY_SOURCE"
    priority_ready = [item for item in results if item["priority"] <= 2 and item["status"] == "PASS"]
    return {
        "overall_status": overall,
        "generated_at": generated_at,
        "provider": "tushare",
        "market": "A",
        "network_used": True,
        "raw_payload_saved": False,
        "secret_values_saved": False,
        "sample_symbol": sample_symbol,
        "latest_trade_date": latest,
        "date_window": {"start_date": start_date, "end_date": end_date, "window_days": window_days},
        "summary": {
            "endpoint_count": len(results),
            "pass_count": pass_count,
            "empty_count": empty_count,
            "blocked_count": blocked_count,
            "priority_ready_count": len(priority_ready),
            "historical_scan_requested": bool(scan_modules),
            "historical_scan_target": historical_date_scan,
            "historical_scan_date_count": len(scan_dates),
            "historical_scan_pass_count": sum(
                1 for item in results if item.get("historical_scan_used") and item.get("status") == "PASS"
            ),
            "modules_ready": sorted({item["module_name"] for item in results if item["status"] == "PASS"}),
        },
        "modules": results,
        "next_step": "OpenClaw stock-agent should run historical sandbox only for PASS modules, starting with priority 1-2 endpoints.",
        "safety": safety_block(),
    }


def safety_block() -> dict[str, bool]:
    return {
        "simulation_research_only": True,
        "no_broker_api": True,
        "no_order_placement": True,
        "no_trading_webhook": True,
        "no_strategy_auto_mutation": True,
        "no_recommendation_record_write": True,
        "no_paper_trade_write": True,
    }


def write_outputs(report: dict[str, Any], run_id: str) -> dict[str, str]:
    run_dir = PROCESSED_DIR / run_id
    run_json = run_dir / "a_share_tushare_strategy_source_probe.json"
    run_md = run_dir / "a_share_tushare_strategy_source_probe.md"
    run_dir.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    text = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    run_json.write_text(text, encoding="utf-8")
    LATEST_JSON.write_text(text, encoding="utf-8")
    md = markdown_report(report)
    run_md.write_text(md, encoding="utf-8")
    LATEST_MD.write_text(md, encoding="utf-8")
    marker = PASS_MARKER if report["overall_status"] == "PASS" else BLOCKED_MARKER
    marker.write_text(
        f"status={report['overall_status']}\nrun_id={run_id}\ngenerated_at={report['generated_at']}\n",
        encoding="utf-8",
    )
    return {
        "run_json": str(run_json),
        "latest_json": str(LATEST_JSON),
        "latest_md": str(LATEST_MD),
        "marker": str(marker),
    }


def markdown_report(report: dict[str, Any]) -> str:
    lines = [
        "# A-share Tushare Strategy Source Probe",
        "",
        f"- Status: `{report['overall_status']}`",
        f"- Generated At: `{report['generated_at']}`",
        f"- Latest Trade Date: `{report.get('latest_trade_date')}`",
        f"- Sample Symbol: `{report.get('sample_symbol')}`",
        "- Boundary: simulation research only; no broker, no order, no trading webhook.",
        "",
        "## Summary",
        "",
    ]
    summary = report.get("summary", {})
    for key in ("endpoint_count", "pass_count", "empty_count", "blocked_count", "priority_ready_count"):
        if key in summary:
            lines.append(f"- {key}: `{summary[key]}`")
    if summary.get("historical_scan_requested"):
        lines.append(f"- historical_scan_target: `{summary.get('historical_scan_target')}`")
        lines.append(f"- historical_scan_pass_count: `{summary.get('historical_scan_pass_count')}`")
    lines.extend(["", "## Endpoints", "", "| Module | Endpoint | Status | Rows | Notes |", "| --- | --- | --- | ---: | --- |"])
    for item in report.get("modules", []):
        note = item.get("error_message") or ", ".join(item.get("columns", [])[:6]) or "no columns"
        if item.get("historical_scan_used"):
            note = f"historical_match={item.get('historical_matched_trade_date') or 'none'}; {note}"
        lines.append(
            f"| {item['module_name']} | `{item['endpoint']}` | `{item['status']}` | {item['row_count']} | {note} |"
        )
    lines.extend(["", "## Next", "", str(report.get("next_step", "Review blocked sources before sandbox.")), ""])
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Probe A-share Tushare strategy sources without saving raw payloads.")
    parser.add_argument("--window-days", type=int, default=120)
    parser.add_argument(
        "--historical-date-scan",
        choices=["all", "daily_core", "moneyflow", "capital_flow", "dragon_tiger", "dragon_tiger_hot_money", "factor_base"],
        help="When latest-date daily endpoints are empty, scan A-share historical case entry dates for matching rows.",
    )
    parser.add_argument("--historical-scan-limit", type=int, default=30)
    parser.add_argument("--run-id", default=f"a_share_tushare_strategy_source_probe_{datetime.now().strftime('%Y%m%dT%H%M%S')}")
    args = parser.parse_args(argv)

    report = run_probe(
        window_days=args.window_days,
        historical_date_scan=args.historical_date_scan,
        historical_scan_limit=args.historical_scan_limit,
    )
    outputs = write_outputs(report, args.run_id)
    print(json.dumps({"status": report["overall_status"], "outputs": outputs}, ensure_ascii=False, indent=2))
    return 0 if report["overall_status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
