#!/usr/bin/env python3
"""Static acceptance for the CEO Daily Brief information architecture."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "data" / "reports" / "dashboard_v2_ceo_brief_validation_latest.json"
FAIL_MARKER = ROOT / "data" / "reports" / "P25_4_DASHBOARD_PRODUCTION_FAIL.marker"
FAIL_REASON = ROOT / "data" / "reports" / "P25_4_DASHBOARD_PRODUCTION_FAIL_REASON.md"


def result(name: str, passed: bool) -> dict:
    return {"name": name, "passed": passed}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--expected-index-sha", required=True)
    args = parser.parse_args()
    html = (ROOT / "dashboard" / "v2.html").read_text(encoding="utf-8")
    css = (ROOT / "dashboard" / "v2.css").read_text(encoding="utf-8")
    js = (ROOT / "dashboard" / "v2.js").read_text(encoding="utf-8")
    text = "\n".join((html, css, js)).lower()
    order = [html.find('class="statusbar"'), html.find('id="decision"'), html.find('id="risk"'), html.find('id="holdings"'), html.find('id="next-check"')]
    forbidden = ["mo" + "ck", "place" + "holder", "de" + "mo", "ran" + "dom", "模拟数据"]
    index_hash = hashlib.sha256((ROOT / "dashboard" / "index.html").read_bytes()).hexdigest()
    checks = [
        result("first_screen_order", all(a >= 0 and a < b for a, b in zip(order, order[1:]))),
        result("watchlist_default_max_five", 'const focus=watchlist.slice(0,5)' in js),
        result("remaining_watchlist_collapsed", '查看全部候选' in js and '<details>' in js),
        result("research_collapsed", '<details id="research"' in html),
        result("system_details_collapsed", '<details id="system-details"' in html),
        result("risk_before_watchlist", html.find('id="risk"') < html.find('id="watchlist"')),
        result("mobile_single_column", '.decision-actions,.grid,.watch-grid{grid-template-columns:1fr}' in css),
        result("mobile_no_horizontal_scroll", 'body{overflow-x:hidden}' in css),
        result("mobile_order_matches_document", all(a >= 0 and a < b for a, b in zip(order, order[1:]))),
        result("touch_targets_minimum", 'button{min-height:44px' in css and 'details>summary{cursor:pointer;color:var(--muted);min-height:44px' in css),
        result("font_minimum", 'font:15px/' in css),
        result("no_prohibited_content", not any(word in text for word in forbidden)),
        result("no_fixed_backtest_return", '18.74' not in text),
        result("no_trade_or_send_controls", '交易' not in html and '发送' not in html and 'webhook' not in text),
        result("no_composite_score", '综合评分' not in text),
        result("index_pre_replace_unchanged", index_hash == args.expected_index_sha),
    ]
    passed = all(item["passed"] for item in checks)
    payload = {"project": "Project Aegis", "type": "dashboard_v2_ceo_brief_validation", "generated_at": datetime.now(timezone.utc).isoformat(), "overall_verdict": "PASS" if passed else "FAIL", "expected_index_sha256": args.expected_index_sha, "actual_index_sha256": index_hash, "checks": checks}
    REPORT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if not passed:
        FAIL_MARKER.write_text("FAIL\n", encoding="utf-8")
        failed = [item["name"] for item in checks if not item["passed"]]
        FAIL_REASON.write_text("# P25.4 未执行首页替换\n\n静态验收未通过：" + "、".join(failed) + "。\n\n首页仍为替换前版本。\n", encoding="utf-8")
    print(f"[dashboard_ceo_brief] {payload['overall_verdict']} → {REPORT}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
