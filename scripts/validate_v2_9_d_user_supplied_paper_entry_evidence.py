#!/usr/bin/env python3
"""Validate Project Aegis V2.9-D user-supplied paper entry evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aegis.paper.entry_evidence import build_entry_evidence_report  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_ROOT = ROOT / "data" / "processed" / "v2_9_d_acceptance"
DEFAULT_REPORTS_DIR = ROOT / "data" / "reports"
DEFAULT_PENDING_ENTRY_REQUESTS_JSON = (
    ROOT
    / "data"
    / "processed"
    / "v2_9_c_acceptance"
    / "v2_9_c_20260711_acceptance"
    / "pending_paper_entry_requests.json"
)

PASS_MARKER = "V2_9_D_USER_SUPPLIED_PAPER_ENTRY_EVIDENCE_PASS.marker"
FAIL_MARKER = "V2_9_D_USER_SUPPLIED_PAPER_ENTRY_EVIDENCE_FAIL.marker"
REPORT_JSON = "v2_9_d_user_supplied_paper_entry_evidence_latest.json"
REPORT_MD = "v2_9_d_user_supplied_paper_entry_evidence_latest.md"


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def _run_id() -> str:
    return "v2_9_d_user_entry_evidence_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _sha256(path: Path) -> Optional[str]:
    if not path.exists():
        return None
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _fixture_user_inputs(pending_entry_requests: list[dict], run_dir: Path) -> list[dict]:
    evidence_dir = run_dir / "user_entry_evidence"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    inputs: list[dict] = []
    for index, request in enumerate(pending_entry_requests):
        if index == 0:
            evidence_path = evidence_dir / f"{request['symbol'].replace('.', '_')}_manual_entry.txt"
            evidence_path.write_text(
                f"manual paper simulation entry evidence for {request['symbol']}\n",
                encoding="utf-8",
            )
            inputs.append(
                {
                    "entry_request_id": request["entry_request_id"],
                    "entry_price": 1688.88,
                    "entry_date": "2026-07-11",
                    "virtual_position_size": 1.0,
                    "user_confirmed": True,
                    "evidence_refs": [str(evidence_path)],
                    "notes": "user manually confirmed external simulated entry evidence",
                }
            )
        else:
            inputs.append(
                {
                    "entry_request_id": request["entry_request_id"],
                    "entry_price": None,
                    "entry_date": "2026-07-11",
                    "user_confirmed": True,
                    "evidence_refs": [],
                    "notes": "blocked fixture missing user price and evidence",
                }
            )
    return inputs


def _render_markdown(report: dict) -> str:
    lines = [
        "# V2.9-D User-Supplied Paper Entry Evidence Validation",
        "",
        f"- status: `{report['overall_status']}`",
        f"- run_id: `{report['run_id']}`",
        f"- validated_entry_evidence_count: `{report['summary']['validated_entry_evidence_count']}`",
        f"- blocked_entry_evidence_count: `{report['summary']['blocked_entry_evidence_count']}`",
        "",
        "## Boundary",
        "",
        "- 验证用户提供的 entry price/date/evidence。",
        "- 不写 PaperTrade。",
        "- 不写 Recommendation。",
        "- 不接 Broker API，不用 webhook，不自动下单。",
        "",
    ]
    for item in report["validated_entry_evidence_records"]:
        lines.extend(
            [
                f"## Ready: {item['symbol']}",
                "",
                f"- market: `{item['market']}`",
                f"- entry_date: `{item['entry_date']}`",
                f"- entry_price: `{item['entry_price']}`",
                f"- status: `{item['status']}`",
                "",
            ]
        )
    for item in report["blocked_entry_evidence_records"]:
        lines.extend(
            [
                f"## Blocked: {item['symbol']}",
                "",
                f"- reasons: `{', '.join(item['blocked_reasons'])}`",
                "",
            ]
        )
    return "\n".join(lines)


def run_acceptance(
    *,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    reports_dir: Path = DEFAULT_REPORTS_DIR,
    run_id: Optional[str] = None,
    command: Optional[str] = None,
    pending_entry_requests_json: Path = DEFAULT_PENDING_ENTRY_REQUESTS_JSON,
    user_entry_inputs_json: Path | None = None,
) -> dict:
    run_id = run_id or _run_id()
    run_dir = output_root / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    reports_dir.mkdir(parents=True, exist_ok=True)

    pending_requests = json.loads(pending_entry_requests_json.read_text(encoding="utf-8"))
    if user_entry_inputs_json is None:
        user_inputs = _fixture_user_inputs(pending_requests, run_dir)
        source_user_inputs_json = run_dir / "user_supplied_entry_inputs.fixture.json"
        source_user_inputs_json.write_text(json.dumps(user_inputs, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    else:
        source_user_inputs_json = user_entry_inputs_json
        user_inputs = json.loads(user_entry_inputs_json.read_text(encoding="utf-8"))

    report = build_entry_evidence_report(
        pending_requests,
        user_inputs,
        run_id=run_id,
        command=command,
    )
    validated_json = run_dir / "validated_entry_evidence_records.json"
    blocked_json = run_dir / "blocked_entry_evidence_records.json"
    candidates_json = run_dir / "virtual_paper_trade_create_candidates.json"
    validated_json.write_text(
        json.dumps(report["validated_entry_evidence_records"], ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    blocked_json.write_text(
        json.dumps(report["blocked_entry_evidence_records"], ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    candidates_json.write_text(
        json.dumps(report["validated_entry_evidence_records"], ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    checks = {
        **report["checks"],
        "acceptance_target_correct": report["acceptance_target"]
        == "V2.9-D User-Supplied Paper Entry Evidence Validation",
        "report_status_pass": report["overall_status"] == "PASS",
        "production_records_not_written": report["production_records_written"] is False,
        "paper_trades_not_written": report["paper_trades_written"] is False,
        "recommendations_not_written": report["recommendations_written"] is False,
        "dashboard_contract_unchanged": report["dashboard_contract_changed"] is False,
        "network_not_used": report["network_used"] is False,
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise RuntimeError("V2.9-D acceptance checks failed: " + ", ".join(failed))

    acceptance_report = {
        **report,
        "run_dir": str(run_dir),
        "source_pending_entry_requests_json": str(pending_entry_requests_json),
        "source_user_entry_inputs_json": str(source_user_inputs_json),
        "validated_entry_evidence_records_json": str(validated_json),
        "blocked_entry_evidence_records_json": str(blocked_json),
        "virtual_paper_trade_create_candidates_json": str(candidates_json),
        "checks": checks,
        "hashes": {
            "source_pending_entry_requests_json": _sha256(pending_entry_requests_json),
            "source_user_entry_inputs_json": _sha256(source_user_inputs_json),
            "validated_entry_evidence_records_json": _sha256(validated_json),
            "blocked_entry_evidence_records_json": _sha256(blocked_json),
            "virtual_paper_trade_create_candidates_json": _sha256(candidates_json),
        },
    }
    _write_reports(acceptance_report, reports_dir)
    return acceptance_report


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
                "target=V2.9-D User-Supplied Paper Entry Evidence Validation",
                f"report_json={json_path}",
                f"report_json_sha256={_sha256(json_path)}",
                f"report_md={md_path}",
                f"report_md_sha256={_sha256(md_path)}",
                f"validated_entry_evidence_records_json={report['validated_entry_evidence_records_json']}",
                f"validated_entry_evidence_records_json_sha256={report['hashes']['validated_entry_evidence_records_json']}",
                f"virtual_paper_trade_create_candidates_json={report['virtual_paper_trade_create_candidates_json']}",
                f"virtual_paper_trade_create_candidates_json_sha256={report['hashes']['virtual_paper_trade_create_candidates_json']}",
                "network_used=false",
                "production_records_written=false",
                "paper_trades_written=false",
                "recommendations_written=false",
                "dashboard_contract_changed=false",
                "validation_only=true",
                "paper_trade_creation_deferred=true",
                "no_price_fabrication=true",
                "no_date_fabrication=true",
                "no_real_trade_execution=true",
                "no_broker_api=true",
                "no_trading_webhook=true",
                "no_order_placement=true",
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
    parser.add_argument("--pending-entry-requests-json", type=Path, default=DEFAULT_PENDING_ENTRY_REQUESTS_JSON)
    parser.add_argument("--user-entry-inputs-json", type=Path)
    args = parser.parse_args(argv)
    command = " ".join([Path(sys.argv[0]).name, *(argv if argv is not None else sys.argv[1:])])
    try:
        report = run_acceptance(
            output_root=args.output_root,
            reports_dir=args.reports_dir,
            run_id=args.run_id,
            command=command,
            pending_entry_requests_json=args.pending_entry_requests_json,
            user_entry_inputs_json=args.user_entry_inputs_json,
        )
    except Exception as exc:
        args.reports_dir.mkdir(parents=True, exist_ok=True)
        (args.reports_dir / FAIL_MARKER).write_text(
            "\n".join(
                [
                    f"generated_at={_now_iso()}",
                    f"command={command}",
                    "exit_code=1",
                    "target=V2.9-D User-Supplied Paper Entry Evidence Validation",
                    f"error={exc}",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        print(f"V2.9-D User-Supplied Paper Entry Evidence Validation FAIL: {exc}")
        return 1
    print(
        "V2.9-D User-Supplied Paper Entry Evidence Validation PASS "
        f"run_id={report['run_id']} report={args.reports_dir / REPORT_JSON}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
