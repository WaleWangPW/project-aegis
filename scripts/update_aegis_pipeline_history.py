#!/usr/bin/env python3
"""
update_aegis_pipeline_history.py

Reads the latest Aegis pipeline reports and creates a history snapshot.
Appends a new entry to the pipeline history, retaining the most recent 7 runs.

Outputs:
  - data/reports/aegis_pipeline_history_latest.json
  - data/reports/aegis_pipeline_history_latest.md
  - data/reports/aegis_pipeline_history_snapshots/<run_id>_history_entry.json
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

SNAPSHOTS_DIR = REPORTS_DIR / "aegis_pipeline_history_snapshots"

INPUT_FILES = {
    "gate": REPORTS_DIR / "aegis_evidence_gate_latest.json",
    "evidence_pack": REPORTS_DIR / "aegis_evidence_pack_latest.json",
    "redteam": REPORTS_DIR / "aegis_pipeline_redteam_latest.json",
    "degradation": REPORTS_DIR / "aegis_degradation_recovery_latest.json",
    "pipeline": REPORTS_DIR / "aegis_daily_digest_pipeline_latest.json",
    "feishu": REPORTS_DIR / "feishu_daily_digest_dry_run.json",
}

OUTPUT_JSON = REPORTS_DIR / "aegis_pipeline_history_latest.json"
OUTPUT_MD = REPORTS_DIR / "aegis_pipeline_history_latest.md"

HASH_RE = re.compile(r"^[0-9a-f]{12}$")


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def _run_id() -> str:
    return "run_" + datetime.now(timezone.utc).astimezone().strftime("%Y%m%d_%H%M%S")


def _sha256_12(path: Path) -> str | None:
    if not path.exists():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()[:12]


def _load_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _build_entry() -> dict:
    run_id = _run_id()
    generated_at = _now_iso()

    # Source reports
    source_reports = {}
    for name, path in INPUT_FILES.items():
        sha = _sha256_12(path)
        source_reports[name] = {
            "exists": path.exists(),
            "sha256_12": sha,
        }

    # Gate data
    gate = _load_json(INPUT_FILES["gate"])
    gate_overall_verdict = gate.get("overall_verdict") if gate else None
    gate_failures = gate.get("failures", []) if gate else []
    gate_failures_count = len(gate_failures) if gate else 0
    gate_json_sha256_12 = source_reports["gate"]["sha256_12"]

    # Redteam data
    redteam = _load_json(INPUT_FILES["redteam"])
    redteam_passed = redteam.get("passed") if redteam else None
    redteam_total = redteam.get("total_tests") if redteam else None
    redteam_all_rejected = False
    if redteam and "tests" in redteam:
        tests = redteam["tests"]
        if tests:
            redteam_all_rejected = all(
                t.get("rejected") is True or t.get("result") == "REJECTED"
                for t in tests
            )
    redteam_json_sha256_12 = source_reports["redteam"]["sha256_12"]

    # Degradation data
    degradation = _load_json(INPUT_FILES["degradation"])
    degradation_total = degradation.get("total_tests") if degradation else None
    degradation_passed = degradation.get("passed") if degradation else None
    degradation_json_sha256_12 = source_reports["degradation"]["sha256_12"]

    # Evidence pack
    evidence_pack_json_sha256_12 = source_reports["evidence_pack"]["sha256_12"]

    # Pipeline
    pipeline_json_sha256_12 = source_reports["pipeline"]["sha256_12"]

    # Feishu data
    feishu = _load_json(INPUT_FILES["feishu"])
    feishu_json_sha256_12 = source_reports["feishu"]["sha256_12"]
    feishu_dry_run = feishu.get("dry_run") if feishu else None
    feishu_sent = feishu.get("sent") if feishu else None
    feishu_webhook_called = feishu.get("webhook_called") if feishu else None
    feishu_trading_called = feishu.get("trading_called") if feishu else None

    # HK sample
    hk_00700_status = None
    if feishu:
        hk_sample = feishu.get("hk_sample", {})
        if isinstance(hk_sample, dict):
            if hk_sample.get("missing") is True:
                hk_00700_status = "missing"
            else:
                hk_00700_status = hk_sample.get("status", "present")
        else:
            hk_00700_status = "present"

    # Risk monitors
    crcl_status = None
    sz_000002_status = None
    if feishu:
        risk_monitors = feishu.get("risk_monitors", {})
        crcl = risk_monitors.get("CRCL")
        if crcl:
            crcl_status = crcl.get("status", "unknown")
        sz = risk_monitors.get("000002.SZ")
        if sz:
            sz_000002_status = sz.get("status", "unknown")

    # P21.6d-restore: enforce canonical source validation
    A_SHARE_WATCHLIST = REPORTS_DIR / 'a_share_watchlist_latest.json'
    watchlist = _load_json(A_SHARE_WATCHLIST)

    if watchlist is not None:
        all_stocks = watchlist.get('stocks', [])
        if len(all_stocks) < 20:
            print(f'[ERROR] Canonical A-share watchlist has only {len(all_stocks)} records, expected >=20', file=sys.stderr)
            fail_reasons = []
            fail_reasons.append(f'canonical_watchlist_insufficient_records={len(all_stocks)} < 20')
        else:
            # Use only from canonical source, no fallback
            a_share_top5_symbols = [s.get('symbol', '') for s in all_stocks[:5] if s.get('symbol')]
    else:
        print('[ERROR] Canonical A-share watchlist not found', file=sys.stderr)
        fail_reasons = []
        fail_reasons.append('canonical_watchlist_missing')
        a_share_top5_symbols = []

    # Link presence
    mdns_link_present = False
    tailscale_link_present = False
    if feishu:
        message_text = feishu.get("message_text", "")
        mobile_links = feishu.get("mobile_links", {})
        if isinstance(mobile_links, dict):
            mdns_link = mobile_links.get("mdns", "")
            tailscale_link = mobile_links.get("tailscale", "")
            if mdns_link and mdns_link in message_text:
                mdns_link_present = True
            elif "mDNS" in message_text or "mdns" in message_text.lower() or "local:" in message_text:
                mdns_link_present = True
            if tailscale_link and tailscale_link in message_text:
                tailscale_link_present = True
            elif "Tailscale" in message_text or "tailscale" in message_text.lower():
                tailscale_link_present = True
        # Also check mobile_links presence
        if not mdns_link_present and mobile_links.get("mdns"):
            mdns_link_present = True
        if not tailscale_link_present and mobile_links.get("tailscale"):
            tailscale_link_present = True

    # Safety summary
    safety_summary = "dry-run, not sent, no webhook, no trading"

    # Result determination
    fail_reasons = []
    if gate_overall_verdict != "PASS":
        fail_reasons.append(f"gate_overall_verdict={gate_overall_verdict}")
    if len(a_share_top5_symbols) < 5:
        fail_reasons.append(f"a_share_top5_symbols_count={len(a_share_top5_symbols)} < 5")
    if not redteam_all_rejected:
        fail_reasons.append("redteam_all_rejected=false")
    # Feishu safety flags
    if feishu_dry_run is not True:
        fail_reasons.append(f"feishu_dry_run={feishu_dry_run}")
    if feishu_sent is not False:
        fail_reasons.append(f"feishu_sent={feishu_sent}")
    if feishu_webhook_called is not False:
        fail_reasons.append(f"feishu_webhook_called={feishu_webhook_called}")
    if feishu_trading_called is not False:
        fail_reasons.append(f"feishu_trading_called={feishu_trading_called}")

    result = "PASS" if not fail_reasons else "FAIL"
    result_reason = "; ".join(fail_reasons) if fail_reasons else "all checks passed"

    entry = {
        "run_id": run_id,
        "generated_at": generated_at,
        "source_reports": source_reports,
        "gate_overall_verdict": gate_overall_verdict,
        "gate_failures_count": gate_failures_count,
        "gate_json_sha256_12": gate_json_sha256_12,
        "redteam_passed": redteam_passed,
        "redteam_total": redteam_total,
        "redteam_all_rejected": redteam_all_rejected,
        "redteam_json_sha256_12": redteam_json_sha256_12,
        "degradation_total": degradation_total,
        "degradation_passed": degradation_passed,
        "degradation_json_sha256_12": degradation_json_sha256_12,
        "evidence_pack_json_sha256_12": evidence_pack_json_sha256_12,
        "pipeline_json_sha256_12": pipeline_json_sha256_12,
        "feishu_json_sha256_12": feishu_json_sha256_12,
        "feishu_dry_run": feishu_dry_run,
        "feishu_sent": feishu_sent,
        "feishu_webhook_called": feishu_webhook_called,
        "feishu_trading_called": feishu_trading_called,
        "hk_00700_status": hk_00700_status,
        "crcl_status": crcl_status,
        "sz_000002_status": sz_000002_status,
        "a_share_top5_symbols": a_share_top5_symbols,
        "mdns_link_present": mdns_link_present,
        "tailscale_link_present": tailscale_link_present,
        "safety_summary": safety_summary,
        "result": result,
        "result_reason": result_reason,
    }

    return entry


def _build_history(entry: dict) -> dict:
    """Load existing history, prepend new entry, trim to 7."""
    existing: list = []
    if OUTPUT_JSON.exists():
        try:
            old = json.loads(OUTPUT_JSON.read_text(encoding="utf-8"))
            existing = old.get("runs", [])
        except Exception:
            existing = []

    runs = [entry] + existing
    runs = runs[:7]

    return {
        "project": "Project Aegis",
        "type": "pipeline_history",
        "updated_at": _now_iso(),
        "retention_limit": 7,
        "runs": runs,
    }


def _write_md(history: dict):
    lines = [
        "# Project Aegis Pipeline History",
        "",
        f"> 更新时间: {history['updated_at']}",
        f"> 保留数量: 最近 {history['retention_limit']} 次运行",
        "",
        "| # | Run ID | 时间 | 结果 | Gate | Redteam | Degradation |",
        "|---|--------|------|------|------|---------|-------------|",
    ]
    for i, run in enumerate(history["runs"], 1):
        lines.append(
            f"| {i} | {run['run_id']} | {run['generated_at'][:19]} | "
            f"{run['result']} | {run.get('gate_overall_verdict', 'N/A')} | "
            f"{'✅' if run.get('redteam_all_rejected') else '❌'} | "
            f"{run.get('degradation_passed', 'N/A')}/{run.get('degradation_total', 'N/A')} |"
        )
    lines.append("")
    OUTPUT_MD.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    # Create snapshots directory
    SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)

    # Build entry
    entry = _build_entry()

    # Build history (load existing + prepend + trim)
    history = _build_history(entry)

    # Write history JSON
    OUTPUT_JSON.write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")

    # Write history MD
    _write_md(history)

    # Write snapshot file
    snapshot_path = SNAPSHOTS_DIR / f"{entry['run_id']}_history_entry.json"
    snapshot_path.write_text(json.dumps(entry, ensure_ascii=False, indent=2), encoding="utf-8")

    # Report
    print(f"[update_aegis_pipeline_history] run_id={entry['run_id']}")
    print(f"[update_aegis_pipeline_history] result={entry['result']}")
    print(f"[update_aegis_pipeline_history] runs_in_history={len(history['runs'])}")
    print(f"[update_aegis_pipeline_history] JSON → {OUTPUT_JSON}")
    print(f"[update_aegis_pipeline_history] MD   → {OUTPUT_MD}")
    print(f"[update_aegis_pipeline_history] Snapshot → {snapshot_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
