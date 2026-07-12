#!/usr/bin/env python3
"""Static and evidence validation for P25.6 real-usage acceptance."""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "data/reports"
OUT = REPORTS / "dashboard_p25_6_real_usage_validation_latest.json"
OUT_MD = REPORTS / "dashboard_p25_6_real_usage_validation_latest.md"


def check(name: str, passed: bool) -> dict:
    return {"name": name, "passed": bool(passed)}


def main() -> int:
    html = (ROOT / "dashboard/v2.html").read_text(encoding="utf-8")
    index = (ROOT / "dashboard/index.html").read_bytes()
    js = (ROOT / "dashboard/v2.js").read_text(encoding="utf-8")
    css = (ROOT / "dashboard/v2.css").read_text(encoding="utf-8")
    usage_path = REPORTS / "p25_6_real_usage_acceptance_latest.json"
    audit_path = REPORTS / "p25_5_dashboard_usage_audit_latest.json"
    usage = json.loads(usage_path.read_text(encoding="utf-8")) if usage_path.exists() else {}
    audit = json.loads(audit_path.read_text(encoding="utf-8")) if audit_path.exists() else {}
    derive = re.search(r"function deriveDailyDecision\(viewModel\) \{.*?\n\}", js, re.S)
    derive_hash = hashlib.sha256((derive.group(0) if derive else "").encode()).hexdigest()
    node = subprocess.run(["node", "--check", "dashboard/v2.js"], cwd=ROOT, capture_output=True, text=True)
    forbidden = ("mo" + "ck", "place" + "holder", "de" + "mo", "ran" + "dom", "模拟数据")
    checks = [
        check("contract_meta_2", 'aegis-dashboard-contract" content="2.0"' in html),
        check("index_equals_v2", index == html.encode()),
        check("node_check", node.returncode == 0),
        check("mobile_390_and_no_overflow", "@media(max-width:390px)" in css and "overflow-x:hidden" in css),
        check("details_collapsed", '<details id="research"' in html and '<details id="system-details"' in html),
        check("required_chinese_copy", all(text in html + js for text in ("今日结论", "风险阻塞", "当前持仓", "当前没有可执行候选", "数据不足，禁止行动"))),
        check("evidence_failure_blocks_action", "if (gate !== 'PASS')" in js and "state:'BLOCKED'" in js),
        check("no_execution_or_sending", all(text not in (html + js).lower() for text in ("place_" + "order(", "broker.buy", "broker.sell", "web" + "hook", "send("))),
        check("no_simulated_content", not any(text in (html + js + css).lower() for text in forbidden)),
        check("no_secret_value", not bool(re.search(r"sk-[A-Za-z0-9]{20,}|bearer\s+[A-Za-z0-9._-]{12,}", html + js, re.I))),
        check("no_composite_score", "综合评分" not in html + js),
        check("history_isolation", "历史策略不等于当前 Watchlist" in js and "回测结果不是实盘收益" in js),
        check("read_only_reports", "reportLink(" in js and "target=\"_blank\"" in js),
        check("derive_logic_unchanged", derive_hash == audit.get("derive_daily_decision_sha256")),
        check("project_scope_aegis", ROOT.name == "repo" and "project-aegis" in str(ROOT)),
        check("usage_report_complete", usage.get("overall_verdict") == "PASS" and isinstance(usage.get("tested_viewports"), list) and "data_semantics" in usage and "security" in usage),
    ]
    passed = all(item["passed"] for item in checks)
    payload = {
        "project": "Project Aegis",
        "type": "p25_6_real_usage_validation",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "overall_verdict": "PASS" if passed else "FAIL",
        "checks": checks,
        "derive_daily_decision_sha256": derive_hash,
        "usage_report": str(usage_path.relative_to(ROOT)),
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    OUT_MD.write_text("# P25.6 真实使用验证\n\n" + "\n".join(f"- {item['name']}: {'PASS' if item['passed'] else 'FAIL'}" for item in checks) + "\n", encoding="utf-8")
    print(f"[p25_6_validator] {payload['overall_verdict']} -> {OUT}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
