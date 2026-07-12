#!/usr/bin/env python3
"""Validate V2.8-C source audit to sandbox refresh queue."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aegis.strategy.source_audit_refresh import write_source_audit_sandbox_refresh_queue  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_ROOT = ROOT / "data" / "processed" / "v2_8_c_acceptance"
DEFAULT_REPORTS_DIR = ROOT / "data" / "reports"
DEFAULT_AUDIT_REPORT = ROOT / "data" / "reports" / "v2_8_b_live_public_strategy_source_audit_latest.json"

PASS_MARKER = "V2_8_C_SOURCE_AUDIT_SANDBOX_REFRESH_QUEUE_PASS.marker"
FAIL_MARKER = "V2_8_C_SOURCE_AUDIT_SANDBOX_REFRESH_QUEUE_FAIL.marker"
REPORT_JSON = "v2_8_c_source_audit_sandbox_refresh_queue_latest.json"
REPORT_MD = "v2_8_c_source_audit_sandbox_refresh_queue_latest.md"


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def _run_id() -> str:
    return "v2_8_c_source_audit_refresh_queue_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _sha256(path: Path) -> Optional[str]:
    if not path.exists():
        return None
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def run_acceptance(
    *,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    reports_dir: Path = DEFAULT_REPORTS_DIR,
    source_audit_report: Path = DEFAULT_AUDIT_REPORT,
    run_id: Optional[str] = None,
    command: Optional[str] = None,
) -> dict:
    run_id = run_id or _run_id()
    run_dir = output_root / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    reports_dir.mkdir(parents=True, exist_ok=True)

    audit_report = _load_json(source_audit_report)
    queue_json = run_dir / "source_audit_sandbox_refresh_queue.json"
    queue = write_source_audit_sandbox_refresh_queue(
        audit_report,
        queue_json,
        run_id=run_id,
        command=command,
    )

    checks = queue["checks"]
    required_checks = [
        "source_audit_passed",
        "uses_live_public_source_audit",
        "network_not_used",
        "reachable_sources_have_hashes",
        "all_reachable_sources_queued",
        "blocked_sources_preserved",
        "blocked_sources_not_queued",
        "covers_a_h_us_with_reachable_sources",
        "requires_sandbox",
        "not_auto_applied",
        "no_user_facing_suggestion",
        "proposal_hashes_written",
        "raw_text_not_stored",
        "sample_bytes_not_stored",
        "no_real_trade",
        "no_broker_api",
        "no_trading_webhook",
        "no_strategy_auto_mutation",
        "no_production_records_mutation",
    ]
    failed = [name for name in required_checks if not checks.get(name)]
    if failed:
        raise RuntimeError("V2.8-C acceptance checks failed: " + ", ".join(failed))

    report = {
        **queue,
        "run_dir": str(run_dir),
        "source_audit_report": str(source_audit_report),
        "source_audit_sandbox_refresh_queue": str(queue_json),
        "production_records_written": False,
        "dashboard_contract_changed": False,
        "summary": {
            "audited_source_count": queue["audited_source_count"],
            "reachable_source_count": queue["reachable_source_count"],
            "blocked_source_count": queue["blocked_source_count"],
            "refresh_proposal_count": queue["refresh_proposal_count"],
            "proposal_ids": [item["proposal_id"] for item in queue["refresh_proposals"]],
            "blocked_source_ids": [item["research_id"] for item in queue["blocked_sources"]],
            "next_target": "V2.8-D Refresh Queue Historical Sandbox Rerun",
        },
        "hashes": {
            "source_audit_report": _sha256(source_audit_report),
            "source_audit_sandbox_refresh_queue": _sha256(queue_json),
        },
    }
    _write_reports(report, reports_dir)
    return report


def _render_markdown(report: dict) -> str:
    return "\n".join(
        [
            "# V2.8-C Source Audit To Sandbox Refresh Queue",
            "",
            f"- status: `{report['overall_status']}`",
            f"- run_id: `{report['run_id']}`",
            f"- source_audit_report: `{report['source_audit_report']}`",
            f"- queue: `{report['source_audit_sandbox_refresh_queue']}`",
            f"- audited_source_count: `{report['summary']['audited_source_count']}`",
            f"- reachable_source_count: `{report['summary']['reachable_source_count']}`",
            f"- blocked_source_count: `{report['summary']['blocked_source_count']}`",
            f"- refresh_proposal_count: `{report['summary']['refresh_proposal_count']}`",
            f"- proposal_ids: `{report['summary']['proposal_ids']}`",
            f"- blocked_source_ids: `{report['summary']['blocked_source_ids']}`",
            "",
            "## Boundary",
            "",
            "- Uses the existing V2.8-B report; no new network fetch.",
            "- Reachable sources can only create sandbox refresh proposals.",
            "- Failed sources remain explicit blockers and are not queued.",
            "- No direct user-facing suggestion, no real trade, no broker API, no trading webhook.",
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
                "target=V2.8-C Source Audit To Sandbox Refresh Queue",
                f"report_json={json_path}",
                f"report_json_sha256={_sha256(json_path)}",
                f"report_md={md_path}",
                f"report_md_sha256={_sha256(md_path)}",
                f"source_audit_report={report['source_audit_report']}",
                f"source_audit_report_sha256={report['hashes']['source_audit_report']}",
                f"source_audit_sandbox_refresh_queue={report['source_audit_sandbox_refresh_queue']}",
                f"source_audit_sandbox_refresh_queue_sha256={report['hashes']['source_audit_sandbox_refresh_queue']}",
                f"audited_source_count={report['summary']['audited_source_count']}",
                f"reachable_source_count={report['summary']['reachable_source_count']}",
                f"blocked_source_count={report['summary']['blocked_source_count']}",
                f"refresh_proposal_count={report['summary']['refresh_proposal_count']}",
                "network_used=false",
                "production_records_written=false",
                "dashboard_contract_changed=false",
                "requires_sandbox=true",
                "auto_applied=false",
                "user_facing_suggestion_allowed=false",
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
    parser.add_argument("--source-audit-report", type=Path, default=DEFAULT_AUDIT_REPORT)
    parser.add_argument("--run-id")
    args = parser.parse_args(argv)
    command = " ".join([Path(sys.argv[0]).name, *(argv if argv is not None else sys.argv[1:])])
    try:
        report = run_acceptance(
            output_root=args.output_root,
            reports_dir=args.reports_dir,
            source_audit_report=args.source_audit_report,
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
                    "target=V2.8-C Source Audit To Sandbox Refresh Queue",
                    f"error={exc}",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        print(f"V2.8-C Source Audit To Sandbox Refresh Queue FAIL: {exc}")
        return 1

    print(
        "V2.8-C Source Audit To Sandbox Refresh Queue PASS "
        f"run_id={report['run_id']} report={args.reports_dir / REPORT_JSON}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
