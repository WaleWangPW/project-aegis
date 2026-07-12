#!/usr/bin/env python3
"""Validate V2.11-F A-share Tushare strategy candidate rebuild."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from aegis.strategy.a_share_tushare_candidate_rebuild import (  # noqa: E402
    build_a_share_tushare_candidate_rebuild_report,
)

REPORTS_DIR = ROOT / "data" / "reports"
OUTPUT_ROOT = ROOT / "data" / "processed" / "v2_11_f_acceptance"
SOURCE_V2_11_C_REPORT_JSON = (
    REPORTS_DIR / "v2_11_c_tushare_a_share_historical_sandbox_live_data_refresh_latest.json"
)
SOURCE_V2_11_D_REPORT_JSON = REPORTS_DIR / "v2_11_d_tushare_backed_a_share_suggestion_gate_refresh_latest.json"
SOURCE_V2_11_E_REPORT_JSON = REPORTS_DIR / "v2_11_e_current_action_packet_after_tushare_gate_latest.json"
SOURCE_V2_11_E_PASS_MARKER = REPORTS_DIR / "V2_11_E_CURRENT_ACTION_PACKET_AFTER_TUSHARE_GATE_PASS.marker"

PASS_MARKER = "V2_11_F_A_SHARE_TUSHARE_STRATEGY_CANDIDATE_REBUILD_PASS.marker"
FAIL_MARKER = "V2_11_F_A_SHARE_TUSHARE_STRATEGY_CANDIDATE_REBUILD_FAIL.marker"
REPORT_JSON = "v2_11_f_a_share_tushare_strategy_candidate_rebuild_latest.json"
REPORT_MD = "v2_11_f_a_share_tushare_strategy_candidate_rebuild_latest.md"


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _sha256(path: Path | None) -> str | None:
    if path is None or not path.exists():
        return None
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _render_markdown(report: dict) -> str:
    summary = report["summary"]
    lines = [
        "# V2.11-F A-Share Tushare Strategy Candidate Rebuild",
        "",
        f"- status: `{report['overall_status']}`",
        f"- run_id: `{report['run_id']}`",
        f"- source_failed_strategy_count: `{summary['source_failed_strategy_count']}`",
        f"- rebuild_proposal_count: `{summary['rebuild_proposal_count']}`",
        f"- user_facing_suggestion_count: `{summary['user_facing_suggestion_count']}`",
        f"- auto_applied_count: `{summary['auto_applied_count']}`",
        f"- next_stage: `{summary['next_stage']}`",
        "",
        "## Rebuild Proposals",
        "",
    ]
    for proposal in report["rebuild_proposals"]:
        lines.extend(
            [
                f"### {proposal['source_strategy_id']}",
                "",
                f"- decision: `{proposal['decision']}`",
                f"- candidate_status: `{proposal['candidate_status']}`",
                f"- failed_reasons: `{proposal['source_failed_reasons']}`",
                f"- rebuild_actions: `{proposal['rebuild_actions']}`",
                f"- minimum_total_sample_count: `{proposal['retest_requirements']['minimum_total_sample_count']}`",
                "",
            ]
        )
    lines.extend(
        [
            "## Boundary",
            "",
            "- Research rebuild only.",
            "- A-share remains blocked until rebuilt sandbox and Suggestion Gate pass.",
            "- No real trade, broker API, trading webhook, order placement, live price, or position size.",
            "- No production Recommendation/PaperTrade/Review/Memory record mutation.",
            "- Dashboard Contract unchanged.",
            "",
        ]
    )
    return "\n".join(lines)


def run_acceptance(
    *,
    output_root: Path = OUTPUT_ROOT,
    reports_dir: Path = REPORTS_DIR,
    run_id: str = "v2_11_f_20260711_acceptance",
    command: str | None = None,
    source_v2_11_c_report_json: Path = SOURCE_V2_11_C_REPORT_JSON,
    source_v2_11_d_report_json: Path = SOURCE_V2_11_D_REPORT_JSON,
    source_v2_11_e_report_json: Path = SOURCE_V2_11_E_REPORT_JSON,
    source_v2_11_e_pass_marker: Path = SOURCE_V2_11_E_PASS_MARKER,
) -> dict:
    run_dir = output_root / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    evidence_refs = [
        str(source_v2_11_c_report_json),
        str(source_v2_11_d_report_json),
        str(source_v2_11_e_report_json),
        str(source_v2_11_e_pass_marker),
    ]
    report = build_a_share_tushare_candidate_rebuild_report(
        source_v2_11_c=_load_json(source_v2_11_c_report_json),
        source_v2_11_d=_load_json(source_v2_11_d_report_json),
        source_v2_11_e=_load_json(source_v2_11_e_report_json),
        run_id=run_id,
        evidence_refs=evidence_refs,
        command=command,
    )

    proposals_json = run_dir / "a_share_tushare_rebuild_proposals.json"
    rebuild_report_json = run_dir / "a_share_tushare_strategy_candidate_rebuild_report.json"
    rebuild_report_md = run_dir / "a_share_tushare_strategy_candidate_rebuild_report.md"
    _write_json(proposals_json, {"rebuild_proposals": report["rebuild_proposals"]})
    _write_json(rebuild_report_json, report)
    rebuild_report_md.write_text(_render_markdown(report), encoding="utf-8")

    checks = {
        **report["checks"],
        "acceptance_target_correct": report["acceptance_target"]
        == "V2.11-F A-Share Tushare Strategy Candidate Rebuild",
        "report_status_pass": report["overall_status"] == "PASS",
        "source_v2_11_e_marker_exists": source_v2_11_e_pass_marker.exists(),
        "proposals_json_written": proposals_json.exists(),
        "rebuild_report_json_written": rebuild_report_json.exists(),
        "rebuild_report_md_written": rebuild_report_md.exists(),
        "hashes_recorded": True,
    }
    report["checks"] = checks
    report["overall_status"] = "PASS" if all(checks.values()) else "FAIL"
    report["generated_at"] = _now_iso()
    report["run_dir"] = str(run_dir)
    report["proposals_json"] = str(proposals_json)
    report["rebuild_report_json"] = str(rebuild_report_json)
    report["rebuild_report_md"] = str(rebuild_report_md)
    report["source_v2_11_c_report_json"] = str(source_v2_11_c_report_json)
    report["source_v2_11_d_report_json"] = str(source_v2_11_d_report_json)
    report["source_v2_11_e_report_json"] = str(source_v2_11_e_report_json)
    report["source_v2_11_e_pass_marker"] = str(source_v2_11_e_pass_marker)
    report["hashes"] = {
        "source_v2_11_c_report_json": _sha256(source_v2_11_c_report_json),
        "source_v2_11_d_report_json": _sha256(source_v2_11_d_report_json),
        "source_v2_11_e_report_json": _sha256(source_v2_11_e_report_json),
        "source_v2_11_e_pass_marker": _sha256(source_v2_11_e_pass_marker),
        "proposals_json": _sha256(proposals_json),
        "rebuild_report_json": _sha256(rebuild_report_json),
        "rebuild_report_md": _sha256(rebuild_report_md),
    }
    _write_json(rebuild_report_json, report)

    report_json = reports_dir / REPORT_JSON
    report_md = reports_dir / REPORT_MD
    _write_json(report_json, report)
    report_md.write_text(_render_markdown(report), encoding="utf-8")

    marker_name = PASS_MARKER if report["overall_status"] == "PASS" else FAIL_MARKER
    stale = reports_dir / (FAIL_MARKER if marker_name == PASS_MARKER else PASS_MARKER)
    if stale.exists():
        stale.unlink()
    (reports_dir / marker_name).write_text(
        "\n".join(
            [
                f"generated_at={report['generated_at']}",
                f"command={command or ''}",
                f"exit_code={0 if report['overall_status'] == 'PASS' else 1}",
                "target=V2.11-F A-Share Tushare Strategy Candidate Rebuild",
                f"report_json={report_json}",
                f"report_json_sha256={_sha256(report_json)}",
                f"report_md={report_md}",
                f"report_md_sha256={_sha256(report_md)}",
                f"proposals_json={proposals_json}",
                f"proposals_json_sha256={_sha256(proposals_json)}",
                f"source_v2_11_c_report_json={source_v2_11_c_report_json}",
                f"source_v2_11_c_report_json_sha256={_sha256(source_v2_11_c_report_json)}",
                f"source_v2_11_d_report_json={source_v2_11_d_report_json}",
                f"source_v2_11_d_report_json_sha256={_sha256(source_v2_11_d_report_json)}",
                f"source_v2_11_e_report_json={source_v2_11_e_report_json}",
                f"source_v2_11_e_report_json_sha256={_sha256(source_v2_11_e_report_json)}",
                f"rebuild_proposal_count={report['summary']['rebuild_proposal_count']}",
                "network_used=false",
                "production_records_written=false",
                "dashboard_contract_changed=false",
                "simulation_only=true",
                "manual_external_execution_only=true",
                "no_real_trade=true",
                "no_broker_api=true",
                "no_trading_webhook=true",
                "no_order_placement=true",
                "no_live_price=true",
                "no_position_size=true",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=OUTPUT_ROOT)
    parser.add_argument("--reports-dir", type=Path, default=REPORTS_DIR)
    parser.add_argument("--run-id", default="v2_11_f_20260711_acceptance")
    parser.add_argument("--source-v2-11-c-report-json", type=Path, default=SOURCE_V2_11_C_REPORT_JSON)
    parser.add_argument("--source-v2-11-d-report-json", type=Path, default=SOURCE_V2_11_D_REPORT_JSON)
    parser.add_argument("--source-v2-11-e-report-json", type=Path, default=SOURCE_V2_11_E_REPORT_JSON)
    parser.add_argument("--source-v2-11-e-pass-marker", type=Path, default=SOURCE_V2_11_E_PASS_MARKER)
    args = parser.parse_args(argv)
    command_args = argv if argv is not None else sys.argv[1:]
    command = " ".join([Path(sys.argv[0]).name, *command_args])
    report = run_acceptance(
        output_root=args.output_root,
        reports_dir=args.reports_dir,
        run_id=args.run_id,
        command=command,
        source_v2_11_c_report_json=args.source_v2_11_c_report_json,
        source_v2_11_d_report_json=args.source_v2_11_d_report_json,
        source_v2_11_e_report_json=args.source_v2_11_e_report_json,
        source_v2_11_e_pass_marker=args.source_v2_11_e_pass_marker,
    )
    print(
        "V2.11-F A-Share Tushare Strategy Candidate Rebuild",
        report["overall_status"],
        f"rebuild_proposals={report['summary']['rebuild_proposal_count']}",
        f"user_facing_suggestions={report['summary']['user_facing_suggestion_count']}",
        f"run_id={args.run_id}",
        f"report={args.reports_dir / REPORT_JSON}",
    )
    return 0 if report["overall_status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
