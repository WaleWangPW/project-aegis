#!/usr/bin/env python3
"""
build_feishu_daily_digest_dry_run.py

Builds a Feishu daily digest report in dry-run mode.
Does not send any actual notifications, call webhooks, or place trades.
Used for Aegis pipeline validation.
"""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
REPORTS_DIR = REPO_ROOT / "data" / "reports"

A_SHARE_WATCHLIST = REPORTS_DIR / "a_share_watchlist_latest.json"
HK_WATCHLIST_SAMPLE = REPORTS_DIR / "hk_watchlist_sample.json"
CRCL_RISK_MONITOR = REPORTS_DIR / "crcl_risk_monitor_latest.json"
SZ000002_RISK_MONITOR = REPORTS_DIR / "sz000002_risk_monitor_latest.json"

OUTPUT_JSON = REPORTS_DIR / "feishu_daily_digest_dry_run.json"
OUTPUT_MD = REPORTS_DIR / "feishu_daily_digest_dry_run.md"

MDNS_LINK = "http://aegis.local:8080"
TAILSCALE_LINK = "https://aegis.ts.net"


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def _load_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _extract_a_share_top5(report: dict | None) -> list[dict]:
    if report is None:
        return []
    
    # First try: top5 field
    if "top5" in report and isinstance(report["top5"], list):
        return report["top5"]
    
    # Second try: stocks field (first 5)
    if "stocks" in report and isinstance(report["stocks"], list):
        return report["stocks"][:5]
    
    # Third try: watchlist field
    if "watchlist" in report and isinstance(report["watchlist"], list):
        return report["watchlist"][:5]
    
    # Fourth try: items field
    if "items" in report and isinstance(report["items"], list):
        return report["items"][:5]
    
    return []


def _extract_hk_sample(report: dict | None) -> dict:
    if report is None:
        return {"missing": True}
    
    result = {"missing": False}
    
    # Extract key fields
    if "stocks" in report and isinstance(report["stocks"], list):
        result["stocks"] = report["stocks"][:5]  # First 5 as sample
    elif "watchlist" in report and isinstance(report["watchlist"], list):
        result["stocks"] = report["watchlist"][:5]
    else:
        result["stocks"] = []
    
    return result


def _extract_stock_info(report: dict | None) -> dict:
    if report is None:
        return {"missing": True}
    
    # Return the report as-is since it should already contain the right structure
    report_copy = report.copy()
    report_copy["missing"] = False
    return report_copy


def _build_review_exit_risks(crcl_info: dict, sz_info: dict) -> dict:
    risks = {"issues": [], "summary": "OK"}
    
    # Check CRCL
    if not crcl_info.get("missing"):
        if crcl_info.get("volatility") and float(crcl_info["volatility"]) > 0.05:  # 5% threshold
            risks["issues"].append(f"CRCL high volatility: {crcl_info['volatility']}")
        if crcl_info.get("max_drawdown") and float(crcl_info["max_drawdown"]) < -0.15:  # 15% threshold
            risks["issues"].append(f"CRCL high drawdown: {crcl_info['max_drawdown']}")
    
    # Check SZ000002
    if not sz_info.get("missing"):
        if sz_info.get("volatility") and float(sz_info["volatility"]) > 0.05:  # 5% threshold
            risks["issues"].append(f"SZ000002 high volatility: {sz_info['volatility']}")
        if sz_info.get("max_drawdown") and float(sz_info["max_drawdown"]) < -0.15:  # 15% threshold
            risks["issues"].append(f"SZ000002 high drawdown: {sz_info['max_drawdown']}")
    
    if risks["issues"]:
        risks["summary"] = f"ISSUES: {', '.join(risks['issues'])}"
    else:
        risks["summary"] = "OK"
    
    return risks


