#!/usr/bin/env python3
"""
build_aegis_health_status.py

Generates a lightweight health status report for dashboard/mobile quick read.
Aggregates status from multiple source reports into a single health status file.
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
REPORTS_DIR = REPO_ROOT / "data" / "reports"

# Input files
GATE_REPORT = REPORTS_DIR / "aegis_evidence_gate_latest.json"
HISTORY_REPORT = REPORTS_DIR / "aegis_pipeline_history_latest.json"
FEISHU_REPORT = REPORTS_DIR / "feishu_daily_digest_dry_run.json"
WATCHLIST_REPORT = REPORTS_DIR / "a_share_watchlist_latest.json"

# Output files
HEALTH_JSON = REPORTS_DIR / "aegis_health_status_latest.json"
HEALTH_MD = REPORTS_DIR / "aegis_health_status_latest.md"


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def _load_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def main() -> int:
    generated_at = _now_iso()
    
    # Load all reports
    gate_data = _load_json(GATE_REPORT)
    history_data = _load_json(HISTORY_REPORT)
    feishu_data = _load_json(FEISHU_REPORT)
    watchlist_data = _load_json(WATCHLIST_REPORT)
    
    # Initialize default values for safety
    gate_overall_verdict = "MISSING"
    history_latest_result = "MISSING"
    feishu_dry_run = False
    sent = True  # Default to dangerous state if missing
    webhook_called = True  # Default to dangerous state if missing
    trading_called = True  # Default to dangerous state if missing
    a_share_top5_symbols = []
    hk_00700_status = "MISSING"
    crcl_status = "MISSING"
    sz_000002_status = "MISSING"
    
    # Extract gate status
    if gate_data:
        gate_overall_verdict = gate_data.get("overall_verdict", "MISSING")
    
    # Extract history status
    if history_data and "runs" in history_data and len(history_data["runs"]) > 0:
        latest_run = history_data["runs"][0]
        history_latest_result = latest_run.get("result", "MISSING")
    
    # Extract feishu status
    if feishu_data:
        feishu_dry_run = feishu_data.get("dry_run", False)
        sent = feishu_data.get("sent", True)
        webhook_called = feishu_data.get("webhook_called", True)
        trading_called = feishu_data.get("trading_called", True)
        
        # Extract HK status
        hk_sample = feishu_data.get("hk_sample", {})
        if hk_sample.get("missing"):
            hk_00700_status = "MISSING"
        else:
            hk_00700_status = hk_sample.get("status", "PRESENT")
        
        # Extract risk monitor statuses
        risk_monitors = feishu_data.get("risk_monitors", {})
        crcl_info = risk_monitors.get("CRCL", {})
        sz_info = risk_monitors.get("000002.SZ", {})
        
        crcl_status = "MISSING" if crcl_info.get("missing") else crcl_info.get("status", "PRESENT")
        sz_000002_status = "MISSING" if sz_info.get("missing") else sz_info.get("status", "PRESENT")
    
    # Extract A-share Top5
    if watchlist_data:
        if "top5" in watchlist_data and isinstance(watchlist_data["top5"], list):
            a_share_top5_symbols = [s.get("symbol", "") for s in watchlist_data["top5"] if s.get("symbol")]
        elif "stocks" in watchlist_data and isinstance(watchlist_data["stocks"], list):
            a_share_top5_symbols = [s.get("symbol", "") for s in watchlist_data["stocks"][:5] if s.get("symbol")]
    
    # Determine health status
    health_status = "NORMAL"  # Default to normal
    health_label = "正常"
    reason = "All systems nominal"
    
    # Check for CRITICAL conditions first
    if sent or webhook_called or trading_called:
        health_status = "CRITICAL"
        health_label = "异常"
        reason = "Critical safety violation detected"
    elif gate_overall_verdict == "FAIL":
        health_status = "CRITICAL"
        health_label = "异常"
        reason = "Evidence gate failed"
    elif gate_overall_verdict == "MISSING":
        health_status = "WARNING"
        health_label = "注意"
        reason = "Gate status unavailable"
    elif history_latest_result == "FAIL":
        health_status = "WARNING"
        health_label = "注意"
        reason = "Latest history run failed"
    elif history_latest_result == "MISSING":
        health_status = "WARNING"
        health_label = "注意"
        reason = "History status unavailable"
    elif len(a_share_top5_symbols) < 5:
        health_status = "WARNING"
        health_label = "注意"
        reason = f"A-share Top5 count insufficient: {len(a_share_top5_symbols)}/5"
    elif gate_overall_verdict != "PASS":
        health_status = "WARNING"
        health_label = "注意"
        reason = f"Gate status: {gate_overall_verdict}"
    
    # Create health status report
    health_report = {
        "project": "Project Aegis",
        "type": "health_status",
        "generated_at": generated_at,
        "health_status": health_status,
        "health_label": health_label,
        "reason": reason,
        "gate_overall_verdict": gate_overall_verdict,
        "history_latest_result": history_latest_result,
        "feishu_dry_run": feishu_dry_run,
        "sent": sent,
        "webhook_called": webhook_called,
        "trading_called": trading_called,
        "a_share_top5_symbols": a_share_top5_symbols,
        "hk_00700_status": hk_00700_status,
        "crcl_status": crcl_status,
        "sz_000002_status": sz_000002_status,
        "source_files": {
            "gate": GATE_REPORT.exists(),
            "history": HISTORY_REPORT.exists(),
            "feishu": FEISHU_REPORT.exists(),
            "watchlist": WATCHLIST_REPORT.exists()
        },
        "safety_confirmations": {
            "dry_run": feishu_dry_run,
            "sent_false": sent is False,
            "webhook_not_called": webhook_called is False,
            "trading_not_called": trading_called is False
        }
    }
    
    # Write JSON
    HEALTH_JSON.parent.mkdir(parents=True, exist_ok=True)
    HEALTH_JSON.write_text(json.dumps(health_report, ensure_ascii=False, indent=2), encoding="utf-8")
    
    # Write Markdown
    md_lines = [
        "# Project Aegis 健康状态",
        "",
        f"> 生成时间: {generated_at}",
        f"> 状态: **{health_label}** ({health_status})",
        f"> 原因: {reason}",
        "",
        "## 详细状态",
        "",
        f"- **Gate 总体状态**: {gate_overall_verdict}",
        f"- **历史最新结果**: {history_latest_result}",
        f"- **飞书 Dry-run**: {feishu_dry_run}",
        f"- **已发送**: {sent}",
        f"- **Webhook 调用**: {webhook_called}",
        f"- **交易调用**: {trading_called}",
        "",
        "## A股 Top5",
        ""
    ]
    
    if a_share_top5_symbols:
        for i, symbol in enumerate(a_share_top5_symbols, 1):
            md_lines.append(f"{i}. {symbol}")
    else:
        md_lines.append("*(无数据)*")
    
    md_lines.extend([
        "",
        "## 风险监控状态",
        f"- **港股 00700**: {hk_00700_status}",
        f"- **CRCL**: {crcl_status}",
        f"- **深股 000002**: {sz_000002_status}",
        "",
        "## 安全确认",
        f"- **Dry-run 模式**: {'✅' if feishu_dry_run else '❌'}",
        f"- **未真实发送**: {'✅' if sent is False else '❌'}",
        f"- **未调用 Webhook**: {'✅' if webhook_called is False else '❌'}",
        f"- **未调用交易**: {'✅' if trading_called is False else '❌'}",
        "",
        "---",
        f"_Generated by build_aegis_health_status.py at {generated_at}_",
    ])
    
    HEALTH_MD.write_text("\n".join(md_lines), encoding="utf-8")
    
    print(f"[build_aegis_health_status] JSON → {HEALTH_JSON}")
    print(f"[build_aegis_health_status] MD   → {HEALTH_MD}")
    print(f"[build_aegis_health_status] Health status: {health_label} ({health_status})")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
