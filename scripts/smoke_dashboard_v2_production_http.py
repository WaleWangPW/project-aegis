#!/usr/bin/env python3
"""HTTP resource acceptance for the Dashboard V2 production surface."""
from __future__ import annotations

import argparse
import json
import re
import socket
import threading
from datetime import datetime, timezone
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "data" / "reports" / "dashboard_v2_production_http_smoke_latest.json"


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def log_message(self, format, *args):
        return


def fetch(port: int, route: str) -> dict:
    try:
        with urlopen(f"http://127.0.0.1:{port}{route}", timeout=5) as response:
            body = response.read()
            return {"route": route, "status": response.status, "passed": response.status == 200, "bytes": len(body)}
    except Exception as exc:
        return {"route": route, "status": None, "passed": False, "error": str(exc)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--page", choices=("v2", "index"), default="v2")
    args = parser.parse_args()
    js = (ROOT / "dashboard" / "v2.js").read_text(encoding="utf-8")
    html = (ROOT / "dashboard" / f"{args.page}.html").read_text(encoding="utf-8")
    json_names = sorted(set(re.findall(r"'([^']+\\.json)'", js)))
    routes = [f"/dashboard/{args.page}.html", "/dashboard/v2.css", "/dashboard/v2.js"]
    routes.extend(f"/data/reports/{name}" for name in json_names if (ROOT / "data" / "reports" / name).is_file())
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        checks = [fetch(port, route) for route in routes]
    finally:
        server.shutdown()
        server.server_close()
    checks.extend([
        {"name": "html_references_css", "passed": 'href="v2.css"' in html},
        {"name": "html_references_js", "passed": 'src="v2.js"' in html},
        {"name": "fetches_reports_relative", "passed": "reportBase = '../data/reports/'" in js},
        {"name": "no_dashboard_reports_path", "passed": "/dashboard/data/reports/" not in js and "/dashboard/data/reports/" not in html},
        {"name": "json_parseable", "passed": all(json.loads((ROOT / "data" / "reports" / name).read_text(encoding="utf-8")) is not None for name in json_names if (ROOT / "data" / "reports" / name).is_file())},
    ])
    passed = all(item["passed"] for item in checks)
    payload = {"project": "Project Aegis", "type": "dashboard_v2_production_http_smoke", "generated_at": datetime.now(timezone.utc).isoformat(), "page": args.page, "overall_verdict": "PASS" if passed else "FAIL", "checks": checks}
    REPORT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[dashboard_http] {payload['overall_verdict']} → {REPORT}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