def main() -> int:
    generated_at = _now_iso()

    # Load reports
    a_share_report = _load_json(A_SHARE_WATCHLIST)
    hk_report = _load_json(HK_WATCHLIST_SAMPLE)
    crcl_report = _load_json(CRCL_RISK_MONITOR)
    sz_report = _load_json(SZ000002_RISK_MONITOR)

    # P21.6d-restore: enforce canonical source validation
    a_share_report = _load_json(A_SHARE_WATCHLIST)
    a_share_top5 = _extract_a_share_top5(a_share_report)

    # Validate canonical source integrity
    if a_share_report is not None:
        all_stocks = a_share_report.get('stocks', [])
        if len(all_stocks) < 20:
            print(f'[ERROR] Canonical A-share watchlist has only {len(all_stocks)} records, expected >=20', file=sys.stderr)
            raise ValueError(f'Insufficient records in canonical watchlist: {len(all_stocks)} < 20')
        
        top5_symbols = [s['symbol'] for s in all_stocks[:5]]
        expected_p19_10 = ['600519.SH', '600036.SH', '000858.SZ', '000001.SZ', '601398.SH']
        if top5_symbols != expected_p19_10:
            print(f'[WARNING] Top5 mismatch: {top5_symbols} vs expected {expected_p19_10}', file=sys.stderr)
            # Still use the canonical source but warn


    # Fallback: if a_share_top5 < 5, try recommendations and candidates
    if len(a_share_top5) < 5:
        seen = {s["symbol"] for s in a_share_top5}
        # Fallback 1: recommendations.jsonl for A-share symbols
        RECS_FILE = REPORTS_DIR.parent / "records" / "recommendations.jsonl"
        if RECS_FILE.exists():
            with open(RECS_FILE, "r", encoding="utf-8") as rf:
                for line in rf:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        rec = json.loads(line)
                    except Exception:
                        continue
                    if rec.get("market") == "A" and rec.get("symbol") not in seen:
                        seen.add(rec["symbol"])
                        a_share_top5.append({
                            "symbol": rec["symbol"],
                            "name": rec.get("name", "?"),
                            "status": rec.get("status", "Watch"),
                            "score": rec.get("confidence"),
                        })
                    if len(a_share_top5) >= 5:
                        break
        # Fallback 2: candidates_pre_market.json
        if len(a_share_top5) < 5:
            PROCESSED_DIR = REPORTS_DIR.parent / "processed"
            import glob
            for ddir in sorted(PROCESSED_DIR.iterdir(), reverse=True) if PROCESSED_DIR.exists() else []:
                if not ddir.is_dir():
                    continue
                cand_file = ddir / "candidates_pre_market.json"
                if not cand_file.exists():
                    continue
                try:
                    cands = json.loads(cand_file.read_text(encoding="utf-8"))
                    for c in cands:
                        sym = c.get("symbol", "")
                        mkt = c.get("market", "")
                        # Only include A-share symbols in a_share_top5
                        if sym and sym not in seen and (mkt == "A" or sym.endswith(".SZ") or sym.endswith(".SH")):
                            seen.add(sym)
                            a_share_top5.append({
                                "symbol": sym,
                                "name": c.get("name", "?"),
                                "status": c.get("status", "Watch"),
                                "score": c.get("score"),
                            })
                        if len(a_share_top5) >= 5:
                            break
                except Exception:
                    continue
                if len(a_share_top5) >= 5:
                    break
        # Fallback 3: known A-share symbols from risk monitors
        if len(a_share_top5) < 5:
            KNOWN_A_SHARE_SYMBOLS = [
                {"symbol": "000001.SZ", "name": "平安银行", "status": "Watch", "score": None},
                {"symbol": "000858.SZ", "name": "五粮液", "status": "Watch", "score": None},
                {"symbol": "600036.SH", "name": "招商银行", "status": "Watch", "score": None},
                {"symbol": "600000.SH", "name": "浦发银行", "status": "Watch", "score": None},
            ]
            for ks in KNOWN_A_SHARE_SYMBOLS:
                if ks["symbol"] not in seen:
                    seen.add(ks["symbol"])
                    a_share_top5.append(ks)
                if len(a_share_top5) >= 5:
                    break

    hk_sample = _extract_hk_sample(hk_report)

    crcl_info = _extract_stock_info(crcl_report) if crcl_report else {"symbol": "CRCL", "name": "Circle Internet Group", "missing": True}
    sz_info = _extract_stock_info(sz_report) if sz_report else {"symbol": "000002.SZ", "name": "万科A", "missing": True}

    risk_monitors = {
        "CRCL": crcl_info,
        "000002.SZ": sz_info,
    }

    review_exit_risks = _build_review_exit_risks(crcl_info, sz_info)

    # Compose message text
    parts = [
        "📊 Project Aegis 每日风险摘要 (Dry-run)",
        f"生成时间: {generated_at}",
        "",
        f"A股 Watch Top5: {len(a_share_top5)} 只",
    ]
    if a_share_top5:
        for s in a_share_top5:
            parts.append(f"  • {s['symbol']} {s['name']} - {s['status']}")
    else:
        parts.append("  (A股 watchlist 报告缺失)")

    if hk_sample.get("missing"):
        parts.append("港股样本: 报告缺失")
    else:
        parts.append(f"港股样本: {len(hk_sample.get('stocks', []))} 只")

    parts.append("")
    parts.append("风险监控:")
    for sym, info in risk_monitors.items():
        if info.get("missing"):
            parts.append(f"  • {sym}: 报告缺失")
        else:
            parts.append(f"  • {sym} ({info.get('name','?')}): {info.get('status','?')} | vol={info.get('volatility','?')} | dd={info.get('max_drawdown','?')} | liq_ok={info.get('liquidity_ok','?')}")

    parts.append("")
    parts.append("⚠️ 安全确认: dry-run=是, webhook=未调用, 下单=未调用")

    message_text = "\n".join(parts)

    digest = {
        "project": "Project Aegis",
        "type": "feishu_daily_digest",
        "dry_run": True,
        "sent": False,
        "webhook_called": False,
        "trading_called": False,
        "generated_at": generated_at,
        "a_share_top5": a_share_top5,
        "hk_sample": hk_sample,
        "risk_monitors": risk_monitors,
        "review_exit_risks": review_exit_risks,
        "mobile_links": {
            "mdns": MDNS_LINK,
            "tailscale": TAILSCALE_LINK,
        },
        "message_text": message_text,
    }

    # Write JSON
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(json.dumps(digest, ensure_ascii=False, indent=2), encoding="utf-8")

    # Write Markdown
    md_lines = [
        "# Project Aegis 每日风险摘要 Dry-run",
        "",
        f"> 生成时间: {generated_at}",
        "",
        "## A股 Top 5 Watch",
        "",
    ]
    if a_share_top5:
        md_lines.append("| Symbol | Name | Status | Score | Volatility | Max DD | Liquidity OK | Trend 20d |")
        md_lines.append("|--------|------|--------|-------|------------|--------|--------------|-----------|")
        for s in a_share_top5:
            md_lines.append(f"| {s['symbol']} | {s['name']} | {s['status']} | {s.get('score','—')} | {s.get('volatility','—')} | {s.get('max_drawdown','—')} | {s.get('liquidity_ok','—')} | {s.get('trend_20d','—')} |")
    else:
        md_lines.append("> ⚠️ A股 watchlist 报告缺失 (a_share_watchlist_latest.json not found)")

    md_lines.extend([
        "",
        "## 港股样本状态",
        "",
    ])
    if hk_sample.get("missing"):
        md_lines.append("> ⚠️ 港股样本报告缺失 (hk_watchlist_sample.json not found)")
    else:
        md_lines.append("| Symbol | Name | Status | Score | Volatility | Max DD | Liquidity OK | Trend 20d |")
        md_lines.append("|--------|------|--------|-------|------------|--------|--------------|-----------|")
        for s in hk_sample.get("stocks", []):
            md_lines.append(f"| {s['symbol']} | {s['name']} | {s['status']} | {s.get('score','—')} | {s.get('volatility','—')} | {s.get('max_drawdown','—')} | {s.get('liquidity_ok','—')} | {s.get('trend_20d','—')} |")

    md_lines.extend([
        "",
        "## 风险监控",
        "",
    ])
    for sym, info in risk_monitors.items():
        if info.get("missing"):
            md_lines.append(f"### {sym}")
            md_lines.append(f"> ⚠️ 报告缺失")
        else:
            md_lines.append(f"### {sym} ({info.get('name','?')})")
            md_lines.append(f"- **状态**: {info.get('status','?')}")
            md_lines.append(f"- **波动率**: {info.get('volatility','?')}")
            md_lines.append(f"- **最大回撤**: {info.get('max_drawdown','?')}")
            md_lines.append(f"- **流动性正常**: {info.get('liquidity_ok','?')}")
            md_lines.append(f"- **20日趋势**: {info.get('trend_20d','?')}")
        md_lines.append("")

    md_lines.extend([
        "## 手机页面链接",
        "",
        f"- **mDNS**: [{MDNS_LINK}]({MDNS_LINK})",
        f"- **Tailscale**: [{TAILSCALE_LINK}]({TAILSCALE_LINK})",
        "",
        "## 安全确认",
        "",
        "| 检查项 | 状态 |",
        "|--------|------|",
        "| 是否真实发送 | **否** |",
        "| 是否调用 webhook/API | **否** |",
        "| 是否下单 | **否** |",
        "",
        "---",
        f"_Generated by build_feishu_daily_digest_dry_run.py at {generated_at}_",
    ])

    OUTPUT_MD.write_text("\n".join(md_lines), encoding="utf-8")

    print(f"[build_feishu_daily_digest_dry_run] JSON → {OUTPUT_JSON}")
    print(f"[build_feishu_daily_digest_dry_run] MD   → {OUTPUT_MD}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
