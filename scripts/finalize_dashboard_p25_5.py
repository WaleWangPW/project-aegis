#!/usr/bin/env python3
"""Write P25.5 markers only from completed, current validation reports."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "data" / "reports"
MARKERS = [
    "P25_5_DASHBOARD_PRODUCTIZATION_PASS.marker",
    "P25_5_MOBILE_PASS.marker",
    "P25_5_COPY_PASS.marker",
    "P25_5_EVIDENCE_GATE_PASS.marker",
    "P25_5_HTTP_PASS.marker",
]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def report(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    index = ROOT / "dashboard" / "index.html"
    v2_html = ROOT / "dashboard" / "v2.html"
    v2_js = ROOT / "dashboard" / "v2.js"
    v2_css = ROOT / "dashboard" / "v2.css"
    validator = ROOT / "scripts" / "validate_dashboard_p25_5_productization.py"
    product = REPORTS / "dashboard_p25_5_productization_latest.json"
    contract_tests = REPORTS / "dashboard_contract_v2_tests_latest.json"
    evidence = REPORTS / "aegis_evidence_gate_latest.json"
    http = REPORTS / "dashboard_p25_5_http_smoke_latest.json"
    required = [index, v2_html, v2_js, v2_css, validator, product, contract_tests, evidence, http]
    if any(not path.exists() for path in required):
        print("[p25_5_finalize] FAIL: missing required file")
        return 1
    product_data, tests_data, evidence_data, http_data = map(report, [product, contract_tests, evidence, http])
    valid = (
        index.read_bytes() == v2_html.read_bytes()
        and product_data.get("overall_verdict") == "PASS"
        and tests_data.get("overall_verdict") == "PASS"
        and tests_data.get("test_count") == 19
        and tests_data.get("failed") in (0, "0")
        and evidence_data.get("overall_verdict") == "PASS"
        and http_data.get("overall_verdict") == "PASS"
    )
    if not valid:
        print("[p25_5_finalize] FAIL: report or copy consistency")
        return 1
    generated_at = datetime.now(timezone.utc).isoformat()
    content = "\n".join([
        f"generated_at={generated_at}",
        "command=.venv/bin/python scripts/finalize_dashboard_p25_5.py",
        "exit_code=0",
        "contract=2.0",
        f"index_sha256={sha(index)}",
        f"v2_html_sha256={sha(v2_html)}",
        f"v2_js_sha256={sha(v2_js)}",
        f"v2_css_sha256={sha(v2_css)}",
        f"validator_sha256={sha(validator)}",
        f"productization_report_sha256={sha(product)}",
        f"contract_test_report_sha256={sha(contract_tests)}",
        f"evidence_gate_report_sha256={sha(evidence)}",
        f"http_smoke_report_sha256={sha(http)}",
        "failed=0",
        "",
    ])
    for name in MARKERS:
        (REPORTS / name).write_text(content, encoding="utf-8")
    for name in ["P25_5_DASHBOARD_PRODUCTIZATION_FAIL.marker", "P25_5_DASHBOARD_PRODUCTIZATION_FAIL_REASON.md"]:
        path = REPORTS / name
        if path.exists():
            path.unlink()
    print("[p25_5_finalize] PASS: five current markers written")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
