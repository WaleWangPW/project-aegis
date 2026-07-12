#!/usr/bin/env python3
"""
run_aegis_degradation_recovery_tests.py

Degradation recovery tests for Project Aegis.
Executes 5 real degradation/recovery scenarios, records results,
and outputs JSON + MD reports.

Uses only Python standard library. No network, no secrets, no trading.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
REPORTS_DIR = REPO_ROOT / "data" / "reports"

FEISHU_JSON = REPORTS_DIR / "feishu_daily_digest_dry_run.json"
REDTEAM_MD = REPORTS_DIR / "aegis_pipeline_redteam_latest.md"
FAKE_HASH = "1e3g5i7k9m0o"  # test-only invalid hash
DASHBOARD_HTML = REPO_ROOT / "dashboard" / "index.html"

OUTPUT_JSON = REPORTS_DIR / "aegis_degradation_recovery_latest.json"
OUTPUT_MD = REPORTS_DIR / "aegis_degradation_recovery_latest.md"

NON_CORE_CANDIDATES = [
    REPORTS_DIR / "crcl_risk_monitor_latest.md",
    REPORTS_DIR / "000002.sz_risk_monitor_latest.md",
    REPORTS_DIR / "risk_monitor_symbols.json",
]


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def _run(cmd: list[str], cwd: Path = REPO_ROOT) -> tuple[int, str, str]:
    """Run a subprocess and return (exit_code, stdout, stderr)."""
    result = subprocess.run(
        cmd,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        timeout=120,
    )
    return result.returncode, result.stdout, result.stderr


def _backup(path: Path) -> Path | None:
    """Backup a file to .bak. Return backup path or None if file doesn't exist."""
    if not path.exists():
        return None
    bak = path.with_suffix(path.suffix + ".bak")
    shutil.copy2(path, bak)
    return bak


def _restore(path: Path, bak: Path | None) -> None:
    """Restore a file from backup."""
    if bak is None or not bak.exists():
        return
    shutil.copy2(bak, path)
    bak.unlink()


def _is_valid_json(path: Path) -> bool:
    """Check if a file contains valid JSON."""
    if not path.exists():
        return False
    try:
        json.loads(path.read_text(encoding="utf-8"))
        return True
    except Exception:
        return False


def _run_full_pipeline() -> tuple[int, str, str]:
    """Run refresh_feishu + refresh_aegis_pipeline + verify_aegis_evidence_gate --strict."""
    rc1, out1, err1 = _run([sys.executable, "scripts/refresh_feishu_dry_run.py"])
    if rc1 != 0:
        return rc1, out1, err1
    rc2, out2, err2 = _run([sys.executable, "scripts/refresh_aegis_daily_digest_pipeline.py"])
    if rc2 != 0:
        return rc2, out1 + "\n" + out2, err1 + "\n" + err2
    rc3, out3, err3 = _run([sys.executable, "scripts/verify_aegis_evidence_gate.py", "--strict"])
    return rc3, out1 + "\n" + out2 + "\n" + out3, err1 + "\n" + err2 + "\n" + err3


# ---------------------------------------------------------------------------
# Test 1: missing_feishu_json
# ---------------------------------------------------------------------------
def test_missing_feishu_json() -> dict:
    scenario = "missing_feishu_json"
    bak = _backup(FEISHU_JSON)

    # Remove original
    if FEISHU_JSON.exists():
        FEISHU_JSON.unlink()

    mutation = "feishu_daily_digest_dry_run.json removed"
    expected = "exit_code=0 (pipeline regenerates feishu JSON)"

    rc, out, err = _run_full_pipeline()

    actual_exit = rc
    rejected_or_recovered = (rc == 0)

    # If new file was generated and is valid, keep it; otherwise restore
    if _is_valid_json(FEISHU_JSON):
        # New file is valid, keep it; delete backup
        if bak and bak.exists():
            bak.unlink()
        restored = False
    else:
        _restore(FEISHU_JSON, bak)
        restored = True

    # Final gate check
    rc_final, _, _ = _run([sys.executable, "scripts/verify_aegis_evidence_gate.py", "--strict"])

    result = "PASS" if (rejected_or_recovered and rc_final == 0) else "FAIL"

    return {
        "scenario": scenario,
        "backup_created": bak is not None,
        "mutation_applied": mutation,
        "expected": expected,
        "actual_exit_code_before_restore": actual_exit,
        "rejected_or_recovered": rejected_or_recovered,
        "restored": restored,
        "final_gate_exit_code": rc_final,
        "result": result,
    }


