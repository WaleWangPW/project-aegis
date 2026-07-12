#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
LATEST = REPO / "data/reports/a_share_signal_snapshots_latest.json"
LATEST_MD = REPO / "data/reports/a_share_signal_snapshots_latest.md"
AUDIT = REPO / "data/reports/p23_2_trade_calendar_audit_latest.json"
SNAPSHOT_DIR = REPO / "data/snapshots/a_share_signal_snapshots"
REPORT = REPO / "data/reports/p23_2_signal_snapshot_validation_latest.json"


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    checks: dict[str, dict[str, Any]] = {}

    checks["latest_json_exists"] = {"passed": LATEST.exists()}
    checks["latest_md_exists"] = {"passed": LATEST_MD.exists()}
    checks["audit_exists"] = {"passed": AUDIT.exists()}
    checks["snapshot_dir_exists"] = {"passed": SNAPSHOT_DIR.exists()}

    payload = read_json(LATEST) if LATEST.exists() else {}
    audit = read_json(AUDIT) if AUDIT.exists() else {}
    snapshots = payload.get("snapshots", [])

    checks["snapshot_count_exactly_6"] = {
        "passed": payload.get("snapshot_count") == 6 and len(snapshots) == 6,
        "count": len(snapshots),
    }

    checks["audit_pass"] = {
        "passed": audit.get("overall_verdict") == "PASS"
        and not audit.get("failures")
    }

    snapshot_files = list(SNAPSHOT_DIR.glob("snapshot_*.json")) if SNAPSHOT_DIR.exists() else []
    checks["snapshot_file_count_exactly_6"] = {
        "passed": len(snapshot_files) == 6,
        "count": len(snapshot_files),
    }

    required_fields = {
        "snapshot_id",
        "strategy_id",
        "signal_date",
        "data_cutoff_date",
        "rebalance_date",
        "entry_date",
        "exit_date",
        "selected_symbols",
        "selected_symbols_count",
        "selected_records",
        "ranking_inputs",
        "risk_filters",
        "liquidity_filters",
        "source_data_hashes",
        "trade_calendar_source",
        "point_in_time",
        "current_watchlist_used",
        "dry_run",
        "sent",
        "trading_called",
    }

    checks["required_fields_complete"] = {
        "passed": all(required_fields.issubset(snapshot.keys()) for snapshot in snapshots)
    }

    checks["selected_count_valid"] = {
        "passed": all(
            snapshot.get("selected_symbols_count") == len(snapshot.get("selected_symbols", []))
            and snapshot.get("selected_symbols_count", 0) >= 5
            for snapshot in snapshots
        )
    }

    checks["historical_strategy_valid"] = {
        "passed": all(
            snapshot.get("strategy_id") == "a_share_historical_liquidity_trend_v1"
            and snapshot.get("strategy_equivalence_claimed") is False
            for snapshot in snapshots
        )
    }

    checks["point_in_time_flags_valid"] = {
        "passed": all(
            snapshot.get("point_in_time") is True
            and snapshot.get("current_watchlist_used") is False
            and snapshot.get("lookahead_bias_control_passed") is True
            for snapshot in snapshots
        )
    }

    checks["safety_flags_valid"] = {
        "passed": all(
            snapshot.get("dry_run") is True
            and snapshot.get("sent") is False
            and snapshot.get("trading_called") is False
            for snapshot in snapshots
        )
    }

    hash_values = []
    for snapshot in snapshots:
        source_hashes = snapshot.get("source_data_hashes", {})
        if isinstance(source_hashes, dict):
            hash_values.extend(source_hashes.values())

    checks["source_hashes_valid"] = {
        "passed": bool(hash_values)
        and all(
            isinstance(value, str)
            and re.fullmatch(r"[0-9a-f]{64}", value)
            for value in hash_values
        ),
        "hash_count": len(hash_values),
    }

    forbidden_text = "\n".join(
        path.read_text(encoding="utf-8", errors="ignore")
        for path in (
            REPO / "scripts/generate_a_share_signal_snapshots.py",
            LATEST,
        )
        if path.exists()
    )

    checks["no_random_or_mock_generation"] = {
        "passed": not bool(
            re.search(
                r"\brandom\b|random\.randint|为了演示|模拟的快照|hash_\{",
                forbidden_text,
                re.I,
            )
        )
    }

    checks["no_current_watchlist_source"] = {
        "passed": "a_share_watchlist_latest.json" not in forbidden_text
    }

    failures = [
        name for name, value in checks.items()
        if not value.get("passed", False)
    ]

    result = {
        "project": "Project Aegis",
        "type": "p23_2_signal_snapshot_validation",
        "validated_at": datetime.now(timezone.utc).isoformat(),
        "checks": checks,
        "failures": failures,
        "overall_verdict": "PASS" if not failures else "FAIL",
    }

    REPORT.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print("SIGNAL_SNAPSHOT_VERDICT_JSON")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print("END_SIGNAL_SNAPSHOT_VERDICT_JSON")

    return 0 if not failures else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(
            f"[validate_a_share_signal_snapshots] "
            f"{type(exc).__name__}: {exc}",
            file=sys.stderr,
        )
        raise SystemExit(1)
