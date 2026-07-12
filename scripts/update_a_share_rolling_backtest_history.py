#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
REPORTS = REPO / "data/reports"

ROLLING = REPORTS / "a_share_point_in_time_rolling_backtest_latest.json"
AUDIT = REPORTS / "a_share_rolling_backtest_raw_price_audit_latest.json"
VALIDATION = REPORTS / "p23_3_rolling_backtest_validation_latest.json"

HISTORY_JSON = REPORTS / "a_share_rolling_backtest_history_latest.json"
HISTORY_MD = REPORTS / "a_share_rolling_backtest_history_latest.md"
SNAPSHOT_DIR = REPORTS / "a_share_rolling_backtest_history_snapshots"

RETENTION_LIMIT = 20


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


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    for path in (ROLLING, AUDIT, VALIDATION):
        if not path.exists():
            raise RuntimeError(f"missing required file: {path}")

    rolling = read_json(ROLLING)
    audit = read_json(AUDIT)
    validation = read_json(VALIDATION)

    if audit.get("overall_verdict") != "PASS" or audit.get("failures"):
        raise RuntimeError("raw price audit is not PASS")

    if validation.get("overall_verdict") != "PASS" or validation.get("failures"):
        raise RuntimeError("rolling validation is not PASS")

    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)

    if HISTORY_JSON.exists():
        history = read_json(HISTORY_JSON)
        entries = history.get("entries", [])
    else:
        entries = []

    source_rolling_sha256 = sha256(ROLLING)
    source_audit_sha256 = sha256(AUDIT)
    source_validation_sha256 = sha256(VALIDATION)

    run_id = str(rolling.get("run_id") or "")
    if not run_id:
        raise RuntimeError("rolling run_id missing")

    entry = {
        "run_id": run_id,
        "generated_at": rolling.get("generated_at"),
        "recorded_at": now(),
        "plan_id": rolling.get("plan_id"),
        "strategy_id": rolling.get("strategy_id"),
        "original_display_strategy_id": rolling.get(
            "original_display_strategy_id"
        ),
        "strategy_equivalence_claimed": rolling.get(
            "strategy_equivalence_claimed"
        ),
        "backtest_type": rolling.get("backtest_type"),
        "point_in_time_required": rolling.get("point_in_time_required"),
        "static_snapshot_backtest": rolling.get("static_snapshot_backtest"),
        "lookahead_bias_control_passed": rolling.get(
            "lookahead_bias_control_passed"
        ),
        "survivorship_bias_warning": rolling.get(
            "survivorship_bias_warning"
        ),
        "snapshot_count": rolling.get("snapshot_count"),
        "periods_count": rolling.get("periods_count"),
        "passed_periods_count": rolling.get("passed_periods_count"),
        "failed_periods_count": rolling.get("failed_periods_count"),
        "portfolio_metrics": rolling.get("portfolio_metrics"),
        "benchmark_metrics": rolling.get("benchmark_metrics"),
        "excess_return": rolling.get("excess_return"),
        "raw_price_audit_verdict": audit.get("overall_verdict"),
        "rolling_validation_verdict": validation.get("overall_verdict"),
        "source_rolling_json_sha256": source_rolling_sha256,
        "source_raw_price_audit_sha256": source_audit_sha256,
        "source_validation_sha256": source_validation_sha256,
        "source_rolling_json_sha256_12": source_rolling_sha256[:12],
        "source_raw_price_audit_sha256_12": source_audit_sha256[:12],
        "source_validation_sha256_12": source_validation_sha256[:12],
        "dry_run": rolling.get("dry_run"),
        "sent": rolling.get("sent"),
        "trading_called": rolling.get("trading_called"),
        "result": "PASS",
    }

    entries = [
        old for old in entries
        if old.get("run_id") != run_id
    ]
    entries.append(entry)
    entries.sort(
        key=lambda item: str(item.get("generated_at") or ""),
        reverse=True,
    )
    entries = entries[:RETENTION_LIMIT]

    snapshot_path = SNAPSHOT_DIR / f"{run_id}_history_entry.json"
    write_json(snapshot_path, entry)

    history = {
        "project": "Project Aegis",
        "type": "a_share_rolling_backtest_history",
        "generated_at": now(),
        "retention_limit": RETENTION_LIMIT,
        "runs_count": len(entries),
        "entries": entries,
        "dry_run": True,
        "sent": False,
        "trading_called": False,
    }

    write_json(HISTORY_JSON, history)

    lines = [
        "# A股 Point-in-Time Rolling Backtest History",
        "",
        f"- Runs count: {len(entries)}",
        f"- Retention limit: {RETENTION_LIMIT}",
        "- All entries require independent raw-price audit PASS.",
        "- Dry-run research only; not live performance.",
        "",
        "| Run ID | Generated | Periods | Total Return | Benchmark | Excess | Audit |",
        "|---|---|---:|---:|---:|---:|---|",
    ]

    for item in entries:
        portfolio = item.get("portfolio_metrics") or {}
        benchmark = item.get("benchmark_metrics") or {}

        lines.append(
            f"| {item.get('run_id')} | {item.get('generated_at')} | "
            f"{item.get('periods_count')} | "
            f"{portfolio.get('total_return')} | "
            f"{benchmark.get('total_return')} | "
            f"{item.get('excess_return')} | "
            f"{item.get('raw_price_audit_verdict')} |"
        )

    HISTORY_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"run_id={run_id}")
    print(f"runs_count={len(entries)}")
    print(f"snapshot={snapshot_path.relative_to(REPO)}")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(
            f"[update_a_share_rolling_backtest_history] "
            f"{type(exc).__name__}: {exc}",
            file=sys.stderr,
        )
        raise SystemExit(1)
