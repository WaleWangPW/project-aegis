#!/usr/bin/env python3
"""Validate Project Aegis V2.0-D Event Timeline and Scenarios acceptance."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aegis.events.timeline import build_event_timeline_report, render_event_timeline_markdown  # noqa: E402
from aegis.models.event_timeline import EventRecord, ScenarioRecord  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_ROOT = ROOT / "data" / "processed" / "v2_0_d_acceptance"
DEFAULT_REPORTS_DIR = ROOT / "data" / "reports"

PASS_MARKER = "V2_0_D_EVENT_TIMELINE_PASS.marker"
FAIL_MARKER = "V2_0_D_EVENT_TIMELINE_FAIL.marker"
REPORT_JSON = "v2_0_d_event_timeline_latest.json"
REPORT_MD = "v2_0_d_event_timeline_latest.md"


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
    return "v2_0_d_event_timeline_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _fixture(created_at: str) -> tuple[list[EventRecord], list[ScenarioRecord]]:
    events = [
        EventRecord(
            event_id="evt_CRCL_system_brief_v2_0_d",
            symbol="CRCL",
            market="US",
            event_date="2026-07-11",
            event_type="user_note",
            title="Portfolio-aware brief accepted",
            summary="Internal system evidence confirms portfolio-aware brief can explain Action/Hold/Wait.",
            source_id="data/reports/v2_0_b_portfolio_aware_brief_latest.json",
            source_url=None,
            evidence_level="verified_primary",
            verified=True,
            decision_relevance="Baseline event for scenario analysis.",
            created_at=created_at,
        ),
        EventRecord(
            event_id="evt_CRCL_social_context_v2_0_d",
            symbol="CRCL",
            market="US",
            event_date="2026-07-11",
            event_type="social_statement",
            title="Social discussion placeholder",
            summary="Community discussion may be tracked as context only.",
            source_id="social_placeholder",
            source_url=None,
            evidence_level="community_discussion",
            verified=False,
            decision_relevance="Context only; not a verified fact.",
            created_at=created_at,
        ),
    ]
    scenarios = [
        ScenarioRecord(
            scenario_id="scn_CRCL_exposure_risk_v2_0_d",
            symbol="CRCL",
            market="US",
            title="If exposure rises further",
            assumption="If portfolio exposure rises while CRCL remains a major holding.",
            impact="mixed",
            rationale="Portfolio-aware brief should keep risk budget in the explanation path.",
            evidence_event_ids=["evt_CRCL_system_brief_v2_0_d"],
            confidence=0.6,
            created_at=created_at,
        )
    ]
    return events, scenarios


def _community_verified_rejected(created_at: str) -> bool:
    try:
        EventRecord(
            event_id="evt_bad_social",
            symbol="CRCL",
            market="US",
            event_date="2026-07-11",
            event_type="social_statement",
            title="Bad verified community event",
            summary="Should be rejected.",
            source_id="bad",
            evidence_level="community_discussion",
            verified=True,
            decision_relevance="Should fail.",
            created_at=created_at,
        )
    except ValidationError:
        return True
    return False


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

    created_at = _now_iso()
    events, scenarios = _fixture(created_at)
    timeline = build_event_timeline_report(symbol="CRCL", market="US", events=events, scenarios=scenarios)
    timeline_json = run_dir / "event_timeline.json"
    timeline_md = run_dir / "event_timeline.md"
    timeline_json.write_text(json.dumps(timeline, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    timeline_md.write_text(render_event_timeline_markdown(timeline), encoding="utf-8")

    checks = {
        "events_present": timeline["event_count"] == 2,
        "verified_event_present": timeline["verified_event_count"] == 1,
        "community_context_not_verified": _community_verified_rejected(created_at),
        "scenario_has_evidence": timeline["scenarios"][0]["evidence_event_ids"] == ["evt_CRCL_system_brief_v2_0_d"],
        "scenario_evidence_resolved": timeline["quality"]["missing_scenario_evidence"] == [],
        "accepted_for_decision_support": timeline["quality"]["accepted_for_decision_support"] is True,
        "does_not_bypass_evidence_gate": timeline["safety"]["does_not_bypass_evidence_gate"] is True,
        "no_broker_or_real_trade": timeline["safety"]["no_real_trade"] is True and timeline["safety"]["no_broker_api"] is True,
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise RuntimeError("V2.0-D acceptance checks failed: " + ", ".join(failed))

    report = {
        "overall_status": "PASS",
        "generated_at": _now_iso(),
        "run_id": run_id,
        "command": command,
        "acceptance_target": "V2.0-D Event Timeline and Scenarios",
        "isolated": True,
        "production_records_written": False,
        "dashboard_contract_changed": False,
        "network_used": False,
        "run_dir": str(run_dir),
        "timeline_json": str(timeline_json),
        "timeline_md": str(timeline_md),
        "checks": checks,
        "summary": {
            "symbol": timeline["symbol"],
            "market": timeline["market"],
            "event_count": timeline["event_count"],
            "verified_event_count": timeline["verified_event_count"],
            "scenario_count": timeline["scenario_count"],
            "accepted_for_decision_support": timeline["quality"]["accepted_for_decision_support"],
        },
        "safety": timeline["safety"]
        | {
            "manual_external_execution_only": True,
            "user_submitted_execution_facts_only": True,
            "no_account_sync": True,
            "no_auto_rebalance": True,
            "no_production_records_mutation": True,
            "no_live_web_ingestion": True,
        },
        "hashes": {
            "timeline_json": _sha256(timeline_json),
            "timeline_md": _sha256(timeline_md),
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
                "# V2.0-D Event Timeline and Scenarios Acceptance",
                "",
                f"- status: {report['overall_status']}",
                f"- target: {report['acceptance_target']}",
                f"- run_id: {report['run_id']}",
                f"- timeline_json: `{report['timeline_json']}`",
                f"- timeline_md: `{report['timeline_md']}`",
                f"- event_count: `{report['summary']['event_count']}`",
                f"- scenario_count: `{report['summary']['scenario_count']}`",
                "- safety: read-only, no live web ingestion, no real trade, no broker API, social context is not fact",
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
                "target=V2.0-D Event Timeline and Scenarios",
                f"report_json={json_path}",
                f"report_json_sha256={_sha256(json_path)}",
                f"report_md={md_path}",
                f"report_md_sha256={_sha256(md_path)}",
                f"run_dir={report['run_dir']}",
                "dashboard_contract_changed=false",
                "production_records_written=false",
                "network_used=false",
                "failed=0",
                "",
            ]
        ),
        encoding="utf-8",
    )
    for stale in (reports_dir / FAIL_MARKER, reports_dir / "V2_0_D_EVENT_TIMELINE_FAIL_REASON.md"):
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
                "target=V2.0-D Event Timeline and Scenarios",
                "failed=1",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (reports_dir / "V2_0_D_EVENT_TIMELINE_FAIL_REASON.md").write_text(
        f"# V2.0-D Event Timeline and Scenarios Failed\n\n{type(exc).__name__}: {exc}\n",
        encoding="utf-8",
    )


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Validate Project Aegis V2.0-D Event Timeline and Scenarios.")
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
        print(f"[v2_0_d_event_timeline] FAIL: {type(exc).__name__}: {exc}")
        return 1

    print("[v2_0_d_event_timeline] PASS")
    print(f"run_id={report['run_id']}")
    print(f"report={reports_dir / REPORT_JSON}")
    print(f"marker={reports_dir / PASS_MARKER}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
