#!/usr/bin/env python3
"""Listen for Feishu stock-assistant card callbacks and record Aegis feedback.

This service is intentionally narrow:
- it uses the OpenClaw Feishu ``stock`` account only;
- it only handles Project Aegis button values;
- it forwards to ``handle_aegis_stock_card_action.py``;
- it never places orders, calls brokers, mutates holdings, or invokes trading webhooks.

Secrets are read from local OpenClaw secret references at runtime and are never
printed or written to Aegis artifacts.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[1]
HANDLER = REPO / "scripts" / "handle_aegis_stock_card_action.py"
REPORTS = REPO / "data" / "reports"
RUNTIME_DIR = REPO / "data" / "runtime"
LOG_PATH = RUNTIME_DIR / "aegis_stock_feishu_callback_server.log"
HEALTH_PATH = REPORTS / "aegis_stock_feishu_callback_server_latest.json"
OPENCLAW_HOME = Path.home() / ".openclaw"
OPENCLAW_CONFIG = OPENCLAW_HOME / "openclaw.json"
OPENCLAW_SECRETREFS = OPENCLAW_HOME / "secrets" / "openclaw-secretrefs.json"


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).astimezone().isoformat()


def _log(message: str) -> None:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    line = f"[{_now()}] {message}"
    with LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")
    print(line, flush=True)


def _load_stock_credentials() -> tuple[str, str]:
    config = json.loads(OPENCLAW_CONFIG.read_text(encoding="utf-8"))
    secretrefs = json.loads(OPENCLAW_SECRETREFS.read_text(encoding="utf-8"))
    account = config["channels"]["feishu"]["accounts"]["stock"]
    app_id = account["appId"]
    app_secret = secretrefs["openclaw_json"]["channels"]["feishu"]["accounts"]["stock"]["appSecret"]
    if not app_id or not app_secret:
        raise RuntimeError("stock Feishu account is missing app id or app secret")
    return app_id, app_secret


def _is_aegis_value(value: dict[str, Any]) -> bool:
    action = str(value.get("action") or "")
    return value.get("system") == "project_aegis" or action.startswith("aegis_")


def _extract_value(data: Any) -> dict[str, Any]:
    if hasattr(data, "event") and getattr(data, "event"):
        action = getattr(data.event, "action", None)
        value = getattr(action, "value", {}) if action else {}
    elif hasattr(data, "action"):
        value = getattr(data.action, "value", {}) or {}
    else:
        value = {}
    return value if isinstance(value, dict) else {}


def record_aegis_value(value: dict[str, Any]) -> tuple[bool, str]:
    if not _is_aegis_value(value):
        return False, "ignored_non_aegis_card_action"
    py = REPO / ".venv" / "bin" / "python3"
    cmd = [str(py if py.exists() else Path(sys.executable)), str(HANDLER), json.dumps(value, ensure_ascii=False)]
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=REPO,
            timeout=30,
        )
    except Exception as exc:  # pragma: no cover - defensive runtime guard
        return False, f"Aegis recorder exception: {type(exc).__name__}"

    output = (result.stdout or result.stderr or "").strip()
    if result.returncode != 0:
        return False, output or f"Aegis recorder exit={result.returncode}"
    if "status=RECORDED" in output:
        symbol = value.get("symbol") or value.get("code") or "Aegis"
        action = value.get("action") or "feedback"
        return True, f"Aegis recorded {symbol} {action}; simulation-only, no order"
    return False, output or "Aegis recorder returned unknown status"


def write_health(status: str, details: dict[str, Any]) -> None:
    REPORTS.mkdir(parents=True, exist_ok=True)
    payload = {
        "type": "aegis_stock_feishu_callback_server",
        "generated_at": _now(),
        "status": status,
        "account": "stock",
        "handler": str(HANDLER),
        "log_path": str(LOG_PATH),
        "details": details,
        "safety": {
            "simulation_only": True,
            "no_broker_api": True,
            "no_order_placement": True,
            "no_trading_webhook": True,
            "no_secret_values_recorded": True,
        },
    }
    HEALTH_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def handle_card_action(data: Any) -> dict[str, Any]:
    value = _extract_value(data)
    action = str(value.get("action") or "")
    if not _is_aegis_value(value):
        _log(f"ignored non-Aegis card action action={action}")
        return {}
    ok, message = record_aegis_value(value)
    _log(f"Aegis card feedback ok={ok} action={action} symbol={value.get('symbol') or value.get('code') or ''}")
    write_health("RECORDED" if ok else "ERROR", {"last_action": action, "last_ok": ok})
    return {"toast": {"type": "success" if ok else "error", "content": message}}


def run_server() -> int:
    try:
        import lark_oapi as lark
    except ImportError:
        _log("missing dependency: lark_oapi")
        write_health("ERROR", {"reason": "missing_lark_oapi"})
        return 1

    app_id, app_secret = _load_stock_credentials()
    _log(f"starting stock Feishu callback server app_id={app_id} account=stock")
    write_health("STARTING", {"app_id": app_id})
    dispatcher = (
        lark.EventDispatcherHandler.builder("", "")
        .register_p2_card_action_trigger(handle_card_action)
        .build()
    )
    client = lark.ws.Client(
        app_id,
        app_secret,
        event_handler=dispatcher,
        log_level=lark.LogLevel.INFO,
    )
    write_health("RUNNING", {"app_id": app_id})
    client.start()
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", help="Record one card value JSON and exit")
    parser.add_argument("--health-check", action="store_true", help="Validate local config without connecting")
    args = parser.parse_args(argv)

    if args.once:
        value = json.loads(args.once)
        ok, message = record_aegis_value(value)
        write_health("RECORDED" if ok else "ERROR", {"once": True, "ok": ok})
        print(message)
        return 0 if ok else 1

    if args.health_check:
        app_id, _ = _load_stock_credentials()
        write_health("READY", {"app_id": app_id, "handler_exists": HANDLER.exists()})
        print(f"status=READY app_id={app_id} handler_exists={HANDLER.exists()}")
        return 0 if HANDLER.exists() else 1

    return run_server()


if __name__ == "__main__":
    raise SystemExit(main())
