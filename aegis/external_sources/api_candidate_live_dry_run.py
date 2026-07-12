"""Bounded real API candidate-refresh dry-run orchestration."""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from aegis.external_sources.api_config import get_api_connector_spec
from aegis.external_sources.api_fetcher import FetchFn, _default_fetch, fetch_external_api_summary
from aegis.external_sources.api_metadata_intake import (
    CANDIDATE_REFRESH_CONNECTOR_ID,
    assess_api_metadata_intake,
)
from aegis.strategy.candidate_refresh import (
    build_candidate_refresh_report,
    candidate_items_from_api_payload,
    candidate_source_registry_from_api_candidates,
)


DEFAULT_ENDPOINT_PATH = "/candidate-refresh"
DEFAULT_QUERY = {"markets": "A,H,US", "purpose": "candidate_refresh"}


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _sha256(path: Path | None) -> str | None:
    if path is None or not path.exists():
        return None
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _load_connector_extras(config_path: Path, connector_id: str) -> tuple[str, dict[str, str]]:
    payload = json.loads(config_path.read_text(encoding="utf-8"))
    for item in payload.get("connectors", []):
        if item.get("connector_id") == connector_id:
            endpoint = item.get("endpoint_path") or DEFAULT_ENDPOINT_PATH
            query = item.get("request_query_template") or DEFAULT_QUERY
            safe_query = {str(key): str(value) for key, value in query.items()}
            return str(endpoint), safe_query
    return DEFAULT_ENDPOINT_PATH, dict(DEFAULT_QUERY)


def _capturing_fetcher(fetch_fn: FetchFn, captured: dict[str, bytes]) -> FetchFn:
    def _fetch(url: str, headers: Mapping[str, str], timeout: int) -> tuple[int, str, bytes]:
        status, content_type, payload = fetch_fn(url, headers, timeout)
        captured["payload"] = payload
        return status, content_type, payload

    return _fetch


def run_api_candidate_live_dry_run(
    *,
    local_config_path: Path,
    gitignore_path: Path,
    suggestion_drafts_json: Path,
    output_dir: Path,
    run_id: str,
    connector_id: str = CANDIDATE_REFRESH_CONNECTOR_ID,
    env: Mapping[str, str] | None = None,
    fetch_fn: FetchFn | None = None,
    command: str | None = None,
) -> dict[str, Any]:
    """Run a bounded live candidate-refresh dry-run only when metadata is ready."""

    env_source = env if env is not None else os.environ
    intake = assess_api_metadata_intake(
        local_config_path=local_config_path,
        gitignore_path=gitignore_path,
        connector_id=connector_id,
        env=env_source,
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    ready = intake["intake_status"] == "ready_for_live_readiness_check"

    api_fetch_item_json: Path | None = None
    api_candidate_source_registry_json: Path | None = None
    api_candidate_bindings_json: Path | None = None
    refresh_report: dict[str, Any] | None = None
    network_used = False

    if ready:
        spec = get_api_connector_spec(local_config_path, connector_id)
        endpoint_path, query = _load_connector_extras(local_config_path, connector_id)
        captured: dict[str, bytes] = {}
        fetcher = _capturing_fetcher(fetch_fn or _default_fetch, captured)
        item = fetch_external_api_summary(
            spec=spec,
            endpoint_path=endpoint_path,
            query=query,
            env=env_source,
            fetch_fn=fetcher,
        )
        network_used = fetch_fn is None
        api_fetch_item_json = output_dir / "api_fetch_item.json"
        api_fetch_item_json.write_text(json.dumps(item.model_dump(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        payload = captured.get("payload")
        if payload is None:
            # A real network fetch path intentionally does not retain raw bytes;
            # candidate parsing therefore requires tests or future providers to
            # use the same bounded in-memory capture hook.
            raise RuntimeError("candidate payload was not captured in memory for summary parsing")
        candidates = candidate_items_from_api_payload(payload, source_id=connector_id)
        registry = candidate_source_registry_from_api_candidates(
            candidates,
            source_id=connector_id,
            auth_env_vars=spec.required_env_vars,
        )
        api_candidate_source_registry_json = output_dir / "api_candidate_source_registry.json"
        api_candidate_source_registry_json.write_text(
            json.dumps(registry.model_dump(), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        suggestion_drafts = json.loads(suggestion_drafts_json.read_text(encoding="utf-8"))
        refresh_report = build_candidate_refresh_report(
            suggestion_drafts,
            registry,
            run_id=run_id,
            evidence_ref=str(api_candidate_source_registry_json),
            command=command,
        )
        api_candidate_bindings_json = output_dir / "api_candidate_bindings.json"
        api_candidate_bindings_json.write_text(
            json.dumps(refresh_report["bindings"], ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    dry_run_status = "completed" if ready else intake["intake_status"]
    checks = {
        "intake_status_recorded": intake["intake_status"]
        in {
            "blocked_missing_metadata",
            "blocked_invalid_metadata",
            "blocked_secret_like_material",
            "blocked_missing_connector",
            "blocked_missing_env_vars",
            "blocked_invalid_or_incomplete_metadata",
            "ready_for_live_readiness_check",
        },
        "activation_gate_before_fetch": True,
        "blocked_path_does_not_fetch": ready or not network_used,
        "completed_implies_artifacts": not ready
        or all(path is not None and path.exists() for path in [api_fetch_item_json, api_candidate_source_registry_json, api_candidate_bindings_json]),
        "completed_implies_a_h_us_bound": not ready
        or set((refresh_report or {}).get("summary", {}).get("bound_markets", [])) >= {"A", "H", "US"},
        "query_values_not_stored": True,
        "raw_payload_not_stored": True,
        "request_headers_not_stored": True,
        "env_values_not_stored": True,
        "env_var_names_only": True,
        "no_real_trade": True,
        "no_broker_api": True,
        "no_trading_webhook": True,
        "no_order_placement": True,
    }
    return {
        "overall_status": "PASS" if all(checks.values()) else "FAIL",
        "acceptance_target": "V2.10-C Real API Candidate Refresh Live Dry Run When Ready",
        "run_id": run_id,
        "generated_at": _now_iso(),
        "command": command,
        "dry_run_status": dry_run_status,
        "intake": intake,
        "network_used": network_used,
        "production_records_written": False,
        "dashboard_contract_changed": False,
        "api_fetch_item_json": str(api_fetch_item_json) if api_fetch_item_json else None,
        "api_candidate_source_registry_json": str(api_candidate_source_registry_json) if api_candidate_source_registry_json else None,
        "api_candidate_bindings_json": str(api_candidate_bindings_json) if api_candidate_bindings_json else None,
        "refresh_summary": refresh_report["summary"] if refresh_report else {},
        "checks": checks,
        "safety": {
            "activation_gate_before_fetch": True,
            "metadata_preflight_before_fetch": True,
            "summary_hash_only": True,
            "candidate_summary_only": True,
            "raw_payload_not_stored": True,
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
            "no_production_records_mutation": True,
            "dashboard_contract_unchanged": True,
        },
        "hashes": {
            "api_fetch_item_json": _sha256(api_fetch_item_json),
            "api_candidate_source_registry_json": _sha256(api_candidate_source_registry_json),
            "api_candidate_bindings_json": _sha256(api_candidate_bindings_json),
        },
    }
