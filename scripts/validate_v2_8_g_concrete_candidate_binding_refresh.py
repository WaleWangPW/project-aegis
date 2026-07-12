#!/usr/bin/env python3
"""Validate V2.8-G concrete candidate binding refresh for refresh-queue drafts."""

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
DEFAULT_OUTPUT_ROOT = ROOT / "data" / "processed" / "v2_8_g_acceptance"
DEFAULT_REPORTS_DIR = ROOT / "data" / "reports"
DEFAULT_SUGGESTION_DRAFTS = (
    ROOT
    / "data"
    / "processed"
    / "v2_8_e_acceptance"
    / "v2_8_e_20260711_acceptance"
    / "refresh_queue_suggestion_drafts.json"
)

PASS_MARKER = "V2_8_G_CONCRETE_CANDIDATE_BINDING_REFRESH_PASS.marker"
FAIL_MARKER = "V2_8_G_CONCRETE_CANDIDATE_BINDING_REFRESH_FAIL.marker"
REPORT_JSON = "v2_8_g_concrete_candidate_binding_refresh_latest.json"
REPORT_MD = "v2_8_g_concrete_candidate_binding_refresh_latest.md"


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def _run_id() -> str:
    return "v2_8_g_concrete_candidate_binding_refresh_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


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
    source_registry_json: Optional[Path] = None,
    run_id: Optional[str] = None,
    command: Optional[str] = None,
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
    source_registry_out = run_dir / "approved_concrete_candidate_source_registry.json"
    bindings_json = run_dir / "concrete_candidate_bindings.json"
    source_drafts_copy = run_dir / "source_refresh_queue_suggestion_drafts.json"
    source_registry_out.write_text(json.dumps(registry.model_dump(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    source_drafts_copy.write_text(json.dumps(suggestion_drafts, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    report = build_candidate_refresh_report(
        suggestion_drafts,
        registry,
        run_id=run_id,
        evidence_ref=str(source_registry_out),
        command=command,
    )
    report["acceptance_target"] = "V2.8-G Concrete Candidate Binding Refresh"
    report["source_acceptance_target"] = "V2.8-E Refresh Queue Suggestion Gate Drafts"
    report["source_suggestion_drafts_json"] = str(suggestion_drafts_json)
    report["approved_concrete_candidate_source_registry_json"] = str(source_registry_out)
    bindings_json.write_text(json.dumps(report["bindings"], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    bound = [binding for binding in report["bindings"] if binding["binding_status"] == "bound"]
    blocked = [binding for binding in report["bindings"] if binding["binding_status"] == "blocked"]
    checks = {
        "candidate_binding_passed": report["overall_status"] == "PASS",
        "a_h_us_bound": set(report["summary"]["bound_markets"]) >= {"A", "H", "US"},
        "blocked_paths_preserved": len(blocked) >= 1
        and all(binding["bound_candidates"] == [] for binding in blocked),
        "every_bound_has_concrete_candidates": all(binding["bound_candidates"] for binding in bound),
        "every_bound_candidate_has_symbol": all(
            candidate.get("symbol") and candidate.get("market")
            for binding in bound
            for candidate in binding["bound_candidates"]
        ),
        "fixture_status_honest": report["safety"]["fixture_not_live_market_data"] is True,
        "user_api_live_blocked_until_metadata": report["user_api_live_status"] == "blocked_missing_metadata",
        "approved_sources_only": report["safety"]["approved_sources_only"] is True,
        "manual_external_execution_only": report["safety"]["manual_external_execution_only"] is True,
        "no_secret_values_stored": report["safety"]["no_secret_values_stored"] is True,
        "no_real_trade": report["safety"]["no_real_trade"] is True,
        "no_broker_api": report["safety"]["no_broker_api"] is True,
        "no_webhook": report["safety"]["no_webhook"] is True,
        "no_production_records_mutation": report["production_records_written"] is False,
        "dashboard_contract_unchanged": report["dashboard_contract_changed"] is False,
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise RuntimeError("V2.8-G acceptance checks failed: " + ", ".join(failed))

    acceptance_report = {
        **report,
        "run_dir": str(run_dir),
        "concrete_candidate_bindings_json": str(bindings_json),
        "copied_source_suggestion_drafts_json": str(source_drafts_copy),
        "checks": checks,
        "hashes": {
            "source_suggestion_drafts_json": _sha256(suggestion_drafts_json),
            "approved_concrete_candidate_source_registry_json": _sha256(source_registry_out),
            "concrete_candidate_bindings_json": _sha256(bindings_json),
            "copied_source_suggestion_drafts_json": _sha256(source_drafts_copy),
        },
    }
    _write_reports(acceptance_report, reports_dir)
    return acceptance_report


def _render_markdown(report: dict) -> str:
    return "\n".join(
        [
            "# V2.8-G Concrete Candidate Binding Refresh",
            "",
            f"- status: `{report['overall_status']}`",
            f"- run_id: `{report['run_id']}`",
            f"- bound_markets: `{report['summary']['bound_markets']}`",
            f"- blocked_markets: `{report['summary']['blocked_markets']}`",
            f"- candidate_counts_by_market: `{report['summary']['candidate_counts_by_market']}`",
            f"- user_api_live_status: `{report['user_api_live_status']}`",
            "",
            "## Boundary",
            "",
            "- Concrete candidates are from approved fixture sources, not live market data.",
            "- Simulation-only and manual external execution only.",
            "- No live price, position size, broker API, webhook, or real order.",
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
                "target=V2.8-G Concrete Candidate Binding Refresh",
                f"report_json={json_path}",
                f"report_json_sha256={_sha256(json_path)}",
                f"report_md={md_path}",
                f"report_md_sha256={_sha256(md_path)}",
                f"concrete_candidate_bindings_json={report['concrete_candidate_bindings_json']}",
                f"concrete_candidate_bindings_json_sha256={report['hashes']['concrete_candidate_bindings_json']}",
                "network_used=false",
                "user_api_live_status=blocked_missing_metadata",
                "fixture_not_live_market_data=true",
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
    parser.add_argument("--suggestion-drafts-json", type=Path, default=DEFAULT_SUGGESTION_DRAFTS)
    parser.add_argument("--source-registry-json", type=Path)
    parser.add_argument("--run-id")
    args = parser.parse_args(argv)
    command = " ".join([Path(sys.argv[0]).name, *(argv if argv is not None else sys.argv[1:])])
    try:
        report = run_acceptance(
            output_root=args.output_root,
            reports_dir=args.reports_dir,
            suggestion_drafts_json=args.suggestion_drafts_json,
            source_registry_json=args.source_registry_json,
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
                    "target=V2.8-G Concrete Candidate Binding Refresh",
                    f"error={exc}",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        print(f"V2.8-G Concrete Candidate Binding Refresh FAIL: {exc}")
        return 1

    print(
        "V2.8-G Concrete Candidate Binding Refresh PASS "
        f"run_id={report['run_id']} report={args.reports_dir / REPORT_JSON}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
