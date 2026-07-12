#!/usr/bin/env python3
"""Validate Project Aegis V2.0-A Portfolio Foundation acceptance."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aegis.portfolio.holdings_loader import HoldingLoader  # noqa: E402
from aegis.portfolio.snapshot import (  # noqa: E402
    RiskBudget,
    build_portfolio_snapshot,
    render_portfolio_snapshot_markdown,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_ROOT = ROOT / "data" / "processed" / "v2_0_a_acceptance"
DEFAULT_REPORTS_DIR = ROOT / "data" / "reports"

PASS_MARKER = "V2_0_A_PORTFOLIO_FOUNDATION_PASS.marker"
FAIL_MARKER = "V2_0_A_PORTFOLIO_FOUNDATION_FAIL.marker"
REPORT_JSON = "v2_0_a_portfolio_foundation_latest.json"
REPORT_MD = "v2_0_a_portfolio_foundation_latest.md"


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def _sha256(path: Path) -> Optional[str]:
    if not path.exists():
        return None
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _run_id() -> str:
    return "v2_0_a_portfolio_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _seed_holdings(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "holdings": [
            {
                "holding_id": "hold_US_WIN_20260701_v2_0_a",
                "symbol": "WIN",
                "name": "Winner Fixture",
                "market": "US",
                "shares": 100,
                "avg_cost": 20.0,
                "currency": "USD",
                "entry_date": "2026-07-01",
                "current_price": 24.0,
                "status": "open",
                "notes": "V2.0-A acceptance fixture.",
            },
            {
                "holding_id": "hold_US_DEF_20260701_v2_0_a",
                "symbol": "DEF",
                "name": "Defensive Fixture",
                "market": "US",
                "shares": 50,
                "avg_cost": 30.0,
                "currency": "USD",
                "entry_date": "2026-07-01",
                "current_price": 28.0,
                "status": "open",
                "notes": "V2.0-A acceptance fixture.",
            },
        ]
    }
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def run_acceptance(
    *,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    reports_dir: Path = DEFAULT_REPORTS_DIR,
    run_id: Optional[str] = None,
    command: Optional[str] = None,
) -> dict:
    run_id = run_id or _run_id()
    run_dir = output_root / run_id
    fixture_config = run_dir / "config" / "holdings.yaml"
    run_dir.mkdir(parents=True, exist_ok=False)
    reports_dir.mkdir(parents=True, exist_ok=True)

    _seed_holdings(fixture_config)
    holdings = HoldingLoader(fixture_config).load_holdings()
    snapshot_report = build_portfolio_snapshot(
        holdings=holdings,
        date="2026-07-11",
        cash=1200.0,
        risk_budget=RiskBudget(max_exposure_pct=0.8, max_single_position_pct=0.35),
    )
    snapshot_json = run_dir / "portfolio_snapshot.json"
    snapshot_md = run_dir / "portfolio_snapshot.md"
    snapshot_json.write_text(json.dumps(snapshot_report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    snapshot_md.write_text(render_portfolio_snapshot_markdown(snapshot_report), encoding="utf-8")

    snapshot = snapshot_report["portfolio_snapshot"]
    checks = {
        "holdings_record": len(snapshot_report["holdings"]) == 2,
        "cash_record": snapshot_report["cash"]["amount"] == 1200.0,
        "position_sizing": all(row["position_pct"] is not None for row in snapshot_report["holdings"]),
        "exposure_summary": snapshot["exposure_pct"] is not None and snapshot["exposure_pct"] > 0,
        "risk_budget_summary": snapshot_report["risk_budget"]["max_exposure_pct"] == 0.8,
        "risk_blockers": isinstance(snapshot_report["risk"]["blockers"], list),
        "manual_execution_boundary": snapshot_report["safety"]["manual_external_execution_only"] is True,
        "no_broker_or_real_trade": (
            snapshot_report["safety"]["no_real_trade"] is True
            and snapshot_report["safety"]["no_broker_api"] is True
            and snapshot_report["safety"]["simulation_only"] is True
        ),
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise RuntimeError("V2.0-A acceptance checks failed: " + ", ".join(failed))

    report = {
        "overall_status": "PASS",
        "generated_at": _now_iso(),
        "run_id": run_id,
        "command": command,
        "acceptance_target": "V2.0-A Portfolio Foundation",
        "isolated": True,
        "production_records_written": False,
        "run_dir": str(run_dir),
        "fixture_holdings": str(fixture_config),
        "snapshot_json": str(snapshot_json),
        "snapshot_md": str(snapshot_md),
        "checks": checks,
        "summary": {
            "holding_count": len(snapshot_report["holdings"]),
            "cash": snapshot_report["cash"]["amount"],
            "total_market_value": snapshot["total_market_value"],
            "exposure_pct": snapshot["exposure_pct"],
            "risk_level": snapshot["risk_level"],
            "blocker_count": len(snapshot_report["risk"]["blockers"]),
        },
        "safety": snapshot_report["safety"]
        | {
            "no_account_sync": True,
            "no_auto_rebalance": True,
            "no_production_records_mutation": True,
        },
        "hashes": {
            "snapshot_json": _sha256(snapshot_json),
            "snapshot_md": _sha256(snapshot_md),
        },
    }
    _write_reports(report, reports_dir)
    return report


def _write_reports(report: dict, reports_dir: Path) -> None:
    json_path = reports_dir / REPORT_JSON
    md_path = reports_dir / REPORT_MD
    marker_path = reports_dir / PASS_MARKER
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md_path.write_text(
        "\n".join(
            [
                "# V2.0-A Portfolio Foundation Acceptance",
                "",
                f"- status: {report['overall_status']}",
                f"- target: {report['acceptance_target']}",
                f"- run_id: {report['run_id']}",
                f"- snapshot_json: `{report['snapshot_json']}`",
                f"- snapshot_md: `{report['snapshot_md']}`",
                f"- holding_count: `{report['summary']['holding_count']}`",
                f"- cash: `{report['summary']['cash']}`",
                f"- exposure_pct: `{report['summary']['exposure_pct']}`",
                f"- risk_level: `{report['summary']['risk_level']}`",
                "- safety: simulation only, no real trade, no broker API, no webhook, no secrets",
                "- external execution: user-submitted facts only, never system order placement",
                "",
            ]
        ),
        encoding="utf-8",
    )
    marker_path.write_text(
        "\n".join(
            [
                f"generated_at={report['generated_at']}",
                f"command={report.get('command') or ''}",
                "exit_code=0",
                "target=V2.0-A Portfolio Foundation",
                f"report_json={json_path}",
                f"report_json_sha256={_sha256(json_path)}",
                f"report_md={md_path}",
                f"report_md_sha256={_sha256(md_path)}",
                f"run_dir={report['run_dir']}",
                "production_records_written=false",
                "failed=0",
                "",
            ]
        ),
        encoding="utf-8",
    )
    for stale in (reports_dir / FAIL_MARKER, reports_dir / "V2_0_A_PORTFOLIO_FOUNDATION_FAIL_REASON.md"):
        if stale.exists():
            stale.unlink()


def _write_failure(exc: Exception, reports_dir: Path, command: str) -> None:
    reports_dir.mkdir(parents=True, exist_ok=True)
    (reports_dir / FAIL_MARKER).write_text(
        "\n".join(
            [
                f"generated_at={_now_iso()}",
                f"command={command}",
                "exit_code=1",
                "target=V2.0-A Portfolio Foundation",
                "failed=1",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (reports_dir / "V2_0_A_PORTFOLIO_FOUNDATION_FAIL_REASON.md").write_text(
        f"# V2.0-A Portfolio Foundation Failed\n\n{type(exc).__name__}: {exc}\n",
        encoding="utf-8",
    )


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Validate Project Aegis V2.0-A Portfolio Foundation.")
    parser.add_argument("--output-root", default=str(DEFAULT_OUTPUT_ROOT))
    parser.add_argument("--reports-dir", default=str(DEFAULT_REPORTS_DIR))
    parser.add_argument("--run-id", default=None)
    args = parser.parse_args(argv)

    command = " ".join([Path(sys.argv[0]).name, *(argv if argv is not None else sys.argv[1:])])
    reports_dir = Path(args.reports_dir)
    try:
        report = run_acceptance(
            output_root=Path(args.output_root),
            reports_dir=reports_dir,
            run_id=args.run_id,
            command=command,
        )
    except Exception as exc:  # noqa: BLE001
        _write_failure(exc, reports_dir, command)
        print(f"[v2_0_a_portfolio_foundation] FAIL: {type(exc).__name__}: {exc}")
        return 1

    print("[v2_0_a_portfolio_foundation] PASS")
    print(f"run_id={report['run_id']}")
    print(f"report={reports_dir / REPORT_JSON}")
    print(f"marker={reports_dir / PASS_MARKER}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
