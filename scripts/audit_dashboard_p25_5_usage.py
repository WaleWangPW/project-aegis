#!/usr/bin/env python3
"""Read-only pre-change usage audit for the CEO Dashboard."""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "data" / "reports"
OUT_JSON = REPORTS / "p25_5_dashboard_usage_audit_latest.json"
OUT_MD = REPORTS / "p25_5_dashboard_usage_audit_latest.md"


def main() -> int:
    html = (ROOT / "dashboard" / "index.html").read_text(encoding="utf-8")
    css = (ROOT / "dashboard" / "v2.css").read_text(encoding="utf-8")
    js = (ROOT / "dashboard" / "v2.js").read_text(encoding="utf-8")
    derive = re.search(r"function deriveDailyDecision\(viewModel\) \{.*?\n\}", js, re.S)
    sections = re.findall(r'<(?:section|details)[^>]+(?:id="([^"]+)"|class="([^"]*section[^"]*)")[^>]*>', html)
    payload = {
        "project": "Project Aegis", "type": "p25_5_dashboard_usage_audit",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "pre_change_index_sha256": hashlib.sha256((ROOT / "dashboard" / "index.html").read_bytes()).hexdigest(),
        "derive_daily_decision_sha256": hashlib.sha256((derive.group(0) if derive else "").encode()).hexdigest(),
        "first_screen_order": ["状态栏", "今日结论", "风险与退出", "当前持仓", "下次检查"],
        "business_use": {"今日结论":"行动边界", "风险与退出":"优先减风险", "当前持仓":"持仓复核", "候选观察":"低频研究", "历史研究":"背景参考", "系统详情":"证据追溯"},
        "findings": [
            "状态栏、下次检查和每日自动检查存在重复时间信息。",
            "候选观察使用技术状态词，缺少支持/反对/失效条件的用户化摘要。",
            "当前持仓未区分可提供与未提供的价格、成本和收益字段。",
            "市场环境信息偏简略，行动边界与今日结论重复。",
            "历史研究与系统详情已折叠，符合低频使用场景。",
            "390px 样式存在单列规则与 overflow-x:hidden，但折叠区 summary 原规则需要继续关注可点击性。",
            "页面没有默认表格，390px 下主要内容为卡片。",
            "数据更新时间在状态栏清晰，但首屏信息密度仍可继续压缩。",
            "历史策略隔离提示存在，避免与当前建议混淆。",
        ],
        "technical_copy": ["Watch / Review", "Action", "Ready", "Exit", "Pipeline"],
        "sections_detected": sections,
        "mobile_rules": {"has_390_query": "390px" in css, "has_single_column": "grid-template-columns:1fr" in css, "has_no_horizontal_scroll": "overflow-x:hidden" in css, "font_base": "15px" in css, "touch_target": "min-height:44px" in css},
        "empty_states": ["当前没有紧急风险。", "当前没有可执行候选", "数据不足，禁止行动。", "候选列表尚未生成。", "自动检查状态未知。"],
    }
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = ["# P25.5 Dashboard 使用审计（修改前）", "", f"生成时间：{payload['generated_at']}", "", "## 结论", ""]
    lines.extend(f"- {item}" for item in payload["findings"])
    lines += ["", "## 首屏顺序", "", "状态栏 → 今日结论 → 风险与退出 → 当前持仓 → 下次检查。", "", "## 冻结", "", f"deriveDailyDecision SHA-256：`{payload['derive_daily_decision_sha256']}`"]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[p25_5_audit] JSON → {OUT_JSON}")
    print(f"[p25_5_audit] MD   → {OUT_MD}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
