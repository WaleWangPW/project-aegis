#!/usr/bin/env python3
"""
build_aegis_evidence_pack.py

Build a comprehensive evidence pack for Project Aegis.
Runs the full pipeline, captures outputs, performs stability tests,
hash cross-validation, secret scans, and produces JSON + MD reports.

Uses only Python standard library. No network, no secrets, no trading.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
REPORTS_DIR = REPO_ROOT / "data" / "reports"
DASHBOARD_DIR = REPO_ROOT / "dashboard"

OUTPUT_JSON = REPORTS_DIR / "aegis_evidence_pack_latest.json"
OUTPUT_MD = REPORTS_DIR / "aegis_evidence_pack_latest.md"
STDOUT_LOG = REPORTS_DIR / "aegis_evidence_pack_stdout_latest.log"

GATE_JSON = REPORTS_DIR / "aegis_evidence_gate_latest.json"
REDTEAM_JSON = REPORTS_DIR / "aegis_pipeline_redteam_latest.json"
AUDIT_JSON = REPORTS_DIR / "aegis_pipeline_evidence_audit_latest.json"
PIPELINE_JSON = REPORTS_DIR / "aegis_daily_digest_pipeline_latest.json"
FEISHU_JSON = REPORTS_DIR / "feishu_daily_digest_dry_run.json"
DEGRADATION_JSON = REPORTS_DIR / "aegis_degradation_recovery_latest.json"

HASH_FILES = [
    SCRIPT_DIR / "verify_aegis_evidence_gate.py",
    SCRIPT_DIR / "redteam_aegis_pipeline_validator.py",
    SCRIPT_DIR / "build_aegis_evidence_pack.py",
    SCRIPT_DIR / "run_aegis_degradation_recovery_tests.py",
    GATE_JSON,
    REDTEAM_JSON,
    AUDIT_JSON,
    PIPELINE_JSON,
    FEISHU_JSON,
    DASHBOARD_DIR / "index.html",
]

SECRET_SCAN_DIRS = [
    ("scripts/*.py", SCRIPT_DIR.glob("*.py")),
    ("data/reports/*.json", REPORTS_DIR.glob("*.json")),
    ("data/reports/*.md", REPORTS_DIR.glob("*.md")),
    ("dashboard/index.html", [DASHBOARD_DIR / "index.html"] if (DASHBOARD_DIR / "index.html").exists() else []),
    ("Makefile", [REPO_ROOT / "Makefile"] if (REPO_ROOT / "Makefile").exists() else []),
    ("README.md", [REPO_ROOT / "README.md"] if (REPO_ROOT / "README.md").exists() else []),
    ("HANDOFF.md", [REPO_ROOT / "HANDOFF.md"] if (REPO_ROOT / "HANDOFF.md").exists() else []),
]

SECRET_PATTERNS = [
    (re.compile(r"sk-[a-zA-Z0-9]{20,}"), "api_key_pattern"),
    (re.compile(r"[aA]uthorization['\"]?\s*[:=]\s*['\"]?[bB]earer\s+"), "bearer_token"),
    (re.compile(r"api_key['\"]?\s*[:=]\s*['\"]?[^\s'\"]{8,}"), "api_key_literal"),
    (re.compile(r"cookie['\"]?\s*[:=]\s*['\"]?[^\s'\"]{8,}"), "cookie_literal"),
    (re.compile(r"secret['\"]?\s*[:=]\s*['\"]?[^\s'\"]{8,}"), "secret_literal"),
    (re.compile(r"open\.feishu\.cn"), "open_feishu_cn"),
    (re.compile(r"hooks\.slack\.com|hooks\.feishu\.cn"), "webhook_url"),
]

SECRET_SAFE_PATTERNS = [
    re.compile(r"webhook_called['\"]?\s*[:=]\s*(false|False|None)"),
    re.compile(r"no.*secrets?.*(?:stored|used|read|loaded)", re.IGNORECASE),
    re.compile(r"secrets?.*(?:not|never|no).*(?:read|stored|used|loaded|imported)", re.IGNORECASE),
    re.compile(r"does not.*read.*secret", re.IGNORECASE),
    re.compile(r"不读取.*secret|不存储.*secret|不输出.*secret", re.IGNORECASE),
    re.compile(r"# .*secret.*安全", re.IGNORECASE),
]

RISK_PATTERNS = [
    (re.compile(r"requests\.(post|get|put|delete)\("), "requests_call"),
    (re.compile(r"httpx\.(post|get|put|delete)\("), "httpx_call"),
    (re.compile(r"urllib\.request\.urlopen\("), "urllib_call"),
    (re.compile(r"^\s*(import\s+aiohttp|from\s+aiohttp\s+import)", re.MULTILINE), "aiohttp_import"),
    (re.compile(r"subprocess\.\w+.*curl|os\.system.*curl"), "subprocess_curl"),
    (re.compile(r"\.post\("), "post_call"),
    (re.compile(r"\.send\("), "send_call"),
    (re.compile(r"broker\.buy|broker\.sell"), "broker_call"),
    (re.compile(r"\border\b.*\b(buy|sell|execute|submit)\b", re.IGNORECASE), "order_call"),
    (re.compile(r"\btrading\b.*\b(execute|call|send|place)\b", re.IGNORECASE), "trading_call"),
]


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def _run(cmd: list[str], cwd: Path = REPO_ROOT, timeout: int = 180) -> tuple[int, str, str, float]:
    """Run subprocess, return (exit_code, stdout, stderr, duration_seconds)."""
    t0 = time.monotonic()
    result = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True, timeout=timeout)
    elapsed = round(time.monotonic() - t0, 2)
    return result.returncode, result.stdout, result.stderr, elapsed


def _sanitize(text: str, max_len: int = 500) -> str:
    """Return last max_len chars of text, sanitized of secrets."""
    if not text:
        return ""
    tail = text[-max_len:] if len(text) > max_len else text
    # Redact potential secrets in output
    for pattern, _ in SECRET_PATTERNS:
        tail = pattern.sub("[REDACTED]", tail)
    return tail


def _sha256_12(path: Path) -> str | None:
    """Compute sha256_12 of a file using Python hashlib."""
    if not path.exists():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()[:12]


def _shasum_256_12(path: Path) -> str | None:
    """Compute sha256_12 of a file using /usr/bin/shasum."""
    if not path.exists():
        return None
    result = subprocess.run(
        ["/usr/bin/shasum", "-a", "256", str(path)],
        capture_output=True, text=True, timeout=30,
    )
    if result.returncode != 0:
        return None
    # Output: <hash>  <path>
    full_hash = result.stdout.strip().split()[0]
    return full_hash[:12]


# ---------------------------------------------------------------------------
# Step 1: Run command sequence
# ---------------------------------------------------------------------------
def run_command_sequence() -> tuple[list[dict], dict]:
    """Run the 7-step command sequence. Returns (command_results, captured_outputs)."""
    commands = [
        ("refresh_feishu_dry_run", [sys.executable, "scripts/refresh_feishu_dry_run.py"]),
        ("refresh_aegis_daily_digest", [sys.executable, "scripts/refresh_aegis_daily_digest_pipeline.py"]),
        ("validate_aegis_daily_digest", [sys.executable, "scripts/validate_aegis_daily_digest_pipeline.py", "--strict"]),
        ("audit_aegis_pipeline_evidence", [sys.executable, "scripts/audit_aegis_pipeline_evidence.py"]),
        ("redteam_aegis_pipeline", [sys.executable, "scripts/redteam_aegis_pipeline_validator.py"]),
        ("verify_aegis_evidence_gate", [sys.executable, "scripts/verify_aegis_evidence_gate.py", "--strict", "--write-report"]),
        ("full_check", None),  # special: run full pipeline
    ]

    results = []
    captured = {
        "gate_stdout": "",
        "redteam_stdout": "",
        "full_check_stdout": "",
    }

    for i, (name, cmd) in enumerate(commands, 1):
        if cmd is None:
            # Full check: refresh_feishu + refresh_aegis + validate + audit + redteam + verify
            full_cmds = [
                [sys.executable, "scripts/refresh_feishu_dry_run.py"],
                [sys.executable, "scripts/refresh_aegis_daily_digest_pipeline.py"],
                [sys.executable, "scripts/validate_aegis_daily_digest_pipeline.py", "--strict"],
                [sys.executable, "scripts/audit_aegis_pipeline_evidence.py"],
                [sys.executable, "scripts/redteam_aegis_pipeline_validator.py"],
                [sys.executable, "scripts/verify_aegis_evidence_gate.py", "--strict"],
            ]
            combined_stdout = ""
            combined_rc = 0
            t0 = time.monotonic()
            for fc in full_cmds:
                rc, out, err, _ = _run(fc)
                combined_rc = rc if rc != 0 else combined_rc
                combined_stdout += out + "\n"
                if rc != 0:
                    combined_stdout += f"[FAILED: {' '.join(fc)}]\n"
            elapsed = round(time.monotonic() - t0, 2)

            results.append({
                "step": i,
                "name": name,
                "command": "full_pipeline (6 sub-commands)",
                "exit_code": combined_rc,
                "duration_seconds": elapsed,
                "stdout_tail_sanitized": _sanitize(combined_stdout),
                "stderr_tail_sanitized": "",
                "result": "PASS" if combined_rc == 0 else "FAIL",
            })
            captured["full_check_stdout"] = combined_stdout

        else:
            rc, out, err, elapsed = _run(cmd)
            results.append({
                "step": i,
                "name": name,
                "command": " ".join(cmd),
                "exit_code": rc,
                "duration_seconds": elapsed,
                "stdout_tail_sanitized": _sanitize(out),
                "stderr_tail_sanitized": _sanitize(err),
                "result": "PASS" if rc == 0 else "FAIL",
            })

            if name == "verify_aegis_evidence_gate":
                captured["gate_stdout"] = out
            elif name == "redteam_aegis_pipeline":
                captured["redteam_stdout"] = out

    return results, captured


# ---------------------------------------------------------------------------
# Step 2: Parse gate verdict
# ---------------------------------------------------------------------------
def parse_gate_verdict(gate_stdout: str) -> dict:
    """Parse GATE_VERDICT_JSON from stdout or fallback to JSON file."""
    verdict = None

    # Try extracting from stdout
    if "GATE_VERDICT_JSON" in gate_stdout:
        start = gate_stdout.find("GATE_VERDICT_JSON")
        end = gate_stdout.find("END_GATE_VERDICT_JSON")
        if start != -1 and end != -1:
            json_str = gate_stdout[start + len("GATE_VERDICT_JSON"):end].strip()
            try:
                verdict = json.loads(json_str)
            except Exception:
                pass

    # Fallback to JSON file
    if verdict is None and GATE_JSON.exists():
        try:
            verdict = json.loads(GATE_JSON.read_text(encoding="utf-8"))
        except Exception:
            pass

    if verdict is None:
        return {"overall_verdict": "UNKNOWN", "checks": {}, "failures": ["could not parse gate verdict"]}

    return {
        "overall_verdict": verdict.get("overall_verdict", "UNKNOWN"),
        "checks": {k: {"passed": v.get("passed", False)} for k, v in verdict.get("checks", {}).items()},
        "failures": verdict.get("failures", []),
    }


# ---------------------------------------------------------------------------
# Step 3: Parse redteam verdict
# ---------------------------------------------------------------------------
def parse_redteam_verdict() -> dict:
    """Parse redteam results from JSON file."""
    if not REDTEAM_JSON.exists():
        return {"passed": 0, "total": 0, "tests": [], "error": "redteam JSON not found"}

    try:
        data = json.loads(REDTEAM_JSON.read_text(encoding="utf-8"))
    except Exception as e:
        return {"passed": 0, "total": 0, "tests": [], "error": str(e)}

    passed = data.get("passed", 0)
    total = data.get("total_tests", 0)
    tests = []
    for t in data.get("tests", []):
        tests.append({
            "test_name": t.get("test_name", ""),
            "rejected": t.get("rejected", False),
            "result": t.get("result", ""),
        })

    return {"passed": passed, "total": total, "tests": tests}


# ---------------------------------------------------------------------------
# Step 4: Seven-run stability test
# ---------------------------------------------------------------------------
def run_stability_tests() -> list[dict]:
    """Run 7 consecutive full pipeline + gate checks."""
    results = []
    for i in range(1, 8):
        print(f"[evidence_pack] stability run {i}/7…")
        t0 = time.monotonic()

        # Run full pipeline
        cmds = [
            [sys.executable, "scripts/refresh_feishu_dry_run.py"],
            [sys.executable, "scripts/refresh_aegis_daily_digest_pipeline.py"],
            [sys.executable, "scripts/validate_aegis_daily_digest_pipeline.py", "--strict"],
            [sys.executable, "scripts/verify_aegis_evidence_gate.py", "--strict"],
        ]
        combined_rc = 0
        for cmd in cmds:
            rc, _, _, _ = _run(cmd)
            if rc != 0:
                combined_rc = rc
                break

        elapsed = round(time.monotonic() - t0, 2)

        gate_sha = _sha256_12(GATE_JSON) or "N/A"
        feishu_sha = _sha256_12(FEISHU_JSON) or "N/A"
        pipeline_sha = _sha256_12(PIPELINE_JSON) or "N/A"

        results.append({
            "run": i,
            "exit_code": combined_rc,
            "duration_seconds": elapsed,
            "gate_sha256_12": gate_sha,
            "feishu_sha256_12": feishu_sha,
            "pipeline_sha256_12": pipeline_sha,
        })
        print(f"[evidence_pack] run {i}: exit={combined_rc}, {elapsed}s, gate={gate_sha}")

    return results


# ---------------------------------------------------------------------------
# Step 5: Hash cross-validation
# ---------------------------------------------------------------------------
def hash_cross_validation() -> list[dict]:
    """Cross-validate hashes using Python hashlib and /usr/bin/shasum."""
    results = []
    for path in HASH_FILES:
        py_sha = _sha256_12(path)
        shasum_sha = _shasum_256_12(path)
        match = (py_sha is not None and py_sha == shasum_sha)
        results.append({
            "path": str(path.relative_to(REPO_ROOT)),
            "python_sha256_12": py_sha or "FILE_NOT_FOUND",
            "shasum_sha256_12": shasum_sha or "FILE_NOT_FOUND",
            "match": match,
        })
    return results


# ---------------------------------------------------------------------------
# Step 6: Secret scan
# ---------------------------------------------------------------------------
def scan_secrets() -> dict:
    """Scan all relevant files for secrets."""
    findings = []

    for label, paths in SECRET_SCAN_DIRS:
        for path in paths:
            if not path.exists():
                continue
            try:
                content = path.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue

            # Skip redteam validator's test injection code
            if path.name == "redteam_aegis_pipeline_validator.py":
                continue

            for pattern, ptype in SECRET_PATTERNS:
                for match in pattern.finditer(content):
                    matched_text = match.group(0)
                    # Check if this is in a safe context
                    is_safe = False
                    for safe_pat in SECRET_SAFE_PATTERNS:
                        if safe_pat.search(matched_text):
                            is_safe = True
                            break

                    if is_safe:
                        continue

                    # Also check surrounding context for safety mentions
                    start = max(0, match.start() - 80)
                    end = min(len(content), match.end() + 80)
                    context = content[start:end]
                    for safe_pat in SECRET_SAFE_PATTERNS:
                        if safe_pat.search(context):
                            is_safe = True
                            break

                    if is_safe:
                        continue

                    findings.append({
                        "file": str(path.relative_to(REPO_ROOT)),
                        "type": ptype,
                        "line_number": content[:match.start()].count("\n") + 1,
                        "matched": "[REDACTED]",
                    })

    return {
        "findings": findings,
        "clean": len(findings) == 0,
    }


# ---------------------------------------------------------------------------
# Step 7: Real send risk scan
# ---------------------------------------------------------------------------
def scan_real_send_risk() -> dict:
    """Scan scripts/*.py (excluding redteam) for real send/trading calls."""
    findings = []

    for path in SCRIPT_DIR.glob("*.py"):
        if path.name == "redteam_aegis_pipeline_validator.py":
            continue

        try:
            content = path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue

        for pattern, ptype in RISK_PATTERNS:
            for match in pattern.finditer(content):
                # Skip comments
                line_start = content.rfind("\n", 0, match.start()) + 1
                line = content[line_start:content.find("\n", match.end())]
                stripped = line.lstrip()
                if stripped.startswith("#"):
                    continue

                findings.append({
                    "file": str(path.relative_to(REPO_ROOT)),
                    "type": ptype,
                    "line_number": content[:match.start()].count("\n") + 1,
                    "matched": matched_text if (matched_text := match.group(0)) else pattern.pattern,
                })

    return {
        "findings": findings,
        "clean": len(findings) == 0,
    }


# ---------------------------------------------------------------------------
# Step 8: Read degradation recovery results
# ---------------------------------------------------------------------------
def read_degradation_recovery() -> dict | None:
    """Read degradation recovery test results if available."""
    if not DEGRADATION_JSON.exists():
        return None
    try:
        return json.loads(DEGRADATION_JSON.read_text(encoding="utf-8"))
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Step 9: Build validation matrix
# ---------------------------------------------------------------------------
def build_validation_matrix(
    command_results: list[dict],
    gate_verdict: dict,
    redteam_verdict: dict,
    stability: list[dict],
    hash_cv: list[dict],
    secret_scan: dict,
    risk_scan: dict,
    degradation: dict | None,
) -> dict:
    """Build the validation matrix."""
    matrix = {}

    # All commands passed
    matrix["all_commands_pass"] = "PASS" if all(r["result"] == "PASS" for r in command_results) else "FAIL"

    # Gate verdict
    matrix["gate_overall_pass"] = "PASS" if gate_verdict["overall_verdict"] == "PASS" else "FAIL"

    # All gate checks passed
    all_checks_pass = all(
        v.get("passed", False) for v in gate_verdict.get("checks", {}).values()
    )
    matrix["gate_all_checks_pass"] = "PASS" if all_checks_pass else "FAIL"

    # Gate failures empty
    matrix["gate_no_failures"] = "PASS" if len(gate_verdict.get("failures", [])) == 0 else "FAIL"

    # Redteam
    matrix["redteam_passed_ge_20"] = "PASS" if redteam_verdict.get("passed", 0) >= 20 else "FAIL"
    matrix["redteam_total_ge_20"] = "PASS" if redteam_verdict.get("total", 0) >= 20 else "FAIL"

    all_rejected = all(t.get("rejected", False) for t in redteam_verdict.get("tests", []))
    matrix["redteam_all_rejected"] = "PASS" if all_rejected else "FAIL"

    # Stability: 7 runs all pass
    matrix["stability_7_runs_all_pass"] = "PASS" if all(r["exit_code"] == 0 for r in stability) else "FAIL"

    # Hash cross-validation: all match
    matrix["hash_cross_validation_all_match"] = "PASS" if all(h["match"] for h in hash_cv) else "FAIL"

    # Secret scan clean
    matrix["secret_scan_clean"] = "PASS" if secret_scan["clean"] else "FAIL"

    # Risk scan clean
    matrix["real_send_risk_scan_clean"] = "PASS" if risk_scan["clean"] else "FAIL"

    # Degradation recovery
    if degradation is not None:
        matrix["degradation_recovery_all_pass"] = "PASS" if degradation.get("all_passed", False) else "FAIL"
    else:
        matrix["degradation_recovery_all_pass"] = "FAIL"

    return matrix


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> int:
    print("[evidence_pack] building Project Aegis evidence pack…")
    started = _now_iso()

    # Step 1: Run command sequence
    print("[evidence_pack] step 1: running 7-step command sequence…")
    command_results, captured = run_command_sequence()

    # Write stdout log
    STDOUT_LOG.parent.mkdir(parents=True, exist_ok=True)
    stdout_log_lines = [
        "=" * 70,
        "Project Aegis Evidence Pack — Captured STDOUT",
        f"Generated: {started}",
        "=" * 70,
        "",
        "## VERIFY_GATE_STDOUT (command 6)",
        "=" * 70,
        captured.get("gate_stdout", ""),
        "",
        "## REDTEAM_STDOUT (command 5)",
        "=" * 70,
        captured.get("redteam_stdout", ""),
        "",
        "## FULL_CHECK_STDOUT (command 7)",
        "=" * 70,
        captured.get("full_check_stdout", ""),
        "",
    ]
    STDOUT_LOG.write_text("\n".join(stdout_log_lines), encoding="utf-8")

    # Step 2: Parse gate verdict
    print("[evidence_pack] step 2: parsing gate verdict…")
    gate_verdict = parse_gate_verdict(captured.get("gate_stdout", ""))

    # Step 3: Parse redteam verdict
    print("[evidence_pack] step 3: parsing redteam verdict…")
    redteam_verdict = parse_redteam_verdict()

    # Step 4: Seven-run stability
    print("[evidence_pack] step 4: running 7-round stability tests…")
    stability = run_stability_tests()

    # Step 5: Hash cross-validation
    print("[evidence_pack] step 5: hash cross-validation…")
    hash_cv = hash_cross_validation()

    # Step 6: Secret scan
    print("[evidence_pack] step 6: secret scan…")
    secret_scan = scan_secrets()

    # Step 7: Real send risk scan
    print("[evidence_pack] step 7: real send risk scan…")
    risk_scan = scan_real_send_risk()

    # Step 8: Read degradation recovery
    print("[evidence_pack] step 8: reading degradation recovery results…")
    degradation = read_degradation_recovery()

    # Step 9: Build validation matrix
    print("[evidence_pack] step 9: building validation matrix…")
    matrix = build_validation_matrix(
        command_results, gate_verdict, redteam_verdict,
        stability, hash_cv, secret_scan, risk_scan, degradation,
    )

    finished = _now_iso()
    all_pass = all(v == "PASS" for v in matrix.values())

    # Build final report
    report = {
        "project": "Project Aegis",
        "type": "evidence_pack",
        "generated_at": started,
        "finished_at": finished,
        "command_results": command_results,
        "captured_outputs": {
            "gate_stdout": _sanitize(captured.get("gate_stdout", ""), 2000),
            "redteam_stdout": _sanitize(captured.get("redteam_stdout", ""), 2000),
            "full_check_stdout": _sanitize(captured.get("full_check_stdout", ""), 2000),
        },
        "gate_verdict": gate_verdict,
        "redteam_verdict": redteam_verdict,
        "degradation_recovery": degradation,
        "seven_run_stability": stability,
        "hash_cross_validation": hash_cv,
        "secret_scan": secret_scan,
        "real_send_risk_scan": risk_scan,
        "validation_matrix": matrix,
        "overall_verdict": "PASS" if all_pass else "FAIL",
    }

    # Write JSON
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    # Write MD
    md_lines = [
        "# Project Aegis — Evidence Pack",
        "",
        f"> Generated: {started}",
        f"> Finished: {finished}",
        f"> Overall Verdict: **{report['overall_verdict']}**",
        "",
        "## Command Results",
        "",
        "| Step | Name | Exit Code | Duration | Result |",
        "|------|------|-----------|----------|--------|",
    ]
    for r in command_results:
        md_lines.append(f"| {r['step']} | {r['name']} | {r['exit_code']} | {r['duration_seconds']}s | {r['result']} |")

    md_lines.extend([
        "",
        "## Gate Verdict",
        "",
        f"- **Overall**: {gate_verdict['overall_verdict']}",
        f"- **Failures**: {gate_verdict.get('failures', [])}",
        "",
        "### Gate Checks",
        "",
        "| Check | Passed |",
        "|-------|--------|",
    ])
    for k, v in gate_verdict.get("checks", {}).items():
        md_lines.append(f"| {k} | {'✅' if v.get('passed') else '❌'} |")

    md_lines.extend([
        "",
        "## Redteam Verdict",
        "",
        f"- **Passed**: {redteam_verdict.get('passed', 0)}/{redteam_verdict.get('total', 0)}",
        f"- **All Rejected**: {all(t.get('rejected') for t in redteam_verdict.get('tests', []))}",
        "",
        "### Redteam Tests",
        "",
        "| Test | Rejected | Result |",
        "|------|----------|--------|",
    ])
    for t in redteam_verdict.get("tests", []):
        md_lines.append(f"| {t['test_name']} | {'✅' if t.get('rejected') else '❌'} | {t.get('result', '')} |")

    md_lines.extend([
        "",
        "## Seven-Run Stability",
        "",
        "| Run | Exit Code | Duration | Gate SHA | Feishu SHA | Pipeline SHA |",
        "|-----|-----------|----------|----------|------------|--------------|",
    ])
    for r in stability:
        md_lines.append(f"| {r['run']} | {r['exit_code']} | {r['duration_seconds']}s | {r['gate_sha256_12']} | {r['feishu_sha256_12']} | {r['pipeline_sha256_12']} |")

    md_lines.extend([
        "",
        "## Hash Cross-Validation",
        "",
        "| File | Python SHA256_12 | shasum SHA256_12 | Match |",
        "|------|-----------------|------------------|-------|",
    ])
    for h in hash_cv:
        md_lines.append(f"| {h['path']} | {h['python_sha256_12']} | {h['shasum_sha256_12']} | {'✅' if h['match'] else '❌'} |")

    md_lines.extend([
        "",
        "## Secret Scan",
        "",
        f"- **Clean**: {'✅' if secret_scan['clean'] else '❌'}",
        f"- **Findings**: {len(secret_scan['findings'])}",
    ])
    if secret_scan["findings"]:
        md_lines.extend(["", "| File | Type | Line |", "|------|------|------|"])
        for f in secret_scan["findings"]:
            md_lines.append(f"| {f['file']} | {f['type']} | {f['line_number']} |")

    md_lines.extend([
        "",
        "## Real Send Risk Scan",
        "",
        f"- **Clean**: {'✅' if risk_scan['clean'] else '❌'}",
        f"- **Findings**: {len(risk_scan['findings'])}",
    ])
    if risk_scan["findings"]:
        md_lines.extend(["", "| File | Type | Line |", "|------|------|------|"])
        for f in risk_scan["findings"]:
            md_lines.append(f"| {f['file']} | {f['type']} | {f['line_number']} |")

    if degradation:
        md_lines.extend([
            "",
            "## Degradation Recovery",
            "",
            f"- **All Passed**: {'✅' if degradation.get('all_passed') else '❌'}",
            f"- **Passed**: {degradation.get('passed', 0)}/{degradation.get('total_tests', 0)}",
        ])
    else:
        md_lines.extend(["", "## Degradation Recovery", "", "⚠️ Not available (run degradation recovery tests first)"])

    md_lines.extend([
        "",
        "## Validation Matrix",
        "",
        "| Check | Result |",
        "|-------|--------|",
    ])
    for k, v in matrix.items():
        md_lines.append(f"| {k} | {'✅' if v == 'PASS' else '❌'} |")

    md_lines.extend([
        "",
        f"## Overall Verdict: **{report['overall_verdict']}**",
        "",
    ])

    OUTPUT_MD.write_text("\n".join(md_lines), encoding="utf-8")

    print(f"\n[evidence_pack] Overall: {report['overall_verdict']}")
    print(f"[evidence_pack] JSON: {OUTPUT_JSON}")
    print(f"[evidence_pack] MD: {OUTPUT_MD}")
    print(f"[evidence_pack] STDOUT log: {STDOUT_LOG}")

    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
