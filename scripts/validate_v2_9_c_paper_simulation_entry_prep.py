#!/usr/bin/env python3
"""Validate Project Aegis V2.9-C Paper Simulation Entry Prep."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aegis.paper.entry_prep import build_entry_prep_report  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_ROOT = ROOT / "data" / "processed" / "v2_9_c_acceptance"
DEFAULT_REPORTS_DIR = ROOT / "data" / "reports"
DEFAULT_PAPER_INTAKE_JSON = (
    ROOT
    / "data"
    / "processed"
    / "v2_9_b_acceptance"
    / "v2_9_b_20260711_acceptance"
    / "paper_simulation_intake_candidates.json"
)

PASS_MARKER = "V2_9_C_PAPER_SIMULATION_ENTRY_PREP_PASS.marker"
FAIL_MARKER = "V2_9_C_PAPER_SIMULATION_ENTRY_PREP_FAIL.marker"
REPORT_JSON = "v2_9_c_paper_simulation_entry_prep_latest.json"
REPORT_MD = "v2_9_c_paper_simulation_entry_prep_latest.md"


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def _run_id() -> str:
    return "v2_9_c_paper_entry_prep_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _sha256(path: Path) -> Optional[str]:
    if not path.exists():
        return None
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _render_markdown(report: dict) -> str:
    lines = [
        "# V2.9-C Paper Simulation Entry Prep",
        "",
        f"- status: `{report['overall_status']}`",
        f"- run_id: `{report['run_id']}`",
        f"- pending_entry_request_count: `{report['summary']['pending_entry_request_count']}`",
        f"- required_user_fields: `{', '.join(report['summary']['required_user_fields'])}`",
        "",
        "## Boundary",
        "",
        "- 只生成 pending virtual entry requests。",
        "- 不写 PaperTrade。",
        "- 不假造 entry_price。",
        "- 不假造 entry_date。",
        "- 不接 Broker API，不用 webhook，不自动下单。",
        "",
    ]
    for item in report["pending_entry_requests"]:
        lines.extend(
            [
                f"## {item['symbol']}",
                "",
                f"- market: `{item['market']}`",
                f"- status: `{item['entry_request_status']}`",
                f"- missing_fields: `{', '.join(item['missing_fields'])}`",
                f"- ready_to_create_paper_trade: `{item['ready_to_create_paper_trade']}`",
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
    paper_intake_json: Path = DEFAULT_PAPER_INTAKE_JSON,
) -> dict:
    run_id = run_id or _run_id()
    run_dir = output_root / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    reports_dir.mkdir(parents=True, exist_ok=True)

    paper_intake = json.loads(paper_intake_json.read_text(encoding="utf-8"))
    report = build_entry_prep_report(
        paper_intake,
        run_id=run_id,
        evidence_ref=str(paper_intake_json),
        command=command,
    )
    pending_requests_json = run_dir / "pending_paper_entry_requests.json"
    pending_requests_json.write_text(
        json.dumps(report["pending_entry_requests"], ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    checks = {
        **report["checks"],
        "acceptance_target_correct": report["acceptance_target"] == "V2.9-C Paper Simulation Entry Prep",
        "report_status_pass": report["overall_status"] == "PASS",
        "production_records_not_written": report["production_records_written"] is False,
        "paper_trades_not_written": report["paper_trades_written"] is False,
        "recommendations_not_written": report["recommendations_written"] is False,
        "dashboard_contract_unchanged": report["dashboard_contract_changed"] is False,
        "network_not_used": report["network_used"] is False,
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise RuntimeError("V2.9-C acceptance checks failed: " + ", ".join(failed))
    acceptance_report = {
        **report,
        "run_dir": str(run_dir),
        "source_paper_intake_json": str(paper_intake_json),
        "pending_entry_requests_json": str(pending_requests_json),
        "checks": checks,
        "hashes": {
            "source_paper_intake_json": _sha256(paper_intake_json),
            "pending_entry_requests_json": _sha256(pending_requests_json),
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
                "target=V2.9-C Paper Simulation Entry Prep",
                f"report_json={json_path}",
                f"report_json_sha256={_sha256(json_path)}",
                f"report_md={md_path}",
                f"report_md_sha256={_sha256(md_path)}",
                f"pending_entry_requests_json={report['pending_entry_requests_json']}",
                f"pending_entry_requests_json_sha256={report['hashes']['pending_entry_requests_json']}",
                "network_used=false",
                "production_records_written=false",
                "paper_trades_written=false",
                "recommendations_written=false",
                "dashboard_contract_changed=false",
                "paper_entry_request_only=true",
                "requires_user_price_before_paper_trade=true",
                "requires_user_date_before_paper_trade=true",
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
    parser.add_argument("--paper-intake-json", type=Path, default=DEFAULT_PAPER_INTAKE_JSON)
    args = parser.parse_args(argv)
    command = " ".join([Path(sys.argv[0]).name, *(argv if argv is not None else sys.argv[1:])])
    try:
        report = run_acceptance(
            output_root=args.output_root,
            reports_dir=args.reports_dir,
            run_id=args.run_id,
            command=command,
            paper_intake_json=args.paper_intake_json,
        )
    except Exception as exc:
        args.reports_dir.mkdir(parents=True, exist_ok=True)
        (args.reports_dir / FAIL_MARKER).write_text(
            "\n".join(
                [
                    f"generated_at={_now_iso()}",
                    f"command={command}",
                    "exit_code=1",
                    "target=V2.9-C Paper Simulation Entry Prep",
                    f"error={exc}",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        print(f"V2.9-C Paper Simulation Entry Prep FAIL: {exc}")
        return 1
    print(f"V2.9-C Paper Simulation Entry Prep PASS run_id={report['run_id']} report={args.reports_dir / REPORT_JSON}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
