#!/usr/bin/env python3
"""Validate Project Aegis V2.3-B Real User API Dry Run entrypoint."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping, Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import scripts.run_api_research_dry_run as dry_runner  # noqa: E402
from aegis.external_sources.api_config import APIConfigError, get_api_connector_spec  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_ROOT = ROOT / "data" / "processed" / "v2_3_b_acceptance"
DEFAULT_REPORTS_DIR = ROOT / "data" / "reports"
REAL_USER_CONFIG = ROOT / "config" / "external_api_connectors.local.json"

PASS_MARKER = "V2_3_B_REAL_USER_API_DRY_RUN_PASS.marker"
FAIL_MARKER = "V2_3_B_REAL_USER_API_DRY_RUN_FAIL.marker"
REPORT_JSON = "v2_3_b_real_user_api_dry_run_latest.json"
REPORT_MD = "v2_3_b_real_user_api_dry_run_latest.md"
_FIXTURE_SECRET = "fixture-v2-3-b-secret-must-not-appear"


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def _run_id() -> str:
    return "v2_3_b_real_user_api_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _sha256(path: Path) -> Optional[str]:
    if not path.exists():
        return None
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _fixture_fetch(url: str, headers: Mapping[str, str], timeout: int) -> tuple[int, str, bytes]:
    assert timeout > 0
    assert _FIXTURE_SECRET in headers.get("Authorization", "")
    payload = {
        "items": [
            {
                "symbol": "600000.SH",
                "market": "A",
                "strategy_family": "value_quality",
                "summary": "Fixture real-user API dry-run response.",
            }
        ],
        "source": "fixture-real-user-config",
        "url_seen": url,
    }
    return 200, "application/json", json.dumps(payload).encode("utf-8")


def _write_fixture_user_config(path: Path) -> None:
    payload = {
        "schema_version": "external_api_connectors.local.fixture.v1",
        "connectors": [
            {
                "connector_id": "api_fixture_real_user_research",
                "name": "Fixture Real User Research API",
                "provider_type": "user_provided_research_api",
                "markets": ["A", "H", "US"],
                "base_url": "https://api.fixture-research-provider.invalid/v1",
                "auth_method": "env_var",
                "required_env_vars": ["AEGIS_RESEARCH_API_KEY"],
                "license_status": "approved",
                "retention_policy": "summary_only",
                "allowed_purposes": ["strategy_research_ingestion"],
                "can_connect": True,
                "notes": "Fixture config with env var name only.",
            }
        ],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _real_config_blocked_reason() -> str:
    try:
        get_api_connector_spec(REAL_USER_CONFIG, "api_fixture_real_user_research")
    except APIConfigError as exc:
        return str(exc)
    return ""


def run_acceptance(
    *,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    reports_dir: Path = DEFAULT_REPORTS_DIR,
    run_id: Optional[str] = None,
    command: Optional[str] = None,
) -> dict:
    run_id = run_id or _run_id()
    run_dir = output_root / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    reports_dir.mkdir(parents=True, exist_ok=True)

    fixture_config = run_dir / "external_api_connectors.local.fixture.json"
    _write_fixture_user_config(fixture_config)
    dry_report = dry_runner.run_dry_run(
        config_path=fixture_config,
        connector_id="api_fixture_real_user_research",
        endpoint_path="/strategy-notes",
        query={"market": "A", "family": "value_quality"},
        output_root=run_dir,
        run_id="fixture_api_dry_run",
        command="fixture real user api dry run",
        fetch_fn=_fixture_fetch,
        env={"AEGIS_RESEARCH_API_KEY": _FIXTURE_SECRET},
    )

    dry_report_json = Path(dry_report["report_json"])
    dry_report_text = dry_report_json.read_text(encoding="utf-8")
    real_config_blocked_reason = _real_config_blocked_reason()
    checks = {
        "fixture_user_config_written": fixture_config.exists(),
        "fixture_dry_run_passed": dry_report["overall_status"] == "PASS",
        "fixture_dry_run_report_exists": dry_report_json.exists(),
        "secret_value_not_serialized": _FIXTURE_SECRET not in dry_report_text,
        "env_var_name_recorded": dry_report["summary"]["auth_env_vars_used"] == ["AEGIS_RESEARCH_API_KEY"],
        "raw_bytes_not_stored": dry_report["safety"]["raw_bytes_not_stored"] is True,
        "request_headers_not_stored": dry_report["safety"]["request_headers_not_stored"] is True,
        "no_real_trade_or_broker": dry_report["safety"]["no_real_trade"] is True
        and dry_report["safety"]["no_broker_api"] is True,
        "real_user_config_missing_is_blocked": bool(real_config_blocked_reason),
        "dashboard_contract_unchanged": dry_report["dashboard_contract_changed"] is False,
        "production_records_not_written": dry_report["production_records_written"] is False,
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise RuntimeError("V2.3-B acceptance checks failed: " + ", ".join(failed))

    report = {
        "overall_status": "PASS",
        "generated_at": _now_iso(),
        "run_id": run_id,
        "command": command,
        "acceptance_target": "V2.3-B Real User API Dry Run When Metadata Is Provided",
        "isolated": True,
        "network_used": False,
        "production_records_written": False,
        "dashboard_contract_changed": False,
        "run_dir": str(run_dir),
        "fixture_config": str(fixture_config),
        "fixture_dry_run_report": str(dry_report_json),
        "real_user_config_path": str(REAL_USER_CONFIG),
        "real_user_config_status": "blocked_missing_metadata" if real_config_blocked_reason else "available",
        "real_user_config_blocked_reason": real_config_blocked_reason,
        "checks": checks,
        "summary": {
            "fixture_connector_id": "api_fixture_real_user_research",
            "auth_env_vars_used": dry_report["summary"]["auth_env_vars_used"],
            "dry_run_content_hash": dry_report["summary"]["content_hash"],
            "next_target": "V2.3-C Live API Dry Run After User Provides Metadata",
        },
        "safety": {
            "fixture_mode": True,
            "real_user_config_not_required_for_acceptance": True,
            "api_key_value_not_stored": True,
            "env_var_names_only": True,
            "request_headers_not_stored": True,
            "raw_bytes_not_stored": True,
            "no_real_trade": True,
            "no_broker_api": True,
            "no_trading_webhook": True,
            "dashboard_contract_unchanged": True,
            "no_production_records_mutation": True,
        },
        "hashes": {
            "fixture_config": _sha256(fixture_config),
            "fixture_dry_run_report": _sha256(dry_report_json),
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
                "# V2.3-B Real User API Dry Run Acceptance",
                "",
                f"- status: {report['overall_status']}",
                f"- target: {report['acceptance_target']}",
                f"- run_id: {report['run_id']}",
                f"- fixture_dry_run_report: `{report['fixture_dry_run_report']}`",
                f"- real_user_config_status: `{report['real_user_config_status']}`",
                "- safety: fixture mode, no API key values, no raw bytes, no headers, no broker API",
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
                "target=V2.3-B Real User API Dry Run When Metadata Is Provided",
                f"report_json={json_path}",
                f"report_json_sha256={_sha256(json_path)}",
                f"report_md={md_path}",
                f"report_md_sha256={_sha256(md_path)}",
                f"fixture_dry_run_report={report['fixture_dry_run_report']}",
                f"fixture_dry_run_report_sha256={report['hashes']['fixture_dry_run_report']}",
                f"real_user_config_status={report['real_user_config_status']}",
                "network_used=false",
                "dashboard_contract_changed=false",
                "production_records_written=false",
                "api_key_value_not_stored=true",
                "no_real_trade=true",
                "no_broker_api=true",
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
    args = parser.parse_args(argv)
    command = " ".join([Path(sys.argv[0]).name, *(argv if argv is not None else sys.argv[1:])])

    try:
        report = run_acceptance(
            output_root=args.output_root,
            reports_dir=args.reports_dir,
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
                    "target=V2.3-B Real User API Dry Run When Metadata Is Provided",
                    f"error={exc}",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        print(f"V2.3-B Real User API Dry Run FAIL: {exc}")
        return 1

    print(f"V2.3-B Real User API Dry Run PASS run_id={report['run_id']} report={args.reports_dir / REPORT_JSON}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
