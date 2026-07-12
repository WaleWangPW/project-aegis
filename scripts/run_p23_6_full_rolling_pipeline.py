#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
REPORTS = REPO / "data/reports"

PASS_MARKER = REPORTS / "P23_6_FULL_ROLLING_PIPELINE_PASS.marker"
FAIL_MARKER = REPORTS / "P23_6_FULL_ROLLING_PIPELINE_FAIL.marker"
FAIL_REASON = REPORTS / "P23_6_FULL_ROLLING_PIPELINE_FAIL_REASON.md"
EVIDENCE = REPORTS / "p23_6_full_rolling_pipeline_evidence.json"


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def run_stage(name: str, command: list[str]) -> dict[str, Any]:
    print(f"[P23.6] {name}: {' '.join(command)}")

    result = subprocess.run(
        command,
        cwd=REPO,
        text=True,
        capture_output=True,
    )

    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)

    return {
        "name": name,
        "command": command,
        "exit_code": result.returncode,
        "result": "PASS" if result.returncode == 0 else "FAIL",
        "stdout_tail": result.stdout[-3000:],
        "stderr_tail": result.stderr[-3000:],
    }


def main() -> int:
    for path in (PASS_MARKER, FAIL_MARKER, FAIL_REASON):
        if path.exists():
            path.unlink()

    stages = [
        (
            "validate_p23_1_design",
            ["make", "validate-p23-1-rolling-backtest-design"],
        ),
        (
            "validate_signal_snapshots",
            ["make", "validate-a-share-signal-snapshots"],
        ),
        (
            "trade_calendar_audit",
            [
                sys.executable,
                "scripts/audit_a_share_signal_snapshot_trade_calendar.py",
            ],
        ),
        (
            "run_rolling_backtest",
            ["make", "run-a-share-point-in-time-rolling-backtest"],
        ),
        (
            "raw_price_audit",
            ["make", "audit-a-share-rolling-backtest-raw-prices"],
        ),
        (
            "validate_rolling_backtest",
            ["make", "validate-a-share-point-in-time-rolling-backtest"],
        ),
        (
            "update_rolling_history",
            ["make", "update-a-share-rolling-backtest-history"],
        ),
        (
            "validate_rolling_history",
            ["make", "validate-a-share-rolling-backtest-history"],
        ),
        (
            "p22_6_regression",
            ["make", "p22-6-full-pipeline"],
        ),
        (
            "evidence_gate",
            ["make", "verify-aegis-evidence-gate"],
        ),
    ]

    results = []

    for name, command in stages:
        stage = run_stage(name, command)
        results.append(stage)

        if stage["exit_code"] != 0:
            evidence = {
                "project": "Project Aegis",
                "type": "p23_6_full_rolling_pipeline",
                "generated_at": now(),
                "stages": results,
                "overall_verdict": "FAIL",
            }

            EVIDENCE.write_text(
                json.dumps(evidence, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            FAIL_MARKER.write_text("FAIL\n", encoding="utf-8")
            FAIL_REASON.write_text(
                f"# P23.6 Full Rolling Pipeline FAIL\n\n"
                f"Failed stage: `{name}`\n"
                f"Exit code: `{stage['exit_code']}`\n",
                encoding="utf-8",
            )
            return 1

    evidence = {
        "project": "Project Aegis",
        "type": "p23_6_full_rolling_pipeline",
        "generated_at": now(),
        "stages": results,
        "overall_verdict": "PASS",
        "dry_run": True,
        "sent": False,
        "trading_called": False,
    }

    EVIDENCE.write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    PASS_MARKER.write_text("PASS\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
