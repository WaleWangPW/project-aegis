#!/usr/bin/env python3
"""Validate V2.14-C refreshed candidate historical sandbox."""

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

from aegis.strategy.refreshed_candidate_historical_sandbox import (  # noqa: E402
    ACCEPTANCE_TARGET,
    build_refreshed_candidate_historical_sandbox_report,
    render_refreshed_candidate_historical_sandbox_markdown,
)

REPORTS_DIR = ROOT / "data" / "reports"
OUTPUT_ROOT = ROOT / "data" / "processed" / "v2_14_c_acceptance"
SOURCE_V2_14_B_REPORT_JSON = REPORTS_DIR / "v2_14_b_candidate_pool_live_refresh_latest.json"
SOURCE_V2_14_B_PASS_MARKER = REPORTS_DIR / "V2_14_B_CANDIDATE_POOL_LIVE_REFRESH_PASS.marker"
SOURCE_V2_11_C_REPORT_JSON = REPORTS_DIR / "v2_11_c_tushare_a_share_historical_sandbox_live_data_refresh_latest.json"
SOURCE_V2_11_C_PASS_MARKER = REPORTS_DIR / "V2_11_C_TUSHARE_A_SHARE_HISTORICAL_SANDBOX_LIVE_DATA_REFRESH_PASS.marker"
SOURCE_V2_12_C_REPORT_JSON = REPORTS_DIR / "v2_12_c_h_us_historical_cache_readiness_latest.json"
SOURCE_V2_12_C_PASS_MARKER = REPORTS_DIR / "V2_12_C_H_US_HISTORICAL_CACHE_READINESS_PASS.marker"

RECORD_PATHS = {
    "recommendations_jsonl": ROOT / "data" / "records" / "recommendations.jsonl",
    "paper_trades_jsonl": ROOT / "data" / "records" / "paper_trades.jsonl",
    "reviews_jsonl": ROOT / "data" / "records" / "reviews.jsonl",
    "memory_jsonl": ROOT / "data" / "records" / "memory.jsonl",
    "investment_memory_jsonl": ROOT / "data" / "records" / "investment_memory.jsonl",
}

