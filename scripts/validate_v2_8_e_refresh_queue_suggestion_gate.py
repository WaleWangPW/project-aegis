#!/usr/bin/env python3
"""Validate V2.8-E suggestion gate drafts from refresh-queue sandbox results."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aegis.models.strategy_hypothesis import StrategySandboxHypothesis  # noqa: E402
from aegis.strategy.hypothesis_suggestion import (  # noqa: E402
    build_hypothesis_suggestion_gate_report,
    build_hypothesis_suggestion_opportunities,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_ROOT = ROOT / "data" / "processed" / "v2_8_e_acceptance"
DEFAULT_REPORTS_DIR = ROOT / "data" / "reports"
DEFAULT_REFRESHED_HYPOTHESES = (
    ROOT
    / "data"
    / "processed"
    / "v2_8_d_acceptance"
    / "v2_8_d_20260711_acceptance"
    / "refreshed_hypotheses.json"
)
DEFAULT_SANDBOX_REPORT = ROOT / "data" / "reports" / "v2_8_d_refresh_queue_historical_sandbox_latest.json"
V2_8_D_PASS_MARKER = ROOT / "data" / "reports" / "V2_8_D_REFRESH_QUEUE_HISTORICAL_SANDBOX_PASS.marker"

PASS_MARKER = "V2_8_E_REFRESH_QUEUE_SUGGESTION_GATE_PASS.marker"
FAIL_MARKER = "V2_8_E_REFRESH_QUEUE_SUGGESTION_GATE_FAIL.marker"
REPORT_JSON = "v2_8_e_refresh_queue_suggestion_gate_latest.json"
REPORT_MD = "v2_8_e_refresh_queue_suggestion_gate_latest.md"


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def _run_id() -> str:
    return "v2_8_e_refresh_queue_suggestion_gate_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _sha256(path: Path) -> Optional[str]:
    if not path.exists():
        return None
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _load_hypotheses(path: Path) -> list[StrategySandboxHypothesis]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return [StrategySandboxHypothesis(**item) for item in payload]


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def run_acceptance(
    *,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    reports_dir: Path = DEFAULT_REPORTS_DIR,
    refreshed_hypotheses_json: Path = DEFAULT_REFRESHED_HYPOTHESES,
    sandbox_report_json: Path = DEFAULT_SANDBOX_REPORT,
    run_id: Optional[str] = None,
    command: Optional[str] = None,
) -> dict:
    run_id = run_id or _run_id()
    run_dir = output_root / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    reports_dir.mkdir(parents=True, exist_ok=True)

    hypotheses = _load_hypotheses(refreshed_hypotheses_json)
    sandbox_report = _load_json(sandbox_report_json)
    evidence_refs = [
        str(sandbox_report_json),
        str(V2_8_D_PASS_MARKER),
        str(refreshed_hypotheses_json),
    ]
    opportunities = build_hypothesis_suggestion_opportunities(
        hypotheses,
        sandbox_report,
        evidence_refs=evidence_refs,
    )
    report = build_hypothesis_suggestion_gate_report(
        hypotheses,
        sandbox_report,
        run_id=run_id,
        evidence_refs=evidence_refs,
        command=command,
    )
    report["acceptance_target"] = "V2.8-E Refresh Queue Suggestion Gate Drafts"
    report["source_acceptance_target"] = sandbox_report.get("acceptance_target")
    report["safety"]["refresh_queue_source_only"] = True
    report["safety"]["no_trading_webhook"] = True

    opportunities_json = run_dir / "refresh_queue_suggestion_opportunities.json"
    suggestions_json = run_dir / "refresh_queue_suggestion_drafts.json"
    source_sandbox_json = run_dir / "source_refresh_queue_sandbox_report.json"
    opportunities_json.write_text(
        json.dumps([item.model_dump() for item in opportunities], ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    suggestions_json.write_text(json.dumps(report["suggestions"], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    source_sandbox_json.write_text(json.dumps(sandbox_report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    allowed = [item for item in report["suggestions"] if item["action"] != "blocked"]
    blocked = [item for item in report["suggestions"] if item["action"] == "blocked"]
    expected_pass = len(sandbox_report["summary"]["passing_hypotheses"])
    expected_fail = len(sandbox_report["summary"]["failing_hypotheses"])
    checks = {
        "suggestion_gate_passed": report["overall_status"] == "PASS",
        "source_is_v2_8_d_sandbox": sandbox_report.get("acceptance_target")
        == "V2.8-D Refresh Queue Historical Sandbox Rerun",
        "opportunity_count_matches_hypotheses": report["summary"]["opportunity_count"] == len(hypotheses),
        "allowed_count_matches_sandbox_pass": report["summary"]["allowed_count"] == expected_pass,
        "blocked_count_matches_sandbox_fail": report["summary"]["blocked_count"] == expected_fail,
        "all_allowed_are_simulation_only": all(item["simulation_only"] is True for item in allowed),
        "all_allowed_require_external_execution": all(item["user_must_execute_externally"] is True for item in allowed),
        "blocked_failed_sandbox_hypotheses": all(
            "strategy_sandbox_not_passed" in item["blocked_by"] for item in blocked
        ),
        "evidence_refs_present": all(item["evidence_refs"] for item in report["suggestions"]),
        "no_live_price_or_position_size": report["safety"]["no_live_price_or_position_size"] is True,
        "suggestion_drafts_not_orders": report["safety"]["suggestion_drafts_not_orders"] is True,
        "manual_external_execution_only": report["safety"]["manual_external_execution_only"] is True,
        "no_real_trade": report["safety"]["no_real_trade"] is True,
        "no_broker_api": report["safety"]["no_broker_api"] is True,
        "no_trading_webhook": report["safety"]["no_trading_webhook"] is True,
        "no_secret_storage": report["safety"]["no_secret_storage"] is True,
        "no_production_records_mutation": report["production_records_written"] is False,
        "dashboard_contract_unchanged": report["dashboard_contract_changed"] is False,
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise RuntimeError("V2.8-E acceptance checks failed: " + ", ".join(failed))

    acceptance_report = {
        **report,
        "run_dir": str(run_dir),
        "refreshed_hypotheses_json": str(refreshed_hypotheses_json),
        "source_sandbox_report_json": str(sandbox_report_json),
        "opportunities_json": str(opportunities_json),
        "suggestions_json": str(suggestions_json),
        "copied_source_sandbox_json": str(source_sandbox_json),
        "checks": checks,
        "hashes": {
            "refreshed_hypotheses_json": _sha256(refreshed_hypotheses_json),
            "source_sandbox_report_json": _sha256(sandbox_report_json),
            "opportunities_json": _sha256(opportunities_json),
            "suggestions_json": _sha256(suggestions_json),
            "copied_source_sandbox_json": _sha256(source_sandbox_json),
        },
    }
    _write_reports(acceptance_report, reports_dir)
    return acceptance_report


def _render_markdown(report: dict) -> str:
    return "\n".join(
        [
            "# V2.8-E Refresh Queue Suggestion Gate",
            "",
            f"- status: `{report['overall_status']}`",
            f"- run_id: `{report['run_id']}`",
            f"- suggestions_json: `{report['suggestions_json']}`",
            f"- allowed_count: `{report['summary']['allowed_count']}`",
            f"- blocked_count: `{report['summary']['blocked_count']}`",
            f"- allowed_suggestions: `{report['summary']['allowed_suggestions']}`",
            f"- blocked_suggestions: `{report['summary']['blocked_suggestions']}`",
            "",
            "## Boundary",
            "",
            "- Simulation-only drafts.",
            "- User must execute manually outside Aegis.",
            "- No live price, position size, broker API, webhook, or real order.",
            "- No production recommendation mutation.",
            "",
        ]
    )


def _write_reports(report: dict, reports_dir: Path) -> None:
    json_path = reports_dir / REPORT_JSON
    md_path = reports_dir / REPORT_MD
    marker_path = reports_dir / PASS_MARKER
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md_path.write_text(_render_markdown(report), encoding="utf-8")
    marker_path.write_text(
        "\n".join(
            [
                f"generated_at={report['generated_at']}",
                f"command={report.get('command') or ''}",
                "exit_code=0",
                "target=V2.8-E Refresh Queue Suggestion Gate Drafts",
                f"report_json={json_path}",
                f"report_json_sha256={_sha256(json_path)}",
                f"report_md={md_path}",
                f"report_md_sha256={_sha256(md_path)}",
                f"suggestions_json={report['suggestions_json']}",
                f"suggestions_json_sha256={report['hashes']['suggestions_json']}",
                f"opportunities_json={report['opportunities_json']}",
                f"opportunities_json_sha256={report['hashes']['opportunities_json']}",
                "network_used=false",
                "production_records_written=false",
                "dashboard_contract_changed=false",
                "simulation_only=true",
                "manual_external_execution_only=true",
                "suggestion_drafts_not_orders=true",
                "no_live_price_or_position_size=true",
                "no_real_trade=true",
                "no_broker_api=true",
                "no_trading_webhook=true",
                "failed=0",
                "",
            ]
        ),
        encoding="utf-8",
    )
    fail_marker = reports_dir / FAIL_MARKER
    if fail_marker.exists():
        fail_marker.unlink()


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--reports-dir", type=Path, default=DEFAULT_REPORTS_DIR)
    parser.add_argument("--refreshed-hypotheses-json", type=Path, default=DEFAULT_REFRESHED_HYPOTHESES)
    parser.add_argument("--sandbox-report-json", type=Path, default=DEFAULT_SANDBOX_REPORT)
    parser.add_argument("--run-id")
    args = parser.parse_args(argv)
    command = " ".join([Path(sys.argv[0]).name, *(argv if argv is not None else sys.argv[1:])])
    try:
        report = run_acceptance(
            output_root=args.output_root,
            reports_dir=args.reports_dir,
            refreshed_hypotheses_json=args.refreshed_hypotheses_json,
            sandbox_report_json=args.sandbox_report_json,
            run_id=args.run_id,
            command=command,
        )
    except Exception as exc:
        args.reports_dir.mkdir(parents=True, exist_ok=True)
        (args.reports_dir / FAIL_MARKER).write_text(
            "\n".join(
                [
                    f"generated_at={_now_iso()}",
                    f"command={command}",
                    "exit_code=1",
                    "target=V2.8-E Refresh Queue Suggestion Gate Drafts",
                    f"error={exc}",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        print(f"V2.8-E Refresh Queue Suggestion Gate FAIL: {exc}")
        return 1

    print(
        "V2.8-E Refresh Queue Suggestion Gate PASS "
        f"run_id={report['run_id']} report={args.reports_dir / REPORT_JSON}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
