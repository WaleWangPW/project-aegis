#!/usr/bin/env python3
"""Serve the Aegis Dashboard with a local intent-ingest endpoint.

This is a localhost-only helper for daily use. It serves the existing static
Dashboard and accepts POST /api/dashboard-intents from the browser. The POST
path reuses the same validated ingest bridge as the CLI, so it only records
simulation feedback evidence and never creates trades, mutates holdings, calls
brokers, places orders, or invokes trading webhooks.
"""
from __future__ import annotations

import argparse
import json
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

try:
    from scripts import ingest_dashboard_local_intents as ingest_bridge
except ModuleNotFoundError:  # pragma: no cover - direct CLI execution path
    import ingest_dashboard_local_intents as ingest_bridge


REPO = Path(__file__).resolve().parents[1]
MAX_BODY_BYTES = 64 * 1024


def process_payload(payload: Any, *, dry_run: bool = False) -> dict[str, Any]:
    intents = ingest_bridge.extract_intents(payload)
    report = ingest_bridge.ingest(intents, dry_run=dry_run)
    return {
        "status": report["status"],
        "intent_count": report["intent_count"],
        "event_count": report["event_count"],
        "latest_feedback": report["latest_feedback"],
        "event_log": report["event_log"],
        "safety": report["safety"],
    }


class AegisDashboardHandler(SimpleHTTPRequestHandler):
    server_version = "AegisDashboardIntentBridge/1.0"

    def __init__(self, *args: Any, directory: str | None = None, **kwargs: Any) -> None:
        super().__init__(*args, directory=directory or str(REPO), **kwargs)

    def _write_json(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status.value)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802 - stdlib API
        if self.path == "/api/dashboard-intents/health":
            self._write_json(
                HTTPStatus.OK,
                {
                    "status": "READY",
                    "service": "aegis_dashboard_intent_bridge",
                    "safety": {
                        "simulation_only": True,
                        "no_broker_api": True,
                        "no_order_placement": True,
                        "no_trading_webhook": True,
                    },
                },
            )
            return
        super().do_GET()

    def do_POST(self) -> None:  # noqa: N802 - stdlib API
        if self.path != "/api/dashboard-intents":
            self._write_json(HTTPStatus.NOT_FOUND, {"status": "ERROR", "error": "unknown endpoint"})
            return
        length = int(self.headers.get("Content-Length") or "0")
        if length <= 0 or length > MAX_BODY_BYTES:
            self._write_json(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, {"status": "ERROR", "error": "invalid body size"})
            return
        try:
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            report = process_payload(payload)
        except Exception as exc:
            self._write_json(HTTPStatus.BAD_REQUEST, {"status": "ERROR", "error": str(exc)})
            return
        self._write_json(HTTPStatus.OK, report)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args()
    server = ThreadingHTTPServer((args.host, args.port), AegisDashboardHandler)
    print(f"Serving Project Aegis Dashboard on http://{args.host}:{args.port}/dashboard/index.html")
    print("Intent endpoint: POST /api/dashboard-intents")
    print("Safety: simulation-only, no broker, no order, no trading webhook")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping Project Aegis Dashboard intent bridge")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
