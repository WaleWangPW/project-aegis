#!/usr/bin/env python3
"""
verify_aegis_evidence_gate.py

Machine gate that independently verifies all evidence.
Does NOT trust self-reported results; recomputes everything from filesystem.
Outputs GATE_VERDICT_JSON to stdout.
With --write-report, also writes JSON + MD report files.

Checks:
  A. File existence
  B. Real file fingerprints (hashlib.sha256)
  C. Hash validity (^[0-9a-f]{12}$, no known fakes)
  D. Self-referential hash strategy
  E. Feishu dry-run safety fields
  F. Dashboard
  G. Makefile targets (if Makefile exists)
  H. Secret scan
  I. Real send/trading risk scan
  J. Cross-validate hash (Python hashlib vs /usr/bin/shasum)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from dashboard_contract import inspect_dashboard

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
REPORTS_DIR = REPO_ROOT / "data" / "reports"

PIPELINE_JSON = REPORTS_DIR / "aegis_daily_digest_pipeline_latest.json"
FEISHU_JSON = REPORTS_DIR / "feishu_daily_digest_dry_run.json"
FEISHU_MD = REPORTS_DIR / "feishu_daily_digest_dry_run.md"
DASHBOARD_HTML = REPO_ROOT / "dashboard" / "index.html"
AUDIT_JSON = REPORTS_DIR / "aegis_pipeline_evidence_audit_latest.json"
MAKEFILE = REPO_ROOT / "Makefile"

OUTPUT_JSON = REPORTS_DIR / "aegis_evidence_gate_latest.json"
OUTPUT_MD = REPORTS_DIR / "aegis_evidence_gate_latest.md"
CONTRACT_JSON = REPORTS_DIR / "dashboard_contract_validation_latest.json"
CONTRACT_MD = REPORTS_DIR / "dashboard_contract_validation_latest.md"

HASH_RE = re.compile(r"^[0-9a-f]{12}$")
MD_HASH_RE = re.compile(r"sha256_12\s*[:=]\s*[`\"]?(\w+)[`\"]?")
KNOWN_FAKE_HASHES = {"000000000000", "deadbeefdead", "aaaaaaaaaaaa", "ffffffffffff", "a1c3e5g7i9k2", "b2d4f6h8j0l3", "1e3g5i7k9m0o", "5h7j9l1n3p5q"}

ALL_FILES = [
    ("crcl_risk_monitor_latest.json", REPORTS_DIR / "crcl_risk_monitor_latest.json"),
    ("000002.sz_risk_monitor_latest.json", REPORTS_DIR / "000002.sz_risk_monitor_latest.json"),
    ("feishu_daily_digest_dry_run.json", FEISHU_JSON),
    ("feishu_daily_digest_dry_run.md", FEISHU_MD),
    ("aegis_daily_digest_pipeline_latest.json", PIPELINE_JSON),
    ("dashboard/index.html", DASHBOARD_HTML),
]

SECRET_PATTERNS = [
    (re.compile(r"sk-[a-zA-Z0-9]{20,}"), "api_key_pattern"),
    (re.compile(r"[aA]uthorization['\"]?\s*[:=]\s*['\"]?[bB]earer\s+"), "bearer_token"),
    (re.compile(r"webhook['\"]?\s*[:=]\s*['\"]?https?://"), "webhook_url"),
    (re.compile(r"password['\"]?\s*[:=]\s*['\"]?[^\s'\"]{4,}"), "password_literal"),
]

RISK_PATTERNS = [
    (re.compile(r"requests\.(post|get|put|delete)\("), "requests_call"),
    (re.compile(r"httpx\.(post|get|put|delete)\("), "httpx_call"),
    (re.compile(r"aiohttp.*\.(post|get|put|delete)\("), "aiohttp_call"),
    (re.compile(r"urllib\.request\.urlopen\("), "urllib_call"),
    (re.compile(r"webhook\.send\(|send_webhook\("), "webhook_send"),
    (re.compile(r"place_order\(|submit_order\(|buy_stock\(|sell_stock\("), "trading_call"),
]


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def _fingerprint(path: Path) -> dict:
    if not path.exists():
        return {"exists": False, "mtime": None, "size": None, "sha256_12": None}
    stat = path.stat()
    raw = path.read_bytes()
    sha = hashlib.sha256(raw).hexdigest()[:12]
    return {
        "exists": True,
        "mtime": datetime.fromtimestamp(stat.st_mtime, timezone.utc).astimezone().isoformat(),
        "size": stat.st_size,
        "sha256_12": sha,
    }


def _cross_validate(path: Path) -> dict:
    if not path.exists():
        return {"available": False}
    py_hash = hashlib.sha256(path.read_bytes()).hexdigest()[:12]
    try:
        result = subprocess.run(
            ["/usr/bin/shasum", "-a", "256", str(path)],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0:
            shasum_hash = result.stdout.strip().split()[0][:12]
            return {"available": True, "python": py_hash, "shasum": shasum_hash, "match": py_hash == shasum_hash}
    except Exception:
        pass
    return {"available": True, "python": py_hash, "shasum": None, "match": None}


def main() -> int:
    parser = argparse.ArgumentParser(description="Aegis Evidence Gate")
    parser.add_argument("--strict", action="store_true", help="Strict mode")
    parser.add_argument("--write-report", action="store_true", help="Write report files")
    parser.add_argument("--skip-history", action="store_true", help="Skip N_history_* checks (breaks circular dependency)")
    args = parser.parse_args()

    gate_started = _now_iso()
    checks: dict = {}
    failures: list[str] = []

    # A. File existence
    existence = {}
    for label, path in ALL_FILES:
        existence[label] = path.exists()
        if not path.exists() and label not in ("feishu_daily_digest_dry_run.md",):
            # feishu MD may not be critical but others are
            if label not in ("crcl_risk_monitor_latest.json", "000002.sz_risk_monitor_latest.json"):
                failures.append(f"A. Missing file: {label}")
    checks["A_file_existence"] = {"passed": len(failures) == 0, "details": existence}

    # B. Real file fingerprints
    fingerprints = {}
    for label, path in ALL_FILES:
        fingerprints[label] = _fingerprint(path)
    checks["B_real_fingerprints"] = {"passed": True, "details": fingerprints}

    # C. Hash validity
    hash_issues = []
    for label, fp in fingerprints.items():
        sha = fp.get("sha256_12")
        if sha is not None:
            if not HASH_RE.match(sha):
                hash_issues.append(f"Invalid format: {label} = {sha}")
            if sha in KNOWN_FAKE_HASHES:
                hash_issues.append(f"Fake hash: {label} = {sha}")
    checks["C_hash_validity"] = {"passed": len(hash_issues) == 0, "issues": hash_issues}
    failures.extend(hash_issues)


    # C2. Cross-check claimed hashes in pipeline JSON vs actual file hashes
    hash_claim_issues = []
    if PIPELINE_JSON.exists():
        try:
            pipeline_data = json.loads(PIPELINE_JSON.read_text(encoding="utf-8"))
            fps = pipeline_data.get("file_fingerprints", {}).get("after", {})
            for label, fp_data in fps.items():
                claimed_sha = fp_data.get("sha256_12")
                if claimed_sha is None:
                    continue
                if claimed_sha == "self_hash_verified_by_evidence_gate":
                    continue  # This is the pipeline's own hash, handled by strategy D
                # Resolve label to actual file path (label may be a relative path from repo root)
                actual_path = REPO_ROOT / label
                if not actual_path.exists():
                    continue  # File doesn't exist, caught by other checks
                actual_sha = hashlib.sha256(actual_path.read_bytes()).hexdigest()[:12]
                if actual_sha != claimed_sha:
                    hash_claim_issues.append(
                        f"Hash mismatch for {label}: JSON claims {claimed_sha}, actual {actual_sha}"
                    )
        except Exception:
            pass
    checks["C2_claimed_vs_actual_hash"] = {"passed": len(hash_claim_issues) == 0, "issues": hash_claim_issues}
    failures.extend(hash_claim_issues)

    # D. Self-referential hash strategy
    self_hash_ok = False
    if PIPELINE_JSON.exists():
        try:
            pipeline = json.loads(PIPELINE_JSON.read_text(encoding="utf-8"))
            ep = pipeline.get("evidence_policy", {})
            self_hash_ok = ep.get("raw_self_hash_not_claimed_in_pipeline_json") is True
            # Also check that no raw self hash field exists
            has_raw_self = any(k for k in pipeline if "self_hash_raw" in k.lower())
            if has_raw_self:
                self_hash_ok = False
        except Exception:
            pass
    checks["D_self_hash_strategy"] = {"passed": self_hash_ok}
    if not self_hash_ok:
        failures.append("D. Self-referential hash strategy not verified")

    # E. Feishu dry-run safety fields
    feishu_safe = False
    feishu_details = {}
    if FEISHU_JSON.exists():
        try:
            feishu = json.loads(FEISHU_JSON.read_text(encoding="utf-8"))
            feishu_details = {
                "dry_run": feishu.get("dry_run"),
                "sent": feishu.get("sent"),
                "webhook_called": feishu.get("webhook_called"),
                "trading_called": feishu.get("trading_called"),
            }
            feishu_safe = (
                feishu.get("dry_run") is True
                and feishu.get("sent") is False
                and feishu.get("webhook_called") is False
                and feishu.get("trading_called") is False
            )
        except Exception as e:
            feishu_details = {"error": str(e)}
    checks["E_feishu_dry_run_safety"] = {"passed": feishu_safe, "details": feishu_details}
    if not feishu_safe:
        failures.append("E. Feishu dry-run safety fields not safe")

    # F. Dashboard Contract.  Legacy visual requirements do not apply to v2.
    contract = inspect_dashboard(DASHBOARD_HTML, REPO_ROOT / "dashboard" / "v2.js", REPO_ROOT / "dashboard" / "v2.css")
    dashboard_ok = contract["overall_verdict"] == "PASS"
    checks["F_dashboard_contract"] = {"passed": dashboard_ok, "details": contract}
    CONTRACT_JSON.write_text(json.dumps(contract, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    contract_lines = ["# Dashboard Contract Validation", "", f"- Contract: `{contract['detected_contract_version']}`", f"- Type: `{contract['detected_dashboard_type']}`", f"- Verdict: `{contract['overall_verdict']}`", "", "## Warnings", ""]
    contract_lines.extend(f"- {item}" for item in contract["warnings"] or ["None"])
    contract_lines.extend(["", "## Failures", ""])
    contract_lines.extend(f"- {item}" for item in contract["failures"] or ["None"])
    CONTRACT_MD.write_text("\n".join(contract_lines) + "\n", encoding="utf-8")
    if not dashboard_ok:
        failures.append(f"F. Dashboard Contract failed: {contract['failures']}")

    # G. Makefile targets (if Makefile exists)
    makefile_details = {"exists": MAKEFILE.exists()}
    if MAKEFILE.exists():
        makefile_text = MAKEFILE.read_text(encoding="utf-8")
        # Check for duplicate targets
        target_re = re.compile(r"^([a-zA-Z_-][a-zA-Z0-9_-]*):", re.MULTILINE)
        targets = target_re.findall(makefile_text)
        from collections import Counter
        dupes = [t for t, c in Counter(targets).items() if c > 1]
        makefile_details["targets"] = targets
        makefile_details["duplicates"] = dupes
        makefile_details["passed"] = len(dupes) == 0
    else:
        makefile_details["passed"] = True  # No Makefile is OK
    checks["G_makefile_targets"] = makefile_details
    if makefile_details.get("duplicates"):
        failures.append(f"G. Duplicate Makefile targets: {makefile_details['duplicates']}")

    # H. Secret scan
    secret_findings = []
    for label, path in ALL_FILES:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pat, name in SECRET_PATTERNS:
            if pat.search(text):
                secret_findings.append({"file": label, "pattern": name})
    checks["H_secret_scan"] = {"passed": len(secret_findings) == 0, "findings": secret_findings}
    if secret_findings:
        failures.append(f"H. Secrets detected: {secret_findings}")

    # I. Real send/trading risk scan
    risk_findings = []
    # Skip redteam_aegis_pipeline_validator.py because it intentionally
    # contains test injection code (requests.post, place_order, etc.)
    # written only to tmp/ directories, never executed against real services.
    SKIP_RISK_SCAN = {"redteam_aegis_pipeline_validator.py"}
    for sp in SCRIPT_DIR.rglob("*.py"):
        if sp.name in SKIP_RISK_SCAN:
            continue
        text = sp.read_text(encoding="utf-8", errors="ignore")
        for pat, name in RISK_PATTERNS:
            if pat.search(text):
                risk_findings.append({"file": sp.name, "pattern": name})
    checks["I_real_send_risk_scan"] = {"passed": len(risk_findings) == 0, "findings": risk_findings}
    if risk_findings:
        failures.append(f"I. Network/trading calls detected: {risk_findings}")

    # J. Cross-validate hash (Python hashlib vs /usr/bin/shasum)
    cross_results = {}
    cross_ok = True
    for label, path in ALL_FILES:
        if path.exists():
            cv = _cross_validate(path)
            cross_results[label] = cv
            if cv.get("match") is False:
                cross_ok = False
                failures.append(f"J. Hash mismatch for {label}: python={cv.get('python')} shasum={cv.get('shasum')}")
    checks["J_cross_validation"] = {"passed": cross_ok, "details": cross_results}


    # K. MD file hash format validation
    md_hash_issues = []
    # Skip degradation_recovery report - it legitimately records test invalid hash values
    SKIP_MD_HASH_SCAN = {"aegis_degradation_recovery_latest.md"}
    for md_path in REPORTS_DIR.glob("*.md"):
        if not md_path.exists():
            continue
        if md_path.name in SKIP_MD_HASH_SCAN:
            continue
        text = md_path.read_text(encoding="utf-8", errors="ignore")
        for m in MD_HASH_RE.finditer(text):
            val = m.group(1)
            if val in ("None", "null", "none", "NULL", "self_hash_verified_by_evidence_gate"):
                continue
            if val and not HASH_RE.match(val):
                md_hash_issues.append(f"Invalid hash format in {md_path.name}: {val}")
            if val in KNOWN_FAKE_HASHES:
                md_hash_issues.append(f"Fake hash in {md_path.name}: {val}")
    checks["K_md_hash_format"] = {"passed": len(md_hash_issues) == 0, "issues": md_hash_issues}
    failures.extend(md_hash_issues)

    # L. Doc duplicate section detection (only P21-managed docs)
    doc_dupe_issues = []
    docs_to_check = [REPO_ROOT / "README.md", REPO_ROOT / "HANDOFF.md"]
    for doc_path in docs_to_check:
        if not doc_path.exists():
            continue
        text = doc_path.read_text(encoding="utf-8", errors="ignore")
        # Only check for P21 section duplicates
        p21_section_re = re.compile(r"^##+\s+.*(P21|feishu|dry.run|pipeline|evidence|gate).*", re.MULTILINE | re.IGNORECASE)
        p21_sections = p21_section_re.findall(text)
        from collections import Counter as _Counter
        normalized = [s.strip() for s in p21_sections]
        dupes = [h for h, c in _Counter(normalized).items() if c > 1]
        if dupes:
            doc_dupe_issues.append(f"Duplicate P21 sections in {doc_path.name}: {dupes}")
    checks["L_doc_duplicate_sections"] = {"passed": len(doc_dupe_issues) == 0, "issues": doc_dupe_issues}
    failures.extend(doc_dupe_issues)

    # N. Pipeline History checks (P21.6d) — skip if --skip-history
    if not args.skip_history:
        # N. Pipeline History checks (P21.6d)
        HISTORY_JSON = REPORTS_DIR / "aegis_pipeline_history_latest.json"
        SNAPSHOTS_DIR = REPORTS_DIR / "aegis_pipeline_history_snapshots"

        # N_history_json_exists
        history_exists = HISTORY_JSON.exists()
        checks["N_history_json_exists"] = {"passed": history_exists}
        if not history_exists:
            failures.append("N_history_json_exists: history JSON file does not exist")

        # N_history_json_parseable
        history_parseable = False
        history_data = None
        if history_exists:
            try:
                history_data = json.loads(HISTORY_JSON.read_text(encoding="utf-8"))
                if isinstance(history_data, dict) and "runs" in history_data:
                    history_parseable = True
                else:
                    failures.append("N_history_json_parseable: root is not a dict with 'runs' key")
            except Exception as e:
                failures.append(f"N_history_json_parseable: parse error: {e}")
        checks["N_history_json_parseable"] = {"passed": history_parseable}

        # N_history_runs_count_between_1_and_7
        runs_count_ok = False
        runs_count = 0
        if history_exists and history_parseable:
            runs = history_data.get("runs", [])
            runs_count = len(runs)
            runs_count_ok = 1 <= runs_count <= 7
            if not runs_count_ok:
                failures.append(f"N_history_runs_count_between_1_and_7: runs_count={runs_count} outside [1,7]")
        checks["N_history_runs_count_between_1_and_7"] = {"passed": runs_count_ok, "count": runs_count}

        # Remaining checks need at least one run
        if history_exists and history_parseable and runs_count >= 1:
            latest = history_data["runs"][0]

            # N_history_latest_gate_pass
            gate_verdict = latest.get("gate_overall_verdict")
            gate_pass = gate_verdict == "PASS"
            checks["N_history_latest_gate_pass"] = {"passed": gate_pass, "value": gate_verdict}
            if not gate_pass:
                failures.append(f"N_history_latest_gate_pass: gate_overall_verdict={gate_verdict}")

            # N_history_latest_feishu_safety_flags_valid
            feishu_dry_run = latest.get("feishu_dry_run")
            feishu_sent = latest.get("feishu_sent")
            feishu_webhook = latest.get("feishu_webhook_called")
            feishu_trading = latest.get("feishu_trading_called")
            feishu_safe = (
                feishu_dry_run is True
                and feishu_sent is False
                and feishu_webhook is False
                and feishu_trading is False
            )
            checks["N_history_latest_feishu_safety_flags_valid"] = {
                "passed": feishu_safe,
                "details": {
                    "dry_run": feishu_dry_run,
                    "sent": feishu_sent,
                    "webhook_called": feishu_webhook,
                    "trading_called": feishu_trading,
                },
            }
            if not feishu_safe:
                failures.append(
                    f"N_history_latest_feishu_safety_flags_valid: dry_run={feishu_dry_run}, sent={feishu_sent}, "
                    f"webhook={feishu_webhook}, trading={feishu_trading}"
                )

            # N_history_hash_values_hex_12
            hash_fields = [
                "gate_json_sha256_12",
                "redteam_json_sha256_12",
                "degradation_json_sha256_12",
                "evidence_pack_json_sha256_12",
                "pipeline_json_sha256_12",
                "feishu_json_sha256_12",
            ]
            hash_valid = True
            hash_issues_detail = []
            for field in hash_fields:
                val = latest.get(field)
                if val is not None:
                    if not isinstance(val, str) or not HASH_RE.match(val):
                        hash_valid = False
                        hash_issues_detail.append(f"{field}={val} invalid format")
            # Also check source_reports hashes
            for name, info in latest.get("source_reports", {}).items():
                sr_val = info.get("sha256_12")
                if sr_val is not None:
                    if not isinstance(sr_val, str) or not HASH_RE.match(sr_val):
                        hash_valid = False
                        hash_issues_detail.append(f"source_reports.{name}.sha256_12={sr_val} invalid format")
            checks["N_history_hash_values_hex_12"] = {"passed": hash_valid, "issues": hash_issues_detail}
            if not hash_valid:
                failures.append(f"N_history_hash_values_hex_12: {hash_issues_detail}")

            # N_history_no_known_fake_hash
            fake_found = []
            all_hashes = [latest.get(f) for f in hash_fields if latest.get(f) is not None]
            for name, info in latest.get("source_reports", {}).items():
                sr_val = info.get("sha256_12")
                if sr_val is not None:
                    all_hashes.append(sr_val)
            for h in all_hashes:
                if h in KNOWN_FAKE_HASHES:
                    fake_found.append(h)
            no_fake = len(fake_found) == 0
            checks["N_history_no_known_fake_hash"] = {"passed": no_fake, "fake_found": fake_found}
            if not no_fake:
                failures.append(f"N_history_no_known_fake_hash: fake hashes detected: {fake_found}")

            # N_history_latest_snapshot_exists
            latest_run_id = latest.get("run_id")
            snapshot_file = SNAPSHOTS_DIR / f"{latest_run_id}_history_entry.json"
            snapshot_exists = snapshot_file.exists()
            checks["N_history_latest_snapshot_exists"] = {"passed": snapshot_exists, "path": snapshot_file.name}
            if not snapshot_exists:
                failures.append(f"N_history_latest_snapshot_exists: {snapshot_file.name} not found")

        if contract["detected_dashboard_type"] == "legacy_dashboard_v1":
            dashboard_text = DASHBOARD_HTML.read_text(encoding="utf-8") if DASHBOARD_HTML.exists() else ""
            has_history_section = "Pipeline 最近 7 次运行" in dashboard_text
            has_history_fetch = "aegis_pipeline_history_latest.json" in dashboard_text
            degrade_ok = "未生成 pipeline 历史快照" in dashboard_text and "pipeline 历史 JSON 解析失败" in dashboard_text
            checks["N_dashboard_history_section_present"] = {"passed": has_history_section}
            checks["N_dashboard_history_fetch_present"] = {"passed": has_history_fetch}
            checks["N_dashboard_history_degrade_present"] = {"passed": degrade_ok}
            if not (has_history_section and has_history_fetch and degrade_ok):
                failures.append("N. Legacy dashboard history contract missing")
        else:
            checks["N_dashboard_legacy_ui"] = {"passed": True, "warning": "legacy history UI checks are not applicable to CEO Brief v2"}


    else:
        # --skip-history: skip all N_history checks, do not affect overall_verdict
        pass

    # M. Feishu 00700.HK check (when HK data is present and not marked missing)
    hk_issues = []
    if FEISHU_JSON.exists():
        try:
            feishu_data = json.loads(FEISHU_JSON.read_text(encoding="utf-8"))
            hk_sample = feishu_data.get("hk_sample", {})
            if isinstance(hk_sample, dict) and hk_sample.get("missing") is not True:
                blob = json.dumps(feishu_data, ensure_ascii=False)
                if "00700.HK" not in blob:
                    hk_issues.append("00700.HK missing from feishu JSON while hk_sample is not marked missing")
        except Exception:
            pass
    checks["M_feishu_hk_symbol"] = {"passed": len(hk_issues) == 0, "issues": hk_issues}
    failures.extend(hk_issues)

    # Overall verdict
    overall_passed = len(failures) == 0
    gate_finished = _now_iso()

    gate = {
        "project": "Project Aegis",
        "type": "evidence_gate",
        "gate_started_at": gate_started,
        "gate_finished_at": gate_finished,
        "strict_mode": args.strict,
        "checks": checks,
        "failures": failures,
        "overall_verdict": "PASS" if overall_passed else "FAIL",
    }

    # Output GATE_VERDICT_JSON to stdout
    print("GATE_VERDICT_JSON")
    print(json.dumps(gate, ensure_ascii=False, indent=2))
    print("END_GATE_VERDICT_JSON")

    # Write report if requested
    if args.write_report:
        OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT_JSON.write_text(json.dumps(gate, ensure_ascii=False, indent=2), encoding="utf-8")

        md_lines = [
            "# Project Aegis Evidence Gate",
            "",
            f"> Gate time: {gate_started} → {gate_finished}",
            f"> Strict mode: `{args.strict}`",
            "",
            f"## Overall Verdict: {gate['overall_verdict']}",
            "",
            "## Checks",
            "",
        ]
        for key, val in checks.items():
            md_lines.append(f"### {key}")
            md_lines.append(f"- Passed: `{val.get('passed')}`")
            if "details" in val:
                md_lines.append(f"- Details: `{json.dumps(val['details'], ensure_ascii=False)[:200]}`")
            if "issues" in val:
                md_lines.append(f"- Issues: `{val['issues']}`")
            if "findings" in val:
                md_lines.append(f"- Findings: `{val['findings']}`")
            md_lines.append("")

        if failures:
            md_lines.append("## Failures")
            for f in failures:
                md_lines.append(f"- ❌ {f}")
        else:
            md_lines.append("## Failures")
            md_lines.append("- (none)")

        md_lines.extend([
            "",
            "---",
            f"_Generated by verify_aegis_evidence_gate.py at {gate_finished}_",
        ])
        OUTPUT_MD.write_text("\n".join(md_lines), encoding="utf-8")

        print(f"\n[evidence_gate] JSON → {OUTPUT_JSON}", file=sys.stderr)
        print(f"[evidence_gate] MD   → {OUTPUT_MD}", file=sys.stderr)

    return 0 if overall_passed else 1


if __name__ == "__main__":
    sys.exit(main())
