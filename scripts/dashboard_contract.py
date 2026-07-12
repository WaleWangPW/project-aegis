"""Dashboard Contract 2.0 inspection shared by the evidence gate and tests."""
from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

CONTRACT_META = '<meta name="aegis-dashboard-contract" content="2.0">'
LEGACY_V1_SHA256 = "c046ba871b5fe809762baf281b60475920cb63dd20972bbad536fba7e50b27c4"


def _check(name: str, passed: bool, detail: str = "") -> dict:
    return {"name": name, "passed": passed, "detail": detail}


def inspect_dashboard(html_path: Path, js_path: Path, css_path: Path) -> dict:
    html = html_path.read_text(encoding="utf-8") if html_path.is_file() else ""
    js = js_path.read_text(encoding="utf-8") if js_path.is_file() else ""
    css = css_path.read_text(encoding="utf-8") if css_path.is_file() else ""
    marker = re.search(r'<meta\s+name="aegis-dashboard-contract"\s+content="([^"]+)"\s*>', html)
    version = marker.group(1) if marker else None
    html_sha = hashlib.sha256(html.encode()).hexdigest() if html else None
    legacy_fingerprint = [
        _check("legacy_no_contract_meta", version is None),
        _check("legacy_known_sha256", html_sha == LEGACY_V1_SHA256),
        _check("legacy_title", "<title>Project Aegis 风险监控</title>" in html),
        _check("legacy_health_light", 'id="health-light-card"' in html),
        _check("legacy_feishu_card", 'id="feishu-dry-run-card"' in html),
        _check("legacy_pipeline_card", 'id="pipeline-history-card"' in html and "aegis_pipeline_history_latest.json" in html),
        _check("legacy_no_v2_assets", 'href="v2.css"' not in html and 'src="v2.js"' not in html),
    ]
    legacy_valid = all(item["passed"] for item in legacy_fingerprint)
    dashboard_type = "ceo_daily_brief_v2" if version == "2.0" else "legacy_dashboard_v1" if version is None and legacy_valid else "unknown"
    security = [
        _check("dashboard_html_readable", bool(html)),
        _check("assets_exist", bool(js) and bool(css)),
        _check("reports_relative_fetch", "reportBase = '../data/reports/'" in js),
        _check("no_dashboard_reports_path", "/dashboard/data/reports/" not in html and "/dashboard/data/reports/" not in js),
        _check("fetch_failure_degrades", "invalid.push(name); return null" in js and "数据未提供" in js),
        _check("gate_failure_blocks_action", "gate !== 'PASS'" in js and "state:'BLOCKED'" in js),
        _check("daily_failure_blocks_action", "latestRun === 'FAIL'" in js),
        _check("risk_before_action", js.find("if (risks.length)") >= 0 and js.find("if (risks.length)") < js.find("if (actions.length)")),
        _check("no_trade_execution", not any(term in (html + js).lower() for term in ("place_" + "order(", "broker." + "buy", "broker." + "sell", "submit_" + "order("))),
        _check("no_send_or_webhook", not re.search(r"webhook\.send\(|send_webhook\(|\.send\(", html + js, re.IGNORECASE)),
        _check("no_secrets", not re.search(r"sk-[A-Za-z0-9]{20,}|bearer\s+[A-Za-z0-9._-]{12,}", html + js)),
        _check("no_simulated_content", not any(term in (html + js + css).lower() for term in ("mo" + "ck", "place" + "holder", "de" + "mo", "ran" + "dom", "模拟数据"))),
        _check("no_composite_score", "综合评分" not in html + js),
        _check("no_trade_or_send_buttons", not re.search(r"<button[^>]*>[^<]*(交易|发送)", html, re.IGNORECASE)),
        _check("read_only_report_links", "reportLink(" in js),
    ]
    v2 = []
    warnings = []
    if dashboard_type == "ceo_daily_brief_v2":
        v2 = [
            _check("contract_meta_exact", version == "2.0"),
            _check("v2_assets_referenced", 'href="v2.css"' in html and 'src="v2.js"' in html),
            _check("ceo_sections", all(text in html for text in ("今日结论", "风险阻塞", "当前持仓", "可执行候选", "观察名单", "市场状态", "历史回测", "系统与证据详情", "刷新")) or all(text in html for text in ("今日结论", "风险与退出", "当前持仓", "候选观察", "市场环境", "历史研究结果", "系统与数据详情", "刷新"))),
            _check("decision_function", "function deriveDailyDecision(viewModel)" in js and "const vm=" in js),
            _check("no_data_action_block", "数据不足，禁止行动" in js),
            _check("no_action_empty_state", "当前没有可执行候选" in js),
            _check("history_isolation_notice", "历史策略不等于当前 Watchlist" in js and "回测结果不是实盘收益" in js),
            _check("real_rolling_mapping", "d.rolling?.portfolio_metrics" in js and "d.audit?.overall_verdict" in js),
            _check("no_fixed_return", "18.74" not in js),
        ]
        warnings = [
            {"name":"legacy_feishu_home_module", "old_requirement":"首页展示飞书日报", "reason":"仅适用于 legacy v1", "v2_replacement":"飞书安全仍由证据层检查", "safety_unchanged":"dry_run/sent/webhook/trading"},
            {"name":"legacy_pipeline_dom", "old_requirement":"首页保留旧 Pipeline 区块与降级文案", "reason":"仅适用于 legacy v1", "v2_replacement":"系统与数据详情及 fetch 失败降级", "safety_unchanged":"数据路径、降级和哈希检查"},
        ]
    elif dashboard_type == "legacy_dashboard_v1":
        v2 = legacy_fingerprint
    else:
        v2 = [_check("recognized_contract", False, f"unsupported contract: {version}")]
    all_checks = security + v2
    return {
        "detected_contract_version": version or ("legacy-v1" if dashboard_type == "legacy_dashboard_v1" else "missing"),
        "detected_dashboard_type": dashboard_type,
        "mandatory_security_checks": security,
        "v2_contract_checks": v2 if dashboard_type == "ceo_daily_brief_v2" else [],
        "legacy_checks": v2 if dashboard_type == "legacy_dashboard_v1" else [],
        "warnings": warnings,
        "failures": [item["name"] for item in all_checks if not item["passed"]],
        "dashboard_sha256": html_sha,
        "js_sha256": hashlib.sha256(js.encode()).hexdigest() if js else None,
        "css_sha256": hashlib.sha256(css.encode()).hexdigest() if css else None,
        "overall_verdict": "PASS" if all(item["passed"] for item in all_checks) else "FAIL",
    }


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: dashboard_contract.py <dashboard-html>")
        return 2
    html_path = Path(sys.argv[1]).resolve()
    root = Path(__file__).resolve().parents[1]
    result = inspect_dashboard(html_path, root / "dashboard" / "v2.js", root / "dashboard" / "v2.css")
    result["validated_at"] = datetime.now(timezone.utc).isoformat()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["overall_verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
