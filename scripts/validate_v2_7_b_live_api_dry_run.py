#!/usr/bin/env python3
"""Validate Project Aegis V2.7-B bounded live API dry-run orchestration."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping, Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aegis.external_sources.live_api_dry_run import build_live_api_dry_run_report  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_ROOT = ROOT / "data" / "processed" / "v2_7_b_acceptance"
DEFAULT_REPORTS_DIR = ROOT / "data" / "reports"
REAL_USER_CONFIG = ROOT / "config" / "external_api_connectors.local.json"
DEFAULT_CONNECTOR_ID = "api_user_research_approved_env"

PASS_MARKER = "V2_7_B_LIVE_API_DRY_RUN_PASS.marker"
FAIL_MARKER = "V2_7_B_LIVE_API_DRY_RUN_FAIL.marker"
REPORT_JSON = "v2_7_b_live_api_dry_run_latest.json"
REPORT_MD = "v2_7_b_live_api_dry_run_latest.md"
_FIXTURE_SECRET = "fixture-v2-7-b-value-not-persisted"


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


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
                "connector_id": DEFAULT_CONNECTOR_ID,
                "name": "Fixture User Research API",
                "provider_type": "user_provided_research_api",
                "markets": ["A", "H", "US"],
                "base_url": "https://api.fixture-research-provider.invalid/v1",
                "auth_method": "env_var",
                "required_env_vars": ["AEGIS_RESEARCH_API_KEY"],
                "license_status": "approved",
                "retention_policy": "summary_only",
                "allowed_purposes": ["strategy_research_ingestion", "candidate_refresh"],
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
            {"symbol": "600036.SH", "market": "A", "name": "招商银行", "score": 0.86},
            {"symbol": "00700.HK", "market": "H", "name": "Tencent Holdings", "score": 0.83},
            {"symbol": "MSFT", "market": "US", "name": "Microsoft", "score": 0.78},
        ],
        "source": "fixture-v2-7-b",
        "url_seen_hash_only": hashlib.sha256(url.encode("utf-8")).hexdigest(),
    }
    return 200, "application/json", json.dumps(payload, ensure_ascii=False).encode("utf-8")


def _render_markdown(report: dict) -> str:
    lines = [
        "# V2.7-B Live API Dry Run",
        "",
        f"- status: `{report['overall_status']}`",
        f"- fixture_status: `{report['fixture_live_dry_run_status']}`",
        f"- real_user_status: `{report['real_user_live_dry_run_status']}`",
        f"- real_user_blocked_by: `{', '.join(report['real_user_blocked_by']) or 'none'}`",
        f"- network_used: `{str(report['network_used']).lower()}`",
        "",
        "## Boundary",
        "",
        "- Uses activation gate before fetch.",
        "- Persists summary/hash evidence only.",
        "- Does not store env var values, query values, request headers, or raw bytes.",
        "- No broker API, no trading webhook, no order placement.",
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
) -> dict:
    run_id = run_id or "v2_7_b_live_api_dry_run_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = output_root / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    reports_dir.mkdir(parents=True, exist_ok=True)

    fixture_config = run_dir / "external_api_connectors.local.fixture.json"
    _write_fixture_config(fixture_config)
    fixture_report = build_live_api_dry_run_report(
        config_path=fixture_config,
        connector_id=connector_id,
        endpoint_path="/candidate-refresh",
        query={"market": "A,H,US", "purpose": "candidate_refresh"},
        output_root=run_dir,
        run_id="fixture_ready_live_api_dry_run",
        env={"AEGIS_RESEARCH_API_KEY": _FIXTURE_SECRET},
        fetch_fn=_fixture_fetch,
        command="fixture v2.7-b live api dry run",
    )
    real_report = build_live_api_dry_run_report(
        config_path=real_config_path,
        connector_id=connector_id,
        endpoint_path="/candidate-refresh",
        query={"market": "A,H,US", "purpose": "candidate_refresh"},
        output_root=run_dir,
        run_id="real_user_live_api_dry_run",
        command="real user v2.7-b live api dry run",
    )

    fixture_report_path = Path(fixture_report["report_json"])
    real_report_path = Path(real_report["report_json"])
    serialized = "\n".join(
        [
            fixture_report_path.read_text(encoding="utf-8"),
            real_report_path.read_text(encoding="utf-8"),
        ]
    )
    checks = {
        "fixture_live_dry_run_completed": fixture_report["live_dry_run_status"] == "completed",
        "fixture_api_fetch_item_exists": bool(fixture_report["api_fetch_item_json"])
        and Path(fixture_report["api_fetch_item_json"]).exists(),
        "real_user_status_recorded": real_report["live_dry_run_status"]
        in {"completed", "blocked_missing_metadata", "blocked_missing_env_vars", "blocked_policy_denied"},
        "real_user_not_claimed_completed_when_blocked": (
            real_report["live_dry_run_status"] == "completed"
            or real_report["activation"]["can_run_live_dry_run"] is False
        ),
        "secret_value_not_serialized": _FIXTURE_SECRET not in serialized,
        "env_var_names_only": fixture_report["safety"]["env_var_names_only"] is True
        and real_report["safety"]["env_var_names_only"] is True,
        "query_values_not_stored": fixture_report["safety"]["query_values_not_stored"] is True
        and real_report["safety"]["query_values_not_stored"] is True,
        "raw_bytes_not_stored": fixture_report["safety"]["raw_bytes_not_stored"] is True
        and real_report["safety"]["raw_bytes_not_stored"] is True,
        "request_headers_not_stored": fixture_report["safety"]["request_headers_not_stored"] is True
        and real_report["safety"]["request_headers_not_stored"] is True,
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
        raise RuntimeError("V2.7-B acceptance checks failed: " + ", ".join(failed))

    report = {
        "overall_status": "PASS",
        "acceptance_target": "V2.7-B Bounded Live API Dry Run Entrypoint",
        "generated_at": _now_iso(),
        "run_id": run_id,
        "command": command,
        "network_used": real_report["network_used"],
        "production_records_written": False,
        "dashboard_contract_changed": False,
        "fixture_live_dry_run_report": str(fixture_report_path),
        "real_user_live_dry_run_report": str(real_report_path),
        "fixture_live_dry_run_status": fixture_report["live_dry_run_status"],
        "real_user_live_dry_run_status": real_report["live_dry_run_status"],
        "real_user_can_run_live_dry_run": real_report["activation"]["can_run_live_dry_run"],
        "real_user_blocked_by": real_report["activation"]["blocked_by"],
        "real_user_missing_env_vars": real_report["activation"]["missing_env_vars"],
        "checks": checks,
        "safety": {
            "activation_gate_before_fetch": True,
            "summary_hash_only": True,
            "env_values_not_stored": True,
            "env_var_names_only": True,
            "query_values_not_stored": True,
            "request_headers_not_stored": True,
            "raw_bytes_not_stored": True,
            "no_real_trade": True,
            "no_broker_api": True,
            "no_trading_webhook": True,
            "no_order_placement": True,
            "dashboard_contract_unchanged": True,
            "no_production_records_mutation": True,
        },
        "hashes": {
            "fixture_config": _sha256(fixture_config),
            "fixture_live_dry_run_report": _sha256(fixture_report_path),
            "real_user_live_dry_run_report": _sha256(real_report_path),
            "fixture_api_fetch_item_json": _sha256(Path(fixture_report["api_fetch_item_json"])),
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
                "target=V2.7-B Bounded Live API Dry Run Entrypoint",
                f"report_json={json_path}",
                f"report_json_sha256={_sha256(json_path)}",
                f"report_md={md_path}",
                f"report_md_sha256={_sha256(md_path)}",
                f"fixture_live_dry_run_status={report['fixture_live_dry_run_status']}",
                f"real_user_live_dry_run_status={report['real_user_live_dry_run_status']}",
                f"real_user_can_run_live_dry_run={str(report['real_user_can_run_live_dry_run']).lower()}",
                f"real_user_blocked_by={','.join(report['real_user_blocked_by'])}",
                f"network_used={str(report['network_used']).lower()}",
                "production_records_written=false",
                "dashboard_contract_changed=false",
                "env_values_not_stored=true",
                "env_var_names_only=true",
                "query_values_not_stored=true",
                "raw_bytes_not_stored=true",
                "request_headers_not_stored=true",
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
        )
    except Exception as exc:
        args.reports_dir.mkdir(parents=True, exist_ok=True)
        (args.reports_dir / FAIL_MARKER).write_text(
            "\n".join(
                [
                    f"generated_at={_now_iso()}",
                    f"command={command}",
                    "exit_code=1",
                    "target=V2.7-B Bounded Live API Dry Run Entrypoint",
                    f"error={exc}",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        print(f"V2.7-B Live API Dry Run FAIL: {exc}")
        return 1

    print(f"V2.7-B Live API Dry Run PASS run_id={report['run_id']} report={args.reports_dir / REPORT_JSON}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