# ---------------------------------------------------------------------------
# Test 2: invalid_feishu_json
# ---------------------------------------------------------------------------
def test_invalid_feishu_json() -> dict:
    scenario = "invalid_feishu_json"
    bak = _backup(FEISHU_JSON)

    # Write invalid JSON
    FEISHU_JSON.write_text("{ invalid json\n", encoding="utf-8")

    mutation = "feishu_daily_digest_dry_run.json content replaced with '{ invalid json'"
    expected = "exit_code=0 (pipeline regenerates valid JSON)"

    rc, out, err = _run_full_pipeline()

    actual_exit = rc
    rejected_or_recovered = (rc == 0)

    # If new file is valid, keep it
    if _is_valid_json(FEISHU_JSON):
        if bak and bak.exists():
            bak.unlink()
        restored = False
    else:
        _restore(FEISHU_JSON, bak)
        restored = True

    rc_final, _, _ = _run([sys.executable, "scripts/verify_aegis_evidence_gate.py", "--strict"])

    result = "PASS" if (rejected_or_recovered and rc_final == 0) else "FAIL"

    return {
        "scenario": scenario,
        "backup_created": bak is not None,
        "mutation_applied": mutation,
        "expected": expected,
        "actual_exit_code_before_restore": actual_exit,
        "rejected_or_recovered": rejected_or_recovered,
        "restored": restored,
        "final_gate_exit_code": rc_final,
        "result": result,
    }


# ---------------------------------------------------------------------------
# Test 3: missing_non_core_report
# ---------------------------------------------------------------------------
def test_missing_non_core_report() -> dict:
    scenario = "missing_non_core_report"

    # Find first existing non-core report
    target = None
    for candidate in NON_CORE_CANDIDATES:
        if candidate.exists():
            target = candidate
            break

    if target is None:
        return {
            "scenario": scenario,
            "backup_created": False,
            "mutation_applied": "No non-core report found to test",
            "expected": "N/A",
            "actual_exit_code_before_restore": -1,
            "rejected_or_recovered": False,
            "restored": False,
            "final_gate_exit_code": -1,
            "result": "FAIL",
        }

    bak = _backup(target)

    # Remove the file
    target.unlink()

    mutation = f"{target.name} removed"
    expected = "core pipeline PASS (non-core report missing is acceptable)"

    rc1, out1, err1 = _run([sys.executable, "scripts/refresh_aegis_daily_digest_pipeline.py"])
    rc2, out2, err2 = _run([sys.executable, "scripts/verify_aegis_evidence_gate.py", "--strict"])

    actual_exit = rc2
    rejected_or_recovered = (rc1 == 0 and rc2 == 0)

    # Restore original file
    _restore(target, bak)
    restored = True

    rc_final, _, _ = _run([sys.executable, "scripts/verify_aegis_evidence_gate.py", "--strict"])

    result = "PASS" if (rejected_or_recovered and rc_final == 0) else "FAIL"

    return {
        "scenario": scenario,
        "backup_created": True,
        "mutation_applied": mutation,
        "expected": expected,
        "actual_exit_code_before_restore": actual_exit,
        "rejected_or_recovered": rejected_or_recovered,
        "restored": restored,
        "final_gate_exit_code": rc_final,
        "result": result,
    }


# ---------------------------------------------------------------------------
# Test 4: injected_invalid_hash_gate_fail_then_restore
# ---------------------------------------------------------------------------
def test_injected_invalid_hash() -> dict:
    scenario = "injected_invalid_hash_gate_fail_then_restore"
    bak = _backup(REDTEAM_MD)

    if not REDTEAM_MD.exists():
        return {
            "scenario": scenario,
            "backup_created": False,
            "mutation_applied": "aegis_pipeline_redteam_latest.md not found",
            "expected": "N/A",
            "actual_exit_code_before_restore": -1,
            "rejected_or_recovered": False,
            "restored": False,
            "final_gate_exit_code": -1,
            "result": "FAIL",
        }

    # Inject invalid hash in sha256_12 field format that K check will detect
    original_content = REDTEAM_MD.read_text(encoding="utf-8")
    # Write in a format matching the K check regex: sha256_12: VALUE
    invalid_hash_line = "\n| injected_test | sha256_12: " + FAKE_HASH + " |\n"
    REDTEAM_MD.write_text(original_content + invalid_hash_line, encoding="utf-8")

    mutation = "injected invalid sha256_12 value [REDACTED] into aegis_pipeline_redteam_latest.md"
    expected = "exit_code != 0 (gate rejects invalid hash)"

    rc, out, err = _run([sys.executable, "scripts/verify_aegis_evidence_gate.py", "--strict"])

    actual_exit = rc
    rejected_or_recovered = (rc != 0)

    # Restore original
    _restore(REDTEAM_MD, bak)
    restored = True

    # Run gate again — should pass
    rc_final, _, _ = _run([sys.executable, "scripts/verify_aegis_evidence_gate.py", "--strict"])

    result = "PASS" if (rejected_or_recovered and rc_final == 0) else "FAIL"

    return {
        "scenario": scenario,
        "backup_created": True,
        "mutation_applied": mutation,
        "expected": expected,
        "actual_exit_code_before_restore": actual_exit,
        "rejected_or_recovered": rejected_or_recovered,
        "restored": restored,
        "final_gate_exit_code": rc_final,
        "result": result,
    }


