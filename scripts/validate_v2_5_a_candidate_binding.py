#!/usr/bin/env python3
"""Validate Project Aegis V2.5-A Approved Candidate Binding For Suggestion Drafts."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aegis.strategy.candidate_binding import build_candidate_binding_report  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_ROOT = ROOT / "data" / "processed" / "v2_5_a_acceptance"
DEFAULT_REPORTS_DIR = ROOT / "data" / "reports"
SUGGESTION_DRAFTS_JSON = (
    ROOT
    / "data"
    / "processed"
    / "v2_4_d_acceptance"
    / "v2_4_d_20260711_acceptance"
    / "research_hypothesis_suggestion_drafts.json"
)
A_SHARE_WATCHLIST_JSON = ROOT / "data" / "reports" / "a_share_watchlist_latest.json"
DESKTOP_STATUS_JSON = ROOT / "data" / "desktop" / "aegis_status.json"

PASS_MARKER = "V2_5_A_APPROVED_CANDIDATE_BINDING_PASS.marker"
FAIL_MARKER = "V2_5_A_APPROVED_CANDIDATE_BINDING_FAIL.marker"
REPORT_JSON = "v2_5_a_candidate_binding_latest.json"
REPORT_MD = "v2_5_a_candidate_binding_latest.md"


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def _run_id() -> str:
    return "v2_5_a_candidate_binding_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


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
    a_share_watchlist_json: Path = A_SHARE_WATCHLIST_JSON,
    desktop_status_json: Path = DESKTOP_STATUS_JSON,
) -> dict:
    run_id = run_id or _run_id()
    run_dir = output_root / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    reports_dir.mkdir(parents=True, exist_ok=True)

    suggestion_drafts = _load_json(suggestion_drafts_json)
    report = build_candidate_binding_report(
        suggestion_drafts,
        a_share_watchlist_json=a_share_watchlist_json,
        desktop_status_json=desktop_status_json,
        run_id=run_id,
        command=command,
    )

    bindings_json = run_dir / "candidate_bindings.json"
    source_suggestions_json = run_dir / "source_suggestion_drafts.json"
    bindings_json.write_text(json.dumps(report["bindings"], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    source_suggestions_json.write_text(json.dumps(suggestion_drafts, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    bindings = report["bindings"]
    bound = [item for item in bindings if item["binding_status"] == "bound"]
    blocked = [item for item in bindings if item["binding_status"] == "blocked"]
    checks = {
        "candidate_binding_passed": report["overall_status"] == "PASS",
        "binding_count_matches_suggestions": report["summary"]["binding_count"] == len(suggestion_drafts),
        "a_share_bound_from_watchlist": any(
            item["market"] == "A"
            and item["binding_status"] == "bound"
            and any(candidate["source"] == "a_share_watchlist_latest" for candidate in item["bound_candidates"])
            for item in bindings
        ),
        "us_bound_from_manual_holding": any(
            item["market"] == "US"
            and item["binding_status"] == "bound"
            and any(candidate["source"] == "current_manual_holding" for candidate in item["bound_candidates"])
            for item in bindings
        ),
        "h_missing_source_blocked": any(
            item["market"] == "H" and "missing_candidate_source" in item["blocked_by"] for item in blocked
        ),
        "failed_sandbox_drafts_still_blocked": all(
            item["binding_status"] == "blocked"
            for item in bindings
            if item["suggestion_id"]
            in {
                "sug_research_hyp_a_value_quality_multifactor",
                "sug_research_hyp_h_smart_beta_multifactor",
                "sug_research_hyp_us_low_vol_risk_overlay",
            }
        ),
        "all_bound_are_simulation_only": all(item["simulation_only"] is True for item in bound),
        "all_bound_require_external_execution": all(item["user_must_execute_externally"] is True for item in bound),
        "evidence_refs_present": all(item["evidence_refs"] for item in bindings),
        "no_real_trade_or_broker": report["safety"]["no_real_trade"] is True
        and report["safety"]["no_broker_api"] is True,
        "no_webhook_or_secrets": report["safety"]["no_webhook"] is True
        and report["safety"]["no_secret_storage"] is True,
        "no_production_records_mutation": report["production_records_written"] is False,
        "dashboard_contract_unchanged": report["dashboard_contract_changed"] is False,
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise RuntimeError("V2.5-A acceptance checks failed: " + ", ".join(failed))

    acceptance_report = {
        **report,
        "run_dir": str(run_dir),
        "source_suggestion_drafts_json": str(suggestion_drafts_json),
        "bindings_json": str(bindings_json),
        "copied_source_suggestion_drafts_json": str(source_suggestions_json),
        "checks": checks,
        "hashes": {
            "source_suggestion_drafts_json": _sha256(suggestion_drafts_json),
            "a_share_watchlist_json": _sha256(a_share_watchlist_json),
            "desktop_status_json": _sha256(desktop_status_json),
            "bindings_json": _sha256(bindings_json),
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
                "# V2.5-A Approved Candidate Binding Acceptance",
                "",
                f"- status: {report['overall_status']}",
                f"- target: {report['acceptance_target']}",
                f"- run_id: {report['run_id']}",
                f"- bindings_json: `{report['bindings_json']}`",
                f"- bound_count: `{report['summary']['bound_count']}`",
                f"- blocked_count: `{report['summary']['blocked_count']}`",
                f"- bound_markets: `{report['summary']['bound_markets']}`",
                f"- blocked_markets: `{report['summary']['blocked_markets']}`",
                "- safety: simulation-only bindings, manual external execution only, no broker/trading/webhook",
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
                "target=V2.5-A Approved Candidate Binding For Suggestion Drafts",
                f"report_json={json_path}",
                f"report_json_sha256={_sha256(json_path)}",
                f"report_md={md_path}",
                f"report_md_sha256={_sha256(md_path)}",
                f"bindings_json={report['bindings_json']}",
                f"bindings_json_sha256={report['hashes']['bindings_json']}",
                "network_used=false",
                "production_records_written=false",
                "dashboard_contract_changed=false",
                "simulation_only=true",
                "manual_external_execution_only=true",
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
    parser.add_argument("--run-id")
    parser.add_argument("--suggestion-drafts-json", type=Path, default=SUGGESTION_DRAFTS_JSON)
    parser.add_argument("--a-share-watchlist-json", type=Path, default=A_SHARE_WATCHLIST_JSON)
    parser.add_argument("--desktop-status-json", type=Path, default=DESKTOP_STATUS_JSON)
    args = parser.parse_args(argv)
    command = " ".join([Path(sys.argv[0]).name, *(argv if argv is not None else sys.argv[1:])])

    try:
        report = run_acceptance(
            output_root=args.output_root,
            reports_dir=args.reports_dir,
            run_id=args.run_id,
            command=command,
            suggestion_drafts_json=args.suggestion_drafts_json,
            a_share_watchlist_json=args.a_share_watchlist_json,
            desktop_status_json=args.desktop_status_json,
        )
    except Exception as exc:
        args.reports_dir.mkdir(parents=True, exist_ok=True)
        (args.reports_dir / FAIL_MARKER).write_text(
            "\n".join(
                [
                    f"generated_at={_now_iso()}",
                    f"command={command}",
                    "exit_code=1",
                    "target=V2.5-A Approved Candidate Binding For Suggestion Drafts",
                    f"error={exc}",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        print(f"V2.5-A Approved Candidate Binding FAIL: {exc}")
        return 1

    print(f"V2.5-A Approved Candidate Binding PASS run_id={report['run_id']} report={args.reports_dir / REPORT_JSON}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

