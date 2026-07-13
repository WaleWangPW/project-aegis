#!/usr/bin/env python3
"""Manage the local Project Aegis Dashboard intent bridge.

This helper is intentionally local-only. It starts/stops the existing
Dashboard server that records browser button clicks as simulation feedback
evidence. It never reads secrets, never connects to brokers, never places
orders, and never calls trading webhooks.
"""
from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[1]
RUNTIME = REPO / "data" / "runtime"
PID_FILE = RUNTIME / "aegis_dashboard_intent_bridge.pid"
LOG_FILE = RUNTIME / "aegis_dashboard_intent_bridge.log"
SERVER_SCRIPT = REPO / "scripts" / "run_aegis_dashboard_intent_bridge_server.py"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8080
START_TIMEOUT_SECONDS = 8.0
STOP_TIMEOUT_SECONDS = 5.0


def dashboard_url(host: str, port: int) -> str:
    return f"http://{host}:{port}/dashboard/index.html"


def health_url(host: str, port: int) -> str:
    return f"http://{host}:{port}/api/dashboard-intents/health"


def read_pid(pid_file: Path = PID_FILE) -> int | None:
    try:
        text = pid_file.read_text(encoding="utf-8").strip()
        return int(text) if text else None
    except (FileNotFoundError, ValueError):
        return None


def process_alive(pid: int | None) -> bool:
    if not pid or pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def probe_health(host: str, port: int, *, timeout: float = 1.0) -> dict[str, Any] | None:
    try:
        with urllib.request.urlopen(health_url(host, port), timeout=timeout) as response:
            if response.status != 200:
                return None
            return json.loads(response.read().decode("utf-8"))
    except (OSError, urllib.error.URLError, json.JSONDecodeError):
        return None


def current_status(host: str, port: int, *, pid_file: Path = PID_FILE) -> dict[str, Any]:
    pid = read_pid(pid_file)
    alive = process_alive(pid)
    health = probe_health(host, port)
    if health and alive:
        status = "RUNNING"
    elif health:
        status = "RUNNING_UNMANAGED"
    elif alive:
        status = "STALE_OR_STARTING"
    else:
        status = "STOPPED"
        if pid_file.exists():
            pid_file.unlink()
    return {
        "status": status,
        "pid": pid,
        "pid_alive": alive,
        "health_ready": health is not None,
        "dashboard_url": dashboard_url(host, port),
        "health_url": health_url(host, port),
        "pid_file": str(pid_file),
        "log_file": str(LOG_FILE),
        "safety": {
            "simulation_only": True,
            "no_broker_api": True,
            "no_order_placement": True,
            "no_trading_webhook": True,
        },
    }


def wait_for_ready(host: str, port: int, deadline_seconds: float) -> bool:
    deadline = time.monotonic() + deadline_seconds
    while time.monotonic() < deadline:
        if probe_health(host, port, timeout=0.5):
            return True
        time.sleep(0.2)
    return False


def python_executable() -> str:
    venv_python = REPO / ".venv" / "bin" / "python"
    if venv_python.exists():
        return str(venv_python)
    return sys.executable


def start_bridge(host: str, port: int, *, pid_file: Path = PID_FILE, log_file: Path = LOG_FILE) -> dict[str, Any]:
    status = current_status(host, port, pid_file=pid_file)
    if status["health_ready"]:
        status["message"] = "Dashboard intent bridge is already serving."
        return status

    RUNTIME.mkdir(parents=True, exist_ok=True)
    log_file.parent.mkdir(parents=True, exist_ok=True)
    log_handle = log_file.open("ab")
    process = subprocess.Popen(
        [
            python_executable(),
            str(SERVER_SCRIPT),
            "--host",
            host,
            "--port",
            str(port),
        ],
        cwd=REPO,
        stdout=log_handle,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    pid_file.write_text(f"{process.pid}\n", encoding="utf-8")

    ready = wait_for_ready(host, port, START_TIMEOUT_SECONDS)
    status = current_status(host, port, pid_file=pid_file)
    status["started_pid"] = process.pid
    status["message"] = "Dashboard intent bridge started." if ready else "Dashboard intent bridge started but is not ready yet."
    return status


def stop_bridge(host: str, port: int, *, pid_file: Path = PID_FILE) -> dict[str, Any]:
    pid = read_pid(pid_file)
    if not process_alive(pid):
        if pid_file.exists():
            pid_file.unlink()
        status = current_status(host, port, pid_file=pid_file)
        status["message"] = "Dashboard intent bridge was not running."
        return status

    assert pid is not None
    os.kill(pid, signal.SIGTERM)
    deadline = time.monotonic() + STOP_TIMEOUT_SECONDS
    while time.monotonic() < deadline and process_alive(pid):
        time.sleep(0.2)
    if process_alive(pid):
        os.kill(pid, signal.SIGKILL)
    if pid_file.exists():
        pid_file.unlink()

    status = current_status(host, port, pid_file=pid_file)
    status["stopped_pid"] = pid
    status["message"] = "Dashboard intent bridge stopped."
    return status


def open_dashboard(host: str, port: int) -> dict[str, Any]:
    status = start_bridge(host, port)
    url = dashboard_url(host, port)
    if sys.platform == "darwin":
        subprocess.run(["open", url], check=False)
        status["message"] = f"Dashboard opened: {url}"
    else:
        status["message"] = f"Dashboard ready: {url}"
    return status


def print_status(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["start", "stop", "status", "open"])
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    args = parser.parse_args()

    if args.command == "start":
        print_status(start_bridge(args.host, args.port))
    elif args.command == "stop":
        print_status(stop_bridge(args.host, args.port))
    elif args.command == "status":
        print_status(current_status(args.host, args.port))
    elif args.command == "open":
        print_status(open_dashboard(args.host, args.port))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
