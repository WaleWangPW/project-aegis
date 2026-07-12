#!/usr/bin/env python3
"""Validate Project Aegis V2.7-A Live API Metadata Activation preflight."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aegis.external_sources.api_activation import build_api_activation_report  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_ROOT = ROOT / "data" / "processed" / "v2_7_a_acceptance"
DEFAULT_REPORTS_DIR = ROOT / "data" / "reports"
REAL_USER_CONFIG = ROOT / "config" / "external_api_connectors.local.json"
DEFAULT_CONNECTOR_ID = "api_user_research_approved_env"

PASS_MARKER = "V2_7_A_LIVE_API_METADATA_ACTIVATION_PASS.marker"
FAIL_MARKER = "V2_7_A_LIVE_API_METADATA_ACTIVATION_FAIL.marker"
REPORT_JSON = "v2_7_a_live_api_metadata_activation_latest.json"
REPORT_MD = "v2_7_a_live_api_metadata_activation_latest.md"


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
                "allowed_purposes": ["strategy_research_ingestion"],
                "can_connect": True,
                "notes": "Fixture metadata only; env var name only.",
            }
        ],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _render_markdown(report: dict) -> str:
    activation = report["activation"]
    lines = [
        "# V2.7-A Live API Metadata Activation",
        "",
        f"- status: `{report['overall_status']}`",
        f"- activation_status: `{activation['activation_status']}`",
        f"- connector_id: `{activation['connector_id']}`",
        f"- can_run_live_dry_run: `{activation['can_run_live_dry_run']}`",
        f"- blocked_by: `{', '.join(activation['blocked_by']) or 'none'}`",
        f"- missing_env_vars: `{', '.join(activation['missing_env_vars']) or 'none'}`",
        "",
        "## Boundary",
        "",
        "- Preflight only.",
        "- No network call.",
        "- Env var names only; values are not stored.",
        "- No real trade, no broker API, no webhook, no order placement.",
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
    run_id = run_id or "v2_7_a_live_api_activation_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = output_root / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    reports_dir.mkdir(parents=True, exist_ok=True)

    fixture_config = run_dir / "external_api_connectors.local.fixture.json"
    _write_fixture_config(fixture_config)
    fixture_ready_report = build_api_activation_report(
        config_path=fixture_config,
        connector_id=connector_id,
        run_id=f"{run_id}_fixture_ready",
        env={"AEGIS_RESEARCH_API_KEY": "fixture-value-not-persisted"},
        command="fixture activation ready preflight",
    )
    fixture_missing_env_report = build_api_activation_report(
        config_path=fixture_config,
        connector_id=connector_id,
        run_id=f"{run_id}_fixture_missing_env",
        env={},
        command="fixture activation missing env preflight",
    )
    real_report = build_api_activation_report(
        config_path=real_config_path,
        connector_id=connector_id,
        run_id=f"{run_id}_real_user",
        command="real user activation preflight",
    )

    fixture_ready_json = run_dir / "fixture_ready_activation_report.json"
    fixture_missing_env_json = run_dir / "fixture_missing_env_activation_report.json"
    real_activation_json = run_dir / "real_user_activation_report.json"
    fixture_ready_json.write_text(json.dumps(fixture_ready_report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    fixture_missing_env_json.write_text(json.dumps(fixture_missing_env_report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    real_activation_json.write_text(json.dumps(real_report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    serialized = "\n".join(
        [
            fixture_ready_json.read_text(encoding="utf-8"),
            fixture_missing_env_json.read_text(encoding="utf-8"),
            real_activation_json.read_text(encoding="utf-8"),
        ]
    )
    checks = {
        "fixture_ready_for_live_dry_run": fixture_ready_report["activation"]["activation_status"]
        == "ready_for_live_dry_run",
        "fixture_missing_env_is_blocked": fixture_missing_env_report["activation"]["activation_status"]
        == "blocked_missing_env_vars",
        "real_user_status_recorded": real_report["activation"]["activation_status"]
        in {"blocked_missing_metadata", "blocked_missing_env_vars", "blocked_policy_denied", "ready_for_live_dry_run"},
        "secret_value_not_serialized": "fixture-value-not-persisted" not in serialized,
        "env_var_names_only": all(
            report["safety"]["env_var_names_only"]
            for report in [fixture_ready_report, fixture_missing_env_report, real_report]
        ),
        "network_not_used": all(
            report["network_used"] is False for report in [fixture_ready_report, fixture_missing_env_report, real_report]
        ),
        "no_real_trade_or_broker": all(
            report["safety"]["no_real_trade"] is True and report["safety"]["no_broker_api"] is True
            for report in [fixture_ready_report, fixture_missing_env_report, real_report]
        ),
        "dashboard_contract_unchanged": all(
            report["dashboard_contract_changed"] is False
            for report in [fixture_ready_report, fixture_missing_env_report, real_report]
        ),
        "production_records_not_written": all(
            report["production_records_written"] is False
            for report in [fixture_ready_report, fixture_missing_env_report, real_report]
        ),
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise RuntimeError("V2.7-A acceptance checks failed: " + ", ".join(failed))

    report = {
        "overall_status": "PASS",
        "acceptance_target": "V2.7-A Live API Metadata Activation",
        "generated_at": _now_iso(),
        "run_id": run_id,
        "command": command,
        "network_used": False,
        "production_records_written": False,
        "dashboard_contract_changed": False,
        "fixture_ready_activation_report": str(fixture_ready_json),
        "fixture_missing_env_activation_report": str(fixture_missing_env_json),
        "real_user_activation_report": str(real_activation_json),
        "real_user_activation_status": real_report["activation"]["activation_status"],
        "real_user_can_run_live_dry_run": real_report["activation"]["can_run_live_dry_run"],
        "real_user_blocked_by": real_report["activation"]["blocked_by"],
        "real_user_missing_env_vars": real_report["activation"]["missing_env_vars"],
        "checks": checks,
        "safety": {
            "preflight_only": True,
            "env_values_not_stored": True,
            "env_var_names_only": True,
            "network_not_used": True,
            "no_real_trade": True,
            "no_broker_api": True,
            "no_webhook": True,
            "no_order_placement": True,
            "dashboard_contract_unchanged": True,
            "no_production_records_mutation": True,
        },
        "hashes": {
            "fixture_config": _sha256(fixture_config),
            "fixture_ready_activation_report": _sha256(fixture_ready_json),
            "fixture_missing_env_activation_report": _sha256(fixture_missing_env_json),
            "real_user_activation_report": _sha256(real_activation_json),
        },
    }
    _write_reports(report, reports_dir)
    return report


def _write_reports(report: dict, reports_dir: Path) -> None:
    json_path = reports_dir / REPORT_JSON
    md_path = reports_dir / REPORT_MD
    marker_path = reports_dir / PASS_MARKER
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md_path.write_text(_render_markdown({"overall_status": report["overall_status"], "activation": {
        "activation_status": report["real_user_activation_status"],
        "connector_id": DEFAULT_CONNECTOR_ID,
        "can_run_live_dry_run": report["real_user_can_run_live_dry_run"],
        "blocked_by": report["real_user_blocked_by"],
        "missing_env_vars": report["real_user_missing_env_vars"],
    }}), encoding="utf-8")
    marker_path.write_text(
        "\n".join(
            [
                f"generated_at={report['generated_at']}",
                f"command={report.get('command') or ''}",
                "exit_code=0",
                "target=V2.7-A Live API Metadata Activation",
                f"report_json={json_path}",
                f"report_json_sha256={_sha256(json_path)}",
                f"report_md={md_path}",
                f"report_md_sha256={_sha256(md_path)}",
                f"real_user_activation_status={report['real_user_activation_status']}",
                f"real_user_can_run_live_dry_run={str(report['real_user_can_run_live_dry_run']).lower()}",
                "network_used=false",
                "production_records_written=false",
                "dashboard_contract_changed=false",
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
                    "target=V2.7-A Live API Metadata Activation",
                    f"error={exc}",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        print(f"V2.7-A Live API Metadata Activation FAIL: {exc}")
        return 1
    print(f"V2.7-A Live API Metadata Activation PASS run_id={report['run_id']} report={args.reports_dir / REPORT_JSON}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
