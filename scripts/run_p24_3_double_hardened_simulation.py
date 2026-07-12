#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
RUNNER = REPO / "scripts/run_aegis_daily_dry_run_hardened.py"
LATEST = REPO / "data/reports/aegis_daily_dry_run_hardened_latest.json"
OUTPUT = REPO / "data/reports/p24_3_double_hardened_simulation_latest.json"
PASS = REPO / "data/reports/P24_3_DOUBLE_HARDENED_SIMULATION_PASS.marker"
FAIL = REPO / "data/reports/P24_3_DOUBLE_HARDENED_SIMULATION_FAIL.marker"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    PASS.unlink(missing_ok=True)
    FAIL.unlink(missing_ok=True)

    rounds = []

    for number in (1, 2):
        result = subprocess.run(
            [sys.executable, str(RUNNER)],
            cwd=REPO,
            capture_output=True,
            text=True,
        )

        report = (
            json.loads(LATEST.read_text(encoding="utf-8"))
            if LATEST.exists()
            else {}
        )

        rounds.append(
            {
                "round": number,
                "exit_code": result.returncode,
                "overall_verdict": report.get("overall_verdict"),
                "stages": [
                    {
                        "name": item.get("name"),
                        "result": item.get("result"),
                        "exit_code": item.get("exit_code"),
                    }
                    for item in report.get("stages", [])
                ],
                "report_sha256": (
                    sha256(LATEST) if LATEST.exists() else None
                ),
                "lock_removed": not (
                    REPO / "data/reports/aegis_daily_dry_run.lock"
                ).exists(),
            }
        )

        if result.returncode != 0:
            break

    passed = (
        len(rounds) == 2
        and all(item["exit_code"] == 0 for item in rounds)
        and all(
            item["overall_verdict"] == "PASS"
            for item in rounds
        )
        and all(item["lock_removed"] for item in rounds)
    )

    payload = {
        "project": "Project Aegis",
        "type": "p24_3_double_hardened_simulation",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "rounds": rounds,
        "enabled": False,
        "dry_run": True,
        "cron_modified": False,
        "launchd_modified": False,
        "overall_verdict": "PASS" if passed else "FAIL",
    }

    OUTPUT.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    (PASS if passed else FAIL).write_text(
        f"{payload['overall_verdict']}\n",
        encoding="utf-8",
    )

    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
