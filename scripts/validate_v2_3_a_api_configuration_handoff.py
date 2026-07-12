#!/usr/bin/env python3
"""Validate Project Aegis V2.3-A Real User API Configuration Handoff."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aegis.external_sources.api_connector import evaluate_api_connector_registry  # noqa: E402
from aegis.models.external_api import ExternalAPIConnectorSpec  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_ROOT = ROOT / "data" / "processed" / "v2_3_a_acceptance"
DEFAULT_REPORTS_DIR = ROOT / "data" / "reports"
HANDOFF_DOC = ROOT / "docs" / "API_CONFIGURATION_HANDOFF.md"
EXAMPLE_CONFIG = ROOT / "config" / "external_api_connectors.example.json"

PASS_MARKER = "V2_3_A_API_CONFIGURATION_HANDOFF_PASS.marker"
FAIL_MARKER = "V2_3_A_API_CONFIGURATION_HANDOFF_FAIL.marker"
REPORT_JSON = "v2_3_a_api_configuration_handoff_latest.json"
REPORT_MD = "v2_3_a_api_configuration_handoff_latest.md"

FORBIDDEN_SECRET_PATTERNS = [
    "sk-",
    "bearer ",
    "password=",
    "api_key=",
    "token=",
    "cookie=",
    "secret=",
]


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def _run_id() -> str:
    return "v2_3_a_api_handoff_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _sha256(path: Path) -> Optional[str]:
    if not path.exists():
        return None
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _load_example_specs(path: Path = EXAMPLE_CONFIG) -> list[ExternalAPIConnectorSpec]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return [ExternalAPIConnectorSpec(**item) for item in payload.get("connectors", [])]


def _text_has_forbidden_secret_value(text: str) -> bool:
    lowered = text.lower()
    return any(pattern in lowered for pattern in FORBIDDEN_SECRET_PATTERNS)


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

    handoff_text = HANDOFF_DOC.read_text(encoding="utf-8")
    example_text = EXAMPLE_CONFIG.read_text(encoding="utf-8")
    specs = _load_example_specs()
    registry = evaluate_api_connector_registry(specs)
    registry_json = run_dir / "validated_api_connector_registry.json"
    registry_json.write_text(json.dumps(registry, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    decisions = {item["connector_id"]: item for item in registry["decisions"]}
    checks = {
        "handoff_doc_exists": HANDOFF_DOC.exists(),
        "example_config_exists": EXAMPLE_CONFIG.exists(),
        "handoff_lists_required_metadata": all(
            term in handoff_text
            for term in [
                "connector_id",
                "base_url",
                "required_env_vars",
                "license_status",
                "retention_policy",
                "allowed_purposes",
            ]
        ),
        "handoff_forbids_secret_values": all(
            term in handoff_text
            for term in ["API key values", "Secret values", "Cookies", "Bearer tokens", "Passwords"]
        ),
        "example_specs_parse": len(specs) == 2,
        "example_official_api_allowed": decisions["api_sec_companyfacts"]["decision"] == "allow",
        "example_user_api_allowed": decisions["api_user_research_approved_env"]["decision"] == "allow",
        "env_var_name_only": decisions["api_user_research_approved_env"]["required_env_vars"] == [
            "AEGIS_RESEARCH_API_KEY"
        ],
        "no_forbidden_secret_values_in_example": not _text_has_forbidden_secret_value(example_text),
        "no_broker_or_webhook": all(
            spec.provider_type not in {"broker_api", "trading_webhook"} for spec in specs
        ),
        "safety_registry_ok": registry["safety"]["no_secret_values_stored"] is True
        and registry["safety"]["no_broker_api"] is True
        and registry["safety"]["no_trading_webhook"] is True,
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise RuntimeError("V2.3-A acceptance checks failed: " + ", ".join(failed))

    report = {
        "overall_status": "PASS",
        "generated_at": _now_iso(),
        "run_id": run_id,
        "command": command,
        "acceptance_target": "V2.3-A Real User API Configuration Handoff",
        "isolated": True,
        "network_used": False,
        "production_records_written": False,
        "dashboard_contract_changed": False,
        "run_dir": str(run_dir),
        "handoff_doc": str(HANDOFF_DOC),
        "example_config": str(EXAMPLE_CONFIG),
        "validated_registry_json": str(registry_json),
        "checks": checks,
        "summary": {
            "example_connector_count": registry["connector_count"],
            "allow_count": registry["allow_count"],
            "deny_count": registry["deny_count"],
            "required_env_vars": decisions["api_user_research_approved_env"]["required_env_vars"],
            "next_target": "V2.3-B Real User API Dry Run When Metadata Is Provided",
        },
        "safety": registry["safety"]
        | {
            "handoff_collects_metadata_only": True,
            "do_not_send_secret_in_chat": True,
            "api_key_values_not_stored": True,
            "no_real_trade": True,
            "no_broker_api": True,
            "no_trading_webhook": True,
            "dashboard_contract_unchanged": True,
            "no_production_records_mutation": True,
        },
        "hashes": {
            "handoff_doc": _sha256(HANDOFF_DOC),
            "example_config": _sha256(EXAMPLE_CONFIG),
            "validated_registry_json": _sha256(registry_json),
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
                "# V2.3-A Real User API Configuration Handoff Acceptance",
                "",
                f"- status: {report['overall_status']}",
                f"- target: {report['acceptance_target']}",
                f"- run_id: {report['run_id']}",
                f"- handoff_doc: `{report['handoff_doc']}`",
                f"- example_config: `{report['example_config']}`",
                f"- required_env_vars: `{', '.join(report['summary']['required_env_vars'])}`",
                "- safety: metadata only, no API key values, no broker API, no trading webhook",
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
                "target=V2.3-A Real User API Configuration Handoff",
                f"report_json={json_path}",
                f"report_json_sha256={_sha256(json_path)}",
                f"report_md={md_path}",
                f"report_md_sha256={_sha256(md_path)}",
                f"handoff_doc={report['handoff_doc']}",
                f"handoff_doc_sha256={report['hashes']['handoff_doc']}",
                f"example_config={report['example_config']}",
                f"example_config_sha256={report['hashes']['example_config']}",
                "network_used=false",
                "dashboard_contract_changed=false",
                "production_records_written=false",
                "api_key_values_not_stored=true",
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
                    "target=V2.3-A Real User API Configuration Handoff",
                    f"error={exc}",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        print(f"V2.3-A Real User API Configuration Handoff FAIL: {exc}")
        return 1

    print(f"V2.3-A Real User API Configuration Handoff PASS run_id={report['run_id']} report={args.reports_dir / REPORT_JSON}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
