#!/usr/bin/env python3
"""Validate Project Aegis V2.5-B Approved Live Candidate Refresh."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aegis.strategy.candidate_refresh import (  # noqa: E402
    build_candidate_refresh_report,
    default_approved_candidate_source_registry,
    load_candidate_source_registry,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_ROOT = ROOT / "data" / "processed" / "v2_5_b_acceptance"
DEFAULT_REPORTS_DIR = ROOT / "data" / "reports"
SUGGESTION_DRAFTS_JSON = (
    ROOT
    / "data"
    / "processed"
    / "v2_4_d_acceptance"
    / "v2_4_d_20260711_acceptance"
    / "research_hypothesis_suggestion_drafts.json"
)

PASS_MARKER = "V2_5_B_APPROVED_CANDIDATE_REFRESH_PASS.marker"
FAIL_MARKER = "V2_5_B_APPROVED_CANDIDATE_REFRESH_FAIL.marker"
REPORT_JSON = "v2_5_b_candidate_refresh_latest.json"
REPORT_MD = "v2_5_b_candidate_refresh_latest.md"


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def _run_id() -> str:
    return "v2_5_b_candidate_refresh_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


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
    run_id: Optional[str] = None,
    command: Optional[str] = None,
    suggestion_drafts_json: Path = SUGGESTION_DRAFTS_JSON,
    source_registry_json: Optional[Path] = None,
) -> dict:
    run_id = run_id or _run_id()
    run_dir = output_root / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    reports_dir.mkdir(parents=True, exist_ok=True)

    suggestion_drafts = _load_json(suggestion_drafts_json)
    registry = (
        load_candidate_source_registry(source_registry_json)
        if source_registry_json is not None
        else default_approved_candidate_source_registry()
    )
    source_registry_out = run_dir / "approved_candidate_source_registry.json"
    refreshed_bindings_json = run_dir / "refreshed_candidate_bindings.json"
    source_suggestions_json = run_dir / "source_suggestion_drafts.json"
    source_registry_out.write_text(json.dumps(registry.model_dump(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    report = build_candidate_refresh_report(
        suggestion_drafts,
        registry,
        run_id=run_id,
        evidence_ref=str(source_registry_out),
        command=command,
    )
    refreshed_bindings_json.write_text(json.dumps(report["bindings"], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    source_suggestions_json.write_text(json.dumps(suggestion_drafts, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    checks = {
        "candidate_refresh_passed": report["overall_status"] == "PASS",
        "a_h_us_bound": set(report["summary"]["bound_markets"]) >= {"A", "H", "US"},
        "h_candidate_source_present": report["summary"]["candidate_counts_by_market"]["H"] >= 1,
        "fixture_status_honest": report["safety"]["fixture_not_live_market_data"] is True,
        "user_api_live_blocked_until_metadata": report["user_api_live_status"] == "blocked_missing_metadata",
        "approved_sources_only": report["safety"]["approved_sources_only"] is True,
        "no_secret_values_stored": report["safety"]["no_secret_values_stored"] is True,
        "manual_external_execution_only": report["safety"]["manual_external_execution_only"] is True,
        "no_real_trade_or_broker": report["safety"]["no_real_trade"] is True
        and report["safety"]["no_broker_api"] is True,
        "no_webhook": report["safety"]["no_webhook"] is True,
        "no_production_records_mutation": report["production_records_written"] is False,
        "dashboard_contract_unchanged": report["dashboard_contract_changed"] is False,
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise RuntimeError("V2.5-B acceptance checks failed: " + ", ".join(failed))

    acceptance_report = {
        **report,
        "run_dir": str(run_dir),
        "source_suggestion_drafts_json": str(suggestion_drafts_json),
        "source_registry_json": str(source_registry_json) if source_registry_json else None,
        "approved_candidate_source_registry_json": str(source_registry_out),
        "refreshed_candidate_bindings_json": str(refreshed_bindings_json),
        "copied_source_suggestion_drafts_json": str(source_suggestions_json),
        "checks": checks,
        "hashes": {
            "source_suggestion_drafts_json": _sha256(suggestion_drafts_json),
            "approved_candidate_source_registry_json": _sha256(source_registry_out),
            "refreshed_candidate_bindings_json": _sha256(refreshed_bindings_json),
            "copied_source_suggestion_drafts_json": _sha256(source_suggestions_json),
        },
    }
    _write_reports(acceptance_report, reports_dir)
    return acceptance_report


def _write_reports(report: dict, reports_dir: Path) -> None:
    json_path = reports_dir / REPORT_JSON
    md_path = reports_dir / REPORT_MD
    marker_path = reports_dir / PASS_MARKER
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md_path.write_text(
        "\n".join(
            [
                "# V2.5-B Approved Candidate Refresh Acceptance",
                "",
                f"- status: {report['overall_status']}",
                f"- target: {report['acceptance_target']}",
                f"- run_id: {report['run_id']}",
                f"- refreshed_bindings_json: `{report['refreshed_candidate_bindings_json']}`",
                f"- bound_markets: `{report['summary']['bound_markets']}`",
                f"- candidate_counts_by_market: `{report['summary']['candidate_counts_by_market']}`",
                f"- user_api_live_status: `{report['user_api_live_status']}`",
                "- safety: approved fixture refresh, not live market data, no broker/trading/webhook/secrets",
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
                "target=V2.5-B Approved Live Candidate Refresh",
                f"report_json={json_path}",
                f"report_json_sha256={_sha256(json_path)}",
                f"report_md={md_path}",
                f"report_md_sha256={_sha256(md_path)}",
                f"refreshed_candidate_bindings_json={report['refreshed_candidate_bindings_json']}",
                f"refreshed_candidate_bindings_json_sha256={report['hashes']['refreshed_candidate_bindings_json']}",
                "network_used=false",
                "user_api_live_status=blocked_missing_metadata",
                "production_records_written=false",
                "dashboard_contract_changed=false",
                "simulation_only=true",
                "manual_external_execution_only=true",
                "no_real_trade=true",
                "no_broker_api=true",
                "no_trading_webhook=true",
                "no_secret_values_stored=true",
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
    parser.add_argument("--suggestion-drafts-json", type=Path, default=SUGGESTION_DRAFTS_JSON)
    parser.add_argument("--source-registry-json", type=Path)
    args = parser.parse_args(argv)
    command = " ".join([Path(sys.argv[0]).name, *(argv if argv is not None else sys.argv[1:])])

    try:
        report = run_acceptance(
            output_root=args.output_root,
            reports_dir=args.reports_dir,
            run_id=args.run_id,
            command=command,
            suggestion_drafts_json=args.suggestion_drafts_json,
            source_registry_json=args.source_registry_json,
        )
    except Exception as exc:
        args.reports_dir.mkdir(parents=True, exist_ok=True)
        (args.reports_dir / FAIL_MARKER).write_text(
            "\n".join(
                [
                    f"generated_at={_now_iso()}",
                    f"command={command}",
                    "exit_code=1",
                    "target=V2.5-B Approved Live Candidate Refresh",
                    f"error={exc}",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        print(f"V2.5-B Approved Candidate Refresh FAIL: {exc}")
        return 1

    print(f"V2.5-B Approved Candidate Refresh PASS run_id={report['run_id']} report={args.reports_dir / REPORT_JSON}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

