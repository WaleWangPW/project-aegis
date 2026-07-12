#!/usr/bin/env python3
"""Create P25.4b markers only from current successful reports and files."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "data" / "reports"


def load(name: str) -> dict:
    return json.loads((REPORTS / name).read_text(encoding="utf-8"))


def main() -> int:
    index = ROOT / "dashboard" / "index.html"
    html = index.read_text(encoding="utf-8")
    gate = load("aegis_evidence_gate_latest.json")
    smoke = load("dashboard_v2_production_http_smoke_latest.json")
    tests = load("dashboard_contract_v2_tests_latest.json")
    contract = load("dashboard_contract_validation_latest.json")
    p22 = (REPORTS / "P22_6_FULL_PIPELINE_PASS.marker").exists()
    okay = all((
        '<meta name="aegis-dashboard-contract" content="2.0">' in html,
        gate.get("overall_verdict") == "PASS",
        smoke.get("overall_verdict") == "PASS" and smoke.get("page") == "index",
        tests.get("overall_verdict") == "PASS",
        contract.get("overall_verdict") == "PASS",
        contract.get("detected_dashboard_type") == "ceo_daily_brief_v2",
        p22,
    ))
    if not okay:
        print("[dashboard_contract_finalize] FAIL")
        return 1
    now = datetime.now(timezone.utc).isoformat()
    sha = hashlib.sha256(index.read_bytes()).hexdigest()
    def digest(path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    content = f"generated_at={now}\ncommand=scripts/finalize_dashboard_contract_v2.py\nexit_code=0\ncontract=2.0\nindex_sha256={sha}\ncontract_validator_sha256={digest(ROOT / 'scripts' / 'dashboard_contract.py')}\ncontract_test_report_sha256={digest(REPORTS / 'dashboard_contract_v2_tests_latest.json')}\nevidence_gate_report_sha256={digest(REPORTS / 'aegis_evidence_gate_latest.json')}\nhttp_smoke_report_sha256={digest(REPORTS / 'dashboard_v2_production_http_smoke_latest.json')}\nlegacy_backup_sha256={digest(ROOT / 'dashboard' / 'backups' / 'index_pre_p25_4b_20260711T125736.html')}\nv2_js_sha256={digest(ROOT / 'dashboard' / 'v2.js')}\nv2_css_sha256={digest(ROOT / 'dashboard' / 'v2.css')}\ntest_count={tests.get('test_count')}\nfailed={tests.get('failed')}\ngate_report=data/reports/aegis_evidence_gate_latest.json\n"
    markers = [
        "P25_4B_DASHBOARD_CONTRACT_V2_PASS.marker",
        "P25_4B_DASHBOARD_CONTRACT_TEST_PASS.marker",
        "P25_4B_DASHBOARD_PRODUCTION_PASS.marker",
        "P25_4B_EVIDENCE_GATE_COMPAT_PASS.marker",
        "P25_4B_HTTP_PASS.marker",
    ]
    for name in markers:
        (REPORTS / name).write_text(content, encoding="utf-8")
    for name in ("P25_4_DASHBOARD_PRODUCTION_FAIL.marker", "P25_4_DASHBOARD_PRODUCTION_FAIL_REASON.md", "P25_4B_DASHBOARD_PRODUCTION_FAIL.marker", "P25_4B_DASHBOARD_PRODUCTION_FAIL_REASON.md"):
        path = REPORTS / name
        if path.exists():
            path.unlink()
    print("[dashboard_contract_finalize] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
