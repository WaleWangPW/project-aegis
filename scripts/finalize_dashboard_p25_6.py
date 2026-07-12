#!/usr/bin/env python3
"""Write P25.6 markers only after final reports are already current."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "data/reports"
MARKERS = [
    "P25_6_REAL_USAGE_PASS.marker",
    "P25_6_HTTP_PASS.marker",
    "P25_6_MOBILE_STATIC_PASS.marker",
    "P25_6_EVIDENCE_GATE_PASS.marker",
]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    files = {
        "index": ROOT / "dashboard/index.html",
        "html": ROOT / "dashboard/v2.html",
        "js": ROOT / "dashboard/v2.js",
        "css": ROOT / "dashboard/v2.css",
        "validator": ROOT / "scripts/validate_dashboard_p25_6_real_usage.py",
        "usage": REPORTS / "p25_6_real_usage_acceptance_latest.json",
        "validation": REPORTS / "dashboard_p25_6_real_usage_validation_latest.json",
        "evidence": REPORTS / "aegis_evidence_gate_latest.json",
        "http": REPORTS / "dashboard_p25_6_http_smoke_latest.json",
    }
    if any(not path.exists() for path in files.values()):
        print("[p25_6_finalize] FAIL: required file missing")
        return 1
    usage, validation, evidence, http = (load(files[key]) for key in ("usage", "validation", "evidence", "http"))
    if not (
        files["index"].read_bytes() == files["html"].read_bytes()
        and usage.get("overall_verdict") == "PASS"
        and validation.get("overall_verdict") == "PASS"
        and evidence.get("overall_verdict") == "PASS"
        and http.get("overall_verdict") == "PASS"
    ):
        print("[p25_6_finalize] FAIL: verdict or copy consistency")
        return 1
    content = "\n".join([
        f"generated_at={datetime.now(timezone.utc).isoformat()}",
        "command=.venv/bin/python scripts/finalize_dashboard_p25_6.py",
        "exit_code=0",
        "contract=2.0",
        f"index_sha256={sha(files['index'])}",
        f"v2_html_sha256={sha(files['html'])}",
        f"v2_js_sha256={sha(files['js'])}",
        f"v2_css_sha256={sha(files['css'])}",
        f"validator_sha256={sha(files['validator'])}",
        f"real_usage_report_sha256={sha(files['usage'])}",
        f"evidence_gate_report_sha256={sha(files['evidence'])}",
        f"http_report_sha256={sha(files['http'])}",
        f"browser_render_available={str(usage.get('browser_render_available')).lower()}",
        "failed=0",
        "",
    ])
    for name in MARKERS:
        (REPORTS / name).write_text(content, encoding="utf-8")
    for name in ("P25_6_REAL_USAGE_FAIL.marker", "P25_6_REAL_USAGE_FAIL_REASON.md"):
        path = REPORTS / name
        if path.exists():
            path.unlink()
    print("[p25_6_finalize] PASS: P25.6 markers written")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