PASS_MARKER = "V2_14_C_REFRESHED_CANDIDATE_HISTORICAL_SANDBOX_PASS.marker"
FAIL_MARKER = "V2_14_C_REFRESHED_CANDIDATE_HISTORICAL_SANDBOX_FAIL.marker"
REPORT_JSON = "v2_14_c_refreshed_candidate_historical_sandbox_latest.json"
REPORT_MD = "v2_14_c_refreshed_candidate_historical_sandbox_latest.md"


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


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run_acceptance(
    *,
    output_root: Path = OUTPUT_ROOT,
    reports_dir: Path = REPORTS_DIR,
    run_id: str = "v2_14_c_20260712_acceptance",
    command: str | None = None,
    source_v2_14_b_report_json: Path = SOURCE_V2_14_B_REPORT_JSON,
    source_v2_14_b_pass_marker: Path = SOURCE_V2_14_B_PASS_MARKER,
    source_v2_11_c_report_json: Path = SOURCE_V2_11_C_REPORT_JSON,
    source_v2_11_c_pass_marker: Path = SOURCE_V2_11_C_PASS_MARKER,
    source_v2_12_c_report_json: Path = SOURCE_V2_12_C_REPORT_JSON,
    source_v2_12_c_pass_marker: Path = SOURCE_V2_12_C_PASS_MARKER,
    record_paths: dict[str, Path] = RECORD_PATHS,
) -> dict:
    run_dir = output_root / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    before = _fingerprints(record_paths)
    report = build_refreshed_candidate_historical_sandbox_report(
        refresh_report=_load_json(source_v2_14_b_report_json),
        a_source_report=_load_json(source_v2_11_c_report_json),
        h_source_report=_load_json(source_v2_12_c_report_json),
        run_id=run_id,
        command=command,
    )
    sandbox_json = run_dir / "refreshed_candidate_historical_sandbox.json"
    sandbox_md = run_dir / "refreshed_candidate_historical_sandbox.md"
    cases_jsonl = run_dir / "refreshed_candidate_historical_cases.jsonl"
    _write_json(sandbox_json, report)
    sandbox_md.write_text(render_refreshed_candidate_historical_sandbox_markdown(report), encoding="utf-8")
    cases_jsonl.write_text(
        "".join(json.dumps(case, ensure_ascii=False) + "\n" for case in report["historical_cases"]),
        encoding="utf-8",
    )
    after = _fingerprints(record_paths)

    checks = {
        **report["checks"],
        "acceptance_target_correct": report["acceptance_target"] == ACCEPTANCE_TARGET,
        "sandbox_status_pass": report["overall_status"] == "PASS",
        "source_v2_14_b_report_exists": source_v2_14_b_report_json.exists(),
        "source_v2_14_b_marker_exists": source_v2_14_b_pass_marker.exists(),
        "source_v2_11_c_report_exists": source_v2_11_c_report_json.exists(),
        "source_v2_11_c_marker_exists": source_v2_11_c_pass_marker.exists(),
        "source_v2_12_c_report_exists": source_v2_12_c_report_json.exists(),
        "source_v2_12_c_marker_exists": source_v2_12_c_pass_marker.exists(),
        "sandbox_json_written": sandbox_json.exists(),
        "sandbox_md_written": sandbox_md.exists(),
        "cases_jsonl_written": cases_jsonl.exists(),
        "production_record_files_unchanged": before == after,
        "source_hashes_recorded": True,
    }
    report["checks"] = checks
    report["overall_status"] = "PASS" if all(checks.values()) else "FAIL"
    report["generated_at"] = _now_iso()
    report["run_dir"] = str(run_dir)
    report["sandbox_json"] = str(sandbox_json)
    report["sandbox_md"] = str(sandbox_md)
    report["cases_jsonl"] = str(cases_jsonl)
    report["source_v2_14_b_report_json"] = str(source_v2_14_b_report_json)
    report["source_v2_14_b_pass_marker"] = str(source_v2_14_b_pass_marker)
    report["source_v2_11_c_report_json"] = str(source_v2_11_c_report_json)
    report["source_v2_11_c_pass_marker"] = str(source_v2_11_c_pass_marker)
    report["source_v2_12_c_report_json"] = str(source_v2_12_c_report_json)
    report["source_v2_12_c_pass_marker"] = str(source_v2_12_c_pass_marker)
    report["production_record_files_before"] = before
    report["production_record_files_after"] = after
    report["hashes"] = {
        "source_v2_14_b_report_json": _sha256(source_v2_14_b_report_json),
        "source_v2_14_b_pass_marker": _sha256(source_v2_14_b_pass_marker),
        "source_v2_11_c_report_json": _sha256(source_v2_11_c_report_json),
        "source_v2_11_c_pass_marker": _sha256(source_v2_11_c_pass_marker),
        "source_v2_12_c_report_json": _sha256(source_v2_12_c_report_json),
        "source_v2_12_c_pass_marker": _sha256(source_v2_12_c_pass_marker),
        "sandbox_json": _sha256(sandbox_json),
        "sandbox_md": _sha256(sandbox_md),
        "cases_jsonl": _sha256(cases_jsonl),
    }
    _write_json(sandbox_json, report)

    report_json = reports_dir / REPORT_JSON
    report_md = reports_dir / REPORT_MD
    _write_json(report_json, report)
    report_md.write_text(render_refreshed_candidate_historical_sandbox_markdown(report), encoding="utf-8")

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
                f"target={ACCEPTANCE_TARGET}",
                f"report_json={report_json}",
                f"report_json_sha256={_sha256(report_json)}",
                f"report_md={report_md}",
                f"report_md_sha256={_sha256(report_md)}",
                f"sandbox_json={sandbox_json}",
                f"sandbox_json_sha256={_sha256(sandbox_json)}",
                f"sandbox_md={sandbox_md}",
                f"sandbox_md_sha256={_sha256(sandbox_md)}",
                f"cases_jsonl={cases_jsonl}",
                f"cases_jsonl_sha256={_sha256(cases_jsonl)}",
                f"covered_candidate_count={report['summary']['covered_candidate_count']}",
                f"missing_coverage_count={report['summary']['missing_coverage_count']}",
                f"historical_case_count={report['summary']['historical_case_count']}",
                f"strategy_pass_count={report['summary']['strategy_pass_count']}",
                f"strategy_fail_count={report['summary']['strategy_fail_count']}",
                "network_used=false",
                "not_user_facing_suggestion=true",
                "suggestion_gate_required=true",
                "production_records_written=false",
                "production_cache_mutated=false",
                "production_provider_config_mutated=false",
                "dashboard_contract_changed=false",
                "no_secret_values_stored=true",
                "request_urls_not_stored=true",
                "raw_payloads_not_stored=true",
                "no_real_trade=true",
                "no_broker_api=true",
                "no_webhook=true",
                "no_order_placement=true",
                "no_position_size=true",
                "no_live_order_signal=true",
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
    parser.add_argument("--run-id", default="v2_14_c_20260712_acceptance")
    parser.add_argument("--source-v2-14-b-report-json", type=Path, default=SOURCE_V2_14_B_REPORT_JSON)
    parser.add_argument("--source-v2-14-b-pass-marker", type=Path, default=SOURCE_V2_14_B_PASS_MARKER)
    parser.add_argument("--source-v2-11-c-report-json", type=Path, default=SOURCE_V2_11_C_REPORT_JSON)
    parser.add_argument("--source-v2-11-c-pass-marker", type=Path, default=SOURCE_V2_11_C_PASS_MARKER)
    parser.add_argument("--source-v2-12-c-report-json", type=Path, default=SOURCE_V2_12_C_REPORT_JSON)
    parser.add_argument("--source-v2-12-c-pass-marker", type=Path, default=SOURCE_V2_12_C_PASS_MARKER)
    args = parser.parse_args(argv)
    command_args = argv if argv is not None else sys.argv[1:]
    command = " ".join([Path(sys.argv[0]).name, *command_args])
    report = run_acceptance(
        output_root=args.output_root,
        reports_dir=args.reports_dir,
        run_id=args.run_id,
        command=command,
        source_v2_14_b_report_json=args.source_v2_14_b_report_json,
        source_v2_14_b_pass_marker=args.source_v2_14_b_pass_marker,
        source_v2_11_c_report_json=args.source_v2_11_c_report_json,
        source_v2_11_c_pass_marker=args.source_v2_11_c_pass_marker,
        source_v2_12_c_report_json=args.source_v2_12_c_report_json,
        source_v2_12_c_pass_marker=args.source_v2_12_c_pass_marker,
    )
    print(
        ACCEPTANCE_TARGET,
        report["overall_status"],
        f"covered_candidate_count={report['summary']['covered_candidate_count']}",
        f"missing_coverage_count={report['summary']['missing_coverage_count']}",
        f"strategy_pass_count={report['summary']['strategy_pass_count']}",
        f"strategy_fail_count={report['summary']['strategy_fail_count']}",
        f"run_id={args.run_id}",
        f"report={args.reports_dir / REPORT_JSON}",
    )
    return 0 if report["overall_status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
