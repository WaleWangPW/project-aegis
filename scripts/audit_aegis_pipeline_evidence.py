#!/usr/bin/env python3
"""
audit_aegis_pipeline_evidence.py

Independent evidence audit. Does NOT trust pipeline self-report.
Re-reads the filesystem and computes real file fingerprints.
Outputs JSON + MD audit reports.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
REPORTS_DIR = REPO_ROOT / "data" / "reports"

PIPELINE_JSON = REPORTS_DIR / "aegis_daily_digest_pipeline_latest.json"
PIPELINE_MD = REPORTS_DIR / "aegis_daily_digest_pipeline_latest.md"
FEISHU_JSON = REPORTS_DIR / "feishu_daily_digest_dry_run.json"
FEISHU_MD = REPORTS_DIR / "feishu_daily_digest_dry_run.md"
DASHBOARD_HTML = REPO_ROOT / "dashboard" / "index.html"

AUDIT_JSON = REPORTS_DIR / "aegis_pipeline_evidence_audit_latest.json"
AUDIT_MD = REPORTS_DIR / "aegis_pipeline_evidence_audit_latest.md"

HASH_RE = re.compile(r"^[0-9a-f]{12}$")
KNOWN_FAKE_HASHES = {"000000000000", "deadbeefdead", "aaaaaaaaaaaa", "ffffffffffff"}

ALL_FILES = [
    ("crcl_risk_monitor_latest.json", REPORTS_DIR / "crcl_risk_monitor_latest.json"),
    ("000002.sz_risk_monitor_latest.json", REPORTS_DIR / "000002.sz_risk_monitor_latest.json"),
    ("a_share_watchlist_latest.json", REPORTS_DIR / "a_share_watchlist_latest.json"),
    ("hk_watchlist_sample.json", REPORTS_DIR / "hk_watchlist_sample.json"),
    ("feishu_daily_digest_dry_run.json", FEISHU_JSON),
    ("feishu_daily_digest_dry_run.md", FEISHU_MD),
    ("aegis_daily_digest_pipeline_latest.json", PIPELINE_JSON),
    ("aegis_daily_digest_pipeline_latest.md", PIPELINE_MD),
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


def _real_fingerprint(path: Path) -> dict:
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


def _cross_validate_hash(path: Path) -> dict:
    """Cross-validate Python hashlib vs /usr/bin/shasum."""
    if not path.exists():
        return {"available": False}
    import subprocess
    py_hash = hashlib.sha256(path.read_bytes()).hexdigest()[:12]
    try:
        result = subprocess.run(
            ["/usr/bin/shasum", "-a", "256", str(path)],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            shasum_hash = result.stdout.strip().split()[0][:12]
            return {
                "available": True,
                "python_hash": py_hash,
                "shasum_hash": shasum_hash,
                "match": py_hash == shasum_hash,
            }
    except Exception:
        pass
    return {"available": True, "python_hash": py_hash, "shasum_hash": None, "match": None}


def main() -> int:
    audit_started = _now_iso()

    # 1. Real file fingerprints
    real_fingerprints = {}
    for label, path in ALL_FILES:
        real_fingerprints[label] = _real_fingerprint(path)

    # 2. Pipeline JSON content audit
    pipeline_audit = {"exists": PIPELINE_JSON.exists()}
    if PIPELINE_JSON.exists():
        try:
            pipeline_data = json.loads(PIPELINE_JSON.read_text(encoding="utf-8"))
            pipeline_audit["parseable"] = True
            pipeline_audit["stage_count"] = len(pipeline_data.get("stages", []))
            pipeline_audit["has_evidence_policy"] = "evidence_policy" in pipeline_data
            pipeline_audit["raw_self_hash_not_claimed"] = pipeline_data.get("evidence_policy", {}).get("raw_self_hash_not_claimed_in_pipeline_json")
            pipeline_audit["placeholder_hash_detected"] = pipeline_data.get("evidence_integrity", {}).get("placeholder_hash_detected")

            # Compare pipeline self-reported fingerprints with real ones
            comparisons = {}
            for phase in ("before", "after"):
                reported = pipeline_data.get("file_fingerprints", {}).get(phase, {})
                for label, fp in reported.items():
                    real = real_fingerprints.get(label, {})
                    reported_sha = fp.get("sha256_12")
                    real_sha = real.get("sha256_12")
                    if reported_sha is not None and real_sha is not None:
                        comparisons[f"{phase}:{label}"] = {
                            "reported": reported_sha,
                            "real": real_sha,
                            "match": reported_sha == real_sha,
                        }
            pipeline_audit["fingerprint_comparisons"] = comparisons
        except Exception as e:
            pipeline_audit["parseable"] = False
            pipeline_audit["error"] = str(e)

    # 3. Hash audit
    hash_audit = {"all_valid": True, "invalid": [], "fake": []}
    for label, fp in real_fingerprints.items():
        sha = fp.get("sha256_12")
        if sha is not None:
            if not HASH_RE.match(sha):
                hash_audit["all_valid"] = False
                hash_audit["invalid"].append({"file": label, "hash": sha})
            if sha in KNOWN_FAKE_HASHES:
                hash_audit["all_valid"] = False
                hash_audit["fake"].append({"file": label, "hash": sha})

    # 4. Dry-run audit
    dry_run_audit = {"exists": FEISHU_JSON.exists()}
    if FEISHU_JSON.exists():
        try:
            feishu = json.loads(FEISHU_JSON.read_text(encoding="utf-8"))
            dry_run_audit["dry_run"] = feishu.get("dry_run")
            dry_run_audit["sent"] = feishu.get("sent")
            dry_run_audit["webhook_called"] = feishu.get("webhook_called")
            dry_run_audit["trading_called"] = feishu.get("trading_called")
            dry_run_audit["safe"] = (
                feishu.get("dry_run") is True
                and feishu.get("sent") is False
                and feishu.get("webhook_called") is False
                and feishu.get("trading_called") is False
            )
        except Exception as e:
            dry_run_audit["error"] = str(e)

    # 5. Dashboard audit
    dashboard_audit = {"exists": DASHBOARD_HTML.exists()}
    if DASHBOARD_HTML.exists():
        html = DASHBOARD_HTML.read_text(encoding="utf-8")
        dashboard_audit["has_feishu_reference"] = ("飞书日报" in html) or ("feishu" in html.lower()) or ("Dry-run" in html)
        dashboard_audit["has_degrade_notice"] = ("降级" in html) or ("degrade" in html.lower())
        dashboard_audit["size"] = len(html)

    # 6. Secret scan
    secret_findings = []
    for label, path in ALL_FILES:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pat, name in SECRET_PATTERNS:
            if pat.search(text):
                secret_findings.append({"file": label, "pattern": name})

    # 7. Real send/trading risk scan
    risk_findings = []
    # Skip redteam_aegis_pipeline_validator.py because it intentionally
    # contains test injection code (requests.post, place_order, etc.)
    # that is only written to tmp/ directories, never executed against
    # real services.
    SKIP_RISK_SCAN = {"redteam_aegis_pipeline_validator.py"}
    for sp in SCRIPT_DIR.glob("*.py"):
        if sp.name in SKIP_RISK_SCAN:
            continue
        text = sp.read_text(encoding="utf-8", errors="ignore")
        for pat, name in RISK_PATTERNS:
            if pat.search(text):
                risk_findings.append({"file": sp.name, "pattern": name})

    # 8. Cross-validate hashes (Python vs shasum)
    cross_validation = {}
    for label, path in ALL_FILES:
        if path.exists() and label != "aegis_daily_digest_pipeline_latest.json":
            cross_validation[label] = _cross_validate_hash(path)

    audit_finished = _now_iso()

    audit = {
        "project": "Project Aegis",
        "type": "pipeline_evidence_audit",
        "audit_started_at": audit_started,
        "audit_finished_at": audit_finished,
        "auditor": "audit_aegis_pipeline_evidence.py (independent)",
        "trust_source": "filesystem_direct_read",
        "real_fingerprints": real_fingerprints,
        "pipeline_json_audit": pipeline_audit,
        "hash_audit": hash_audit,
        "dry_run_audit": dry_run_audit,
        "dashboard_audit": dashboard_audit,
        "secret_scan": {
            "findings": secret_findings,
            "clean": len(secret_findings) == 0,
        },
        "real_send_risk_scan": {
            "findings": risk_findings,
            "clean": len(risk_findings) == 0,
        },
        "cross_validation": cross_validation,
        "overall_verdict": "PASS" if (
            hash_audit["all_valid"]
            and dry_run_audit.get("safe") is True
            and len(secret_findings) == 0
            and len(risk_findings) == 0
        ) else "FAIL",
    }

    AUDIT_JSON.parent.mkdir(parents=True, exist_ok=True)
    AUDIT_JSON.write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")

    # Write MD
    md_lines = [
        "# Project Aegis Pipeline Evidence Audit",
        "",
        f"> 审计时间: {audit_started} → {audit_finished}",
        f"> 审计者: {audit['auditor']}",
        f"> 信任来源: {audit['trust_source']}",
        "",
        f"## Overall Verdict: {audit['overall_verdict']}",
        "",
        "## Real File Fingerprints",
        "",
        "| File | Exists | Size | sha256_12 |",
        "|------|--------|------|-----------|",
    ]
    for label, fp in real_fingerprints.items():
        md_lines.append(f"| {label} | {fp.get('exists')} | {fp.get('size','—')} | `{fp.get('sha256_12','—')}` |")

    md_lines.extend([
        "",
        "## Hash Audit",
        "",
        f"- All valid: `{hash_audit['all_valid']}`",
        f"- Invalid hashes: {len(hash_audit['invalid'])}",
        f"- Fake hashes: {len(hash_audit['fake'])}",
        "",
        "## Dry-run Audit",
        "",
        f"- Exists: `{dry_run_audit.get('exists')}`",
        f"- dry_run: `{dry_run_audit.get('dry_run')}`",
        f"- sent: `{dry_run_audit.get('sent')}`",
        f"- webhook_called: `{dry_run_audit.get('webhook_called')}`",
        f"- trading_called: `{dry_run_audit.get('trading_called')}`",
        f"- Safe: `{dry_run_audit.get('safe')}`",
        "",
        "## Dashboard Audit",
        "",
        f"- Exists: `{dashboard_audit.get('exists')}`",
        f"- Has feishu reference: `{dashboard_audit.get('has_feishu_reference')}`",
        f"- Has degrade notice: `{dashboard_audit.get('has_degrade_notice')}`",
        f"- Size: `{dashboard_audit.get('size')}` bytes",
        "",
        "## Secret Scan",
        "",
        f"- Clean: `{audit['secret_scan']['clean']}`",
        f"- Findings: {len(secret_findings)}",
        "",
        "## Real Send / Trading Risk Scan",
        "",
        f"- Clean: `{audit['real_send_risk_scan']['clean']}`",
        f"- Findings: {len(risk_findings)}",
        "",
        "## Cross Validation (Python hashlib vs shasum)",
        "",
        "| File | Python | shasum | Match |",
        "|------|--------|--------|-------|",
    ])
    for label, cv in cross_validation.items():
        if cv.get("available"):
            md_lines.append(f"| {label} | `{cv.get('python_hash','—')}` | `{cv.get('shasum_hash','—')}` | `{cv.get('match')}` |")

    md_lines.extend([
        "",
        "---",
        f"_Generated by audit_aegis_pipeline_evidence.py at {audit_finished}_",
    ])
    AUDIT_MD.write_text("\n".join(md_lines), encoding="utf-8")

    print(f"[audit] JSON → {AUDIT_JSON}")
    print(f"[audit] MD   → {AUDIT_MD}")
    print(f"[audit] Verdict: {audit['overall_verdict']}")
    return 0 if audit["overall_verdict"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
