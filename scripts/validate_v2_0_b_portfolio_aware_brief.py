#!/usr/bin/env python3
"""Validate Project Aegis V2.0-B Portfolio-Aware Daily Brief acceptance."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aegis.models.recommendation import RecommendationRecord  # noqa: E402
from aegis.portfolio.aware_brief import (  # noqa: E402
    build_portfolio_aware_brief,
    render_portfolio_aware_brief_markdown,
)
from aegis.portfolio.snapshot import RiskBudget, build_portfolio_snapshot  # noqa: E402
from aegis.models.holding import Holding  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_ROOT = ROOT / "data" / "processed" / "v2_0_b_acceptance"
DEFAULT_REPORTS_DIR = ROOT / "data" / "reports"

PASS_MARKER = "V2_0_B_PORTFOLIO_AWARE_BRIEF_PASS.marker"
FAIL_MARKER = "V2_0_B_PORTFOLIO_AWARE_BRIEF_FAIL.marker"
REPORT_JSON = "v2_0_b_portfolio_aware_brief_latest.json"
REPORT_MD = "v2_0_b_portfolio_aware_brief_latest.md"


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
    return "v2_0_b_portfolio_aware_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _rec(rec_id: str, symbol: str, status: str, summary: str) -> RecommendationRecord:
    return RecommendationRecord(
        recommendation_id=rec_id,
        date="2026-07-11",
        session="pre_market",
        symbol=symbol,
        name=f"{symbol} V2.0-B Fixture",
        market="US",
        sector="Acceptance",
        status=status,
        action_label="prepare_entry_plan" if status == "Action" else "hold_or_watch",
        market_snapshot_id=f"mkt_{rec_id}",
        candidate_id=f"cand_{rec_id}",
        expert_opinions=[],
        support_reasons=["fixture support"],
        oppose_reasons=[],
        risks=["fixture risk"] if status == "Action" else [],
        invalidation_conditions=["fixture invalidation"] if status == "Action" else [],
        confidence=0.7,
        decision_summary=summary,
        lifecycle_status="open",
        created_at=_now_iso(),
        updated_at=_now_iso(),
    )


def _portfolio_report() -> dict:
    holdings = [
        Holding(
            holding_id="hold_US_HOLD_20260711",
            symbol="HOLD",
            name="Held Fixture",
            market="US",
            shares=50,
            avg_cost=30.0,
            current_price=34.0,
            currency="USD",
            entry_date="2026-07-01",
            status="open",
        ),
        Holding(
            holding_id="hold_US_CORE_20260711",
            symbol="CORE",
            name="Core Fixture",
            market="US",
            shares=70,
            avg_cost=30.0,
            current_price=30.0,
            currency="USD",
            entry_date="2026-07-01",
            status="open",
        ),
    ]
    return build_portfolio_snapshot(
        holdings=holdings,
        date="2026-07-11",
        cash=1200.0,
        risk_budget=RiskBudget(max_exposure_pct=0.8, max_single_position_pct=0.5),
    )


def _recommendations() -> list[RecommendationRecord]:
    return [
        _rec(
            "rec_20260711_pre_market_US_NEW_v2_0_b",
            "NEW",
            "Action",
            "Fixture Action that portfolio risk should evaluate before simulated entry.",
        ),
        _rec(
            "rec_20260711_pre_market_US_HOLD_v2_0_b",
            "HOLD",
            "Watch",
            "Fixture Watch for existing holding.",
        ),
        _rec(
            "rec_20260711_pre_market_US_WAIT_v2_0_b",
            "WAIT",
            "Watch",
            "Fixture Watch for non-held candidate.",
        ),
    ]


def run_acceptance(
    *,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    reports_dir: Path = DEFAULT_REPORTS_DIR,
    run_id: Optional[str] = None,
    command: Optional[str] = None,
) -> dict:
    run_id = run_id or _run_id()
    run_dir = output_root / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    reports_dir.mkdir(parents=True, exist_ok=True)

    portfolio_report = _portfolio_report()
    brief = build_portfolio_aware_brief(
        recommendations=_recommendations(),
        portfolio_report=portfolio_report,
        planned_position_value=1000.0,
    )
    portfolio_json = run_dir / "portfolio_snapshot.json"
    brief_json = run_dir / "portfolio_aware_brief.json"
    brief_md = run_dir / "portfolio_aware_brief.md"
    portfolio_json.write_text(json.dumps(portfolio_report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    brief_json.write_text(json.dumps(brief, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    brief_md.write_text(render_portfolio_aware_brief_markdown(brief), encoding="utf-8")

    actions = {item["symbol"]: item["portfolio_action"] for item in brief["items"]}
    explanation_text = " ".join(item["explanation"] + " " + " ".join(item["evidence"]) for item in brief["items"])
    checks = {
        "recommendations_evaluated": brief["recommendation_count"] == 3,
        "action_explained": actions.get("NEW") == "wait_due_to_portfolio_risk",
        "hold_explained": actions.get("HOLD") == "hold",
        "wait_explained": actions.get("WAIT") == "wait",
        "cash_exposure_risk_budget_used": all(
            token in explanation_text
            for token in ("cash=", "current_exposure_pct=", "max_exposure_pct=", "max_single_position_pct=")
        ),
        "dashboard_contract_unchanged": brief["safety"]["dashboard_contract_unchanged"] is True,
        "no_broker_or_real_trade": brief["safety"]["no_real_trade"] is True and brief["safety"]["no_broker_api"] is True,
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise RuntimeError("V2.0-B acceptance checks failed: " + ", ".join(failed))

    report = {
        "overall_status": "PASS",
        "generated_at": _now_iso(),
        "run_id": run_id,
        "command": command,
        "acceptance_target": "V2.0-B Portfolio-Aware Daily Brief",
        "isolated": True,
        "production_records_written": False,
        "dashboard_contract_changed": False,
        "run_dir": str(run_dir),
        "portfolio_json": str(portfolio_json),
        "brief_json": str(brief_json),
        "brief_md": str(brief_md),
        "checks": checks,
        "summary": {
            "recommendation_count": brief["recommendation_count"],
            "action_counts": brief["action_counts"],
            "portfolio_snapshot_id": brief["portfolio_snapshot_id"],
        },
        "safety": brief["safety"]
        | {
            "manual_external_execution_only": True,
            "user_submitted_execution_facts_only": True,
            "no_account_sync": True,
            "no_auto_rebalance": True,
            "no_production_records_mutation": True,
        },
        "hashes": {
            "portfolio_json": _sha256(portfolio_json),
            "brief_json": _sha256(brief_json),
            "brief_md": _sha256(brief_md),
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
                "# V2.0-B Portfolio-Aware Daily Brief Acceptance",
                "",
                f"- status: {report['overall_status']}",
                f"- target: {report['acceptance_target']}",
                f"- run_id: {report['run_id']}",
                f"- brief_json: `{report['brief_json']}`",
                f"- brief_md: `{report['brief_md']}`",
                f"- action_counts: `{report['summary']['action_counts']}`",
                "- safety: read-only, simulation only, no real trade, no broker API, Dashboard Contract unchanged",
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
                "target=V2.0-B Portfolio-Aware Daily Brief",
                f"report_json={json_path}",
                f"report_json_sha256={_sha256(json_path)}",
                f"report_md={md_path}",
                f"report_md_sha256={_sha256(md_path)}",
                f"run_dir={report['run_dir']}",
                "dashboard_contract_changed=false",
                "production_records_written=false",
                "failed=0",
                "",
            ]
        ),
        encoding="utf-8",
    )
    for stale in (reports_dir / FAIL_MARKER, reports_dir / "V2_0_B_PORTFOLIO_AWARE_BRIEF_FAIL_REASON.md"):
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
                "target=V2.0-B Portfolio-Aware Daily Brief",
                "failed=1",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (reports_dir / "V2_0_B_PORTFOLIO_AWARE_BRIEF_FAIL_REASON.md").write_text(
        f"# V2.0-B Portfolio-Aware Daily Brief Failed\n\n{type(exc).__name__}: {exc}\n",
        encoding="utf-8",
    )


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Validate Project Aegis V2.0-B Portfolio-Aware Daily Brief.")
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
        print(f"[v2_0_b_portfolio_aware_brief] FAIL: {type(exc).__name__}: {exc}")
        return 1

    print("[v2_0_b_portfolio_aware_brief] PASS")
    print(f"run_id={report['run_id']}")
    print(f"report={reports_dir / REPORT_JSON}")
    print(f"marker={reports_dir / PASS_MARKER}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
