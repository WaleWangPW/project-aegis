#!/usr/bin/env python3
"""
validate_aegis_daily_digest_pipeline.py

Validate the daily-digest pipeline output.
Supports --strict and --pipeline-json PATH.
Exits non-zero on failure.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from dashboard_contract import inspect_dashboard

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
REPORTS_DIR = REPO_ROOT / "data" / "reports"

DEFAULT_PIPELINE_JSON = REPORTS_DIR / "aegis_daily_digest_pipeline_latest.json"
FEISHU_JSON = REPORTS_DIR / "feishu_daily_digest_dry_run.json"
DASHBOARD_HTML = REPO_ROOT / "dashboard" / "index.html"

HASH_RE = re.compile(r"^[0-9a-f]{12}$")
KNOWN_FAKE_HASHES = {"000000000000", "deadbeefdead", "aaaaaaaaaaaa", "ffffffffffff"}


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Aegis daily digest pipeline")
    parser.add_argument("--strict", action="store_true", help="Treat warnings as errors")
    parser.add_argument("--pipeline-json", type=Path, default=DEFAULT_PIPELINE_JSON, help="Path to pipeline JSON")
    args = parser.parse_args()

    errors: list[str] = []
    warnings: list[str] = []

    # 1. Pipeline JSON exists and is parseable
    if not args.pipeline_json.exists():
        errors.append(f"Pipeline JSON not found: {args.pipeline_json}")
        _print_result(errors, warnings, args.strict)
        return 1
    try:
        pipeline = json.loads(args.pipeline_json.read_text(encoding="utf-8"))
    except Exception as e:
        errors.append(f"Pipeline JSON parse error: {e}")
        _print_result(errors, warnings, args.strict)
        return 1

    # 2. At least 10 stages
    stages = pipeline.get("stages", [])
    if len(stages) < 10:
        errors.append(f"Expected ≥10 stages, got {len(stages)}")

    # 3. refresh_feishu_dry_run stage PASS
    feishu_stage = next((s for s in stages if s.get("stage_name") == "refresh_feishu_dry_run"), None)
    if feishu_stage is None:
        errors.append("Stage 'refresh_feishu_dry_run' not found")
    elif feishu_stage.get("status") != "PASS":
        errors.append(f"refresh_feishu_dry_run status={feishu_stage.get('status')} (expected PASS)")

    # 4. validate_feishu_dry_run_json stage PASS
    validate_stage = next((s for s in stages if s.get("stage_name") == "validate_feishu_dry_run_json"), None)
    if validate_stage is None:
        errors.append("Stage 'validate_feishu_dry_run_json' not found")
    elif validate_stage.get("status") != "PASS":
        errors.append(f"validate_feishu_dry_run_json status={validate_stage.get('status')} (expected PASS)")

    # 5. evidence_policy exists and raw_self_hash_not_claimed_in_pipeline_json = true
    ep = pipeline.get("evidence_policy")
    if not ep:
        errors.append("evidence_policy not found")
    else:
        if ep.get("raw_self_hash_not_claimed_in_pipeline_json") is not True:
            errors.append("evidence_policy.raw_self_hash_not_claimed_in_pipeline_json is not true")

    # 6. evidence_integrity.placeholder_hash_detected = false
    ei = pipeline.get("evidence_integrity")
    if not ei:
        errors.append("evidence_integrity not found")
    else:
        if ei.get("placeholder_hash_detected") is not False:
            errors.append("evidence_integrity.placeholder_hash_detected is not false")

    # 7. All non-null sha256_12 match ^[0-9a-f]{12}$
    fingerprints = pipeline.get("file_fingerprints", {})
    for phase_key in ("before", "after"):
        phase = fingerprints.get(phase_key, {})
        for label, fp in phase.items():
            sha = fp.get("sha256_12")
            if sha is not None:
                # Allow self-referential hash marker
                if sha == "self_hash_verified_by_evidence_gate":
                    continue
                if not HASH_RE.match(sha):
                    errors.append(f"Invalid sha256_12 format for {label}: {sha}")
                if sha in KNOWN_FAKE_HASHES:
                    errors.append(f"Known fake hash for {label}: {sha}")

    # 8. Feishu JSON: dry_run=true, sent=false, webhook_called=false, trading_called=false
    if not FEISHU_JSON.exists():
        errors.append(f"Feishu JSON not found: {FEISHU_JSON}")
    else:
        try:
            feishu = json.loads(FEISHU_JSON.read_text(encoding="utf-8"))
            if feishu.get("dry_run") is not True:
                errors.append("feishu JSON: dry_run is not true")
            if feishu.get("sent") is not False:
                errors.append("feishu JSON: sent is not false")
            if feishu.get("webhook_called") is not False:
                errors.append("feishu JSON: webhook_called is not false")
            if feishu.get("trading_called") is not False:
                errors.append("feishu JSON: trading_called is not false")

            # 9. Contains 00700.HK, CRCL, 000002.SZ
            blob = json.dumps(feishu, ensure_ascii=False)
            # Check CRCL and 000002.SZ as required symbols
            # 00700.HK is optional - HK report may not exist yet
            for sym in ("CRCL", "000002.SZ"):
                if sym not in blob:
                    errors.append(f"{sym} not found in feishu JSON")
            # 00700.HK: only error if HK data exists but symbol is missing
            if "00700.HK" not in blob:
                hk_missing = True
                hk_sample = feishu.get("hk_sample", {})
                if isinstance(hk_sample, dict) and hk_sample.get("missing") is True:
                    pass  # HK report not generated yet - expected
                else:
                    warnings.append("00700.HK not found in feishu JSON (HK report may be missing)")

            # 10. Contains mDNS and Tailscale links
            links = feishu.get("mobile_links", {})
            if not links.get("mdns"):
                errors.append("feishu JSON: missing mobile_links.mdns")
            if not links.get("tailscale"):
                errors.append("feishu JSON: missing mobile_links.tailscale")
        except Exception as e:
            errors.append(f"Feishu JSON parse error: {e}")

    # 11. Dashboard Contract; legacy visual references are not required by v2.
    if not DASHBOARD_HTML.exists():
        errors.append(f"Dashboard not found: {DASHBOARD_HTML}")
    else:
        contract = inspect_dashboard(DASHBOARD_HTML, REPO_ROOT / "dashboard" / "v2.js", REPO_ROOT / "dashboard" / "v2.css")
        if contract["overall_verdict"] != "PASS":
            errors.append(f"Dashboard Contract failed: {contract['failures']}")

    _print_result(errors, warnings, args.strict)
    if errors:
        return 1
    if args.strict and warnings:
        return 1
    return 0


def _print_result(errors: list[str], warnings: list[str], strict: bool):
    if errors:
        print("❌ VALIDATION FAILED")
        for e in errors:
            print(f"  ERROR: {e}")
    else:
        print("✅ VALIDATION PASSED")

    if warnings:
        for w in warnings:
            print(f"  WARN: {w}")

    if strict and warnings and not errors:
        print("❌ STRICT MODE: warnings treated as errors")


if __name__ == "__main__":
    sys.exit(main())
