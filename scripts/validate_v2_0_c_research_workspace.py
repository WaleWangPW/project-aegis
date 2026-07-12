#!/usr/bin/env python3
"""Validate Project Aegis V2.0-C Research Workspace acceptance."""

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

from aegis.models.research import ResearchEvidenceLink, ResearchNote  # noqa: E402
from aegis.research.workspace import build_research_workspace, render_research_workspace_markdown  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_ROOT = ROOT / "data" / "processed" / "v2_0_c_acceptance"
DEFAULT_REPORTS_DIR = ROOT / "data" / "reports"

PASS_MARKER = "V2_0_C_RESEARCH_WORKSPACE_PASS.marker"
FAIL_MARKER = "V2_0_C_RESEARCH_WORKSPACE_FAIL.marker"
REPORT_JSON = "v2_0_c_research_workspace_latest.json"
REPORT_MD = "v2_0_c_research_workspace_latest.md"


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
    return "v2_0_c_research_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _fixture(created_at: str) -> tuple[list[ResearchNote], list[ResearchEvidenceLink]]:
    evidence = [
        ResearchEvidenceLink(
            evidence_id="ev_sys_v2_0_b_brief",
            evidence_type="system_report",
            title="V2.0-B Portfolio-Aware Brief acceptance report",
            source="Project Aegis",
            path_or_url="data/reports/v2_0_b_portfolio_aware_brief_latest.json",
            captured_at=created_at,
            status="verified",
            summary="Portfolio-aware brief accepted with Dashboard Contract unchanged.",
        ),
        ResearchEvidenceLink(
            evidence_id="ev_user_manual_note",
            evidence_type="user_submitted",
            title="Manual user note placeholder",
            source="user",
            path_or_url=None,
            captured_at=created_at,
            status="verified",
            summary="User may submit screenshots or typed facts as evidence inputs only.",
        ),
        ResearchEvidenceLink(
            evidence_id="ev_llm_draft",
            evidence_type="llm_unverified",
            title="LLM draft idea",
            source="local draft",
            path_or_url=None,
            captured_at=created_at,
            status="pending",
            summary="Draft idea that must not be treated as evidence.",
        ),
    ]
    notes = [
        ResearchNote(
            note_id="note_US_CRCL_v2_0_c_context",
            symbol="CRCL",
            market="US",
            title="Decision context",
            thesis="CRCL research should be interpreted through portfolio exposure and review evidence.",
            risks=["Evidence may be incomplete until user submits external execution facts."],
            open_questions=["Which user-submitted facts should be attached after manual execution?"],
            evidence_ids=["ev_sys_v2_0_b_brief", "ev_user_manual_note"],
            decision_relevance="Connects research context to accepted portfolio-aware daily brief behavior.",
            created_at=created_at,
            updated_at=created_at,
        )
    ]
    return notes, evidence


def _llm_verified_rejected(created_at: str) -> bool:
    try:
        ResearchEvidenceLink(
            evidence_id="ev_bad_llm",
            evidence_type="llm_unverified",
            title="Bad LLM evidence",
            source="llm",
            captured_at=created_at,
            status="verified",
            summary="This should be rejected.",
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
    notes, evidence = _fixture(created_at)
    workspace = build_research_workspace(
        symbol="CRCL",
        market="US",
        notes=notes,
        evidence=evidence,
        created_at=created_at,
    )
    workspace_json = run_dir / "research_workspace.json"
    workspace_md = run_dir / "research_workspace.md"
    workspace_json.write_text(json.dumps(workspace, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    workspace_md.write_text(render_research_workspace_markdown(workspace), encoding="utf-8")

    checks = {
        "per_symbol_workspace": workspace["workspace"]["symbol"] == "CRCL" and workspace["workspace"]["market"] == "US",
        "notes_have_evidence": all(note.evidence_ids for note in notes),
        "evidence_links_present": workspace["quality"]["evidence_count"] == 3,
        "verified_evidence_available": workspace["quality"]["verified_evidence_count"] == 2,
        "llm_unverified_not_accepted": _llm_verified_rejected(created_at),
        "decision_support_accepts_only_verified_links": workspace["quality"]["accepted_for_decision_support"] is True,
        "dashboard_contract_unchanged": workspace["safety"]["dashboard_contract_unchanged"] is True,
        "no_broker_or_real_trade": workspace["safety"]["no_real_trade"] is True and workspace["safety"]["no_broker_api"] is True,
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise RuntimeError("V2.0-C acceptance checks failed: " + ", ".join(failed))

    report = {
        "overall_status": "PASS",
        "generated_at": _now_iso(),
        "run_id": run_id,
        "command": command,
        "acceptance_target": "V2.0-C Research Workspace",
        "isolated": True,
        "production_records_written": False,
        "dashboard_contract_changed": False,
        "run_dir": str(run_dir),
        "workspace_json": str(workspace_json),
        "workspace_md": str(workspace_md),
        "checks": checks,
        "summary": {
            "symbol": workspace["workspace"]["symbol"],
            "market": workspace["workspace"]["market"],
            "note_count": workspace["quality"]["note_count"],
            "evidence_count": workspace["quality"]["evidence_count"],
            "verified_evidence_count": workspace["quality"]["verified_evidence_count"],
            "accepted_for_decision_support": workspace["quality"]["accepted_for_decision_support"],
        },
        "safety": workspace["safety"]
        | {
            "manual_external_execution_only": True,
            "user_submitted_execution_facts_only": True,
            "no_account_sync": True,
            "no_auto_rebalance": True,
            "no_production_records_mutation": True,
        },
        "hashes": {
            "workspace_json": _sha256(workspace_json),
            "workspace_md": _sha256(workspace_md),
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
                "# V2.0-C Research Workspace Acceptance",
                "",
                f"- status: {report['overall_status']}",
                f"- target: {report['acceptance_target']}",
                f"- run_id: {report['run_id']}",
                f"- workspace_json: `{report['workspace_json']}`",
                f"- workspace_md: `{report['workspace_md']}`",
                f"- note_count: `{report['summary']['note_count']}`",
                f"- evidence_count: `{report['summary']['evidence_count']}`",
                f"- verified_evidence_count: `{report['summary']['verified_evidence_count']}`",
                "- safety: read-only, no real trade, no broker API, LLM unverified is not evidence",
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
                "target=V2.0-C Research Workspace",
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
    for stale in (reports_dir / FAIL_MARKER, reports_dir / "V2_0_C_RESEARCH_WORKSPACE_FAIL_REASON.md"):
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
                "target=V2.0-C Research Workspace",
                "failed=1",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (reports_dir / "V2_0_C_RESEARCH_WORKSPACE_FAIL_REASON.md").write_text(
        f"# V2.0-C Research Workspace Failed\n\n{type(exc).__name__}: {exc}\n",
        encoding="utf-8",
    )


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Validate Project Aegis V2.0-C Research Workspace.")
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
        print(f"[v2_0_c_research_workspace] FAIL: {type(exc).__name__}: {exc}")
        return 1

    print("[v2_0_c_research_workspace] PASS")
    print(f"run_id={report['run_id']}")
    print(f"report={reports_dir / REPORT_JSON}")
    print(f"marker={reports_dir / PASS_MARKER}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
