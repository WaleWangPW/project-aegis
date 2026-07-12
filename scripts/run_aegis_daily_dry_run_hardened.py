#!/usr/bin/env python3
from __future__ import annotations

import json
import logging
import logging.handlers
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
CONFIG = REPO / "config/automation/aegis_daily_dry_run_schedule_v1.json"
REPORT = REPO / "data/reports/aegis_daily_dry_run_hardened_latest.json"
FAIL_REPORT = REPO / "data/reports/aegis_daily_dry_run_hardened_fail_reason.md"
PASS_MARKER = REPO / "data/reports/P24_2_HARDENED_DRY_RUN_PASS.marker"
FAIL_MARKER = REPO / "data/reports/P24_2_HARDENED_DRY_RUN_FAIL.marker"


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def setup_logger(cfg: dict[str, Any]) -> logging.Logger:
    log_path = REPO / cfg["log_file"]
    log_path.parent.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("aegis_daily_dry_run")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    handler = logging.handlers.RotatingFileHandler(
        log_path,
        maxBytes=int(cfg["log_max_bytes"]),
        backupCount=int(cfg["log_backup_count"]),
        encoding="utf-8",
    )
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    )
    logger.addHandler(handler)
    return logger


def acquire_lock(lock_path: Path, stale_seconds: int) -> dict[str, Any]:
    recovery = {
        "stale_lock_found": False,
        "stale_lock_removed": False,
    }

    if lock_path.exists():
        age = time.time() - lock_path.stat().st_mtime

        if age > stale_seconds:
            recovery["stale_lock_found"] = True
            lock_path.unlink()
            recovery["stale_lock_removed"] = True
        else:
            raise RuntimeError(
                f"active lock exists: {lock_path}; age_seconds={age:.1f}"
            )

    lock_payload = {
        "pid": os.getpid(),
        "created_at": now(),
    }
    write_json(lock_path, lock_payload)
    return recovery


def main() -> int:
    cfg = read_json(CONFIG)

    if cfg.get("enabled") is not False:
        raise RuntimeError("schedule must remain disabled")
    if cfg.get("dry_run") is not True:
        raise RuntimeError("dry_run must remain true")
    if cfg.get("cron_modified") is not False:
        raise RuntimeError("cron_modified must remain false")
    if cfg.get("launchd_modified") is not False:
        raise RuntimeError("launchd_modified must remain false")

    for marker in (PASS_MARKER, FAIL_MARKER):
        marker.unlink(missing_ok=True)
    FAIL_REPORT.unlink(missing_ok=True)

    logger = setup_logger(cfg)
    lock_path = REPO / cfg["lock_file"]
    pipeline_started = time.monotonic()
    recovery = acquire_lock(
        lock_path,
        int(cfg["lock_stale_seconds"]),
    )

    stages = []
    overall = "FAIL"
    failure_reason = None

    logger.info("P24.2 hardened dry-run started")

    try:
        for stage in cfg["stages"]:
            elapsed = time.monotonic() - pipeline_started
            if elapsed >= int(cfg["pipeline_timeout_seconds"]):
                failure_reason = "pipeline_timeout"
                break

            stage_started = time.monotonic()
            command = [str(x) for x in stage["command"]]
            timeout = int(
                stage.get(
                    "timeout_seconds",
                    cfg["stage_timeout_seconds"],
                )
            )

            logger.info(
                "stage_start name=%s command=%s timeout=%s",
                stage["name"],
                command,
                timeout,
            )

            try:
                result = subprocess.run(
                    command,
                    cwd=REPO,
                    text=True,
                    capture_output=True,
                    timeout=timeout,
                    check=False,
                )

                stage_result = {
                    "name": stage["name"],
                    "command": command,
                    "timeout_seconds": timeout,
                    "duration_seconds": round(
                        time.monotonic() - stage_started,
                        3,
                    ),
                    "exit_code": result.returncode,
                    "timed_out": False,
                    "result": (
                        "PASS" if result.returncode == 0 else "FAIL"
                    ),
                    "stdout_tail": result.stdout[-4000:],
                    "stderr_tail": result.stderr[-4000:],
                }

            except subprocess.TimeoutExpired as exc:
                stage_result = {
                    "name": stage["name"],
                    "command": command,
                    "timeout_seconds": timeout,
                    "duration_seconds": round(
                        time.monotonic() - stage_started,
                        3,
                    ),
                    "exit_code": None,
                    "timed_out": True,
                    "result": "FAIL",
                    "stdout_tail": (
                        exc.stdout[-4000:]
                        if isinstance(exc.stdout, str)
                        else ""
                    ),
                    "stderr_tail": (
                        exc.stderr[-4000:]
                        if isinstance(exc.stderr, str)
                        else ""
                    ),
                }

            stages.append(stage_result)
            logger.info(
                "stage_end name=%s result=%s exit_code=%s duration=%s",
                stage_result["name"],
                stage_result["result"],
                stage_result["exit_code"],
                stage_result["duration_seconds"],
            )

            if stage_result["result"] != "PASS":
                failure_reason = (
                    f"stage_failed:{stage_result['name']}"
                )
                break

        all_passed = (
            len(stages) == len(cfg["stages"])
            and all(item["result"] == "PASS" for item in stages)
        )

        overall = "PASS" if all_passed else "FAIL"

        report = {
            "project": "Project Aegis",
            "type": "aegis_daily_dry_run_hardened",
            "run_id": datetime.now(timezone.utc).strftime(
                "p24_2_%Y%m%dT%H%M%SZ"
            ),
            "generated_at": now(),
            "schedule_id": cfg["schedule_id"],
            "enabled": False,
            "dry_run": True,
            "cron_modified": False,
            "launchd_modified": False,
            "no_overlap": True,
            "lock_recovery": recovery,
            "pipeline_duration_seconds": round(
                time.monotonic() - pipeline_started,
                3,
            ),
            "stages": stages,
            "failure_reason": failure_reason,
            "lock_removed_on_exit": True,
            "overall_verdict": overall,
        }

        write_json(REPORT, report)

        if overall == "PASS":
            PASS_MARKER.write_text("PASS\n", encoding="utf-8")
            logger.info("P24.2 hardened dry-run PASS")
            return 0

        FAIL_MARKER.write_text("FAIL\n", encoding="utf-8")
        FAIL_REPORT.write_text(
            "# P24.2 Hardened Dry-run FAIL\n\n"
            f"- Failure reason: `{failure_reason}`\n"
            f"- Generated at: `{now()}`\n",
            encoding="utf-8",
        )
        logger.error(
            "P24.2 hardened dry-run FAIL reason=%s",
            failure_reason,
        )
        return 1

    finally:
        lock_path.unlink(missing_ok=True)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        FAIL_MARKER.write_text("FAIL\n", encoding="utf-8")
        FAIL_REPORT.write_text(
            "# P24.2 Hardened Dry-run FAIL\n\n"
            f"- Exception: `{type(exc).__name__}: {exc}`\n",
            encoding="utf-8",
        )
        print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
        raise SystemExit(1)
