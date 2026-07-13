#!/usr/bin/env python3
"""Run the A-share current-day retry only after the readiness gate is READY.

The guard never reads or prints secret values. It first refreshes the read-only
preflight report. If the preflight is WAITING/BLOCKED/NOT_NEEDED, it records a
guard report and exits without running the retry chain. If the preflight is
READY, it runs the approved `make a-share-current-day-retry` chain, then
refreshes the daily-use audit.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "data" / "reports"
RUNTIME = ROOT / "data" / "runtime"
READINESS = REPORTS / "a_share_current_day_retry_readiness_latest.json"
OUT_JSON = REPORTS / "a_share_current_day_retry_guarded_latest.json"
OUT_MD = REPORTS / "a_share_current_day_retry_guarded_latest.md"
LOG_FILE = RUNTIME / "a_share_current_day_retry_guarded.log"
MARKET_CACHE_MANIFEST = REPORTS / "p23_2_historical_market_cache_manifest.json"


def now_local() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc).astimezone()


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def run_logged(command: list[str]) -> int:
    RUNTIME.mkdir(parents=True, exist_ok=True)
    with LOG_FILE.open("a", encoding="utf-8") as handle:
        handle.write(f"\n[{now_local().isoformat(timespec='seconds')}] $ {' '.join(command)}\n")
        handle.flush()
        completed = subprocess.run(command, cwd=ROOT, stdout=handle, stderr=subprocess.STDOUT, check=False)
        handle.write(f"[exit_code={completed.returncode}]\n")
    return completed.returncode


def refresh_readiness() -> tuple[int, dict[str, Any] | None]:
    exit_code = run_logged(["make", "build-a-share-current-day-retry-readiness"])
    return exit_code, read_json(READINESS)


def build_report(
    *,
    status: str,
    readiness: dict[str, Any] | None,
    preflight_exit_code: int | None,
    retry_exit_code: int | None,
    audit_exit_code: int | None,
    started_at: str,
    finished_at: str,
    wait_mode: bool,
) -> dict[str, Any]:
    manifest = read_json(MARKET_CACHE_MANIFEST)
    failed_dates = (((manifest or {}).get("daily_cache") or {}).get("failed_dates")) or []
    return {
        "type": "a_share_current_day_retry_guarded",
        "status": status,
        "started_at": started_at,
        "finished_at": finished_at,
        "wait_mode": wait_mode,
        "preflight_status": (readiness or {}).get("status"),
        "preflight_ready_to_run": (readiness or {}).get("ready_to_run"),
        "preflight_exit_code": preflight_exit_code,
        "retry_exit_code": retry_exit_code,
        "audit_exit_code": audit_exit_code,
        "recommended_command": (readiness or {}).get("recommended_command"),
        "blockers": (readiness or {}).get("blockers") or [],
        "retry_failure": {
            "failed_dates": failed_dates,
            "manifest_path": str(MARKET_CACHE_MANIFEST) if manifest else None,
        }
        if retry_exit_code not in {None, 0}
        else None,
        "log_file": str(LOG_FILE),
        "safety": {
            "simulation_only": True,
            "preflight_required": True,
            "no_secret_values_printed": True,
            "no_broker_api": True,
            "no_order_placement": True,
            "no_trading_webhook": True,
        },
    }


def render_markdown(report: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# A-share Current-Day Retry Guarded Runner",
            "",
            f"- status: `{report['status']}`",
            f"- preflight_status: `{report.get('preflight_status')}`",
            f"- preflight_ready_to_run: `{report.get('preflight_ready_to_run')}`",
            f"- retry_exit_code: `{report.get('retry_exit_code')}`",
            f"- blockers: `{', '.join(report.get('blockers') or []) or 'none'}`",
            f"- log_file: `{report.get('log_file')}`",
            "",
            "## Safety",
            "",
            "- Runs the retry chain only after the preflight is READY.",
            "- Does not print secret values, connect to brokers, place orders, or call trading webhooks.",
            "",
        ]
    )


def write_report(report: dict[str, Any]) -> None:
    write_json(OUT_JSON, report)
    OUT_MD.write_text(render_markdown(report), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--wait", action="store_true", help="Poll until READY or timeout.")
    parser.add_argument("--poll-seconds", type=int, default=60)
    parser.add_argument("--max-wait-seconds", type=int, default=7200)
    args = parser.parse_args()

    started_at = now_local().isoformat(timespec="seconds")
    deadline = time.monotonic() + max(0, args.max_wait_seconds)
    preflight_exit_code: int | None = None
    readiness: dict[str, Any] | None = None

    while True:
        preflight_exit_code, readiness = refresh_readiness()
        preflight_status = (readiness or {}).get("status")
        if preflight_status == "READY" or not args.wait or time.monotonic() >= deadline:
            break
        if preflight_status not in {"WAITING"}:
            break
        time.sleep(max(5, args.poll_seconds))

    retry_exit_code: int | None = None
    audit_exit_code: int | None = None
    preflight_status = (readiness or {}).get("status")
    if preflight_status == "READY" and (readiness or {}).get("ready_to_run") is True:
        retry_exit_code = run_logged(["make", "a-share-current-day-retry"])
        audit_exit_code = run_logged(["make", "dashboard-daily-use-check"])
        status = "PASS" if retry_exit_code == 0 and audit_exit_code == 0 else "FAIL"
    elif preflight_status == "WAITING":
        status = "WAITING"
    elif preflight_status == "NOT_NEEDED":
        audit_exit_code = run_logged(["make", "dashboard-daily-use-check"])
        status = "NOT_NEEDED"
    else:
        status = "BLOCKED"

    report = build_report(
        status=status,
        readiness=readiness,
        preflight_exit_code=preflight_exit_code,
        retry_exit_code=retry_exit_code,
        audit_exit_code=audit_exit_code,
        started_at=started_at,
        finished_at=now_local().isoformat(timespec="seconds"),
        wait_mode=args.wait,
    )
    write_report(report)
    if report["status"] == "PASS":
        final_audit_exit_code = run_logged(["make", "build-aegis-goal-completion-audit"])
        report["final_audit_exit_code"] = final_audit_exit_code
        write_report(report)
    print(f"status={report['status']}")
    print(f"preflight_status={report.get('preflight_status')}")
    print(f"retry_exit_code={report.get('retry_exit_code')}")
    print(f"out_json={OUT_JSON}")
    return 0 if report["status"] in {"PASS", "WAITING", "NOT_NEEDED"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
