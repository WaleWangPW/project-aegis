#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CONFIG = REPO / "config/automation/aegis_daily_dry_run_schedule_v1.json"
LOCK = REPO / "data/reports/aegis_daily_dry_run.lock"
REPORT = REPO / "data/reports/p24_2_guard_tests_latest.json"


def run() -> int:
    original = json.loads(CONFIG.read_text(encoding="utf-8"))
    checks = {}

    try:
        LOCK.write_text("active\n", encoding="utf-8")
        result = subprocess.run(
            [sys.executable, "scripts/run_aegis_daily_dry_run_hardened.py"],
            cwd=REPO,
            capture_output=True,
            text=True,
        )
        checks["active_lock_rejected"] = result.returncode != 0
        LOCK.unlink(missing_ok=True)

        LOCK.write_text("stale\n", encoding="utf-8")
        stale = time.time() - int(original["lock_stale_seconds"]) - 60
        os.utime(LOCK, (stale, stale))

        test_cfg = dict(original)
        test_cfg["stages"] = [
            {
                "name": "stale_lock_probe",
                "command": [
                    sys.executable,
                    "-c",
                    "print('stale lock recovered')",
                ],
                "timeout_seconds": 30,
            }
        ]
        CONFIG.write_text(
            json.dumps(test_cfg, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

        result = subprocess.run(
            [sys.executable, "scripts/run_aegis_daily_dry_run_hardened.py"],
            cwd=REPO,
            capture_output=True,
            text=True,
        )
        checks["stale_lock_recovered"] = result.returncode == 0
        LOCK.unlink(missing_ok=True)

        timeout_cfg = dict(original)
        timeout_cfg["stages"] = [
            {
                "name": "timeout_probe",
                "command": [
                    sys.executable,
                    "-c",
                    "import time; time.sleep(3)",
                ],
                "timeout_seconds": 1,
            }
        ]
        CONFIG.write_text(
            json.dumps(timeout_cfg, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

        result = subprocess.run(
            [sys.executable, "scripts/run_aegis_daily_dry_run_hardened.py"],
            cwd=REPO,
            capture_output=True,
            text=True,
        )

        timeout_report = json.loads(
            (
                REPO
                / "data/reports/aegis_daily_dry_run_hardened_latest.json"
            ).read_text(encoding="utf-8")
        )

        checks["timeout_rejected"] = (
            result.returncode != 0
            and timeout_report["stages"][0]["timed_out"] is True
        )
        checks["lock_removed_after_timeout"] = not LOCK.exists()

    finally:
        CONFIG.write_text(
            json.dumps(original, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        LOCK.unlink(missing_ok=True)

    passed = all(checks.values())

    payload = {
        "project": "Project Aegis",
        "type": "p24_2_guard_tests",
        "checks": checks,
        "overall_verdict": "PASS" if passed else "FAIL",
    }
    REPORT.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(run())
