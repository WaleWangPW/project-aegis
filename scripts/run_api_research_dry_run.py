#!/usr/bin/env python3
"""Run an approved API research dry-run from non-secret connector metadata."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aegis.external_sources.api_config import get_api_connector_spec  # noqa: E402
from aegis.external_sources.api_fetcher import APIFetchError, fetch_external_api_summary  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_ROOT = ROOT / "data" / "processed" / "api_research_dry_runs"


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def _run_id() -> str:
    return "api_research_dry_run_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _sha256(path: Path) -> Optional[str]:
    if not path.exists():
        return None
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _parse_query(values: list[str]) -> dict[str, str]:
    query: dict[str, str] = {}
    for value in values:
        if "=" not in value:
            raise ValueError(f"query must use key=value format: {value}")
        key, val = value.split("=", 1)
        query[key] = val
    return query


def run_dry_run(
    *,
    config_path: Path,
    connector_id: str,
    endpoint_path: str,
    query: Optional[dict[str, str]] = None,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    run_id: Optional[str] = None,
    command: Optional[str] = None,
    fetch_fn=None,
    env=None,
) -> dict:
    run_id = run_id or _run_id()
    run_dir = output_root / run_id
    run_dir.mkdir(parents=True, exist_ok=False)

    spec = get_api_connector_spec(config_path, connector_id)
    fetch_kwargs = {}
    if fetch_fn is not None:
        fetch_kwargs["fetch_fn"] = fetch_fn
    if env is not None:
        fetch_kwargs["env"] = env
    item = fetch_external_api_summary(
        spec=spec,
        endpoint_path=endpoint_path,
        query=query or {},
        **fetch_kwargs,
    )
    item_json = run_dir / "api_fetch_item.json"
    item_json.write_text(json.dumps(item.model_dump(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    report = {
        "overall_status": "PASS",
        "generated_at": _now_iso(),
        "run_id": run_id,
        "command": command,
        "target": "API Research Dry Run",
        "network_used": fetch_fn is None,
        "production_records_written": False,
        "dashboard_contract_changed": False,
        "config_path": str(config_path),
        "connector_id": connector_id,
        "endpoint_path": endpoint_path,
        "query_keys": sorted((query or {}).keys()),
        "run_dir": str(run_dir),
        "api_fetch_item_json": str(item_json),
        "summary": {
            "status_code": item.status_code,
            "content_type": item.content_type,
            "auth_env_vars_used": item.auth_env_vars_used,
            "content_hash": item.content_hash,
            "summary": item.summary,
        },
        "safety": {
            "api_key_value_not_stored": True,
            "request_headers_not_stored": item.request_headers_stored is False,
            "raw_bytes_not_stored": item.raw_bytes_stored is False,
            "no_real_trade": True,
            "no_broker_api": True,
            "no_trading_webhook": True,
            "dashboard_contract_unchanged": True,
            "no_production_records_mutation": True,
        },
        "hashes": {
            "api_fetch_item_json": _sha256(item_json),
        },
    }
    report_json = run_dir / "api_research_dry_run_report.json"
    report["report_json"] = str(report_json)
    report_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--connector-id", required=True)
    parser.add_argument("--endpoint-path", default="")
    parser.add_argument("--query", action="append", default=[])
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--run-id")
    args = parser.parse_args(argv)
    command = " ".join([Path(sys.argv[0]).name, *(argv if argv is not None else sys.argv[1:])])

    try:
        report = run_dry_run(
            config_path=args.config,
            connector_id=args.connector_id,
            endpoint_path=args.endpoint_path,
            query=_parse_query(args.query),
            output_root=args.output_root,
            run_id=args.run_id,
            command=command,
        )
    except (APIFetchError, Exception) as exc:
        print(f"API Research Dry Run FAIL: {exc}")
        return 1

    print(f"API Research Dry Run PASS run_id={report['run_id']} report={report['report_json']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
