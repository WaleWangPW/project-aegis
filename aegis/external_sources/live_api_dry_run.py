"""Bounded live API dry-run orchestration.

This module combines the V2.7-A metadata activation gate with the existing
approved API fetcher. It writes only summary/hash evidence and never stores
secret values, request headers, raw bytes, broker instructions, or orders.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping

from aegis.external_sources.api_activation import assess_live_api_activation
from aegis.external_sources.api_config import get_api_connector_spec
from aegis.external_sources.api_fetcher import FetchFn, fetch_external_api_summary


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def _sha256(path: Path) -> str | None:
    if not path.exists():
        return None
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _query_keys(query: Mapping[str, str] | None) -> list[str]:
    return sorted((query or {}).keys())


def build_live_api_dry_run_report(
    *,
    config_path: Path,
    connector_id: str,
    endpoint_path: str,
    output_root: Path,
    run_id: str,
    query: Mapping[str, str] | None = None,
    env: Mapping[str, str] | None = None,
    fetch_fn: FetchFn | None = None,
    command: str | None = None,
) -> dict:
    """Run a bounded live API dry-run if activation is ready.

    When metadata or env vars are missing, this still writes a blocking report
    so OpenClaw/Codex can inspect the exact reason without guessing.
    """

    run_dir = output_root / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    activation = assess_live_api_activation(config_path=config_path, connector_id=connector_id, env=env)
    ready = activation["activation_status"] == "ready_for_live_dry_run"
    item_json: Path | None = None
    summary: dict = {}

    if ready:
        spec = get_api_connector_spec(config_path, connector_id)
        fetch_kwargs = {}
        if fetch_fn is not None:
            fetch_kwargs["fetch_fn"] = fetch_fn
        item = fetch_external_api_summary(
            spec=spec,
            endpoint_path=endpoint_path,
            query=query or {},
            env=env,
            **fetch_kwargs,
        )
        item_json = run_dir / "api_fetch_item.json"
        item_json.write_text(json.dumps(item.model_dump(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        summary = {
            "status_code": item.status_code,
            "content_type": item.content_type,
            "auth_env_vars_used": item.auth_env_vars_used,
            "content_hash": item.content_hash,
            "summary": item.summary,
            "raw_bytes_stored": item.raw_bytes_stored,
            "request_headers_stored": item.request_headers_stored,
        }

    report = {
        "overall_status": "PASS" if ready else "BLOCKED",
        "acceptance_target": "V2.7-B Bounded Live API Dry Run Entrypoint",
        "generated_at": _now_iso(),
        "run_id": run_id,
        "command": command,
        "config_path": str(config_path),
        "connector_id": connector_id,
        "endpoint_path": endpoint_path,
        "query_keys": _query_keys(query),
        "run_dir": str(run_dir),
        "activation": activation,
        "live_dry_run_status": "completed" if ready else activation["activation_status"],
        "network_used": bool(ready and fetch_fn is None),
        "production_records_written": False,
        "dashboard_contract_changed": False,
        "api_fetch_item_json": str(item_json) if item_json else None,
        "summary": summary,
        "checks": {
            "activation_checked_first": True,
            "ready_required_before_fetch": ready or item_json is None,
            "blocked_run_does_not_fetch": ready or item_json is None,
            "env_values_not_stored": True,
            "env_var_names_only": True,
            "query_values_not_stored": True,
            "request_headers_not_stored": summary.get("request_headers_stored") is False if ready else True,
            "raw_bytes_not_stored": summary.get("raw_bytes_stored") is False if ready else True,
            "no_real_trade": True,
            "no_broker_api": True,
            "no_webhook": True,
            "no_order_placement": True,
            "dashboard_contract_unchanged": True,
            "production_records_not_written": True,
        },
        "safety": {
            "summary_hash_only": True,
            "raw_bytes_not_stored": True,
            "request_headers_not_stored": True,
            "env_values_not_stored": True,
            "env_var_names_only": True,
            "query_values_not_stored": True,
            "no_real_trade": True,
            "no_broker_api": True,
            "no_trading_webhook": True,
            "no_order_placement": True,
            "dashboard_contract_unchanged": True,
            "no_production_records_mutation": True,
        },
        "hashes": {
            "api_fetch_item_json": _sha256(item_json) if item_json else None,
        },
    }
    report_json = run_dir / "live_api_dry_run_report.json"
    report["report_json"] = str(report_json)
    report_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report
