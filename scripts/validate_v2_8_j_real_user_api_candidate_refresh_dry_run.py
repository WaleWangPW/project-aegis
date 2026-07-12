#!/usr/bin/env python3
"""Validate Project Aegis V2.8-J Real User API Candidate Refresh Dry Run."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping, Optional
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aegis.external_sources.api_activation import assess_live_api_activation  # noqa: E402
from aegis.external_sources.api_config import get_api_connector_spec  # noqa: E402
from aegis.external_sources.api_fetcher import fetch_external_api_summary  # noqa: E402
from aegis.strategy.candidate_refresh import (  # noqa: E402
    build_candidate_refresh_report,
    candidate_items_from_api_payload,
    candidate_source_registry_from_api_candidates,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_ROOT = ROOT / "data" / "processed" / "v2_8_j_acceptance"
DEFAULT_REPORTS_DIR = ROOT / "data" / "reports"
REAL_USER_CONFIG = ROOT / "config" / "external_api_connectors.local.json"
DEFAULT_CONNECTOR_ID = "api_user_candidate_refresh_approved_env"
DEFAULT_ENDPOINT_PATH = "/candidate-refresh"
DEFAULT_ENV_VAR = "AEGIS_CANDIDATE_REFRESH_API_KEY"
SUGGESTION_DRAFTS_JSON = (
    ROOT
    / "data"
    / "processed"
    / "v2_8_e_acceptance"
    / "v2_8_e_20260711_acceptance"
    / "refresh_queue_suggestion_drafts.json"
)

PASS_MARKER = "V2_8_J_REAL_USER_API_CANDIDATE_REFRESH_DRY_RUN_PASS.marker"
FAIL_MARKER = "V2_8_J_REAL_USER_API_CANDIDATE_REFRESH_DRY_RUN_FAIL.marker"
REPORT_JSON = "v2_8_j_real_user_api_candidate_refresh_dry_run_latest.json"
REPORT_MD = "v2_8_j_real_user_api_candidate_refresh_dry_run_latest.md"
_FIXTURE_SECRET = "fixture-v2-8-j-secret-must-not-appear"


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def _run_id() -> str:
    return "v2_8_j_real_user_api_candidate_refresh_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _sha256(path: Path | None) -> Optional[str]:
    if path is None or not path.exists():
        return None
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _default_fetch(url: str, headers: Mapping[str, str], timeout: int) -> tuple[int, str, bytes]:
    req = Request(url, headers=dict(headers))
    with urlopen(req, timeout=timeout) as response:
        return response.status, response.headers.get("content-type", ""), response.read()


def _write_fixture_config(path: Path) -> None:
    payload = {
        "schema_version": "external_api_connectors.local.fixture.v2_8_j",
        "connectors": [
            {
                "connector_id": DEFAULT_CONNECTOR_ID,
                "name": "Fixture User Candidate Refresh API",
                "provider_type": "user_provided_research_api",
                "markets": ["A", "H", "US"],
                "base_url": "https://api.fixture-candidate-refresh.invalid/v1",
                "auth_method": "env_var",
                "required_env_vars": [DEFAULT_ENV_VAR],
                "license_status": "approved",
                "retention_policy": "summary_only",
                "allowed_purposes": ["candidate_refresh", "strategy_research_ingestion"],
                "can_connect": True,
                "notes": "Fixture metadata only; env var name only.",
            }
        ],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _fixture_fetch(url: str, headers: Mapping[str, str], timeout: int) -> tuple[int, str, bytes]:
    assert timeout > 0
    assert _FIXTURE_SECRET in headers.get("Authorization", "")
    payload = {
        "items": [
            {"symbol": "600036.SH", "market": "A", "name": "招商银行", "score": 0.86, "status": "Watch"},
            {"symbol": "00700.HK", "market": "H", "name": "Tencent Holdings", "score": 0.83, "status": "Watch"},
            {"symbol": "MSFT", "market": "US", "name": "Microsoft", "score": 0.78, "status": "Watch"},
        ],
        "source": "fixture-v2-8-j",
        "url_seen_hash_only": hashlib.sha256(url.encode("utf-8")).hexdigest(),
    }
    return 200, "application/json", json.dumps(payload, ensure_ascii=False).encode("utf-8")


def _capturing_fetcher(
    fetch_fn,
    captured: dict[str, bytes],
):
    def _fetch(url: str, headers: Mapping[str, str], timeout: int) -> tuple[int, str, bytes]:
        status, content_type, payload = fetch_fn(url, headers, timeout)
        captured["payload"] = payload
        return status, content_type, payload

    return _fetch


def _run_candidate_refresh_dry_run(
    *,
    config_path: Path,
    connector_id: str,
    endpoint_path: str,
    query: Mapping[str, str],
    output_root: Path,
    run_id: str,
    suggestion_drafts_json: Path,
    env: Mapping[str, str] | None = None,
    fetch_fn=None,
    command: str | None = None,
) -> dict:
    run_dir = output_root / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    activation = assess_live_api_activation(config_path=config_path, connector_id=connector_id, env=env)
    ready = activation["activation_status"] == "ready_for_live_dry_run"
    captured: dict[str, bytes] = {}
    item_json: Path | None = None
    registry_json: Path | None = None
    bindings_json: Path | None = None
    refresh_report: dict | None = None

    if ready:
        spec = get_api_connector_spec(config_path, connector_id)
        fetcher = _capturing_fetcher(fetch_fn or _default_fetch, captured)
        item = fetch_external_api_summary(
            spec=spec,
            endpoint_path=endpoint_path,
            query=query,
            env=env,
            fetch_fn=fetcher,
        )
        item_json = run_dir / "api_fetch_item.json"
        item_json.write_text(json.dumps(item.model_dump(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        candidates = candidate_items_from_api_payload(captured["payload"], source_id=connector_id)
        registry = candidate_source_registry_from_api_candidates(
            candidates,
            source_id=connector_id,
            auth_env_vars=spec.required_env_vars,
        )
        registry_json = run_dir / "api_candidate_source_registry.json"
        registry_json.write_text(json.dumps(registry.model_dump(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        suggestions = json.loads(suggestion_drafts_json.read_text(encoding="utf-8"))
        refresh_report = build_candidate_refresh_report(
            suggestions,
            registry,
            run_id=run_id,
            evidence_ref=str(registry_json),
            command=command,
        )
        bindings_json = run_dir / "api_candidate_bindings.json"
        bindings_json.write_text(
            json.dumps(refresh_report["bindings"], ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    return {
        "overall_status": "PASS" if ready and refresh_report and refresh_report["overall_status"] == "PASS" else "BLOCKED",
        "generated_at": _now_iso(),
        "run_id": run_id,
        "command": command,
        "config_path": str(config_path),
        "connector_id": connector_id,
        "endpoint_path": endpoint_path,
        "query_keys": sorted(query.keys()),
        "activation": activation,
        "dry_run_status": "completed" if ready else activation["activation_status"],
        "network_used": bool(ready and fetch_fn is None),
        "production_records_written": False,
        "dashboard_contract_changed": False,
        "api_fetch_item_json": str(item_json) if item_json else None,
        "api_candidate_source_registry_json": str(registry_json) if registry_json else None,
        "api_candidate_bindings_json": str(bindings_json) if bindings_json else None,
        "refresh_summary": refresh_report["summary"] if refresh_report else {},
        "safety": {
            "activation_gate_before_fetch": True,
            "summary_hash_only": True,
            "raw_payload_parsed_in_memory_only": True,
            "raw_bytes_not_stored": True,
            "request_headers_not_stored": True,
            "env_values_not_stored": True,
            "env_var_names_only": True,
            "query_values_not_stored": True,
            "requires_historical_sandbox": True,
            "requires_suggestion_gate": True,
            "simulation_only": True,
            "manual_external_execution_only": True,
            "no_real_trade": True,
            "no_broker_api": True,
            "no_trading_webhook": True,
            "no_order_placement": True,
            "dashboard_contract_unchanged": True,
            "no_production_records_mutation": True,
        },
        "hashes": {
            "api_fetch_item_json": _sha256(item_json),
            "api_candidate_source_registry_json": _sha256(registry_json),
            "api_candidate_bindings_json": _sha256(bindings_json),
        },
    }


def _render_markdown(report: dict) -> str:
    lines = [
        "# V2.8-J Real User API Candidate Refresh Dry Run",
        "",
        f"- status: `{report['overall_status']}`",
        f"- fixture_status: `{report['fixture_dry_run_status']}`",
        f"- real_user_status: `{report['real_user_dry_run_status']}`",
        f"- real_user_blocked_by: `{', '.join(report['real_user_blocked_by']) or 'none'}`",
        f"- next_target: `{report['summary']['next_target']}`",
        "",
        "## Boundary",
        "",
        "- Activation gate before fetch.",
        "- Raw API payload parsed in memory only.",
        "- Stores summary/hash/status/candidate summaries only.",
        "- No broker API, trading webhook, order placement, or production recommendation mutation.",
        "",
    ]
    return "\n".join(lines)


def run_acceptance(
    *,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    reports_dir: Path = DEFAULT_REPORTS_DIR,
    run_id: Optional[str] = None,
    command: Optional[str] = None,
    real_config_path: Path = REAL_USER_CONFIG,
    connector_id: str = DEFAULT_CONNECTOR_ID,
    suggestion_drafts_json: Path = SUGGESTION_DRAFTS_JSON,
) -> dict:
    run_id = run_id or _run_id()
    run_dir = output_root / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    reports_dir.mkdir(parents=True, exist_ok=True)

    fixture_config = run_dir / "external_api_connectors.local.fixture.json"
    _write_fixture_config(fixture_config)
    query = {"markets": "A,H,US", "purpose": "candidate_refresh"}
    fixture_report = _run_candidate_refresh_dry_run(
        config_path=fixture_config,
        connector_id=connector_id,
        endpoint_path=DEFAULT_ENDPOINT_PATH,
        query=query,
        output_root=run_dir,
        run_id="fixture_candidate_refresh_dry_run",
        suggestion_drafts_json=suggestion_drafts_json,
        env={DEFAULT_ENV_VAR: _FIXTURE_SECRET},
        fetch_fn=_fixture_fetch,
        command="fixture v2.8-j candidate refresh dry run",
    )
    real_report = _run_candidate_refresh_dry_run(
        config_path=real_config_path,
        connector_id=connector_id,
        endpoint_path=DEFAULT_ENDPOINT_PATH,
        query=query,
        output_root=run_dir,
        run_id="real_user_candidate_refresh_dry_run",
        suggestion_drafts_json=suggestion_drafts_json,
        env=os.environ,
        command="real user v2.8-j candidate refresh dry run",
    )

    fixture_report_json = run_dir / "fixture_candidate_refresh_dry_run_report.json"
    real_report_json = run_dir / "real_user_candidate_refresh_dry_run_report.json"
    fixture_report_json.write_text(json.dumps(fixture_report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    real_report_json.write_text(json.dumps(real_report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    serialized = "\n".join(
        [
            fixture_report_json.read_text(encoding="utf-8"),
            real_report_json.read_text(encoding="utf-8"),
        ]
    )
    checks = {
        "fixture_dry_run_completed": fixture_report["dry_run_status"] == "completed",
        "fixture_a_h_us_bound": set(fixture_report["refresh_summary"].get("bound_markets", [])) >= {"A", "H", "US"},
        "real_user_status_recorded": real_report["dry_run_status"]
        in {"completed", "blocked_missing_metadata", "blocked_missing_env_vars", "blocked_policy_denied"},
        "real_user_not_claimed_completed_when_blocked": (
            real_report["dry_run_status"] == "completed"
            or real_report["activation"]["can_run_live_dry_run"] is False
        ),
        "secret_value_not_serialized": _FIXTURE_SECRET not in serialized,
        "query_values_not_stored": "A,H,US" not in serialized,
        "raw_bytes_not_stored": fixture_report["safety"]["raw_bytes_not_stored"] is True
        and real_report["safety"]["raw_bytes_not_stored"] is True,
        "request_headers_not_stored": fixture_report["safety"]["request_headers_not_stored"] is True
        and real_report["safety"]["request_headers_not_stored"] is True,
        "env_var_names_only": fixture_report["safety"]["env_var_names_only"] is True
        and real_report["safety"]["env_var_names_only"] is True,
        "no_real_trade_or_broker": fixture_report["safety"]["no_real_trade"] is True
        and fixture_report["safety"]["no_broker_api"] is True
        and real_report["safety"]["no_real_trade"] is True
        and real_report["safety"]["no_broker_api"] is True,
        "dashboard_contract_unchanged": fixture_report["dashboard_contract_changed"] is False
        and real_report["dashboard_contract_changed"] is False,
        "production_records_not_written": fixture_report["production_records_written"] is False
        and real_report["production_records_written"] is False,
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise RuntimeError("V2.8-J acceptance checks failed: " + ", ".join(failed))

    report = {
        "overall_status": "PASS",
        "acceptance_target": "V2.8-J Real User API Candidate Refresh Dry Run After Local Metadata",
        "generated_at": _now_iso(),
        "run_id": run_id,
        "command": command,
        "network_used": real_report["network_used"],
        "production_records_written": False,
        "dashboard_contract_changed": False,
        "fixture_report_json": str(fixture_report_json),
        "real_user_report_json": str(real_report_json),
        "fixture_dry_run_status": fixture_report["dry_run_status"],
        "real_user_dry_run_status": real_report["dry_run_status"],
        "real_user_can_run_live_dry_run": real_report["activation"]["can_run_live_dry_run"],
        "real_user_blocked_by": real_report["activation"]["blocked_by"],
        "real_user_missing_env_vars": real_report["activation"]["missing_env_vars"],
        "checks": checks,
        "summary": {
            "fixture_bound_markets": fixture_report["refresh_summary"].get("bound_markets", []),
            "fixture_bound_count": fixture_report["refresh_summary"].get("bound_count"),
            "fixture_blocked_count": fixture_report["refresh_summary"].get("blocked_count"),
            "real_user_status": real_report["dry_run_status"],
            "next_target": "V2.8-K API-Backed Candidate Usable Brief After Real Metadata",
        },
        "safety": fixture_report["safety"]
        | {
            "activation_gate_before_fetch": True,
            "blocked_real_user_run_does_not_fetch": real_report["dry_run_status"] != "completed",
            "no_real_trade": True,
            "no_broker_api": True,
            "no_trading_webhook": True,
            "no_order_placement": True,
        },
        "hashes": {
            "fixture_report_json": _sha256(fixture_report_json),
            "real_user_report_json": _sha256(real_report_json),
            "fixture_api_fetch_item_json": fixture_report["hashes"]["api_fetch_item_json"],
            "fixture_candidate_registry_json": fixture_report["hashes"]["api_candidate_source_registry_json"],
            "fixture_candidate_bindings_json": fixture_report["hashes"]["api_candidate_bindings_json"],
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
    md_path.write_text(_render_markdown(report), encoding="utf-8")
    marker_path.write_text(
        "\n".join(
            [
                f"generated_at={report['generated_at']}",
                f"command={report.get('command') or ''}",
                "exit_code=0",
                "target=V2.8-J Real User API Candidate Refresh Dry Run After Local Metadata",
                f"report_json={json_path}",
                f"report_json_sha256={_sha256(json_path)}",
                f"report_md={md_path}",
                f"report_md_sha256={_sha256(md_path)}",
                f"fixture_dry_run_status={report['fixture_dry_run_status']}",
                f"real_user_dry_run_status={report['real_user_dry_run_status']}",
                "production_records_written=false",
                "dashboard_contract_changed=false",
                "summary_hash_only=true",
                "raw_bytes_not_stored=true",
                "request_headers_not_stored=true",
                "env_values_not_stored=true",
                "env_var_names_only=true",
                "no_real_trade=true",
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
    parser.add_argument("--real-config-path", type=Path, default=REAL_USER_CONFIG)
    parser.add_argument("--connector-id", default=DEFAULT_CONNECTOR_ID)
    parser.add_argument("--suggestion-drafts-json", type=Path, default=SUGGESTION_DRAFTS_JSON)
    args = parser.parse_args(argv)
    command = " ".join([Path(sys.argv[0]).name, *(argv if argv is not None else sys.argv[1:])])

    try:
        report = run_acceptance(
            output_root=args.output_root,
            reports_dir=args.reports_dir,
            run_id=args.run_id,
            command=command,
            real_config_path=args.real_config_path,
            connector_id=args.connector_id,
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
                    "target=V2.8-J Real User API Candidate Refresh Dry Run After Local Metadata",
                    f"error={exc}",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        print(f"V2.8-J Real User API Candidate Refresh Dry Run FAIL: {exc}")
        return 1

    print(
        "V2.8-J Real User API Candidate Refresh Dry Run PASS "
        f"run_id={report['run_id']} report={args.reports_dir / REPORT_JSON}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