# ---------------------------------------------------------------------------
# Test 5: dashboard_degrade_removed_gate_fail_then_restore
# ---------------------------------------------------------------------------
def test_dashboard_degrade_removed() -> dict:
    scenario = "dashboard_degrade_removed_gate_fail_then_restore"
    bak = _backup(DASHBOARD_HTML)

    if not DASHBOARD_HTML.exists():
        return {
            "scenario": scenario,
            "backup_created": False,
            "mutation_applied": "dashboard/index.html not found",
            "expected": "N/A",
            "actual_exit_code_before_restore": -1,
            "rejected_or_recovered": False,
            "restored": False,
            "final_gate_exit_code": -1,
            "result": "FAIL",
        }

    # Read content and replace degradation notice
    original_content = DASHBOARD_HTML.read_text(encoding="utf-8")
    mutated_content = original_content.replace("未生成飞书", "")
    DASHBOARD_HTML.write_text(mutated_content, encoding="utf-8")

    mutation = "replaced '未生成飞书' with empty string in dashboard/index.html"
    expected = "exit_code != 0 (gate detects missing degrade notice)"

    rc, out, err = _run([sys.executable, "scripts/verify_aegis_evidence_gate.py", "--strict"])

    actual_exit = rc
    rejected_or_recovered = (rc != 0)

    # Restore original
    _restore(DASHBOARD_HTML, bak)
    restored = True

    # Run gate again — should pass
    rc_final, _, _ = _run([sys.executable, "scripts/verify_aegis_evidence_gate.py", "--strict"])

    result = "PASS" if (rejected_or_recovered and rc_final == 0) else "FAIL"

    return {
        "scenario": scenario,
        "backup_created": True,
        "mutation_applied": mutation,
        "expected": expected,
        "actual_exit_code_before_restore": actual_exit,
        "rejected_or_recovered": rejected_or_recovered,
        "restored": restored,
        "final_gate_exit_code": rc_final,
        "result": result,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> int:
    print("[degradation_recovery] starting 5 degradation recovery tests…")
    started = _now_iso()

    tests = [
        ("test_1_missing_feishu_json", test_missing_feishu_json),
        ("test_2_invalid_feishu_json", test_invalid_feishu_json),
        ("test_3_missing_non_core_report", test_missing_non_core_report),
        ("test_4_injected_invalid_hash", test_injected_invalid_hash),
        ("test_5_dashboard_degrade_removed", test_dashboard_degrade_removed),
    ]

    results = []
    for name, fn in tests:
        print(f"[degradation_recovery] running {name}…")
        t0 = time.monotonic()
        r = fn()
        elapsed = round(time.monotonic() - t0, 2)
        r["test_name"] = name
        r["duration_seconds"] = elapsed
        print(f"[degradation_recovery] {name}: {r['result']} ({elapsed}s)")
        results.append(r)

    finished = _now_iso()
    all_pass = all(r["result"] == "PASS" for r in results)

    report = {
        "project": "Project Aegis",
        "type": "degradation_recovery_tests",
        "started_at": started,
        "finished_at": finished,
        "total_tests": len(results),
        "passed": sum(1 for r in results if r["result"] == "PASS"),
        "failed": sum(1 for r in results if r["result"] == "FAIL"),
        "all_passed": all_pass,
        "tests": results,
    }

    # Write JSON
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    # Write MD
    md_lines = [
        "# Project Aegis — Degradation Recovery Tests",
        "",
        f"> Started: {started}",
        f"> Finished: {finished}",
        f"> Total: {report['total_tests']} | Passed: {report['passed']} | Failed: {report['failed']}",
        "",
        "## Test Results",
        "",
        "| # | Scenario | Result | Exit Before Restore | Final Gate | Duration |",
        "|---|----------|--------|---------------------|------------|----------|",
    ]
    for i, r in enumerate(results, 1):
        md_lines.append(
            f"| {i} | {r['scenario']} | {r['result']} | {r['actual_exit_code_before_restore']} | {r['final_gate_exit_code']} | {r['duration_seconds']}s |"
        )

    md_lines.append("")
    for i, r in enumerate(results, 1):
        md_lines.append(f"### Test {i}: {r['scenario']}")
        md_lines.append("")
        md_lines.append(f"- **Result**: {r['result']}")
        md_lines.append(f"- **Backup created**: {r['backup_created']}")
        md_lines.append(f"- **Mutation**: {r['mutation_applied']}")
        md_lines.append(f"- **Expected**: {r['expected']}")
        md_lines.append(f"- **Exit code before restore**: {r['actual_exit_code_before_restore']}")
        md_lines.append(f"- **Rejected/Recovered**: {r['rejected_or_recovered']}")
        md_lines.append(f"- **Restored**: {r['restored']}")
        md_lines.append(f"- **Final gate exit code**: {r['final_gate_exit_code']}")
        md_lines.append("")

    OUTPUT_MD.write_text("\n".join(md_lines), encoding="utf-8")

    print(f"\n[degradation_recovery] {'ALL PASS' if all_pass else 'SOME FAILED'}")
    print(f"[degradation_recovery] JSON: {OUTPUT_JSON}")
    print(f"[degradation_recovery] MD: {OUTPUT_MD}")

    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
