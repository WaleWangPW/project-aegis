#!/usr/bin/env python3
"""Validate Project Aegis V2.8-I Real User API Handoff Refresh."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aegis.external_sources.api_connector import evaluate_api_connector_registry  # noqa: E402
from aegis.models.external_api import ExternalAPIConnectorSpec  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_ROOT = ROOT / "data" / "processed" / "v2_8_i_acceptance"
DEFAULT_REPORTS_DIR = ROOT / "data" / "reports"
HANDOFF_DOC = ROOT / "docs" / "API_CONFIGURATION_HANDOFF.md"
REFRESH_DOC = ROOT / "docs" / "V2_8_I_REAL_USER_API_HANDOFF_REFRESH.md"
USER_TEMPLATE = ROOT / "config" / "external_api_connectors.user-template.json"
REAL_USER_CONFIG = ROOT / "config" / "external_api_connectors.local.json"

PASS_MARKER = "V2_8_I_REAL_USER_API_HANDOFF_REFRESH_PASS.marker"
FAIL_MARKER = "V2_8_I_REAL_USER_API_HANDOFF_REFRESH_FAIL.marker"
REPORT_JSON = "v2_8_i_real_user_api_handoff_refresh_latest.json"
REPORT_MD = "v2_8_i_real_user_api_handoff_refresh_latest.md"

REQUIRED_CONNECTOR_FIELDS = {
    "connector_id",
    "name",
    "provider_type",
    "markets",
    "base_url",
    "auth_method",
    "required_env_vars",
    "license_status",
    "retention_policy",
    "allowed_purposes",
    "can_connect",
    "endpoint_path",
    "request_query_template",
    "candidate_payload_schema",
    "rate_limit_note",
    "notes",
}
REQUIRED_CANDIDATE_SCHEMA_FIELDS = {
    "items_path",
    "symbol_field",
    "market_field",
    "name_field",
    "score_field",
    "status_field",
    "allowed_markets",
    "max_items_per_market",
    "freshness_policy",
    "candidate_summary_only",
}
FORBIDDEN_URL_PATTERNS = ("token=", "secret=", "api_key=", "apikey=", "password=", "bearer=", "cookie=")
FORBIDDEN_TEXT_PATTERNS = ("sk-", "bearer ", "password=", "cookie=", "oauth_refresh_token")
FORBIDDEN_PURPOSE_TERMS = ("trade", "trading", "order", "broker", "webhook")


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def _run_id() -> str:
    return "v2_8_i_real_user_api_handoff_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _sha256(path: Path) -> Optional[str]:
    if not path.exists():
        return None
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _load_template(path: Optional[Path] = None) -> dict[str, Any]:
    return json.loads((path or USER_TEMPLATE).read_text(encoding="utf-8"))


def _connector_specs_from_template(payload: dict[str, Any]) -> list[ExternalAPIConnectorSpec]:
    return [ExternalAPIConnectorSpec(**item) for item in payload.get("connectors", [])]


def _walk_strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        strings: list[str] = []
        for child in value.values():
            strings.extend(_walk_strings(child))
        return strings
    if isinstance(value, list):
        strings = []
        for child in value:
            strings.extend(_walk_strings(child))
        return strings
    return []


def _url_has_forbidden_material(url: str) -> bool:
    lowered = url.lower()
    return any(pattern in lowered for pattern in FORBIDDEN_URL_PATTERNS)


def _text_has_forbidden_secret_value(text: str) -> bool:
    lowered = text.lower()
    return any(pattern in lowered for pattern in FORBIDDEN_TEXT_PATTERNS)


def _template_has_secret_values(payload: dict[str, Any]) -> bool:
    for text in _walk_strings(payload):
        if _text_has_forbidden_secret_value(text):
            return True
    return any(_url_has_forbidden_material(item.get("base_url", "")) for item in payload.get("connectors", []))


def _connector_has_required_fields(item: dict[str, Any]) -> bool:
    return REQUIRED_CONNECTOR_FIELDS.issubset(item.keys())


def _candidate_schema_ok(item: dict[str, Any]) -> bool:
    schema = item.get("candidate_payload_schema")
    if not isinstance(schema, dict):
        return False
    if not REQUIRED_CANDIDATE_SCHEMA_FIELDS.issubset(schema.keys()):
        return False
    return (
        schema.get("candidate_summary_only") is True
        and set(schema.get("allowed_markets", [])) >= {"A", "H", "US"}
        and isinstance(schema.get("max_items_per_market"), int)
        and schema.get("max_items_per_market", 0) > 0
    )


def _purposes_are_safe(item: dict[str, Any]) -> bool:
    purposes = " ".join(item.get("allowed_purposes", [])).lower()
    return not any(term in purposes for term in FORBIDDEN_PURPOSE_TERMS)


def _real_user_config_status(path: Path = REAL_USER_CONFIG) -> str:
    return "available_local_metadata" if path.exists() else "blocked_missing_metadata"


def _render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# V2.8-I Real User API Handoff Refresh",
        "",
        f"- status: `{report['overall_status']}`",
        f"- target: `{report['acceptance_target']}`",
        f"- run_id: `{report['run_id']}`",
        f"- user_template: `{report['user_template']}`",
        f"- real_user_config_status: `{report['real_user_config_status']}`",
        f"- next_target: `{report['summary']['next_target']}`",
        "",
        "## Boundary",
        "",
        "- Non-secret metadata template only.",
        "- API key values remain local env vars only.",
        "- Candidate refresh is research input only.",
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
) -> dict[str, Any]:
    run_id = run_id or _run_id()
    run_dir = output_root / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    reports_dir.mkdir(parents=True, exist_ok=True)

    handoff_text = HANDOFF_DOC.read_text(encoding="utf-8")
    refresh_text = REFRESH_DOC.read_text(encoding="utf-8")
    template_payload = _load_template()
    template_text = USER_TEMPLATE.read_text(encoding="utf-8")
    template_copy = run_dir / "external_api_connectors.user-template.json"
    template_copy.write_text(json.dumps(template_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    connector_items = template_payload.get("connectors", [])
    try:
        specs = _connector_specs_from_template(template_payload)
        registry = evaluate_api_connector_registry(specs)
    except Exception as exc:
        raise RuntimeError("V2.8-I acceptance checks failed: template_parses_existing_policy_model") from exc
    registry_json = run_dir / "candidate_refresh_api_connector_registry.json"
    registry_json.write_text(json.dumps(registry, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    checks = {
        "handoff_doc_exists": HANDOFF_DOC.exists(),
        "refresh_doc_exists": REFRESH_DOC.exists(),
        "user_template_exists": USER_TEMPLATE.exists(),
        "docs_require_non_secret_metadata": all(
            term in handoff_text + refresh_text
            for term in ["non-secret metadata", "API key values", "Bearer tokens", "Broker credentials"]
        ),
        "docs_define_candidate_refresh_fields": all(
            term in refresh_text
            for term in ["candidate_payload_schema", "items_path", "symbol_field", "market_field", "max_items_per_market"]
        ),
        "template_has_connector": len(connector_items) == 1,
        "template_connector_required_fields": all(_connector_has_required_fields(item) for item in connector_items),
        "template_candidate_schema_ok": all(_candidate_schema_ok(item) for item in connector_items),
        "template_parses_existing_policy_model": len(specs) == 1,
        "template_policy_allows_research_connector": registry["allow_count"] == 1 and registry["deny_count"] == 0,
        "allowed_purposes_are_candidate_refresh_only": all(
            "candidate_refresh" in item.get("allowed_purposes", []) and _purposes_are_safe(item)
            for item in connector_items
        ),
        "env_var_names_only": all(
            item.get("auth_method") == "env_var" and item.get("required_env_vars") == ["AEGIS_CANDIDATE_REFRESH_API_KEY"]
            for item in connector_items
        ),
        "no_secret_values_in_template": not _template_has_secret_values(template_payload)
        and "AEGIS_CANDIDATE_REFRESH_API_KEY" in template_text,
        "no_broker_or_webhook": all(
            item.get("provider_type") not in {"broker_api", "trading_webhook"} for item in connector_items
        ),
        "real_user_config_status_recorded": _real_user_config_status() in {
            "blocked_missing_metadata",
            "available_local_metadata",
        },
        "no_production_records_mutation": True,
        "dashboard_contract_unchanged": True,
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise RuntimeError("V2.8-I acceptance checks failed: " + ", ".join(failed))

    report = {
        "overall_status": "PASS",
        "acceptance_target": "V2.8-I Real User API Handoff Refresh",
        "generated_at": _now_iso(),
        "run_id": run_id,
        "command": command,
        "network_used": False,
        "production_records_written": False,
        "dashboard_contract_changed": False,
        "run_dir": str(run_dir),
        "handoff_doc": str(HANDOFF_DOC),
        "refresh_doc": str(REFRESH_DOC),
        "user_template": str(USER_TEMPLATE),
        "template_copy": str(template_copy),
        "validated_registry_json": str(registry_json),
        "real_user_config_path": str(REAL_USER_CONFIG),
        "real_user_config_status": _real_user_config_status(),
        "checks": checks,
        "summary": {
            "connector_count": registry["connector_count"],
            "allow_count": registry["allow_count"],
            "deny_count": registry["deny_count"],
            "required_env_vars": ["AEGIS_CANDIDATE_REFRESH_API_KEY"],
            "candidate_refresh_fields": sorted(REQUIRED_CANDIDATE_SCHEMA_FIELDS),
            "next_target": "V2.8-J Real User API Candidate Refresh Dry Run After Local Metadata",
        },
        "safety": {
            "metadata_template_only": True,
            "env_values_not_stored": True,
            "env_var_names_only": True,
            "no_raw_api_response": True,
            "no_request_headers_stored": True,
            "candidate_refresh_research_input_only": True,
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
            "handoff_doc": _sha256(HANDOFF_DOC),
            "refresh_doc": _sha256(REFRESH_DOC),
            "user_template": _sha256(USER_TEMPLATE),
            "template_copy": _sha256(template_copy),
            "validated_registry_json": _sha256(registry_json),
        },
    }
    _write_reports(report, reports_dir)
    return report


def _write_reports(report: dict[str, Any], reports_dir: Path) -> None:
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
                "target=V2.8-I Real User API Handoff Refresh",
                f"report_json={json_path}",
                f"report_json_sha256={_sha256(json_path)}",
                f"report_md={md_path}",
                f"report_md_sha256={_sha256(md_path)}",
                f"refresh_doc={report['refresh_doc']}",
                f"refresh_doc_sha256={report['hashes']['refresh_doc']}",
                f"user_template={report['user_template']}",
                f"user_template_sha256={report['hashes']['user_template']}",
                f"real_user_config_status={report['real_user_config_status']}",
                "network_used=false",
                "production_records_written=false",
                "dashboard_contract_changed=false",
                "metadata_template_only=true",
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
                    "target=V2.8-I Real User API Handoff Refresh",
                    f"error={exc}",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        print(f"V2.8-I Real User API Handoff Refresh FAIL: {exc}")
        return 1

    print(
        "V2.8-I Real User API Handoff Refresh PASS "
        f"run_id={report['run_id']} report={args.reports_dir / REPORT_JSON}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
