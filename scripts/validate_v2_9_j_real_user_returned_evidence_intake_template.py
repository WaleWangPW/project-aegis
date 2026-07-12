#!/usr/bin/env python3
"""Validate Project Aegis V2.9-J real user returned evidence intake template."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aegis.paper.returned_evidence_refresh import build_returned_evidence_refresh_report  # noqa: E402
from aegis.paper.returned_evidence_template import (  # noqa: E402
    materialize_example_returned_evidence,
    validate_materialized_example,
    validate_user_returned_evidence_template,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_ROOT = ROOT / "data" / "processed" / "v2_9_j_acceptance"
DEFAULT_REPORTS_DIR = ROOT / "data" / "reports"
DEFAULT_CURRENT_BRIEF_JSON = ROOT / "data" / "reports" / "v2_9_h_current_usable_simulation_brief_latest.json"
DEFAULT_REVIEW_MEMORY_JSON = ROOT / "data" / "reports" / "v2_9_g_formal_review_memory_records_latest.json"
USER_TEMPLATE = ROOT / "config" / "user_returned_evidence.user-template.json"
GITIGNORE = ROOT / ".gitignore"
RECORD_PATHS = {
    "reviews_jsonl": ROOT / "data" / "records" / "reviews.jsonl",
    "memory_jsonl": ROOT / "data" / "records" / "memory.jsonl",
    "investment_memory_jsonl": ROOT / "data" / "records" / "investment_memory.jsonl",
    "paper_trades_jsonl": ROOT / "data" / "records" / "paper_trades.jsonl",
    "recommendations_jsonl": ROOT / "data" / "records" / "recommendations.jsonl",
}

PASS_MARKER = "V2_9_J_REAL_USER_RETURNED_EVIDENCE_TEMPLATE_PASS.marker"
FAIL_MARKER = "V2_9_J_REAL_USER_RETURNED_EVIDENCE_TEMPLATE_FAIL.marker"
REPORT_JSON = "v2_9_j_real_user_returned_evidence_template_latest.json"
REPORT_MD = "v2_9_j_real_user_returned_evidence_template_latest.md"


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def _run_id() -> str:
    return "v2_9_j_real_user_returned_evidence_template_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _sha256(path: Path) -> Optional[str]:
    if not path.exists():
        return None
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _fingerprint(path: Path) -> dict:
    return {
        "exists": path.exists(),
        "size": path.stat().st_size if path.exists() else None,
        "sha256": _sha256(path),
    }


def _fingerprints(paths: dict[str, Path]) -> dict[str, dict]:
    return {name: _fingerprint(path) for name, path in paths.items()}


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _render_markdown(report: dict) -> str:
    return "\n".join(
        [
            "# V2.9-J Real User Returned Evidence Intake Template",
            "",
            f"- status: `{report['overall_status']}`",
            f"- run_id: `{report['run_id']}`",
            f"- template: `{report['user_template']}`",
            f"- local_user_file_path: `{report['local_user_file_path']}`",
            f"- materialized_example_status: `{report['materialized_example_validation']['overall_status']}`",
            "",
            "## Boundary",
            "",
            "- Template only; real user file stays local and gitignored.",
            "- No API keys, cookies, bearer tokens, broker credentials, or webhook URLs.",
            "- No production review/memory/paper trade/recommendation records are written.",
            "- No broker API, no trading webhook, no real order placement.",
            "",
        ]
    )


def run_acceptance(
    *,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    reports_dir: Path = DEFAULT_REPORTS_DIR,
    run_id: Optional[str] = None,
    command: Optional[str] = None,
    current_brief_json: Path = DEFAULT_CURRENT_BRIEF_JSON,
    review_memory_json: Path = DEFAULT_REVIEW_MEMORY_JSON,
    user_template: Path = USER_TEMPLATE,
    record_paths: dict[str, Path] = RECORD_PATHS,
) -> dict:
    run_id = run_id or _run_id()
    run_dir = output_root / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    reports_dir.mkdir(parents=True, exist_ok=True)

    before = _fingerprints(record_paths)
    current_brief = _load_json(current_brief_json)
    review_memory_report = _load_json(review_memory_json)
    template_payload = _load_json(user_template)
    gitignore_text = GITIGNORE.read_text(encoding="utf-8")
    template_validation = validate_user_returned_evidence_template(
        template_payload,
        current_brief=current_brief,
        gitignore_text=gitignore_text,
    )
    template_copy = run_dir / "user_returned_evidence.user-template.json"
    template_copy.write_text(json.dumps(template_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    example_evidence_path = run_dir / "example_user_returned_outcome_note.txt"
    example_evidence_path.write_text(
        "Template materialization example. User manually supplied this note; no secrets, no broker data.\n",
        encoding="utf-8",
    )
    materialized = materialize_example_returned_evidence(
        template_payload,
        current_brief=current_brief,
        evidence_path=example_evidence_path,
    )
    materialized_json = run_dir / "user_returned_evidence.local.example.json"
    materialized_json.write_text(json.dumps(materialized, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    materialized_validation = validate_materialized_example(
        materialized,
        current_brief=current_brief,
        formal_review_memory_report=review_memory_report,
    )
    refresh_report = build_returned_evidence_refresh_report(
        current_brief=current_brief,
        formal_review_memory_report=review_memory_report,
        returned_inputs=materialized,
        run_id=run_id,
        command=command,
    )
    refresh_report_json = run_dir / "v2_9_i_refresh_from_template_example.json"
    refresh_report_json.write_text(json.dumps(refresh_report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    after = _fingerprints(record_paths)

    checks = {
        "template_file_exists": user_template.exists(),
        "gitignore_exists": GITIGNORE.exists(),
        "template_validation_pass": template_validation["overall_status"] == "PASS",
        "materialized_example_validation_pass": materialized_validation["overall_status"] == "PASS",
        "v2_9_i_refresh_compatible": refresh_report["checks"]["outcome_refresh_present"] is True
        and refresh_report["checks"]["refreshed_memory_present"] is True,
        "actual_return_source_user_evidence": refresh_report["checks"]["actual_return_from_user_evidence_only"] is True,
        "no_return_fabrication": refresh_report["checks"]["no_return_fabrication"] is True,
        "production_record_files_unchanged": before == after,
        "production_records_not_written": refresh_report["production_records_written"] is False,
        "network_not_used": refresh_report["network_used"] is False,
        "dashboard_contract_unchanged": refresh_report["dashboard_contract_changed"] is False,
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise RuntimeError("V2.9-J acceptance checks failed: " + ", ".join(failed))

    report = {
        "overall_status": "PASS",
        "acceptance_target": "V2.9-J Real User Returned Evidence Intake Template",
        "generated_at": _now_iso(),
        "run_id": run_id,
        "command": command,
        "network_used": False,
        "production_records_written": False,
        "dashboard_contract_changed": False,
        "run_dir": str(run_dir),
        "user_template": str(user_template),
        "template_copy": str(template_copy),
        "local_user_file_path": template_payload["local_file_path"],
        "materialized_example_json": str(materialized_json),
        "example_evidence_path": str(example_evidence_path),
        "refresh_report_json": str(refresh_report_json),
        "source_current_brief_json": str(current_brief_json),
        "source_review_memory_json": str(review_memory_json),
        "template_validation": template_validation,
        "materialized_example_validation": materialized_validation,
        "refresh_report_summary": refresh_report["summary"],
        "production_record_files_before": before,
        "production_record_files_after": after,
        "checks": checks,
        "safety": {
            "simulation_only": True,
            "template_only": True,
            "local_user_file_gitignored": True,
            "user_returned_evidence_only": True,
            "actual_return_from_user_evidence_only": True,
            "no_return_fabrication": True,
            "production_records_not_written": True,
            "no_real_trade_execution": True,
            "no_broker_api": True,
            "no_webhook": True,
            "no_order_placement": True,
            "no_strategy_mutation": True,
            "dashboard_contract_unchanged": True,
        },
        "hashes": {
            "user_template": _sha256(user_template),
            "template_copy": _sha256(template_copy),
            "materialized_example_json": _sha256(materialized_json),
            "example_evidence_path": _sha256(example_evidence_path),
            "refresh_report_json": _sha256(refresh_report_json),
            "source_current_brief_json": _sha256(current_brief_json),
            "source_review_memory_json": _sha256(review_memory_json),
        },
    }
    _write_reports(report, reports_dir)
    return report


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
                "target=V2.9-J Real User Returned Evidence Intake Template",
                f"report_json={json_path}",
                f"report_json_sha256={_sha256(json_path)}",
                f"report_md={md_path}",
                f"report_md_sha256={_sha256(md_path)}",
                f"user_template={report['user_template']}",
                f"user_template_sha256={report['hashes']['user_template']}",
                f"materialized_example_json={report['materialized_example_json']}",
                f"materialized_example_json_sha256={report['hashes']['materialized_example_json']}",
                "network_used=false",
                "production_records_written=false",
                "dashboard_contract_changed=false",
                "simulation_only=true",
                "template_only=true",
                "local_user_file_gitignored=true",
                "user_returned_evidence_only=true",
                "actual_return_from_user_evidence_only=true",
                "no_return_fabrication=true",
                "no_real_trade_execution=true",
                "no_broker_api=true",
                "no_trading_webhook=true",
                "no_order_placement=true",
                "no_strategy_mutation=true",
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
    parser.add_argument("--current-brief-json", type=Path, default=DEFAULT_CURRENT_BRIEF_JSON)
    parser.add_argument("--review-memory-json", type=Path, default=DEFAULT_REVIEW_MEMORY_JSON)
    parser.add_argument("--user-template", type=Path, default=USER_TEMPLATE)
    args = parser.parse_args(argv)
    command = " ".join([Path(sys.argv[0]).name, *(argv if argv is not None else sys.argv[1:])])

    try:
        report = run_acceptance(
            output_root=args.output_root,
            reports_dir=args.reports_dir,
            run_id=args.run_id,
            command=command,
            current_brief_json=args.current_brief_json,
            review_memory_json=args.review_memory_json,
            user_template=args.user_template,
        )
    except Exception as exc:
        args.reports_dir.mkdir(parents=True, exist_ok=True)
        (args.reports_dir / FAIL_MARKER).write_text(
            "\n".join(
                [
                    f"generated_at={_now_iso()}",
                    f"command={command}",
                    "exit_code=1",
                    "target=V2.9-J Real User Returned Evidence Intake Template",
                    f"error={exc}",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        print(f"V2.9-J Real User Returned Evidence Intake Template FAIL: {exc}")
        return 1

    print(
        "V2.9-J Real User Returned Evidence Intake Template "
        f"PASS run_id={report['run_id']} report={args.reports_dir / REPORT_JSON}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
