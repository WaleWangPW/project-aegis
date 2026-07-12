#!/usr/bin/env python3
"""Serve the repository briefly and verify Dashboard V2 assets and report routes."""
from __future__ import annotations

import json
import socket
import threading
from datetime import datetime, timezone
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "reports" / "dashboard_v2_real_http_smoke_latest.json"
ROUTES = ["/dashboard/v2.html", "/dashboard/v2.css", "/dashboard/v2.js", "/data/reports/aegis_health_status_latest.json", "/data/reports/aegis_evidence_gate_latest.json", "/data/reports/a_share_watchlist_latest.json", "/data/reports/a_share_point_in_time_rolling_backtest_latest.json"]


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)
    def log_message(self, format, *args):
        return


def main() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0)); port = probe.getsockname()[1]
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
    checks = []
    try:
        for route in ROUTES:
            try:
                with urlopen(f"http://127.0.0.1:{port}{route}", timeout=5) as response:
                    checks.append({"route":route, "status":response.status, "passed":response.status == 200})
            except Exception as exc:
                checks.append({"route":route, "status":None, "passed":False, "error":str(exc)})
        js = (ROOT / "dashboard" / "v2.js").read_text(encoding="utf-8")
        checks.append({"route":"client_request_path", "status":None, "passed":"/dashboard/data/reports/" not in js})
    finally:
        server.shutdown(); server.server_close()
    passed = all(row["passed"] for row in checks)
    payload = {"project":"Project Aegis", "type":"dashboard_v2_real_http_smoke", "generated_at":datetime.now(timezone.utc).isoformat(), "port":port, "overall_verdict":"PASS" if passed else "FAIL", "checks":checks}
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[dashboard_v2_http_smoke] {payload['overall_verdict']} → {OUT}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
