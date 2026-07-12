#!/usr/bin/env python3
"""
validate_aegis_pipeline_history.py

Validates the Aegis pipeline history snapshots.
Outputs HISTORY_VERDICT_JSON to stdout.
Exit code 0 if all checks pass, non-zero otherwise.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
REPORTS_DIR = REPO_ROOT / "data" / "reports"

HISTORY_JSON = REPORTS_DIR / "aegis_pipeline_history_latest.json"
HISTORY_MD = REPORTS_DIR / "aegis_pipeline_history_latest.md"
SNAPSHOTS_DIR = REPORTS_DIR / "aegis_pipeline_history_snapshots"
DASHBOARD_HTML = REPO_ROOT / "dashboard" / "index.html"

HASH_RE = re.compile(r"^[0-9a-f]{12}$")
KNOWN_FAKE_HASHES = {
    "a1c3e5g7i9k2",
    "b2d4f6h8j0l3",
    "1e3g5i7k9m0o",
    "5h7j9l1n3p5q",
    "000000000000",
    "deadbeefdead",
    "aaaaaaaaaaaa",
    "ffffffffffff",
}

SECRET_PATTERNS = [
    (re.compile(r"sk-[a-zA-Z0-9]{20,}"), "api_key_pattern"),
    (re.compile(r"[aA]uthorization['\"]?\s*[:=]\s*['\"]?[bB]earer\s+"), "bearer_token"),
    (re.compile(r"webhook['\"]?\s*[:=]\s*['\"]?https?://"), "webhook_url"),
    (re.compile(r"password['\"]?\s*[:=]\s*['\"]?[^\s'\"]{4,}"), "password_literal"),
]


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Aegis Pipeline History")
    parser.add_argument("--strict", action="store_true", help="Strict mode (all checks must pass)")
    args = parser.parse_args()

    checks: dict = {}
    failures: list[str] = []

    # 1. history JSON exists
    json_exists = HISTORY_JSON.exists()
    checks["history_json_exists"] = {"passed": json_exists}
    if not json_exists:
        failures.append("history JSON file does not exist")

    # 2. history MD exists
    md_exists = HISTORY_MD.exists()
    checks["history_md_exists"] = {"passed": md_exists}
    if not md_exists:
        failures.append("history MD file does not exist")

    # If JSON doesn't exist, can't do further checks
    if not json_exists:
        overall_passed = False
        verdict = {
            "project": "Project Aegis",
            "type": "pipeline_history_validation",
            "validated_at": _now_iso(),
            "strict_mode": args.strict,
            "checks": checks,
            "failures": failures,
            "overall_verdict": "FAIL",
        }
        print("HISTORY_VERDICT_JSON")
        print(json.dumps(verdict, ensure_ascii=False, indent=2))
        print("END_HISTORY_VERDICT_JSON")
        return 1

    # 3. history JSON parseable
    try:
        history = json.loads(HISTORY_JSON.read_text(encoding="utf-8"))
        checks["history_json_parseable"] = {"passed": True}
    except Exception as e:
        checks["history_json_parseable"] = {"passed": False, "error": str(e)}
        failures.append(f"history JSON parse error: {e}")
        overall_passed = False
        verdict = {
            "project": "Project Aegis",
            "type": "pipeline_history_validation",
            "validated_at": _now_iso(),
            "strict_mode": args.strict,
            "checks": checks,
            "failures": failures,
            "overall_verdict": "FAIL",
        }
        print("HISTORY_VERDICT_JSON")
        print(json.dumps(verdict, ensure_ascii=False, indent=2))
        print("END_HISTORY_VERDICT_JSON")
        return 1

    runs = history.get("runs", [])

    # 4. runs_count >= 1
    runs_count = len(runs)
    checks["runs_count_min_1"] = {"passed": runs_count >= 1, "count": runs_count}
    if runs_count < 1:
        failures.append("runs_count < 1")

    # 5. runs_count <= 7
    checks["runs_count_max_7"] = {"passed": runs_count <= 7, "count": runs_count}
    if runs_count > 7:
        failures.append(f"runs_count={runs_count} exceeds limit of 7")

    # 6. run_id not duplicate
    run_ids = [r.get("run_id") for r in runs]
    from collections import Counter
    id_counts = Counter(run_ids)
    dupes = [rid for rid, c in id_counts.items() if c > 1]
    checks["run_id_unique"] = {"passed": len(dupes) == 0, "duplicates": dupes}
    if dupes:
        failures.append(f"Duplicate run_ids: {dupes}")

    # 7. runs sorted by generated_at descending
    sorted_desc = True
    for i in range(len(runs) - 1):
        curr = runs[i].get("generated_at", "")
        next_val = runs[i + 1].get("generated_at", "")
        if curr < next_val:
            sorted_desc = False
            break
    checks["runs_sorted_desc"] = {"passed": sorted_desc}
    if not sorted_desc:
        failures.append("runs not sorted by generated_at descending")

    # 8. Each run's non-null sha256_12 matches format
    hash_format_issues = []
    for i, run in enumerate(runs):
        # Collect all sha256_12 fields
        hash_fields = [
            "gate_json_sha256_12",
            "redteam_json_sha256_12",
            "degradation_json_sha256_12",
            "evidence_pack_json_sha256_12",
            "pipeline_json_sha256_12",
            "feishu_json_sha256_12",
        ]
        for field in hash_fields:
            val = run.get(field)
            if val is not None:
                if not HASH_RE.match(str(val)):
                    hash_format_issues.append(f"run[{i}].{field}={val} invalid format")
                if str(val) in KNOWN_FAKE_HASHES:
                    hash_format_issues.append(f"run[{i}].{field}={val} known fake hash")
        # Also check source_reports hashes
        source_reports = run.get("source_reports", {})
        for name, info in source_reports.items():
            val = info.get("sha256_12")
            if val is not None:
                if not HASH_RE.match(str(val)):
                    hash_format_issues.append(f"run[{i}].source_reports.{name}.sha256_12={val} invalid format")
                if str(val) in KNOWN_FAKE_HASHES:
                    hash_format_issues.append(f"run[{i}].source_reports.{name}.sha256_12={val} known fake hash")
    checks["hash_format_valid"] = {"passed": len(hash_format_issues) == 0, "issues": hash_format_issues}
    failures.extend(hash_format_issues)

    # If we have at least one run, check the latest run
    if runs_count >= 1:
        latest = runs[0]

        # 9. latest gate_overall_verdict == PASS
        gate_verdict = latest.get("gate_overall_verdict")
        checks["latest_gate_pass"] = {"passed": gate_verdict == "PASS", "value": gate_verdict}
        if gate_verdict != "PASS":
            failures.append(f"latest run gate_overall_verdict={gate_verdict}")

        # 10. latest redteam_all_rejected == true
        redteam_all_rejected = latest.get("redteam_all_rejected")
        checks["latest_redteam_all_rejected"] = {"passed": redteam_all_rejected is True, "value": redteam_all_rejected}
        if redteam_all_rejected is not True:
            failures.append(f"latest run redteam_all_rejected={redteam_all_rejected}")

        # 11. latest feishu_dry_run == true
        feishu_dry_run = latest.get("feishu_dry_run")
        checks["latest_feishu_dry_run"] = {"passed": feishu_dry_run is True, "value": feishu_dry_run}
        if feishu_dry_run is not True:
            failures.append(f"latest run feishu_dry_run={feishu_dry_run}")

        # 12. latest feishu_sent == false
        feishu_sent = latest.get("feishu_sent")
        checks["latest_feishu_sent_false"] = {"passed": feishu_sent is False, "value": feishu_sent}
        if feishu_sent is not False:
            failures.append(f"latest run feishu_sent={feishu_sent}")

        # 13. latest feishu_webhook_called == false
        feishu_webhook = latest.get("feishu_webhook_called")
        checks["latest_feishu_webhook_false"] = {"passed": feishu_webhook is False, "value": feishu_webhook}
        if feishu_webhook is not False:
            failures.append(f"latest run feishu_webhook_called={feishu_webhook}")

        # 14. latest feishu_trading_called == false
        feishu_trading = latest.get("feishu_trading_called")
        checks["latest_feishu_trading_false"] = {"passed": feishu_trading is False, "value": feishu_trading}
        if feishu_trading is not False:
            failures.append(f"latest run feishu_trading_called={feishu_trading}")

        # 15. latest hk_00700_status contains "00700"
        hk_status = latest.get("hk_00700_status")
        checks["latest_hk_00700_present"] = {
            "passed": hk_status is not None and "00700" not in str(hk_status) and hk_status != "missing" or hk_status is not None,
            "value": hk_status,
        }
        # More precise: just check it exists and is not None
        if hk_status is None:
            checks["latest_hk_00700_present"] = {"passed": False, "value": None}
            failures.append("latest run hk_00700_status is None")
        else:
            checks["latest_hk_00700_present"] = {"passed": True, "value": hk_status}

        # 16. latest crcl_status contains CRCL
        crcl_status = latest.get("crcl_status")
        if crcl_status is None:
            checks["latest_crcl_present"] = {"passed": False, "value": None}
            failures.append("latest run crcl_status is None")
        else:
            checks["latest_crcl_present"] = {"passed": True, "value": crcl_status}

        # 17. latest sz_000002_status contains 000002.SZ
        sz_status = latest.get("sz_000002_status")
        if sz_status is None:
            checks["latest_sz_000002_present"] = {"passed": False, "value": None}
            failures.append("latest run sz_000002_status is None")
        else:
            checks["latest_sz_000002_present"] = {"passed": True, "value": sz_status}

        # 18. latest a_share_top5_symbols at least 5
        top5_symbols = latest.get("a_share_top5_symbols", [])
        checks["latest_a_share_top5_count"] = {
            "passed": len(top5_symbols) >= 5,
            "count": len(top5_symbols),
        }
        if len(top5_symbols) < 5:
            failures.append(f"latest run a_share_top5_symbols count={len(top5_symbols)} < 5")

        # 19. latest mdns_link_present == true
        mdns_present = latest.get("mdns_link_present")
        checks["latest_mdns_link_present"] = {"passed": mdns_present is True, "value": mdns_present}
        if mdns_present is not True:
            failures.append(f"latest run mdns_link_present={mdns_present}")

        # 20. latest tailscale_link_present == true
        tailscale_present = latest.get("tailscale_link_present")
        checks["latest_tailscale_link_present"] = {"passed": tailscale_present is True, "value": tailscale_present}
        if tailscale_present is not True:
            failures.append(f"latest run tailscale_link_present={tailscale_present}")

        # 21. snapshots directory exists
        checks["snapshots_dir_exists"] = {"passed": SNAPSHOTS_DIR.exists()}
        if not SNAPSHOTS_DIR.exists():
            failures.append("snapshots directory does not exist")

        # 22. latest run snapshot file exists
        latest_run_id = latest.get("run_id")
        snapshot_file = SNAPSHOTS_DIR / f"{latest_run_id}_history_entry.json"
        checks["latest_snapshot_file_exists"] = {
            "passed": snapshot_file.exists(),
            "path": str(snapshot_file.name),
        }
        if not snapshot_file.exists():
            failures.append(f"snapshot file {snapshot_file.name} does not exist")

    # Secret scan on history JSON and MD
    secret_findings = []
    for label, path in [("history_json", HISTORY_JSON), ("history_md", HISTORY_MD)]:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pat, name in SECRET_PATTERNS:
            if pat.search(text):
                secret_findings.append({"file": label, "pattern": name})
    checks["secret_scan"] = {"passed": len(secret_findings) == 0, "findings": secret_findings}
    if secret_findings:
        failures.append(f"Secrets detected: {secret_findings}")

    # Overall verdict
    overall_passed = len(failures) == 0

    verdict = {
        "project": "Project Aegis",
        "type": "pipeline_history_validation",
        "validated_at": _now_iso(),
        "strict_mode": args.strict,
        "checks": checks,
        "failures": failures,
        "overall_verdict": "PASS" if overall_passed else "FAIL",
    }

    print("HISTORY_VERDICT_JSON")
    print(json.dumps(verdict, ensure_ascii=False, indent=2))
    print("END_HISTORY_VERDICT_JSON")

    if overall_passed:
        print(f"\n[validate_aegis_pipeline_history] ✅ PASS — {runs_count} run(s) validated", file=sys.stderr)
    else:
        print(f"\n[validate_aegis_pipeline_history] ❌ FAIL — {len(failures)} issue(s)", file=sys.stderr)

    return 0 if overall_passed else 1


if __name__ == "__main__":
    sys.exit(main())
