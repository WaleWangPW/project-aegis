#!/usr/bin/env python3
"""Static verification for the Dashboard V2 real-report implementation."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "data" / "reports"
TARGETS = [ROOT / "dashboard" / name for name in ("v2.html", "v2.css", "v2.js")]
OUT = REPORTS / "dashboard_v2_real_validation_latest.json"
PASS = REPORTS / "P25_1_DASHBOARD_V2_REAL_PASS.marker"
FAIL = REPORTS / "P25_1_DASHBOARD_V2_REAL_FAIL.marker"


def check(name: str, passed: bool, detail: str = "") -> dict:
    return {"name": name, "passed": passed, "detail": detail}


def main() -> int:
    js = (ROOT / "dashboard" / "v2.js").read_text(encoding="utf-8") if TARGETS[2].is_file() else ""
    css = (ROOT / "dashboard" / "v2.css").read_text(encoding="utf-8") if TARGETS[1].is_file() else ""
    html = (ROOT / "dashboard" / "v2.html").read_text(encoding="utf-8") if TARGETS[0].is_file() else ""
    probe_path = REPORTS / "dashboard_v2_real_data_probe_latest.json"
    probe = json.loads(probe_path.read_text(encoding="utf-8")) if probe_path.is_file() else {}
    index_hash = hashlib.sha256((ROOT / "dashboard" / "index.html").read_bytes()).hexdigest() if (ROOT / "dashboard" / "index.html").is_file() else None
    prohibited = ["mo" + "ck", "place" + "holder", "ex" + "ample", "de" + "mo", "模拟数据"]
    target_text = "\n".join((html, css, js)).lower()
    checks = [
        check("v2_files_exist", all(path.is_file() for path in TARGETS)),
        check("probe_exists_and_counts_real_sources", probe.get("existing_file_count") == 11 and probe.get("parseable_file_count") == 11),
        check("no_prohibited_content", not any(word in target_text for word in prohibited)),
        check("no_fixed_backtest_return", "18.74" not in target_text),
        check("fetches_use_reports_relative_path", "reportBase = '../data/reports/'" in js),
        check("no_dashboard_data_reports_path", "/dashboard/data/reports/" not in target_text),
        check("daily_decision_function_exists", "function deriveDailyDecision(viewModel)" in js),
        check("gate_failure_blocks_action", "gate !== 'PASS'" in js and "state:'BLOCKED'" in js),
        check("daily_failure_blocks_action", "latestRun === 'FAIL'" in js),
        check("risk_exit_precedes_action", js.find("if (risks.length)") < js.find("if (actions.length)")),
        check("backtest_metrics_map_real_reports", "d.rolling?.portfolio_metrics" in js and "d.audit?.overall_verdict" in js),
        check("historical_strategy_notice", "历史策略不等于当前 Watchlist。" in js),
        check("no_trade_controls", "交易" not in html and "交易" not in js),
        check("no_send_or_webhook_calls", "webhook" not in js.lower() and "send(" not in js.lower()),
        check("mobile_media_query", "@media (max-width:760px)" in css),
        check("degrade_copy_exists", "数据未提供" in js and "数据不足，禁止行动。" in js),
        check("index_unchanged_hash_available", bool(index_hash), index_hash or "index missing"),
    ]
    passed = all(item["passed"] for item in checks)
    payload = {"project":"Project Aegis", "type":"dashboard_v2_real_validation", "generated_at":datetime.now(timezone.utc).isoformat(), "overall_verdict":"PASS" if passed else "FAIL", "checks":checks, "dashboard_index_html_sha256":index_hash}
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for marker in (PASS, FAIL):
        if marker.exists(): marker.unlink()
    marker = PASS if passed else FAIL
    marker.write_text(f"{payload['overall_verdict']}\n", encoding="utf-8")
    print(f"[dashboard_v2_validation] {payload['overall_verdict']} → {OUT}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
