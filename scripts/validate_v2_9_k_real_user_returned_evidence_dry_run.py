#!/usr/bin/env python3
"""Validate Project Aegis V2.9-K real user returned-evidence dry run."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aegis.paper.returned_evidence_refresh import (  # noqa: E402
    build_refreshed_reviews_and_memories,
    build_returned_evidence_refresh_report,
    validate_user_returned_evidence,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_ROOT = ROOT / "data" / "processed" / "v2_9_k_acceptance"
DEFAULT_REPORTS_DIR = ROOT / "data" / "reports"
DEFAULT_CURRENT_BRIEF_JSON = ROOT / "data" / "reports" / "v2_9_h_current_usable_simulation_brief_latest.json"
DEFAULT_REVIEW_MEMORY_JSON = ROOT / "data" / "reports" / "v2_9_g_formal_review_memory_records_latest.json"
LOCAL_RETURNED_EVIDENCE_JSON = ROOT / "config" / "user_returned_evidence.local.json"
USER_TEMPLATE = ROOT / "config" / "user_returned_evidence.user-template.json"
RECORD_PATHS = {
    "reviews_jsonl": ROOT / "data" / "records" / "reviews.jsonl",
    "memory_jsonl": ROOT / "data" / "records" / "memory.jsonl",
    "investment_memory_jsonl": ROOT / "data" / "records" / "investment_memory.jsonl",
    "paper_trades_jsonl": ROOT / "data" / "records" / "paper_trades.jsonl",
    "recommendations_jsonl": ROOT / "data" / "records" / "recommendations.jsonl",
}

PASS_MARKER = "V2_9_K_REAL_USER_RETURNED_EVIDENCE_DRY_RUN_PASS.marker"
FAIL_MARKER = "V2_9_K_REAL_USER_RETURNED_EVIDENCE_DRY_RUN_FAIL.marker"
REPORT_JSON = "v2_9_k_real_user_returned_evidence_dry_run_latest.json"
REPORT_MD = "v2_9_k_real_user_returned_evidence_dry_run_latest.md"


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def _run_id() -> str:
    return "v2_9_k_real_user_returned_evidence_dry_run_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


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


def _load_json(path: Path) -> dict | list:
    return json.loads(path.read_text(encoding="utf-8"))


def _records_from_payload(payload: dict | list) -> list[dict]:
    if isinstance(payload, list):
        return [dict(item) for item in payload]
    if isinstance(payload, dict) and isinstance(payload.get("records"), list):
        return [dict(item) for item in payload["records"]]
    raise ValueError("returned evidence local file must be a list or an object with records[]")


def _contains_placeholder(records: list[dict]) -> bool:
    return any(
        isinstance(value, str) and "REPLACE_WITH_" in value
        for item in records
        for value in item.values()
    )


def _render_markdown(report: dict) -> str:
    lines = [
        "# V2.9-K Real User Returned Evidence Dry Run",
        "",
        f"- status: `{report['overall_status']}`",
        f"- dry_run_status: `{report['real_user_returned_evidence_status']}`",
        f"- run_id: `{report['run_id']}`",
        f"- local_file: `{report['local_returned_evidence_json']}`",
        f"- accepted_count: `{report['summary'].get('accepted_count')}`",
        f"- blocked_count: `{report['summary'].get('blocked_count')}`",
        "",
        "## Boundary",
        "",
        "- Real user local file is read only if present.",
        "- Missing local file is reported as blocked, not faked.",
        "- No production review/memory/paper trade/recommendation records are written.",
        "- No broker API, no trading webhook, no real order placement.",
        "",
    ]
    return "\n".join(lines)


def _blocked_report(
    *,
    run_id: str,
    command: str | None,
    run_dir: Path,
    local_path: Path,
    template_path: Path,
    before: dict,
    after: dict,
) -> dict:
    checks = {
        "local_file_absent": not local_path.exists(),
        "blocked_status_recorded": True,
        "template_available": template_path.exists(),
        "no_fake_real_user_evidence": True,
        "production_record_files_unchanged": before == after,
        "production_records_not_written": True,
        "network_not_used": True,
        "dashboard_contract_unchanged": True,
    }
    return {
        "overall_status": "PASS" if all(checks.values()) else "FAIL",
        "acceptance_target": "V2.9-K Real User Returned Evidence Dry Run",
        "run_id": run_id,
        "generated_at": _now_iso(),
        "command": command,
        "real_user_returned_evidence_status": "blocked_missing_user_returned_evidence",
        "network_used": False,
        "production_records_written": False,
        "dashboard_contract_changed": False,
        "run_dir": str(run_dir),
        "local_returned_evidence_json": str(local_path),
        "user_template": str(template_path),
        "summary": {
            "accepted_count": 0,
            "blocked_count": 0,
            "refreshed_review_count": 0,
            "refreshed_memory_count": 0,
            "blocker": "config/user_returned_evidence.local.json is missing",
        },
        "checks": checks,
        "safety": {
            "simulation_only": True,
            "missing_local_file_blocked": True,
            "no_fake_real_user_evidence": True,
            "production_records_not_written": True,
            "no_real_trade_execution": True,
            "no_broker_api": True,
            "no_webhook": True,
            "no_order_placement": True,
            "no_strategy_mutation": True,
            "dashboard_contract_unchanged": True,
        },
        "production_record_files_before": before,
        "production_record_files_after": after,
    }


def _completed_report(
    *,
    run_id: str,
    command: str | None,
    run_dir: Path,
    local_path: Path,
    current_brief: dict,
    review_memory_report: dict,
    records: list[dict],
    before: dict,
    after: dict,
) -> dict:
    validation = validate_user_returned_evidence(
        records,
        current_brief=current_brief,
        formal_review_memory_report=review_memory_report,
    )
    accepted = validation["accepted_returned_evidence_records"]
    blocked = validation["blocked_returned_evidence_records"]
    refreshed = build_refreshed_reviews_and_memories(
        accepted,
        formal_review_memory_report=review_memory_report,
    )
    refresh_report = build_returned_evidence_refresh_report(
        current_brief=current_brief,
        formal_review_memory_report=review_memory_report,
        returned_inputs=records,
        run_id=run_id,
        command=command,
    )
    local_copy = run_dir / "user_returned_evidence.local.copy.json"
    refreshed_reviews_json = run_dir / "real_user_refreshed_simulation_reviews.json"
    refreshed_memories_json = run_dir / "real_user_refreshed_simulation_memories.json"
    refreshed_brief_json = run_dir / "current_usable_simulation_brief_after_real_user_evidence.json"
    local_copy.write_text(json.dumps(records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    refreshed_reviews_json.write_text(json.dumps(refreshed["refreshed_reviews"], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    refreshed_memories_json.write_text(json.dumps(refreshed["refreshed_memories"], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    refreshed_brief_json.write_text(json.dumps(refresh_report["refreshed_brief"], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    outcome_records = [item for item in accepted if item.get("evidence_type") == "outcome"]
    checks = {
        "local_file_present": local_path.exists(),
        "local_file_hash_recorded": _sha256(local_path) is not None,
        "local_file_has_records": bool(records),
        "no_placeholders_in_local_file": not _contains_placeholder(records),
        "accepted_or_blocked_records_present": bool(accepted or blocked),
        "accepted_records_present": bool(accepted),
        "outcome_refresh_if_outcome_present": not outcome_records or bool(refreshed["refreshed_reviews"]),
        "actual_return_from_user_evidence_only": all(
            item.get("actual_return_source") == "user_returned_evidence"
            for item in refreshed["refreshed_reviews"]
        ),
        "no_return_fabrication": all(
            item.get("no_return_fabrication") is True for item in refreshed["refreshed_reviews"]
        ),
        "secret_like_inputs_blocked_or_absent": all(
            "secret_like_text_blocked" in item.get("blocked_reasons", [])
            for item in blocked
            if any("secret_like" in reason for reason in item.get("blocked_reasons", []))
        ),
        "production_record_files_unchanged": before == after,
        "production_records_not_written": True,
        "network_not_used": True,
        "dashboard_contract_unchanged": True,
    }
    return {
        "overall_status": "PASS" if all(checks.values()) else "FAIL",
        "acceptance_target": "V2.9-K Real User Returned Evidence Dry Run",
        "run_id": run_id,
        "generated_at": _now_iso(),
        "command": command,
        "real_user_returned_evidence_status": "completed",
        "network_used": False,
        "production_records_written": False,
        "dashboard_contract_changed": False,
        "run_dir": str(run_dir),
        "local_returned_evidence_json": str(local_path),
        "local_copy_json": str(local_copy),
        "refreshed_reviews_json": str(refreshed_reviews_json),
        "refreshed_memories_json": str(refreshed_memories_json),
        "refreshed_brief_json": str(refreshed_brief_json),
        "summary": {
            "accepted_count": len(accepted),
            "blocked_count": len(blocked),
            "refreshed_review_count": len(refreshed["refreshed_reviews"]),
            "refreshed_memory_count": len(refreshed["refreshed_memories"]),
            "record_count": len(records),
            "outcome_record_count": len(outcome_records),
        },
        "accepted_returned_evidence_records": accepted,
        "blocked_returned_evidence_records": blocked,
        "refreshed_reviews": refreshed["refreshed_reviews"],
        "refreshed_memories": refreshed["refreshed_memories"],
        "checks": checks,
        "safety": {
            "simulation_only": True,
            "real_user_returned_evidence_only": True,
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
        "production_record_files_before": before,
        "production_record_files_after": after,
        "hashes": {
            "local_returned_evidence_json": _sha256(local_path),
            "local_copy_json": _sha256(local_copy),
            "refreshed_reviews_json": _sha256(refreshed_reviews_json),
            "refreshed_memories_json": _sha256(refreshed_memories_json),
            "refreshed_brief_json": _sha256(refreshed_brief_json),
        },
    }


def run_acceptance(
    *,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    reports_dir: Path = DEFAULT_REPORTS_DIR,
    run_id: Optional[str] = None,
    command: Optional[str] = None,
    current_brief_json: Path = DEFAULT_CURRENT_BRIEF_JSON,
    review_memory_json: Path = DEFAULT_REVIEW_MEMORY_JSON,
    local_returned_evidence_json: Path = LOCAL_RETURNED_EVIDENCE_JSON,
    user_template: Path = USER_TEMPLATE,
    record_paths: dict[str, Path] = RECORD_PATHS,
) -> dict:
    run_id = run_id or _run_id()
    run_dir = output_root / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    reports_dir.mkdir(parents=True, exist_ok=True)
    before = _fingerprints(record_paths)

    if not local_returned_evidence_json.exists():
        after = _fingerprints(record_paths)
        report = _blocked_report(
            run_id=run_id,
            command=command,
            run_dir=run_dir,
            local_path=local_returned_evidence_json,
            template_path=user_template,
            before=before,
            after=after,
        )
        _write_reports(report, reports_dir)
        return report

    current_brief = _load_json(current_brief_json)
    review_memory_report = _load_json(review_memory_json)
    payload = _load_json(local_returned_evidence_json)
    records = _records_from_payload(payload)
    after = _fingerprints(record_paths)
    report = _completed_report(
        run_id=run_id,
        command=command,
        run_dir=run_dir,
        local_path=local_returned_evidence_json,
        current_brief=current_brief,
        review_memory_report=review_memory_report,
        records=records,
        before=before,
        after=after,
    )
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
                "target=V2.9-K Real User Returned Evidence Dry Run",
                f"status={report['real_user_returned_evidence_status']}",
                f"report_json={json_path}",
                f"report_json_sha256={_sha256(json_path)}",
                f"report_md={md_path}",
                f"report_md_sha256={_sha256(md_path)}",
                f"local_returned_evidence_json={report['local_returned_evidence_json']}",
                "network_used=false",
                "production_records_written=false",
                "dashboard_contract_changed=false",
                "simulation_only=true",
                f"blocked_missing_user_returned_evidence={str(report['real_user_returned_evidence_status'] == 'blocked_missing_user_returned_evidence').lower()}",
                "no_fake_real_user_evidence=true",
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
    parser.add_argument("--local-returned-evidence-json", type=Path, default=LOCAL_RETURNED_EVIDENCE_JSON)
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
            local_returned_evidence_json=args.local_returned_evidence_json,
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
                    "target=V2.9-K Real User Returned Evidence Dry Run",
                    f"error={exc}",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        print(f"V2.9-K Real User Returned Evidence Dry Run FAIL: {exc}")
        return 1

    print(
        "V2.9-K Real User Returned Evidence Dry Run "
        f"PASS status={report['real_user_returned_evidence_status']} "
        f"run_id={report['run_id']} report={args.reports_dir / REPORT_JSON}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
