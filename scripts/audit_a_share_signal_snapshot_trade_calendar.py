#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
CALENDAR = REPO / "data/cache/p23_2_historical_market/trade_calendar.json"
SNAPSHOTS = REPO / "data/reports/a_share_signal_snapshots_latest.json"
REPORT_JSON = REPO / "data/reports/p23_2_trade_calendar_audit_latest.json"
REPORT_MD = REPO / "data/reports/p23_2_trade_calendar_audit_latest.md"


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def compact(value: str) -> str:
    return value.replace("-", "")


def main() -> int:
    calendar = read_json(CALENDAR)
    snapshot_payload = read_json(SNAPSHOTS)

    open_dates = sorted(str(value) for value in calendar.get("open_dates", []))
    open_set = set(open_dates)
    open_index = {value: index for index, value in enumerate(open_dates)}

    period_audits = []
    failures = []

    snapshots = snapshot_payload.get("snapshots", [])
    if snapshot_payload.get("snapshot_count") != 6 or len(snapshots) != 6:
        failures.append("snapshot_count_not_6")

    for snapshot in snapshots:
        values = {
            field: compact(str(snapshot.get(field) or ""))
            for field in (
                "signal_date",
                "data_cutoff_date",
                "rebalance_date",
                "entry_date",
                "exit_date",
            )
        }

        checks = {}

        for field, value in values.items():
            checks[f"{field}_open"] = value in open_set
            try:
                checks[f"{field}_not_weekend"] = date.fromisoformat(
                    snapshot[field]
                ).weekday() < 5
            except Exception:
                checks[f"{field}_not_weekend"] = False

        checks["date_order"] = (
            values["data_cutoff_date"]
            <= values["signal_date"]
            < values["rebalance_date"]
            <= values["entry_date"]
            < values["exit_date"]
        )

        try:
            checks["holding_period_20_open_days"] = (
                open_index[values["exit_date"]]
                - open_index[values["entry_date"]]
                == 20
            )
        except KeyError:
            checks["holding_period_20_open_days"] = False

        passed = all(checks.values())
        if not passed:
            failures.append(snapshot.get("snapshot_id") or "unknown_snapshot")

        period_audits.append(
            {
                "snapshot_id": snapshot.get("snapshot_id"),
                "dates": values,
                "checks": checks,
                "passed": passed,
            }
        )

    result = {
        "project": "Project Aegis",
        "type": "p23_2_trade_calendar_audit",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_snapshot_sha256": hashlib.sha256(SNAPSHOTS.read_bytes()).hexdigest(),
        "source_calendar_sha256": hashlib.sha256(CALENDAR.read_bytes()).hexdigest(),
        "snapshot_count": len(snapshots),
        "period_audits": period_audits,
        "failures": failures,
        "overall_verdict": "PASS" if not failures else "FAIL",
    }

    write_json(REPORT_JSON, result)

    lines = [
        "# P23.2 Trade Calendar Audit",
        "",
        f"- Verdict: **{result['overall_verdict']}**",
        f"- Snapshot count: {len(snapshots)}",
        "",
        "| Snapshot | Signal | Entry | Exit | 20 open days | Result |",
        "|---|---|---|---|---|---|",
    ]

    for item in period_audits:
        dates = item["dates"]
        lines.append(
            f"| {item['snapshot_id']} | {dates['signal_date']} | "
            f"{dates['entry_date']} | {dates['exit_date']} | "
            f"{item['checks']['holding_period_20_open_days']} | "
            f"{'PASS' if item['passed'] else 'FAIL'} |"
        )

    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print("P23_2_TRADE_CALENDAR_AUDIT_VERDICT_JSON")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print("END_P23_2_TRADE_CALENDAR_AUDIT_VERDICT_JSON")

    return 0 if not failures else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(
            f"[audit_a_share_signal_snapshot_trade_calendar] "
            f"{type(exc).__name__}: {exc}",
            file=sys.stderr,
        )
        raise SystemExit(1)
