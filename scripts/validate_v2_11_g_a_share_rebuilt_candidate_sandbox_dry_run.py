#!/usr/bin/env python3
"""Validate V2.11-G A-share rebuilt candidate sandbox dry-run."""

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

from aegis.strategy.a_share_rebuilt_candidate_sandbox import (  # noqa: E402
    build_a_share_rebuilt_candidate_sandbox_report,
)

REPORTS_DIR = ROOT / "data" / "reports"
OUTPUT_ROOT = ROOT / "data" / "processed" / "v2_11_g_acceptance"
SOURCE_V2_11_C_REPORT_JSON = (
    REPORTS_DIR / "v2_11_c_tushare_a_share_historical_sandbox_live_data_refresh_latest.json"
)
SOURCE_V2_11_F_REPORT_JSON = REPORTS_DIR / "v2_11_f_a_share_tushare_strategy_candidate_rebuild_latest.json"
SOURCE_V2_11_F_PASS_MARKER = REPORTS_DIR / "V2_11_F_A_SHARE_TUSHARE_STRATEGY_CANDIDATE_REBUILD_PASS.marker"

PASS_MARKER = "V2_11_G_A_SHARE_REBUILT_CANDIDATE_SANDBOX_DRY_RUN_PASS.marker"
FAIL_MARKER = "V2_11_G_A_SHARE_REBUILT_CANDIDATE_SANDBOX_DRY_RUN_FAIL.marker"
REPORT_JSON = "v2_11_g_a_share_rebuilt_candidate_sandbox_dry_run_latest.json"
REPORT_MD = "v2_11_g_a_share_rebuilt_candidate_sandbox_dry_run_latest.md"


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
        "# V2.11-G A-Share Rebuilt Candidate Sandbox Dry Run",
        "",
        f"- status: `{report['overall_status']}`",
        f"- run_id: `{report['run_id']}`",
        f"- rebuilt_candidate_count: `{summary['rebuilt_candidate_count']}`",
        f"- expanded_case_count: `{summary['expanded_case_count']}`",
        f"- strategy_pass_count: `{summary['strategy_pass_count']}`",
        f"- strategy_fail_count: `{summary['strategy_fail_count']}`",
        f"- a_share_reentry_allowed: `{summary['a_share_reentry_allowed']}`",
        f"- next_stage: `{summary['next_stage']}`",
        "",
        "## Results",
        "",
    ]
    for result in report["results"]:
        metrics = result["metrics"]
        lines.extend(
            [
                f"### {result['strategy_id']}",
                "",
                f"- status: `{result['status']}`",
                f"- sample_count: `{metrics['sample_count']}`",
                f"- win_rate: `{metrics['win_rate']}`",
                f"- average_return: `{metrics['average_return']}`",
                f"- max_drawdown: `{metrics['max_drawdown']}`",
                f"- failed_reasons: `{metrics['failed_reasons']}`",
                "",
            ]
        )
    lines.extend(
        [
            "## Boundary",
            "",
            "- Expanded historical sandbox only.",
            "- A-share remains blocked because no rebuilt strategy passed.",
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
    run_id: str = "v2_11_g_20260711_acceptance",
    command: str | None = None,
    source_v2_11_c_report_json: Path = SOURCE_V2_11_C_REPORT_JSON,
    source_v2_11_f_report_json: Path = SOURCE_V2_11_F_REPORT_JSON,
    source_v2_11_f_pass_marker: Path = SOURCE_V2_11_F_PASS_MARKER,
    cache_dir: Path | None = None,
) -> dict:
    run_dir = output_root / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    source_c = _load_json(source_v2_11_c_report_json)
    source_f = _load_json(source_v2_11_f_report_json)
    resolved_cache_dir = cache_dir or Path(source_c["source_historical_cache_dir"])
    evidence_refs = [str(source_v2_11_c_report_json), str(source_v2_11_f_report_json), str(source_v2_11_f_pass_marker)]
    report = build_a_share_rebuilt_candidate_sandbox_report(
        source_v2_11_c=source_c,
        source_v2_11_f=source_f,
        cache_dir=resolved_cache_dir,
        run_id=run_id,
        evidence_refs=evidence_refs,
        command=command,
    )

    candidates_json = run_dir / "a_share_rebuilt_candidates.json"
    cases_jsonl = run_dir / "a_share_rebuilt_expanded_cases.jsonl"
    sandbox_report_json = run_dir / "a_share_rebuilt_candidate_sandbox_report.json"
    sandbox_report_md = run_dir / "a_share_rebuilt_candidate_sandbox_report.md"
    _write_json(candidates_json, {"rebuilt_candidates": report["rebuilt_candidates"]})
    cases_jsonl.write_text(
        "".join(json.dumps(item, ensure_ascii=False) + "\n" for item in report["expanded_cases"]),
        encoding="utf-8",
    )
    _write_json(sandbox_report_json, report)
    sandbox_report_md.write_text(_render_markdown(report), encoding="utf-8")

    checks = {
        **report["checks"],
        "acceptance_target_correct": report["acceptance_target"]
        == "V2.11-G A-Share Rebuilt Candidate Sandbox Dry Run",
        "report_status_pass": report["overall_status"] == "PASS",
        "source_v2_11_f_marker_exists": source_v2_11_f_pass_marker.exists(),
        "cache_dir_exists": resolved_cache_dir.exists(),
        "candidates_json_written": candidates_json.exists(),
        "cases_jsonl_written": cases_jsonl.exists(),
        "sandbox_report_json_written": sandbox_report_json.exists(),
        "sandbox_report_md_written": sandbox_report_md.exists(),
        "hashes_recorded": True,
    }
    report["checks"] = checks
    report["overall_status"] = "PASS" if all(checks.values()) else "FAIL"
    report["generated_at"] = _now_iso()
    report["run_dir"] = str(run_dir)
    report["cache_dir"] = str(resolved_cache_dir)
    report["rebuilt_candidates_json"] = str(candidates_json)
    report["expanded_cases_jsonl"] = str(cases_jsonl)
    report["sandbox_report_json"] = str(sandbox_report_json)
    report["sandbox_report_md"] = str(sandbox_report_md)
    report["source_v2_11_c_report_json"] = str(source_v2_11_c_report_json)
    report["source_v2_11_f_report_json"] = str(source_v2_11_f_report_json)
    report["source_v2_11_f_pass_marker"] = str(source_v2_11_f_pass_marker)
    report["hashes"] = {
        "source_v2_11_c_report_json": _sha256(source_v2_11_c_report_json),
        "source_v2_11_f_report_json": _sha256(source_v2_11_f_report_json),
        "source_v2_11_f_pass_marker": _sha256(source_v2_11_f_pass_marker),
        "rebuilt_candidates_json": _sha256(candidates_json),
        "expanded_cases_jsonl": _sha256(cases_jsonl),
        "sandbox_report_json": _sha256(sandbox_report_json),
        "sandbox_report_md": _sha256(sandbox_report_md),
    }
    _write_json(sandbox_report_json, report)

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
                "target=V2.11-G A-Share Rebuilt Candidate Sandbox Dry Run",
                f"report_json={report_json}",
                f"report_json_sha256={_sha256(report_json)}",
                f"report_md={report_md}",
                f"report_md_sha256={_sha256(report_md)}",
                f"expanded_cases_jsonl={cases_jsonl}",
                f"expanded_cases_jsonl_sha256={_sha256(cases_jsonl)}",
                f"strategy_pass_count={report['summary']['strategy_pass_count']}",
                f"strategy_fail_count={report['summary']['strategy_fail_count']}",
                f"expanded_case_count={report['summary']['expanded_case_count']}",
                f"a_share_reentry_allowed={str(report['summary']['a_share_reentry_allowed']).lower()}",
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
    parser.add_argument("--run-id", default="v2_11_g_20260711_acceptance")
    parser.add_argument("--source-v2-11-c-report-json", type=Path, default=SOURCE_V2_11_C_REPORT_JSON)
    parser.add_argument("--source-v2-11-f-report-json", type=Path, default=SOURCE_V2_11_F_REPORT_JSON)
    parser.add_argument("--source-v2-11-f-pass-marker", type=Path, default=SOURCE_V2_11_F_PASS_MARKER)
    parser.add_argument("--cache-dir", type=Path, default=None)
    args = parser.parse_args(argv)
    command_args = argv if argv is not None else sys.argv[1:]
    command = " ".join([Path(sys.argv[0]).name, *command_args])
    report = run_acceptance(
        output_root=args.output_root,
        reports_dir=args.reports_dir,
        run_id=args.run_id,
        command=command,
        source_v2_11_c_report_json=args.source_v2_11_c_report_json,
        source_v2_11_f_report_json=args.source_v2_11_f_report_json,
        source_v2_11_f_pass_marker=args.source_v2_11_f_pass_marker,
        cache_dir=args.cache_dir,
    )
    print(
        "V2.11-G A-Share Rebuilt Candidate Sandbox Dry Run",
        report["overall_status"],
        f"expanded_cases={report['summary']['expanded_case_count']}",
        f"pass={report['summary']['strategy_pass_count']}",
        f"fail={report['summary']['strategy_fail_count']}",
        f"a_share_reentry_allowed={report['summary']['a_share_reentry_allowed']}",
        f"run_id={args.run_id}",
        f"report={args.reports_dir / REPORT_JSON}",
    )
    return 0 if report["overall_status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
