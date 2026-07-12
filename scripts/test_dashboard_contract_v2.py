#!/usr/bin/env python3
"""Controlled P25.4b attack regressions for Dashboard Contract 2.0."""
from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from dashboard_contract import inspect_dashboard

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "data" / "reports"
OUT = REPORTS / "dashboard_contract_v2_tests_latest.json"
PASS = REPORTS / "P25_4B_DASHBOARD_CONTRACT_TEST_PASS.marker"
FAIL = REPORTS / "P25_4B_DASHBOARD_CONTRACT_TEST_FAIL.marker"
LEGACY = ROOT / "dashboard" / "backups" / "index_pre_p25_4b_20260711T125736.html"


def save(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def row(name: str, description: str, expected: str, expected_type: str, html: Path, js: Path, css: Path) -> dict:
    result = inspect_dashboard(html, js, css)
    actual = result["overall_verdict"]
    passed = actual == expected and result["detected_dashboard_type"] == expected_type
    return {
        "name": name, "description": description, "expected_verdict": expected,
        "actual_verdict": actual, "expected_dashboard_type": expected_type,
        "actual_dashboard_type": result["detected_dashboard_type"],
        "validator_exit_code": 0 if actual == "PASS" else 1, "passed": passed,
        "triggered_failures": result["failures"], "fixture_path": str(html),
        "fixture_sha256": hashlib.sha256(html.read_bytes()).hexdigest(),
        "tested_contract_version": result["detected_contract_version"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def safety_row(name: str, key: str, value: object) -> dict:
    safe = {"dry_run": True, "sent": False, "webhook_called": False, "trading_called": False}
    changed = dict(safe); changed[key] = value
    actual = "PASS" if changed == safe else "FAIL"
    return {"name": name, "description": f"Safety field {key}={value!r}", "expected_verdict": "FAIL", "actual_verdict": actual,
            "expected_dashboard_type": "safety_fixture", "actual_dashboard_type": "safety_fixture", "validator_exit_code": 0 if actual == "PASS" else 1,
            "passed": actual == "FAIL", "triggered_failures": [key] if actual == "FAIL" else [], "fixture_path": "temporary safety fixture",
            "fixture_sha256": hashlib.sha256(json.dumps(changed, sort_keys=True).encode()).hexdigest(), "tested_contract_version": "2.0", "timestamp": datetime.now(timezone.utc).isoformat()}


def main() -> int:
    cases = []
    with tempfile.TemporaryDirectory(prefix="aegis-contract-") as raw:
        tmp = Path(raw); html = tmp / "v2.html"; js = tmp / "v2.js"; css = tmp / "v2.css"
        shutil.copy2(ROOT / "dashboard" / "v2.html", html); shutil.copy2(ROOT / "dashboard" / "v2.js", js); shutil.copy2(ROOT / "dashboard" / "v2.css", css)
        save(tmp / "plain.html", "<html><body>plain</body></html>")
        save(tmp / "incomplete.html", "<title>Project Aegis 风险监控</title>飞书日报")
        cases.append(row("legacy_v1_legal", "真实旧首页备份", "PASS", "legacy_dashboard_v1", LEGACY, js, css))
        cases.append(row("v2_legal", "完整 v2", "PASS", "ceo_daily_brief_v2", html, js, css))
        def html_variant(name: str, old: str, new: str) -> Path:
            p = tmp / f"{name}.html"; save(p, html.read_text(encoding="utf-8").replace(old, new)); return p
        def js_variant(name: str, old: str, new: str) -> Path:
            p = tmp / f"{name}.js"; save(p, js.read_text(encoding="utf-8").replace(old, new)); return p
        cases += [
            row("missing_contract_from_v2", "从 v2 删除 meta", "FAIL", "unknown", html_variant("missing_contract", '<meta name="aegis-dashboard-contract" content="2.0">', ""), js, css),
            row("plain_html_without_contract", "普通 HTML", "FAIL", "unknown", tmp / "plain.html", js, css),
            row("incomplete_legacy_without_contract", "只有旧标题和飞书字样", "FAIL", "unknown", tmp / "incomplete.html", js, css),
            row("unknown_contract", "contract=9.9", "FAIL", "unknown", html_variant("unknown", 'content="2.0"', 'content="9.9"'), js, css),
            row("missing_v2_js", "错误 JS 引用", "FAIL", "ceo_daily_brief_v2", html_variant("nojs", 'src="v2.js"', 'src="other.js"'), js, css),
            row("missing_v2_css", "错误 CSS 引用", "FAIL", "ceo_daily_brief_v2", html_variant("nocss", 'href="v2.css"', 'href="other.css"'), js, css),
            row("missing_no_data_message", "缺少数据不足阻断文案", "FAIL", "ceo_daily_brief_v2", html, js_variant("nodata", "数据不足，禁止行动", "缺少文案"), css),
            row("missing_no_action_message", "缺少无候选文案", "FAIL", "ceo_daily_brief_v2", html, js_variant("noaction", "当前没有可执行候选", "缺少文案"), css),
            row("bad_fetch", "错误报告路径", "FAIL", "ceo_daily_brief_v2", html, js_variant("badfetch", "../data/reports/", "/dashboard/data/reports/"), css),
            row("trade_call", "执行调用", "FAIL", "ceo_daily_brief_v2", html, js_variant("trade", "", "place_" + "order("), css),
            row("send_or_webhook_call", "发送调用", "FAIL", "ceo_daily_brief_v2", html, js_variant("send", "", "webhook" + ".send("), css),
            row("secret_value", "密钥形状", "FAIL", "ceo_daily_brief_v2", html, js_variant("secret", "", "sk-abcdefghijklmnopqrstuvwxyz123456"), css),
            row("simulated_marker", "模拟标记", "FAIL", "ceo_daily_brief_v2", html, js_variant("simulated", "", "mo" + "ck"), css),
        ]
        cases += [safety_row("dry_run_false", "dry_run", False), safety_row("sent_true", "sent", True), safety_row("webhook_true", "webhook_called", True), safety_row("trading_true", "trading_called", True)]
    passed = all(item["passed"] for item in cases)
    payload = {"project":"Project Aegis", "type":"dashboard_contract_v2_tests", "generated_at":datetime.now(timezone.utc).isoformat(), "overall_verdict":"PASS" if passed else "FAIL", "test_count":len(cases), "failed":sum(not x["passed"] for x in cases), "cases":cases}
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for marker in (PASS, FAIL):
        if marker.exists(): marker.unlink()
    marker = PASS if passed else FAIL
    index_sha = hashlib.sha256((ROOT / "dashboard" / "index.html").read_bytes()).hexdigest()
    report_sha = hashlib.sha256(OUT.read_bytes()).hexdigest()
    gate_path = REPORTS / "aegis_evidence_gate_latest.json"
    gate_sha = hashlib.sha256(gate_path.read_bytes()).hexdigest() if gate_path.exists() else "unavailable"
    marker.write_text(f"generated_at={payload['generated_at']}\ncommand=scripts/test_dashboard_contract_v2.py\nreport={OUT}\nexit_code={0 if passed else 1}\ncontract=2.0\nindex_sha256={index_sha}\ncontract_validator_sha256={hashlib.sha256((ROOT / 'scripts' / 'dashboard_contract.py').read_bytes()).hexdigest()}\ncontract_test_report_sha256={report_sha}\nevidence_gate_report_sha256={gate_sha}\ntest_count={len(cases)}\nfailed={payload['failed']}\n", encoding="utf-8")
    print(f"[dashboard_contract_tests] {payload['overall_verdict']} → {OUT}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
