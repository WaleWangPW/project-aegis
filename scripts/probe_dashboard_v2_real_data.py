#!/usr/bin/env python3
"""Inspect the reports consumed by Dashboard V2 without changing their contents."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "data" / "reports"
OUTPUT_JSON = REPORTS / "dashboard_v2_real_data_probe_latest.json"
OUTPUT_MD = REPORTS / "dashboard_v2_real_data_probe_latest.md"
FILES = [
    "aegis_health_status_latest.json",
    "aegis_evidence_gate_latest.json",
    "aegis_daily_dry_run_hardened_latest.json",
    "aegis_pipeline_history_latest.json",
    "a_share_watchlist_latest.json",
    "crcl_risk_monitor_latest.json",
    "000002.sz_risk_monitor_latest.json",
    "feishu_daily_digest_dry_run.json",
    "a_share_point_in_time_rolling_backtest_latest.json",
    "a_share_rolling_backtest_history_latest.json",
    "a_share_rolling_backtest_raw_price_audit_latest.json",
]
MAPPINGS = {
    "aegis_health_status_latest.json": ["health_status", "health_label", "generated_at", "gate_overall_verdict", "history_latest_result"],
    "aegis_evidence_gate_latest.json": ["overall_verdict", "failures", "gate_finished_at"],
    "aegis_daily_dry_run_hardened_latest.json": ["generated_at", "overall_verdict", "stages", "lock_recovery"],
    "aegis_pipeline_history_latest.json": ["updated_at", "runs"],
    "a_share_watchlist_latest.json": ["generated_at", "stocks", "top5"],
    "crcl_risk_monitor_latest.json": ["report_metadata", "current_status", "exit_watch_eligibility", "risk_metrics", "data_sources"],
    "000002.sz_risk_monitor_latest.json": ["report_metadata", "current_status", "exit_watch_eligibility", "risk_metrics", "data_sources"],
    "feishu_daily_digest_dry_run.json": ["generated_at", "hk_sample", "risk_monitors", "review_exit_risks"],
    "a_share_point_in_time_rolling_backtest_latest.json": ["generated_at", "strategy_id", "portfolio_metrics", "benchmark_metrics", "excess_return"],
    "a_share_rolling_backtest_history_latest.json": ["generated_at", "entries"],
    "a_share_rolling_backtest_raw_price_audit_latest.json": ["generated_at", "overall_verdict", "reported_aggregate_metrics"],
}


def inspect(path: Path) -> dict:
    row = {"file": path.name, "exists": path.is_file(), "json_parseable": False,
           "top_level_fields": [], "generated_at": None, "mtime": None,
           "sha256": None, "mappable_fields": MAPPINGS[path.name], "missing_fields": []}
    if not path.is_file():
        row["missing_fields"] = MAPPINGS[path.name]
        return row
    raw = path.read_bytes()
    row["sha256"] = hashlib.sha256(raw).hexdigest()
    row["mtime"] = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat()
    try:
        value = json.loads(raw)
    except (ValueError, UnicodeDecodeError) as exc:
        row["parse_error"] = str(exc)
        row["missing_fields"] = MAPPINGS[path.name]
        return row
    row["json_parseable"] = True
    if isinstance(value, dict):
        row["top_level_fields"] = list(value.keys())
        row["generated_at"] = value.get("generated_at") or value.get("gate_finished_at") or value.get("updated_at")
        row["missing_fields"] = [field for field in MAPPINGS[path.name] if field not in value]
    else:
        row["top_level_type"] = type(value).__name__
        row["missing_fields"] = MAPPINGS[path.name]
    return row


def main() -> int:
    rows = [inspect(REPORTS / name) for name in FILES]
    payload = {
        "project": "Project Aegis",
        "type": "dashboard_v2_real_data_probe",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "required_file_count": len(FILES),
        "existing_file_count": sum(row["exists"] for row in rows),
        "parseable_file_count": sum(row["json_parseable"] for row in rows),
        "files": rows,
    }
    OUTPUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = ["# Dashboard V2 真实数据探针", "", f"生成时间：{payload['generated_at']}", "",
             f"文件：{payload['existing_file_count']}/{payload['required_file_count']} 存在；{payload['parseable_file_count']} 可解析。", "",
             "| 文件 | 存在 | JSON | generated_at | 可映射字段 | 缺失字段 |", "|---|---|---|---|---|---|"]
    for row in rows:
        lines.append("| {file} | {exists} | {json_parseable} | {generated_at} | {mappable} | {missing} |".format(
            file=row["file"], exists="是" if row["exists"] else "否", json_parseable="是" if row["json_parseable"] else "否",
            generated_at=row["generated_at"] or "未提供", mappable=", ".join(row["mappable_fields"]),
            missing=", ".join(row["missing_fields"]) or "无"))
    OUTPUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[dashboard_v2_probe] JSON → {OUTPUT_JSON}")
    print(f"[dashboard_v2_probe] MD   → {OUTPUT_MD}")
    return 0 if payload["existing_file_count"] == len(FILES) and payload["parseable_file_count"] == len(FILES) else 1


if __name__ == "__main__":
    raise SystemExit(main())
