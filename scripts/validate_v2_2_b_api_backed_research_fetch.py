#!/usr/bin/env python3
"""Validate Project Aegis V2.2-B API-backed Research Fetch Dry Run."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping, Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aegis.external_sources.api_fetcher import APIFetchError, fetch_external_api_summary  # noqa: E402
from aegis.models.external_api import ExternalAPIConnectorSpec  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_ROOT = ROOT / "data" / "processed" / "v2_2_b_acceptance"
DEFAULT_REPORTS_DIR = ROOT / "data" / "reports"

PASS_MARKER = "V2_2_B_API_BACKED_RESEARCH_FETCH_PASS.marker"
FAIL_MARKER = "V2_2_B_API_BACKED_RESEARCH_FETCH_FAIL.marker"
REPORT_JSON = "v2_2_b_api_backed_research_fetch_latest.json"
REPORT_MD = "v2_2_b_api_backed_research_fetch_latest.md"
_FIXTURE_SECRET = "fixture-secret-value-must-not-appear"


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def _run_id() -> str:
    return "v2_2_b_api_fetch_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _sha256(path: Path) -> Optional[str]:
    if not path.exists():
        return None
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _approved_research_api() -> ExternalAPIConnectorSpec:
    return ExternalAPIConnectorSpec(
        connector_id="api_user_research_approved_env",
        name="User Approved Strategy Research API",
        provider_type="user_provided_research_api",
        markets=["A", "H", "US"],
        base_url="https://api.example-research-provider.invalid/v1",
        auth_method="env_var",
        required_env_vars=["AEGIS_RESEARCH_API_KEY"],
        license_status="approved",
        retention_policy="summary_only",
        allowed_purposes=["strategy_research_ingestion"],
        can_connect=True,
        notes="Stores env var name only; actual key stays outside repo and Vault.",
    )


def _forbidden_broker_api() -> ExternalAPIConnectorSpec:
    return ExternalAPIConnectorSpec(
        connector_id="api_broker_forbidden",
        name="Forbidden Broker API",
        provider_type="broker_api",
        markets=["US"],
        base_url="https://broker.example.invalid/api",
        auth_method="env_var",
        required_env_vars=["BROKER_API_KEY"],
        license_status="forbidden",
        retention_policy="no_storage",
        allowed_purposes=["order_placement"],
        can_connect=False,
    )


def _fixture_fetch(url: str, headers: Mapping[str, str], timeout: int) -> tuple[int, str, bytes]:
    assert timeout > 0
    assert "Authorization" in headers
    assert _FIXTURE_SECRET in headers["Authorization"]
    payload = {
        "items": [
            {
                "symbol": "600000.SH",
                "market": "A",
                "strategy_family": "low_volatility",
                "summary": "Fixture API research item for bounded dry run.",
            }
        ],
        "source": "fixture-approved-research-api",
        "url_seen": url,
    }
    return 200, "application/json", json.dumps(payload).encode("utf-8")


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

    item = fetch_external_api_summary(
        spec=_approved_research_api(),
        endpoint_path="/strategy-notes",
        query={"market": "A", "family": "low_volatility"},
        env={"AEGIS_RESEARCH_API_KEY": _FIXTURE_SECRET},
        fetch_fn=_fixture_fetch,
    )
    item_json = run_dir / "api_fetch_item.json"
    item_json.write_text(json.dumps(item.model_dump(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    denied_broker = False
    try:
        fetch_external_api_summary(
            spec=_forbidden_broker_api(),
            endpoint_path="/orders",
            env={"BROKER_API_KEY": _FIXTURE_SECRET},
            fetch_fn=_fixture_fetch,
        )
    except APIFetchError:
        denied_broker = True

    serialized = item_json.read_text(encoding="utf-8")
    checks = {
        "approved_api_fetch_succeeded": item.status_code == 200,
        "summary_created": bool(item.summary),
        "content_hash_created": bool(item.content_hash),
        "raw_bytes_not_stored": item.raw_bytes_stored is False,
        "request_headers_not_stored": item.request_headers_stored is False,
        "env_var_name_recorded": item.auth_env_vars_used == ["AEGIS_RESEARCH_API_KEY"],
        "secret_value_not_serialized": _FIXTURE_SECRET not in serialized,
        "broker_api_denied": denied_broker,
        "no_real_trade_or_broker": "no_broker_api" in item.safety_notes,
        "no_trading_webhook": "no_trading_webhook" in item.safety_notes,
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise RuntimeError("V2.2-B acceptance checks failed: " + ", ".join(failed))

    report = {
        "overall_status": "PASS",
        "generated_at": _now_iso(),
        "run_id": run_id,
        "command": command,
        "acceptance_target": "V2.2-B API-backed Research Fetch Dry Run",
        "isolated": True,
        "network_used": False,
        "production_records_written": False,
        "dashboard_contract_changed": False,
        "run_dir": str(run_dir),
        "api_fetch_item_json": str(item_json),
        "checks": checks,
        "summary": {
            "connector_id": item.connector_id,
            "endpoint_path": item.endpoint_path,
            "status_code": item.status_code,
            "auth_env_vars_used": item.auth_env_vars_used,
            "next_target": "V2.2-C API Research To Sandbox Candidate Bridge",
        },
        "safety": {
            "api_key_value_not_stored": True,
            "env_var_names_only": True,
            "request_headers_not_stored": True,
            "raw_bytes_not_stored": True,
            "no_cookie_access": True,
            "no_paywall_bypass": True,
            "no_real_trade": True,
            "no_broker_api": True,
            "no_trading_webhook": True,
            "no_strategy_auto_mutation": True,
            "dashboard_contract_unchanged": True,
            "no_production_records_mutation": True,
        },
        "hashes": {
            "api_fetch_item_json": _sha256(item_json),
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
                "# V2.2-B API-backed Research Fetch Dry Run Acceptance",
                "",
                f"- status: {report['overall_status']}",
                f"- target: {report['acceptance_target']}",
                f"- run_id: {report['run_id']}",
                f"- api_fetch_item_json: `{report['api_fetch_item_json']}`",
                f"- connector_id: `{report['summary']['connector_id']}`",
                f"- endpoint_path: `{report['summary']['endpoint_path']}`",
                "- safety: no API key values, no headers stored, no raw bytes, no broker API, no trading webhook",
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
                "target=V2.2-B API-backed Research Fetch Dry Run",
                f"report_json={json_path}",
                f"report_json_sha256={_sha256(json_path)}",
                f"report_md={md_path}",
                f"report_md_sha256={_sha256(md_path)}",
                f"run_dir={report['run_dir']}",
                f"api_fetch_item_json={report['api_fetch_item_json']}",
                f"api_fetch_item_json_sha256={report['hashes']['api_fetch_item_json']}",
                "network_used=false",
                "dashboard_contract_changed=false",
                "production_records_written=false",
                "api_key_value_not_stored=true",
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
                    "target=V2.2-B API-backed Research Fetch Dry Run",
                    f"error={exc}",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        print(f"V2.2-B API-backed Research Fetch Dry Run FAIL: {exc}")
        return 1

    print(f"V2.2-B API-backed Research Fetch Dry Run PASS run_id={report['run_id']} report={args.reports_dir / REPORT_JSON}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
