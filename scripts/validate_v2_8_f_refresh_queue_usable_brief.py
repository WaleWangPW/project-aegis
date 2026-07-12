#!/usr/bin/env python3
"""Validate V2.8-F refresh queue usable brief."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aegis.strategy.refresh_queue_brief import (  # noqa: E402
    build_refresh_queue_usable_brief,
    render_refresh_queue_usable_brief_markdown,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_ROOT = ROOT / "data" / "processed" / "v2_8_f_acceptance"
DEFAULT_REPORTS_DIR = ROOT / "data" / "reports"
DEFAULT_SUGGESTION_DRAFTS = (
    ROOT
    / "data"
    / "processed"
    / "v2_8_e_acceptance"
    / "v2_8_e_20260711_acceptance"
    / "refresh_queue_suggestion_drafts.json"
)
DEFAULT_EVIDENCE_REFS = [
    str(ROOT / "data" / "reports" / "v2_8_e_refresh_queue_suggestion_gate_latest.json"),
    str(ROOT / "data" / "reports" / "V2_8_E_REFRESH_QUEUE_SUGGESTION_GATE_PASS.marker"),
]

PASS_MARKER = "V2_8_F_REFRESH_QUEUE_USABLE_BRIEF_PASS.marker"
FAIL_MARKER = "V2_8_F_REFRESH_QUEUE_USABLE_BRIEF_FAIL.marker"
REPORT_JSON = "v2_8_f_refresh_queue_usable_brief_latest.json"
REPORT_MD = "v2_8_f_refresh_queue_usable_brief_latest.md"


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def _run_id() -> str:
    return "v2_8_f_refresh_queue_usable_brief_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _sha256(path: Path) -> Optional[str]:
    if not path.exists():
        return None
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _load_json(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))


def run_acceptance(
    *,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    reports_dir: Path = DEFAULT_REPORTS_DIR,
    suggestion_drafts_json: Path = DEFAULT_SUGGESTION_DRAFTS,
    run_id: Optional[str] = None,
    command: Optional[str] = None,
) -> dict:
    run_id = run_id or _run_id()
    run_dir = output_root / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    reports_dir.mkdir(parents=True, exist_ok=True)

    drafts = _load_json(suggestion_drafts_json)
    brief = build_refresh_queue_usable_brief(
        suggestion_drafts=drafts,
        run_id=run_id,
        evidence_refs=DEFAULT_EVIDENCE_REFS,
    )
    brief_json = run_dir / "refresh_queue_usable_brief.json"
    brief_md = run_dir / "refresh_queue_usable_brief.md"
    source_drafts_copy = run_dir / "source_refresh_queue_suggestion_drafts.json"
    brief_json.write_text(json.dumps(brief, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    brief_md.write_text(render_refresh_queue_usable_brief_markdown(brief), encoding="utf-8")
    source_drafts_copy.write_text(json.dumps(drafts, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    checks = {
        **brief["checks"],
        "acceptance_target_correct": brief["acceptance_target"] == "V2.8-F Refresh Queue Usable Brief Update",
        "report_status_pass": brief["overall_status"] == "PASS",
        "production_records_not_written": brief["production_records_written"] is False,
        "dashboard_contract_unchanged": brief["dashboard_contract_changed"] is False,
        "network_not_used": brief["network_used"] is False,
        "no_real_trade": brief["safety"]["no_real_trade"] is True,
        "no_trading_webhook": brief["safety"]["no_trading_webhook"] is True,
        "strategy_basket_not_stock_order": brief["safety"]["strategy_basket_not_stock_order"] is True,
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise RuntimeError("V2.8-F acceptance checks failed: " + ", ".join(failed))

    acceptance_report = {
        **brief,
        "command": command,
        "run_dir": str(run_dir),
        "source_suggestion_drafts_json": str(suggestion_drafts_json),
        "brief_json": str(brief_json),
        "brief_md": str(brief_md),
        "copied_source_suggestion_drafts_json": str(source_drafts_copy),
        "checks": checks,
        "hashes": {
            "source_suggestion_drafts_json": _sha256(suggestion_drafts_json),
            "brief_json": _sha256(brief_json),
            "brief_md": _sha256(brief_md),
            "copied_source_suggestion_drafts_json": _sha256(source_drafts_copy),
        },
    }
    _write_reports(acceptance_report, reports_dir)
    return acceptance_report


def _write_reports(report: dict, reports_dir: Path) -> None:
    json_path = reports_dir / REPORT_JSON
    md_path = reports_dir / REPORT_MD
    marker_path = reports_dir / PASS_MARKER
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md_path.write_text(render_refresh_queue_usable_brief_markdown(report), encoding="utf-8")
    marker_path.write_text(
        "\n".join(
            [
                f"generated_at={report['generated_at']}",
                f"command={report.get('command') or ''}",
                "exit_code=0",
                "target=V2.8-F Refresh Queue Usable Brief Update",
                f"report_json={json_path}",
                f"report_json_sha256={_sha256(json_path)}",
                f"report_md={md_path}",
                f"report_md_sha256={_sha256(md_path)}",
                f"brief_json={report['brief_json']}",
                f"brief_json_sha256={report['hashes']['brief_json']}",
                "network_used=false",
                "production_records_written=false",
                "dashboard_contract_changed=false",
                "simulation_only=true",
                "manual_external_execution_only=true",
                "strategy_basket_not_stock_order=true",
                "no_real_trade=true",
                "no_broker_api=true",
                "no_trading_webhook=true",
                "no_live_order=true",
                "no_live_price=true",
                "no_position_size=true",
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
    parser.add_argument("--suggestion-drafts-json", type=Path, default=DEFAULT_SUGGESTION_DRAFTS)
    parser.add_argument("--run-id")
    args = parser.parse_args(argv)
    command = " ".join([Path(sys.argv[0]).name, *(argv if argv is not None else sys.argv[1:])])
    try:
        report = run_acceptance(
            output_root=args.output_root,
            reports_dir=args.reports_dir,
            suggestion_drafts_json=args.suggestion_drafts_json,
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
                    "target=V2.8-F Refresh Queue Usable Brief Update",
                    f"error={exc}",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        print(f"V2.8-F Refresh Queue Usable Brief FAIL: {exc}")
        return 1

    print(
        "V2.8-F Refresh Queue Usable Brief PASS "
        f"run_id={report['run_id']} report={args.reports_dir / REPORT_JSON}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
