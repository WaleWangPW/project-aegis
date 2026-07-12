#!/usr/bin/env python3
"""
redteam_aegis_pipeline_history.py

Red-team negative tests for the Aegis pipeline history validator.
Creates mutated copies in tmp/p21_6_history_redteam/ and runs the validator
against each. Does NOT modify production files.

Outputs:
  - data/reports/aegis_pipeline_history_redteam_latest.json
  - data/reports/aegis_pipeline_history_redteam_latest.md
Outputs HISTORY_REDTEAM_VERDICT_JSON to stdout.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
REPORTS_DIR = REPO_ROOT / "data" / "reports"

HISTORY_JSON = REPORTS_DIR / "aegis_pipeline_history_latest.json"
SNAPSHOTS_DIR = REPORTS_DIR / "aegis_pipeline_history_snapshots"
DASHBOARD_HTML = REPO_ROOT / "dashboard" / "index.html"

REDTEAM_DIR = REPO_ROOT / "tmp" / "p21_6_history_redteam"
VALIDATOR_SCRIPT = SCRIPT_DIR / "validate_aegis_pipeline_history.py"

OUTPUT_JSON = REPORTS_DIR / "aegis_pipeline_history_redteam_latest.json"
OUTPUT_MD = REPORTS_DIR / "aegis_pipeline_history_redteam_latest.md"


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def _setup_redteam_dir():
    """Create a fresh redteam directory with copies of production files."""
    if REDTEAM_DIR.exists():
        shutil.rmtree(REDTEAM_DIR)
    REDTEAM_DIR.mkdir(parents=True)

    # Create sub-structure mirroring repo
    (REDTEAM_DIR / "data" / "reports" / "aegis_pipeline_history_snapshots").mkdir(parents=True)
    (REDTEAM_DIR / "dashboard").mkdir(parents=True)
    (REDTEAM_DIR / "scripts").mkdir(parents=True)

    # Copy validator
    shutil.copy2(VALIDATOR_SCRIPT, REDTEAM_DIR / "scripts" / "validate_aegis_pipeline_history.py")

    # Copy history JSON
    if HISTORY_JSON.exists():
        shutil.copy2(HISTORY_JSON, REDTEAM_DIR / "data" / "reports" / "aegis_pipeline_history_latest.json")
        # Also copy history MD
        history_md = REPORTS_DIR / "aegis_pipeline_history_latest.md"
        if history_md.exists():
            shutil.copy2(history_md, REDTEAM_DIR / "data" / "reports" / "aegis_pipeline_history_latest.md")

    # Copy snapshots
    if SNAPSHOTS_DIR.exists():
        for f in SNAPSHOTS_DIR.glob("*.json"):
            shutil.copy2(f, REDTEAM_DIR / "data" / "reports" / "aegis_pipeline_history_snapshots" / f.name)

    # Copy dashboard
    if DASHBOARD_HTML.exists():
        shutil.copy2(DASHBOARD_HTML, REDTEAM_DIR / "dashboard" / "index.html")


def _load_history() -> dict:
    p = REDTEAM_DIR / "data" / "reports" / "aegis_pipeline_history_latest.json"
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return {"project": "Project Aegis", "type": "pipeline_history", "updated_at": _now_iso(), "retention_limit": 7, "runs": []}


def _save_history(data: dict):
    p = REDTEAM_DIR / "data" / "reports" / "aegis_pipeline_history_latest.json"
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _run_validator() -> int:
    """Run the validator in the redteam directory and return exit code."""
    result = subprocess.run(
        [sys.executable, str(REDTEAM_DIR / "scripts" / "validate_aegis_pipeline_history.py"), "--strict"],
        capture_output=True,
        text=True,
        timeout=30,
        cwd=str(REDTEAM_DIR),
    )
    return result.returncode


def _make_valid_history() -> dict:
    """Create a valid history with one passing run for baseline tests."""
    return {
        "project": "Project Aegis",
        "type": "pipeline_history",
        "updated_at": _now_iso(),
        "retention_limit": 7,
        "runs": [
            {
                "run_id": "run_20260710_013000",
                "generated_at": "2026-07-10T01:30:00+08:00",
                "source_reports": {
                    "gate": {"exists": True, "sha256_12": "a1b2c3d4e5f6"},
                    "evidence_pack": {"exists": True, "sha256_12": "b2c3d4e5f6a1"},
                    "redteam": {"exists": True, "sha256_12": "c3d4e5f6a1b2"},
                    "degradation": {"exists": True, "sha256_12": "d4e5f6a1b2c3"},
                    "pipeline": {"exists": True, "sha256_12": "e5f6a1b2c3d4"},
                    "feishu": {"exists": True, "sha256_12": "f6a1b2c3d4e5"},
                },
                "gate_overall_verdict": "PASS",
                "gate_failures_count": 0,
                "gate_json_sha256_12": "a1b2c3d4e5f6",
                "redteam_passed": 20,
                "redteam_total": 20,
                "redteam_all_rejected": True,
                "redteam_json_sha256_12": "c3d4e5f6a1b2",
                "degradation_total": 5,
                "degradation_passed": 5,
                "degradation_json_sha256_12": "d4e5f6a1b2c3",
                "evidence_pack_json_sha256_12": "b2c3d4e5f6a1",
                "pipeline_json_sha256_12": "e5f6a1b2c3d4",
                "feishu_json_sha256_12": "f6a1b2c3d4e5",
                "feishu_dry_run": True,
                "feishu_sent": False,
                "feishu_webhook_called": False,
                "feishu_trading_called": False,
                "hk_00700_status": "present",
                "crcl_status": "Exit",
                "sz_000002_status": "Exit",
                "a_share_top5_symbols": ["000001.SZ", "000002.SZ", "000003.SZ", "000004.SZ", "000005.SZ"],
                "mdns_link_present": True,
                "tailscale_link_present": True,
                "safety_summary": "dry-run, not sent, no webhook, no trading",
                "result": "PASS",
                "result_reason": "all checks passed",
            }
        ],
    }


def _ensure_valid_baseline():
    """Ensure we have a valid history + snapshot file for tests that mutate."""
    history = _make_valid_history()
    _save_history(history)
    # Write the snapshot file
    run_id = history["runs"][0]["run_id"]
    snapshot_dir = REDTEAM_DIR / "data" / "reports" / "aegis_pipeline_history_snapshots"
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    snapshot_path = snapshot_dir / f"{run_id}_history_entry.json"
    snapshot_path.write_text(json.dumps(history["runs"][0], ensure_ascii=False, indent=2), encoding="utf-8")
    # Write the MD file
    md_path = REDTEAM_DIR / "data" / "reports" / "aegis_pipeline_history_latest.md"
    md_path.write_text("# Project Aegis Pipeline History\n\n| # | Run ID | 时间 | 结果 |\n|---|--------|------|------|\n| 1 | run_20260710_013000 | 2026-07-10T01:30 | PASS |\n", encoding="utf-8")


def main() -> int:
    _setup_redteam_dir()
    _ensure_valid_baseline()

    tests = []

    # Test 1: missing_history_file
    history_path = REDTEAM_DIR / "data" / "reports" / "aegis_pipeline_history_latest.json"
    history_path.unlink()
    exit_code = _run_validator()
    tests.append({
        "test_name": "missing_history_file",
        "mutation": "删除 history JSON 文件",
        "expected_exit_nonzero": True,
        "actual_exit_code": exit_code,
        "rejected": exit_code != 0,
        "result": "PASS" if exit_code != 0 else "FAIL",
    })
    # Restore
    _ensure_valid_baseline()

    # Test 2: invalid_history_json
    history_path.write_text("{ invalid json !!!", encoding="utf-8")
    exit_code = _run_validator()
    tests.append({
        "test_name": "invalid_history_json",
        "mutation": "写入非法 JSON 内容",
        "expected_exit_nonzero": True,
        "actual_exit_code": exit_code,
        "rejected": exit_code != 0,
        "result": "PASS" if exit_code != 0 else "FAIL",
    })
    _ensure_valid_baseline()

    # Test 3: runs_count_gt_7
    h = _load_history()
    for i in range(9):
        run = dict(h["runs"][0])
        run["run_id"] = f"run_extra_{i}"
        run["generated_at"] = f"2026-07-0{i:02d}T01:30:00+08:00"
        h["runs"].append(run)
    _save_history(h)
    exit_code = _run_validator()
    tests.append({
        "test_name": "runs_count_gt_7",
        "mutation": "构造 10 条 run（超过 7 条限制）",
        "expected_exit_nonzero": True,
        "actual_exit_code": exit_code,
        "rejected": exit_code != 0,
        "result": "PASS" if exit_code != 0 else "FAIL",
    })
    _ensure_valid_baseline()

    # Test 4: duplicate_run_id
    h = _load_history()
    dup_run = dict(h["runs"][0])
    h["runs"].append(dup_run)
    _save_history(h)
    exit_code = _run_validator()
    tests.append({
        "test_name": "duplicate_run_id",
        "mutation": "构造重复的 run_id",
        "expected_exit_nonzero": True,
        "actual_exit_code": exit_code,
        "rejected": exit_code != 0,
        "result": "PASS" if exit_code != 0 else "FAIL",
    })
    _ensure_valid_baseline()

    # Test 5: invalid_hash_format
    h = _load_history()
    h["runs"][0]["gate_json_sha256_12"] = "ZZZinvalidZZZ"
    _save_history(h)
    exit_code = _run_validator()
    tests.append({
        "test_name": "invalid_hash_format",
        "mutation": "将 gate_json_sha256_12 改为 ZZZinvalidZZZ",
        "expected_exit_nonzero": True,
        "actual_exit_code": exit_code,
        "rejected": exit_code != 0,
        "result": "PASS" if exit_code != 0 else "FAIL",
    })
    _ensure_valid_baseline()

    # Test 6: known_fake_hash
    h = _load_history()
    h["runs"][0]["redteam_json_sha256_12"] = "a1c3e5g7i9k2"
    _save_history(h)
    exit_code = _run_validator()
    tests.append({
        "test_name": "known_fake_hash",
        "mutation": "插入已知假 hash a1c3e5g7i9k2",
        "expected_exit_nonzero": True,
        "actual_exit_code": exit_code,
        "rejected": exit_code != 0,
        "result": "PASS" if exit_code != 0 else "FAIL",
    })
    _ensure_valid_baseline()

    # Test 7: latest_gate_fail
    h = _load_history()
    h["runs"][0]["gate_overall_verdict"] = "FAIL"
    _save_history(h)
    exit_code = _run_validator()
    tests.append({
        "test_name": "latest_gate_fail",
        "mutation": "latest run gate_overall_verdict=FAIL",
        "expected_exit_nonzero": True,
        "actual_exit_code": exit_code,
        "rejected": exit_code != 0,
        "result": "PASS" if exit_code != 0 else "FAIL",
    })
    _ensure_valid_baseline()

    # Test 8: redteam_not_all_rejected
    h = _load_history()
    h["runs"][0]["redteam_all_rejected"] = False
    _save_history(h)
    exit_code = _run_validator()
    tests.append({
        "test_name": "redteam_not_all_rejected",
        "mutation": "latest run redteam_all_rejected=false",
        "expected_exit_nonzero": True,
        "actual_exit_code": exit_code,
        "rejected": exit_code != 0,
        "result": "PASS" if exit_code != 0 else "FAIL",
    })
    _ensure_valid_baseline()

    # Test 9: feishu_sent_true
    h = _load_history()
    h["runs"][0]["feishu_sent"] = True
    _save_history(h)
    exit_code = _run_validator()
    tests.append({
        "test_name": "feishu_sent_true",
        "mutation": "latest run feishu_sent=true",
        "expected_exit_nonzero": True,
        "actual_exit_code": exit_code,
        "rejected": exit_code != 0,
        "result": "PASS" if exit_code != 0 else "FAIL",
    })
    _ensure_valid_baseline()

    # Test 10: webhook_called_true
    h = _load_history()
    h["runs"][0]["feishu_webhook_called"] = True
    _save_history(h)
    exit_code = _run_validator()
    tests.append({
        "test_name": "webhook_called_true",
        "mutation": "latest run feishu_webhook_called=true",
        "expected_exit_nonzero": True,
        "actual_exit_code": exit_code,
        "rejected": exit_code != 0,
        "result": "PASS" if exit_code != 0 else "FAIL",
    })
    _ensure_valid_baseline()

    # Test 11: trading_called_true
    h = _load_history()
    h["runs"][0]["feishu_trading_called"] = True
    _save_history(h)
    exit_code = _run_validator()
    tests.append({
        "test_name": "trading_called_true",
        "mutation": "latest run feishu_trading_called=true",
        "expected_exit_nonzero": True,
        "actual_exit_code": exit_code,
        "rejected": exit_code != 0,
        "result": "PASS" if exit_code != 0 else "FAIL",
    })
    _ensure_valid_baseline()

    # Test 12: missing_00700
    h = _load_history()
    h["runs"][0]["hk_00700_status"] = None
    del h["runs"][0]["hk_00700_status"]
    _save_history(h)
    exit_code = _run_validator()
    tests.append({
        "test_name": "missing_00700",
        "mutation": "删除 hk_00700_status 字段",
        "expected_exit_nonzero": True,
        "actual_exit_code": exit_code,
        "rejected": exit_code != 0,
        "result": "PASS" if exit_code != 0 else "FAIL",
    })
    _ensure_valid_baseline()

    # Test 13: missing_mobile_link
    h = _load_history()
    h["runs"][0]["mdns_link_present"] = False
    _save_history(h)
    exit_code = _run_validator()
    tests.append({
        "test_name": "missing_mobile_link",
        "mutation": "mdns_link_present=false",
        "expected_exit_nonzero": True,
        "actual_exit_code": exit_code,
        "rejected": exit_code != 0,
        "result": "PASS" if exit_code != 0 else "FAIL",
    })
    _ensure_valid_baseline()

    # Test 14: missing_snapshot_file
    h = _load_history()
    run_id = h["runs"][0]["run_id"]
    snapshot_file = REDTEAM_DIR / "data" / "reports" / "aegis_pipeline_history_snapshots" / f"{run_id}_history_entry.json"
    if snapshot_file.exists():
        snapshot_file.unlink()
    _save_history(h)
    exit_code = _run_validator()
    tests.append({
        "test_name": "missing_snapshot_file",
        "mutation": "删除 latest run 对应的 snapshot 文件",
        "expected_exit_nonzero": True,
        "actual_exit_code": exit_code,
        "rejected": exit_code != 0,
        "result": "PASS" if exit_code != 0 else "FAIL",
    })
    _ensure_valid_baseline()

    # Test 15: dashboard_missing_history_degrade
    dashboard_path = REDTEAM_DIR / "dashboard" / "index.html"
    if dashboard_path.exists():
        html = dashboard_path.read_text(encoding="utf-8")
        # Remove the degrade text
        html_modified = html.replace("未生成 pipeline 历史快照", "XXXXX").replace("pipeline 历史 JSON 解析失败", "YYYYY")
        dashboard_path.write_text(html_modified, encoding="utf-8")
    # For this test, we check if the dashboard contains the degrade text
    # The validator doesn't directly check dashboard content, so we check the dashboard HTML
    has_degrade = "未生成 pipeline 历史快照" in dashboard_path.read_text(encoding="utf-8") if dashboard_path.exists() else False
    rejected = not has_degrade  # If degrade text is missing, it's "rejected" (bad dashboard)
    tests.append({
        "test_name": "dashboard_missing_history_degrade",
        "mutation": "检查 dashboard 是否有'未生成 pipeline 历史快照'降级提示",
        "expected_exit_nonzero": True,
        "actual_exit_code": 0 if has_degrade else 1,
        "rejected": rejected,
        "result": "PASS" if rejected else "FAIL",
    })
    # Restore dashboard
    if DASHBOARD_HTML.exists():
        shutil.copy2(DASHBOARD_HTML, dashboard_path)

    # Test 16: dashboard_invalid_history_degrade
    if dashboard_path.exists():
        html = dashboard_path.read_text(encoding="utf-8")
        has_invalid_degrade = "pipeline 历史 JSON 解析失败" in html
        rejected = has_invalid_degrade  # If degrade text exists, dashboard properly handles it
        # For this test: PASS if the dashboard has the degrade text (meaning it handles invalid JSON)
        tests.append({
            "test_name": "dashboard_invalid_history_degrade",
            "mutation": "检查 dashboard 是否有'pipeline 历史 JSON 解析失败'降级提示",
            "expected_exit_nonzero": True,
            "actual_exit_code": 0 if has_invalid_degrade else 1,
            "rejected": not has_invalid_degrade,
            "result": "PASS" if not has_invalid_degrade else "FAIL",
        })
    else:
        tests.append({
            "test_name": "dashboard_invalid_history_degrade",
            "mutation": "dashboard 不存在",
            "expected_exit_nonzero": True,
            "actual_exit_code": 1,
            "rejected": True,
            "result": "PASS",
        })

    # Wait - let me re-think tests 15 and 16.
    # The dashboard tests should check that the dashboard HAS the degrade text.
    # If the dashboard HAS it → good → test PASS (dashboard properly handles degradation)
    # If the dashboard does NOT have it → bad → test FAIL
    # But the "rejected" field means "the bad data was rejected by the validator"
    # For dashboard tests, it's more about whether the dashboard properly shows degrade notices.

    # Let me re-do these two tests with correct logic:
    # Test 15: Dashboard should have "未生成 pipeline 历史快照" text
    # Test 16: Dashboard should have "pipeline 历史 JSON 解析失败" text

    # Actually, looking at the test names more carefully:
    # dashboard_missing_history_degrade: check dashboard has degrade text for missing history
    # dashboard_invalid_history_degrade: check dashboard has degrade text for invalid history JSON

    # These are dashboard content checks, not validator checks.
    # PASS if dashboard HAS the text, FAIL if not.

    # Let me fix the last two tests:
    tests[-2] = {
        "test_name": "dashboard_missing_history_degrade",
        "mutation": "检查 dashboard 是否包含'未生成 pipeline 历史快照'",
        "expected_exit_nonzero": True,
        "actual_exit_code": 0 if ("未生成 pipeline 历史快照" in (dashboard_path.read_text(encoding="utf-8") if dashboard_path.exists() else "")) else 1,
        "rejected": "未生成 pipeline 历史快照" not in (dashboard_path.read_text(encoding="utf-8") if dashboard_path.exists() else ""),
        "result": "PASS" if "未生成 pipeline 历史快照" not in (dashboard_path.read_text(encoding="utf-8") if dashboard_path.exists() else "") else "FAIL",
    }

    # Hmm, I need to think about this differently.
    # The test should PASS when bad data is REJECTED.
    # For dashboard tests: if the dashboard does NOT have degrade text, that's BAD → test should detect it → PASS
    # If the dashboard HAS degrade text, that's GOOD → no issue → but we want to verify it's there
    #
    # Actually re-reading the requirements:
    # "15. dashboard_missing_history_degrade: 检查 dashboard 是否有'未生成 pipeline 历史快照'"
    # "16. dashboard_invalid_history_degrade: 检查 dashboard 是否有'pipeline 历史 JSON 解析失败'"
    #
    # These tests verify the dashboard HAS the degrade text. If it has it → the test confirms dashboard handles degradation.
    # result=PASS means the check passed (dashboard has the text).
    # If dashboard doesn't have the text → result=FAIL.

    # Let me re-read the overall requirement:
    # "所有测试 result 必须 PASS（坏数据被拒绝）"
    # So for dashboard tests, "坏数据" = dashboard without degrade text.
    # "被拒绝" = test detects the missing text and reports it as an issue.
    #
    # But wait - the dashboard tests are checking if the dashboard has the degrade notices.
    # If the dashboard HAS them → that's the correct state → test PASS
    # If the dashboard does NOT have them → that's a problem → test FAIL
    #
    # But the requirement says "所有测试 result 必须 PASS（坏数据被拒绝）"
    # This means the test should simulate bad data and verify it's rejected.
    #
    # For dashboard tests, the "bad data" would be a dashboard WITHOUT degrade text.
    # The test checks if the dashboard has it. If it does → the "bad dashboard" was not the case → PASS.
    # If it doesn't → the "bad dashboard" IS the case → the test should FAIL.
    #
    # Actually I think the logic should be:
    # - Test 15: Check if dashboard has "未生成 pipeline 历史快照" → if YES, PASS (dashboard handles missing history)
    # - Test 16: Check if dashboard has "pipeline 历史 JSON 解析失败" → if YES, PASS (dashboard handles invalid JSON)
    #
    # All tests must PASS, meaning the dashboard must have both degrade notices.

    # Let me redo these properly:
    dashboard_text = dashboard_path.read_text(encoding="utf-8") if dashboard_path.exists() else ""
    has_missing_degrade = "未生成 pipeline 历史快照" in dashboard_text
    has_invalid_degrade = "pipeline 历史 JSON 解析失败" in dashboard_text

    tests[-2] = {
        "test_name": "dashboard_missing_history_degrade",
        "mutation": "检查 dashboard 是否包含'未生成 pipeline 历史快照'降级提示",
        "expected_exit_nonzero": True,
        "actual_exit_code": 0 if has_missing_degrade else 1,
        "rejected": has_missing_degrade,
        "result": "PASS" if has_missing_degrade else "FAIL",
    }

    tests[-1] = {
        "test_name": "dashboard_invalid_history_degrade",
        "mutation": "检查 dashboard 是否包含'pipeline 历史 JSON 解析失败'降级提示",
        "expected_exit_nonzero": True,
        "actual_exit_code": 0 if has_invalid_degrade else 1,
        "rejected": has_invalid_degrade,
        "result": "PASS" if has_invalid_degrade else "FAIL",
    }

    # Summary
    total_tests = len(tests)
    passed = sum(1 for t in tests if t["result"] == "PASS")
    failed = total_tests - passed

    verdict = {
        "project": "Project Aegis",
        "type": "pipeline_history_redteam",
        "generated_at": _now_iso(),
        "total_tests": total_tests,
        "passed": passed,
        "failed": failed,
        "tests": tests,
        "overall_verdict": "PASS" if failed == 0 else "FAIL",
    }

    # Write output files
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(json.dumps(verdict, ensure_ascii=False, indent=2), encoding="utf-8")

    # Write MD
    md_lines = [
        "# Project Aegis Pipeline History Red-team",
        "",
        f"> 生成时间: {verdict['generated_at']}",
        f"> 测试总数: {total_tests} | 通过: {passed} | 失败: {failed}",
        "",
        "| # | 测试名称 | 变异 | 期望非零退出 | 实际退出码 | 被拒绝 | 结果 |",
        "|---|----------|------|-------------|-----------|--------|------|",
    ]
    for i, t in enumerate(tests, 1):
        md_lines.append(
            f"| {i} | {t['test_name']} | {t['mutation']} | "
            f"{'是' if t['expected_exit_nonzero'] else '否'} | "
            f"{t['actual_exit_code']} | "
            f"{'✅' if t['rejected'] else '❌'} | "
            f"{t['result']} |"
        )
    md_lines.append("")
    OUTPUT_MD.write_text("\n".join(md_lines), encoding="utf-8")

    # Output to stdout
    print("HISTORY_REDTEAM_VERDICT_JSON")
    print(json.dumps(verdict, ensure_ascii=False, indent=2))
    print("END_HISTORY_REDTEAM_VERDICT_JSON")

    print(f"\n[redteam_aegis_pipeline_history] {passed}/{total_tests} tests passed", file=sys.stderr)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
