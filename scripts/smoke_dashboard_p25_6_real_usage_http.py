#!/usr/bin/env python3
"""HTTP resource acceptance for the production P25.6 dashboard."""
from __future__ import annotations

import json
import re
from urllib.request import urlopen
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/reports/dashboard_p25_6_http_smoke_latest.json"
BASE = "http://localhost:8080"


def get(path: str) -> tuple[int, bytes]:
    with urlopen(f"{BASE}{path}", timeout=10) as response:
        return response.status, response.read()


def main() -> int:
    checks: dict[str, object] = {}
    try:
        page_status, page = get("/dashboard/index.html")
        css_status, _ = get("/dashboard/v2.css")
        js_status, js = get("/dashboard/v2.js")
        page_text, js_text = page.decode("utf-8"), js.decode("utf-8")
        sources = sorted(set(re.findall(r"'([^']+_latest\\.json)'", js_text)))
        report_statuses = {}
        for source in sources:
            status, body = get(f"/data/reports/{source}")
            json.loads(body.decode("utf-8"))
            report_statuses[source] = status
        checks = {
            "index_http_200": page_status == 200,
            "css_http_200": css_status == 200,
            "js_http_200": js_status == 200,
            "contract_meta": 'aegis-dashboard-contract" content="2.0"' in page_text,
            "correct_assets": 'href="v2.css"' in page_text and 'src="v2.js"' in page_text,
            "no_bad_report_path": "/dashboard/data/reports/" not in page_text + js_text,
            "all_real_report_fetches_http_200": all(status == 200 for status in report_statuses.values()),
            "report_statuses": report_statuses,
        }
    except Exception as error:
        checks = {"http_error": str(error)}
    passed = all(value is True for key, value in checks.items() if key != "report_statuses")
    payload = {
        "project": "Project Aegis",
        "type": "p25_6_real_usage_http_smoke",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "tested_url": f"{BASE}/dashboard/index.html",
        "overall_verdict": "PASS" if passed else "FAIL",
        "checks": checks,
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[p25_6_http] {payload['overall_verdict']} -> {OUT}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
