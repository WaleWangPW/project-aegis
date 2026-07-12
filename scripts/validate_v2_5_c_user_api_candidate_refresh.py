#!/usr/bin/env python3
"""Validate Project Aegis V2.5-C User API Live Candidate Refresh entrypoint."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping, Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import scripts.run_api_research_dry_run as api_dry_run  # noqa: E402
from aegis.external_sources.api_config import APIConfigError, get_api_connector_spec  # noqa: E402
from aegis.strategy.candidate_refresh import (  # noqa: E402
    build_candidate_refresh_report,
    candidate_items_from_api_payload,
    candidate_source_registry_from_api_candidates,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_ROOT = ROOT / "data" / "processed" / "v2_5_c_acceptance"
DEFAULT_REPORTS_DIR = ROOT / "data" / "reports"
REAL_USER_CONFIG = ROOT / "config" / "external_api_connectors.local.json"
SUGGESTION_DRAFTS_JSON = (
    ROOT
    / "data"
    / "processed"
    / "v2_4_d_acceptance"
    / "v2_4_d_20260711_acceptance"
    / "research_hypothesis_suggestion_drafts.json"
)

PASS_MARKER = "V2_5_C_USER_API_CANDIDATE_REFRESH_PASS.marker"
FAIL_MARKER = "V2_5_C_USER_API_CANDIDATE_REFRESH_FAIL.marker"
REPORT_JSON = "v2_5_c_user_api_candidate_refresh_latest.json"
REPORT_MD = "v2_5_c_user_api_candidate_refresh_latest.md"
_FIXTURE_SECRET = "fixture-v2-5-c-secret-must-not-appear"


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def _run_id() -> str:
    return "v2_5_c_user_api_candidate_refresh_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _sha256(path: Path) -> Optional[str]:
    if not path.exists():
        return None
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _write_fixture_config(path: Path) -> None:
    payload = {
        "schema_version": "external_api_connectors.local.fixture.v1",
        "connectors": [
            {
                "connector_id": "api_fixture_candidate_refresh",
                "name": "Fixture Candidate Refresh API",
                "provider_type": "user_provided_research_api",
                "markets": ["A", "H", "US"],
                "base_url": "https://api.fixture-candidate-provider.invalid/v1",
                "auth_method": "env_var",
                "required_env_vars": ["AEGIS_RESEARCH_API_KEY"],
                "license_status": "approved",
                "retention_policy": "summary_only",
                "allowed_purposes": ["candidate_refresh"],
                "can_connect": True,
                "notes": "Fixture config with env var name only.",
            }
        ],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _fixture_candidate_fetch(url: str, headers: Mapping[str, str], timeout: int) -> tuple[int, str, bytes]:
    assert timeout > 0
    assert _FIXTURE_SECRET in headers.get("Authorization", "")
    payload = {
        "items": [
            {"symbol": "600036.SH", "market": "A", "name": "招商银行", "score": 0.86, "status": "Watch"},
            {"symbol": "00700.HK", "market": "H", "name": "Tencent Holdings", "score": 0.83, "status": "Watch"},
            {"symbol": "MSFT", "market": "US", "name": "Microsoft", "score": 0.78, "status": "Watch"},
        ],
        "source": "fixture-user-api-candidate-refresh",
        "url_seen": url,
    }
    return 200, "application/json", json.dumps(payload).encode("utf-8")


def _real_config_status() -> tuple[str, str]:
    try:
        get_api_connector_spec(REAL_USER_CONFIG, "api_fixture_candidate_refresh")
    except APIConfigError as exc:
        return "blocked_missing_metadata", str(exc)
    return "available", ""


def run_acceptance(
    *,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    reports_dir: Path = DEFAULT_REPORTS_DIR,
    run_id: Optional[str] = None,
    command: Optional[str] = None,
    suggestion_drafts_json: Path = SUGGESTION_DRAFTS_JSON,
) -> dict:
    run_id = run_id or _run_id()
    run_dir = output_root / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    reports_dir.mkdir(parents=True, exist_ok=True)

    fixture_config = run_dir / "external_api_connectors.local.fixture.json"
    _write_fixture_config(fixture_config)
    dry_report = api_dry_run.run_dry_run(
        config_path=fixture_config,
        connector_id="api_fixture_candidate_refresh",
        endpoint_path="/candidate-refresh",
        query={"markets": "A,H,US"},
        output_root=run_dir,
        run_id="fixture_candidate_api_dry_run",
        command="fixture candidate api dry run",
        fetch_fn=_fixture_candidate_fetch,
        env={"AEGIS_RESEARCH_API_KEY": _FIXTURE_SECRET},
    )
    dry_report_json = Path(dry_report["report_json"])
    dry_fetch_item_json = Path(dry_report["api_fetch_item_json"])
    dry_report_text = dry_report_json.read_text(encoding="utf-8")

    _status, content_type, payload = _fixture_candidate_fetch(
        "https://api.fixture-candidate-provider.invalid/v1/candidate-refresh",
        {"Authorization": "Bearer " + _FIXTURE_SECRET},
        10,
    )
    candidates = candidate_items_from_api_payload(payload, source_id="api_fixture_candidate_refresh")
    registry = candidate_source_registry_from_api_candidates(
        candidates,
        source_id="api_fixture_candidate_refresh",
    )
    registry_json = run_dir / "api_candidate_source_registry.json"
    registry_json.write_text(json.dumps(registry.model_dump(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    suggestions = json.loads(suggestion_drafts_json.read_text(encoding="utf-8"))
    refresh_report = build_candidate_refresh_report(
        suggestions,
        registry,
        run_id=run_id,
        evidence_ref=str(registry_json),
        command="fixture user api candidate refresh binding",
    )
    bindings_json = run_dir / "api_refreshed_candidate_bindings.json"
    bindings_json.write_text(json.dumps(refresh_report["bindings"], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    real_status, real_blocked_reason = _real_config_status()
    checks = {
        "fixture_api_dry_run_passed": dry_report["overall_status"] == "PASS",
        "secret_value_not_serialized": _FIXTURE_SECRET not in dry_report_text,
        "raw_bytes_not_stored": dry_report["safety"]["raw_bytes_not_stored"] is True,
        "headers_not_stored": dry_report["safety"]["request_headers_not_stored"] is True,
        "candidate_payload_parsed": len(candidates) == 3,
        "api_registry_summary_only": registry.safety["candidate_summary_only"] is True,
        "a_h_us_bound_from_api_candidates": set(refresh_report["summary"]["bound_markets"]) >= {"A", "H", "US"},
        "real_user_config_status_recorded": real_status in {"blocked_missing_metadata", "available"},
        "no_secret_values_stored": refresh_report["safety"]["no_secret_values_stored"] is True,
        "no_real_trade_or_broker": refresh_report["safety"]["no_real_trade"] is True
        and refresh_report["safety"]["no_broker_api"] is True,
        "no_webhook": refresh_report["safety"]["no_webhook"] is True,
        "no_production_records_mutation": refresh_report["production_records_written"] is False,
        "dashboard_contract_unchanged": refresh_report["dashboard_contract_changed"] is False,
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise RuntimeError("V2.5-C acceptance checks failed: " + ", ".join(failed))

    report = {
        **refresh_report,
        "acceptance_target": "V2.5-C User API Live Candidate Refresh",
        "fixture_mode": True,
        "network_used": False,
        "real_user_config_path": str(REAL_USER_CONFIG),
        "real_user_config_status": real_status,
        "real_user_config_blocked_reason": real_blocked_reason,
        "fixture_config": str(fixture_config),
        "fixture_api_dry_run_report": str(dry_report_json),
        "fixture_api_fetch_item_json": str(dry_fetch_item_json),
        "api_candidate_source_registry_json": str(registry_json),
        "api_refreshed_candidate_bindings_json": str(bindings_json),
        "checks": checks,
        "hashes": {
            "fixture_config": _sha256(fixture_config),
            "fixture_api_dry_run_report": _sha256(dry_report_json),
            "fixture_api_fetch_item_json": _sha256(dry_fetch_item_json),
            "api_candidate_source_registry_json": _sha256(registry_json),
            "api_refreshed_candidate_bindings_json": _sha256(bindings_json),
            "source_suggestion_drafts_json": _sha256(suggestion_drafts_json),
        },
    }
    _write_reports(report, reports_dir)
    return report


def _write_reports(report: dict, reports_dir: Path) -> None:
    json_path = reports_dir / REPORT_JSON
    md_path = reports_dir / REPORT_MD
    marker_path = reports_dir / PASS_MARKER
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md_path.write_text(
        "\n".join(
            [
                "# V2.5-C User API Candidate Refresh Acceptance",
                "",
                f"- status: {report['overall_status']}",
                f"- target: {report['acceptance_target']}",
                f"- run_id: {report['run_id']}",
                f"- fixture_api_dry_run_report: `{report['fixture_api_dry_run_report']}`",
                f"- api_refreshed_candidate_bindings_json: `{report['api_refreshed_candidate_bindings_json']}`",
                f"- bound_markets: `{report['summary']['bound_markets']}`",
                f"- real_user_config_status: `{report['real_user_config_status']}`",
                "- safety: fixture mode, raw bytes not stored, headers not stored, no broker/trading/webhook/secrets",
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
                "target=V2.5-C User API Live Candidate Refresh",
                f"report_json={json_path}",
                f"report_json_sha256={_sha256(json_path)}",
                f"report_md={md_path}",
                f"report_md_sha256={_sha256(md_path)}",
                f"api_refreshed_candidate_bindings_json={report['api_refreshed_candidate_bindings_json']}",
                f"api_refreshed_candidate_bindings_json_sha256={report['hashes']['api_refreshed_candidate_bindings_json']}",
                f"real_user_config_status={report['real_user_config_status']}",
                "network_used=false",
                "fixture_mode=true",
                "production_records_written=false",
                "dashboard_contract_changed=false",
                "raw_bytes_not_stored=true",
                "request_headers_not_stored=true",
                "no_secret_values_stored=true",
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
    args = parser.parse_args(argv)
    command = " ".join([Path(sys.argv[0]).name, *(argv if argv is not None else sys.argv[1:])])

    try:
        report = run_acceptance(
            output_root=args.output_root,
            reports_dir=args.reports_dir,
            run_id=args.run_id,
            command=command,
            suggestion_drafts_json=args.suggestion_drafts_json,
        )
    except Exception as exc:
        args.reports_dir.mkdir(parents=True, exist_ok=True)
        (args.reports_dir / FAIL_MARKER).write_text(
            "\n".join(
                [
                    f"generated_at={_now_iso()}",
                    f"command={command}",
                    "exit_code=1",
                    "target=V2.5-C User API Live Candidate Refresh",
                    f"error={exc}",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        print(f"V2.5-C User API Candidate Refresh FAIL: {exc}")
        return 1

    print(f"V2.5-C User API Candidate Refresh PASS run_id={report['run_id']} report={args.reports_dir / REPORT_JSON}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

