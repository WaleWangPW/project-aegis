#!/usr/bin/env python3
"""Validate Project Aegis V2.4-D Research Hypotheses To Suggestion Gate Drafts."""

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
DEFAULT_OUTPUT_ROOT = ROOT / "data" / "processed" / "v2_4_d_acceptance"
DEFAULT_REPORTS_DIR = ROOT / "data" / "reports"
HYPOTHESIS_QUEUE_JSON = (
    ROOT
    / "data"
    / "processed"
    / "v2_4_b_acceptance"
    / "v2_4_b_20260711_acceptance"
    / "strategy_sandbox_hypothesis_queue.json"
)
HYPOTHESIS_SANDBOX_REPORT_JSON = (
    ROOT
    / "data"
    / "processed"
    / "v2_4_c_acceptance"
    / "v2_4_c_20260711_acceptance"
    / "hypothesis_sandbox_report.json"
)
V2_4_C_REPORT_JSON = ROOT / "data" / "reports" / "v2_4_c_historical_sandbox_research_hypotheses_latest.json"
V2_4_C_PASS_MARKER = ROOT / "data" / "reports" / "V2_4_C_HISTORICAL_SANDBOX_RESEARCH_HYPOTHESES_PASS.marker"

PASS_MARKER = "V2_4_D_RESEARCH_HYPOTHESES_SUGGESTION_GATE_PASS.marker"
FAIL_MARKER = "V2_4_D_RESEARCH_HYPOTHESES_SUGGESTION_GATE_FAIL.marker"
REPORT_JSON = "v2_4_d_research_hypotheses_suggestion_gate_latest.json"
REPORT_MD = "v2_4_d_research_hypotheses_suggestion_gate_latest.md"


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def _run_id() -> str:
    return "v2_4_d_hypothesis_suggestion_gate_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


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
    return [StrategySandboxHypothesis(**item) for item in payload["hypotheses"]]


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def run_acceptance(
    *,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    reports_dir: Path = DEFAULT_REPORTS_DIR,
    run_id: Optional[str] = None,
    command: Optional[str] = None,
    hypothesis_queue_json: Path = HYPOTHESIS_QUEUE_JSON,
    sandbox_report_json: Path = HYPOTHESIS_SANDBOX_REPORT_JSON,
) -> dict:
    run_id = run_id or _run_id()
    run_dir = output_root / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    reports_dir.mkdir(parents=True, exist_ok=True)

    hypotheses = _load_hypotheses(hypothesis_queue_json)
    sandbox_report = _load_json(sandbox_report_json)
    evidence_refs = [
        str(V2_4_C_REPORT_JSON),
        str(V2_4_C_PASS_MARKER),
        str(sandbox_report_json),
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

    opportunities_json = run_dir / "research_hypothesis_suggestion_opportunities.json"
    suggestions_json = run_dir / "research_hypothesis_suggestion_drafts.json"
    source_sandbox_json = run_dir / "source_hypothesis_sandbox_report.json"
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
        "no_real_trade_or_broker": report["safety"]["no_real_trade"] is True
        and report["safety"]["no_broker_api"] is True,
        "no_webhook_or_secrets": report["safety"]["no_webhook"] is True
        and report["safety"]["no_secret_storage"] is True,
        "no_production_records_mutation": report["production_records_written"] is False,
        "dashboard_contract_unchanged": report["dashboard_contract_changed"] is False,
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise RuntimeError("V2.4-D acceptance checks failed: " + ", ".join(failed))

    acceptance_report = {
        **report,
        "run_dir": str(run_dir),
        "source_hypothesis_queue_json": str(hypothesis_queue_json),
        "source_hypothesis_sandbox_report_json": str(sandbox_report_json),
        "opportunities_json": str(opportunities_json),
        "suggestions_json": str(suggestions_json),
        "copied_source_sandbox_json": str(source_sandbox_json),
        "checks": checks,
        "hashes": {
            "source_hypothesis_queue_json": _sha256(hypothesis_queue_json),
            "source_hypothesis_sandbox_report_json": _sha256(sandbox_report_json),
            "opportunities_json": _sha256(opportunities_json),
            "suggestions_json": _sha256(suggestions_json),
            "copied_source_sandbox_json": _sha256(source_sandbox_json),
        },
    }
    _write_reports(acceptance_report, reports_dir)
    return acceptance_report


def _write_reports(report: dict, reports_dir: Path) -> None:
    json_path = reports_dir / REPORT_JSON
    md_path = reports_dir / REPORT_MD
    marker_path = reports_dir / PASS_MARKER
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md_path.write_text(
        "\n".join(
            [
                "# V2.4-D Research Hypotheses Suggestion Gate Acceptance",
                "",
                f"- status: {report['overall_status']}",
                f"- target: {report['acceptance_target']}",
                f"- run_id: {report['run_id']}",
                f"- suggestions_json: `{report['suggestions_json']}`",
                f"- allowed_count: `{report['summary']['allowed_count']}`",
                f"- blocked_count: `{report['summary']['blocked_count']}`",
                f"- allowed_suggestions: `{report['summary']['allowed_suggestions']}`",
                f"- blocked_suggestions: `{report['summary']['blocked_suggestions']}`",
                "- safety: simulation-only drafts, manual external execution only, no broker/trading/webhook",
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
                "target=V2.4-D Research Hypotheses To Suggestion Gate Drafts",
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
    parser.add_argument("--run-id")
    parser.add_argument("--hypothesis-queue-json", type=Path, default=HYPOTHESIS_QUEUE_JSON)
    parser.add_argument("--sandbox-report-json", type=Path, default=HYPOTHESIS_SANDBOX_REPORT_JSON)
    args = parser.parse_args(argv)
    command = " ".join([Path(sys.argv[0]).name, *(argv if argv is not None else sys.argv[1:])])

    try:
        report = run_acceptance(
            output_root=args.output_root,
            reports_dir=args.reports_dir,
            run_id=args.run_id,
            command=command,
            hypothesis_queue_json=args.hypothesis_queue_json,
            sandbox_report_json=args.sandbox_report_json,
        )
    except Exception as exc:
        args.reports_dir.mkdir(parents=True, exist_ok=True)
        (args.reports_dir / FAIL_MARKER).write_text(
            "\n".join(
                [
                    f"generated_at={_now_iso()}",
                    f"command={command}",
                    "exit_code=1",
                    "target=V2.4-D Research Hypotheses To Suggestion Gate Drafts",
                    f"error={exc}",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        print(f"V2.4-D Research Hypotheses Suggestion Gate FAIL: {exc}")
        return 1

    print(f"V2.4-D Research Hypotheses Suggestion Gate PASS run_id={report['run_id']} report={args.reports_dir / REPORT_JSON}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

