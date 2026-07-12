#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
REPORTS = REPO / "data/reports"

HISTORY_JSON = REPORTS / "a_share_rolling_backtest_history_latest.json"
HISTORY_MD = REPORTS / "a_share_rolling_backtest_history_latest.md"
SNAPSHOT_DIR = REPORTS / "a_share_rolling_backtest_history_snapshots"

ROLLING = REPORTS / "a_share_point_in_time_rolling_backtest_latest.json"
AUDIT = REPORTS / "a_share_rolling_backtest_raw_price_audit_latest.json"
VALIDATION = REPORTS / "p23_3_rolling_backtest_validation_latest.json"

OUTPUT = REPORTS / "p23_5_rolling_history_validation_latest.json"


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    checks: dict[str, dict[str, Any]] = {}

    checks["history_json_exists"] = {"passed": HISTORY_JSON.exists()}
    checks["history_md_exists"] = {"passed": HISTORY_MD.exists()}
    checks["snapshot_dir_exists"] = {"passed": SNAPSHOT_DIR.exists()}

    history = read_json(HISTORY_JSON) if HISTORY_JSON.exists() else {}
    entries = history.get("entries", [])

    checks["runs_count_between_1_and_20"] = {
        "passed": 1 <= len(entries) <= 20,
        "count": len(entries),
    }

    run_ids = [str(item.get("run_id")) for item in entries]
    checks["run_id_unique"] = {
        "passed": len(run_ids) == len(set(run_ids)),
    }

    generated = [str(item.get("generated_at") or "") for item in entries]
    checks["runs_sorted_desc"] = {
        "passed": generated == sorted(generated, reverse=True),
    }

    latest = entries[0] if entries else {}

    checks["latest_result_pass"] = {
        "passed": latest.get("result") == "PASS"
    }

    checks["latest_audits_pass"] = {
        "passed": (
            latest.get("raw_price_audit_verdict") == "PASS"
            and latest.get("rolling_validation_verdict") == "PASS"
        )
    }

    checks["latest_semantics_valid"] = {
        "passed": (
            latest.get("point_in_time_required") is True
            and latest.get("static_snapshot_backtest") is False
            and latest.get("lookahead_bias_control_passed") is True
            and latest.get("strategy_equivalence_claimed") is False
        )
    }

    checks["latest_safety_flags_valid"] = {
        "passed": (
            latest.get("dry_run") is True
            and latest.get("sent") is False
            and latest.get("trading_called") is False
        )
    }

    hash_keys = (
        "source_rolling_json_sha256",
        "source_raw_price_audit_sha256",
        "source_validation_sha256",
    )

    checks["full_sha256_format_valid"] = {
        "passed": bool(entries)
        and all(
            re.fullmatch(r"[0-9a-f]{64}", str(item.get(key) or ""))
            for item in entries
            for key in hash_keys
        )
    }

    latest_hash_match = False

    if latest:
        latest_hash_match = (
            latest.get("source_rolling_json_sha256") == sha256(ROLLING)
            and latest.get("source_raw_price_audit_sha256") == sha256(AUDIT)
            and latest.get("source_validation_sha256") == sha256(VALIDATION)
        )

    checks["latest_source_hashes_match"] = {
        "passed": latest_hash_match
    }

    snapshot_exists = bool(latest) and (
        SNAPSHOT_DIR / f"{latest.get('run_id')}_history_entry.json"
    ).exists()

    checks["latest_snapshot_file_exists"] = {
        "passed": snapshot_exists
    }

    checks["portfolio_metrics_present"] = {
        "passed": isinstance(latest.get("portfolio_metrics"), dict)
        and "total_return" in latest.get("portfolio_metrics", {})
    }

    checks["benchmark_metrics_present"] = {
        "passed": isinstance(latest.get("benchmark_metrics"), dict)
        and "total_return" in latest.get("benchmark_metrics", {})
    }

    failures = [
        name
        for name, value in checks.items()
        if not value.get("passed", False)
    ]

    result = {
        "project": "Project Aegis",
        "type": "p23_5_rolling_history_validation",
        "validated_at": datetime.now(timezone.utc).isoformat(),
        "checks": checks,
        "failures": failures,
        "overall_verdict": "PASS" if not failures else "FAIL",
    }

    OUTPUT.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print("ROLLING_BACKTEST_HISTORY_VERDICT_JSON")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print("END_ROLLING_BACKTEST_HISTORY_VERDICT_JSON")

    return 0 if not failures else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(
            f"[validate_a_share_rolling_backtest_history] "
            f"{type(exc).__name__}: {exc}",
            file=sys.stderr,
        )
        raise SystemExit(1)
