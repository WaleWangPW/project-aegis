#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CONFIG = REPO / "config/automation/aegis_daily_dry_run_schedule_v1.json"
REPORT = REPO / "data/reports/aegis_daily_dry_run_schedule_simulation_latest.json"
LOCK = REPO / "data/reports/aegis_daily_dry_run.lock"


def main() -> int:
    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))

    if cfg.get("enabled") is not False:
        raise RuntimeError("schedule must remain disabled")
    if cfg.get("dry_run") is not True:
        raise RuntimeError("dry_run must be true")
    if LOCK.exists():
        raise RuntimeError("lock file already exists")

    LOCK.write_text(str(datetime.now(timezone.utc)), encoding="utf-8")
    stages = []

    try:
        for stage in cfg["stages"]:
            result = subprocess.run(
                stage["command"],
                cwd=REPO,
                text=True,
                capture_output=True,
            )

            stages.append({
                "name": stage["name"],
                "command": stage["command"],
                "exit_code": result.returncode,
                "result": "PASS" if result.returncode == 0 else "FAIL",
                "stdout_tail": result.stdout[-2000:],
                "stderr_tail": result.stderr[-2000:]
            })

            if result.returncode != 0:
                break

        passed = len(stages) == len(cfg["stages"]) and all(
            item["exit_code"] == 0 for item in stages
        )

        report = {
            "project": "Project Aegis",
            "type": "daily_dry_run_schedule_simulation",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "schedule_id": cfg["schedule_id"],
            "enabled": False,
            "dry_run": True,
            "cron_modified": False,
            "launchd_modified": False,
            "stages": stages,
            "overall_verdict": "PASS" if passed else "FAIL"
        }

        REPORT.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8"
        )

        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if passed else 1

    finally:
        LOCK.unlink(missing_ok=True)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
        raise SystemExit(1)
