#!/usr/bin/env python3
from __future__ import annotations

import json
import math
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
REPORTS = REPO / "data/reports"

SNAPSHOTS = REPORTS / "a_share_signal_snapshots_latest.json"
ROLLING = REPORTS / "a_share_point_in_time_rolling_backtest_latest.json"
AUDIT = REPORTS / "a_share_rolling_backtest_raw_price_audit_latest.json"
OUTPUT = REPORTS / "p23_3_rolling_backtest_validation_latest.json"


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    checks: dict[str, dict[str, Any]] = {}

    for name, path in (
        ("snapshots_exists", SNAPSHOTS),
        ("rolling_exists", ROLLING),
        ("raw_price_audit_exists", AUDIT),
    ):
        checks[name] = {"passed": path.exists()}

    snapshots_payload = read_json(SNAPSHOTS)
    rolling = read_json(ROLLING)
    audit = read_json(AUDIT)

    snapshots = snapshots_payload.get("snapshots", [])
    periods = rolling.get("periods", [])

    checks["period_count_matches_snapshots"] = {
        "passed": len(periods) == len(snapshots) == 6,
        "snapshot_count": len(snapshots),
        "period_count": len(periods),
    }

    snapshots_by_id = {
        item["snapshot_id"]: item for item in snapshots
    }

    selected_match = True
    dates_match = True
    valid_symbols_ok = True
    point_in_time_periods = True

    for period in periods:
        snapshot = snapshots_by_id.get(period.get("snapshot_id"))

        if snapshot is None:
            selected_match = False
            dates_match = False
            continue

        if period.get("selected_symbols") != snapshot.get(
            "selected_symbols"
        ):
            selected_match = False

        if (
            period.get("entry_date") != snapshot.get("entry_date")
            or period.get("exit_date") != snapshot.get("exit_date")
            or period.get("data_cutoff_date")
            != snapshot.get("data_cutoff_date")
        ):
            dates_match = False

        if period.get("valid_symbols_count", 0) < 5:
            valid_symbols_ok = False

        if period.get("point_in_time_passed") is not True:
            point_in_time_periods = False

    checks["selected_symbols_match_snapshots"] = {
        "passed": selected_match
    }
    checks["entry_exit_dates_match_snapshots"] = {
        "passed": dates_match
    }
    checks["valid_symbols_gte_5_each_period"] = {
        "passed": valid_symbols_ok
    }
    checks["all_periods_point_in_time"] = {
        "passed": point_in_time_periods
    }

    checks["top_level_semantics_valid"] = {
        "passed": (
            rolling.get("backtest_type")
            == "point_in_time_rolling_backtest"
            and rolling.get("point_in_time_required") is True
            and rolling.get("static_snapshot_backtest") is False
            and rolling.get("lookahead_bias_control_passed") is True
            and rolling.get("strategy_equivalence_claimed") is False
        )
    }

    checks["safety_flags_valid"] = {
        "passed": (
            rolling.get("dry_run") is True
            and rolling.get("sent") is False
            and rolling.get("trading_called") is False
        )
    }

    checks["portfolio_metrics_valid"] = {
        "passed": isinstance(
            rolling.get("portfolio_metrics"), dict
        )
        and all(
            key in rolling["portfolio_metrics"]
            for key in (
                "total_return",
                "annualized_return",
                "max_drawdown",
                "volatility",
                "sharpe",
                "win_rate",
            )
        )
    }

    checks["benchmark_metrics_valid"] = {
        "passed": isinstance(
            rolling.get("benchmark_metrics"), dict
        )
        and "total_return" in rolling["benchmark_metrics"]
    }

    checks["raw_price_audit_pass"] = {
        "passed": (
            audit.get("overall_verdict") == "PASS"
            and not audit.get("failures")
            and audit.get("symbol_price_evidence_count") == 120
            and audit.get("benchmark_price_evidence_count") == 6
            and audit.get("period_evidence_count") == 6
        )
    }

    source_text = "\n".join(
        path.read_text(encoding="utf-8", errors="ignore")
        for path in (
            REPO / "scripts/run_a_share_point_in_time_rolling_backtest.py",
            REPO / "scripts/audit_a_share_rolling_backtest_raw_prices.py",
        )
    )

    checks["no_random_or_fixed_returns"] = {
        "passed": not bool(
            re.search(
                r"\brandom\b|fixed_returns|predefined_returns|"
                r"example_price|sample_price",
                source_text,
                re.I,
            )
        )
    }

    checks["numeric_values_finite"] = {
        "passed": all(
            math.isfinite(float(period["net_portfolio_return"]))
            and math.isfinite(float(period["benchmark_return"]))
            for period in periods
        )
    }

    failures = [
        name
        for name, value in checks.items()
        if not value.get("passed", False)
    ]

    result = {
        "project": "Project Aegis",
        "type": "p23_3_rolling_backtest_validation",
        "validated_at": datetime.now(timezone.utc).isoformat(),
        "checks": checks,
        "failures": failures,
        "overall_verdict": "PASS" if not failures else "FAIL",
    }

    OUTPUT.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print("ROLLING_BACKTEST_VERDICT_JSON")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print("END_ROLLING_BACKTEST_VERDICT_JSON")

    return 0 if not failures else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(
            f"[validate_a_share_point_in_time_rolling_backtest] "
            f"{type(exc).__name__}: {exc}",
            file=sys.stderr,
        )
        raise SystemExit(1)
