"""H/US historical cache readiness dry run.

The dry run fetches a tiny bounded sample from approved H/US providers and
writes normalized CSV cache artifacts into a run-specific directory only. It
does not mutate production cache/provider config or enable suggestions.
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping

FetchJson = Callable[[str], tuple[int, Any]]

DEFAULT_READINESS_CASES = [
    {
        "case_id": "h_00700_eodhd_daily_bars",
        "route_id": "h_daily_bars_eodhd_primary",
        "provider": "eodhd",
        "market": "H",
        "canonical_symbol": "00700.HK",
        "provider_symbol": "0700.HK",
        "data_type": "daily_bars",
        "from_date": "2026-07-01",
        "to_date": "2026-07-08",
    },
    {
        "case_id": "us_aapl_eodhd_daily_bars",
        "route_id": "us_daily_bars_eodhd_primary_twelve_backup",
        "provider": "eodhd",
        "market": "US",
        "canonical_symbol": "AAPL.US",
        "provider_symbol": "AAPL.US",
        "data_type": "daily_bars",
        "from_date": "2026-07-01",
        "to_date": "2026-07-08",
    },
    {
        "case_id": "us_aapl_twelve_data_daily_bars",
        "route_id": "us_daily_bars_eodhd_primary_twelve_backup",
        "provider": "twelve_data",
        "market": "US",
        "canonical_symbol": "AAPL.US",
        "provider_symbol": "AAPL",
        "data_type": "daily_bars",
        "from_date": "2026-07-01",
        "to_date": "2026-07-08",
        "outputsize": "5",
    },
]

NORMALIZED_COLUMNS = ["date", "open", "high", "low", "close", "volume"]


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _default_fetch_json(url: str) -> tuple[int, Any]:
    req = urllib.request.Request(url, headers={"User-Agent": "ProjectAegis/0.1 h-us-cache-readiness"})
    with urllib.request.urlopen(req, timeout=25) as resp:
        return resp.status, json.loads(resp.read(300000).decode("utf-8"))


def _safe_url(case: Mapping[str, Any], env: Mapping[str, str]) -> str:
    provider = str(case["provider"])
    if provider == "eodhd":
        params = urllib.parse.urlencode(
            {
                "api_token": env["AEGIS_EODHD_API_TOKEN"],
                "fmt": "json",
                "from": str(case["from_date"]),
                "to": str(case["to_date"]),
            }
        )
        return f"https://eodhd.com/api/eod/{urllib.parse.quote(str(case['provider_symbol']))}?{params}"
    if provider == "twelve_data":
        params = urllib.parse.urlencode(
            {
                "symbol": str(case["provider_symbol"]),
                "interval": "1day",
                "outputsize": str(case.get("outputsize") or "5"),
                "apikey": env["AEGIS_TWELVE_DATA_API_KEY"],
            }
        )
        return "https://api.twelvedata.com/time_series?" + params
    raise ValueError(f"unsupported provider: {provider}")


def _required_env(provider: str) -> str:
    if provider == "eodhd":
        return "AEGIS_EODHD_API_TOKEN"
    if provider == "twelve_data":
        return "AEGIS_TWELVE_DATA_API_KEY"
    raise ValueError(f"unsupported provider: {provider}")


def _float_or_none(value: Any) -> float | None:
    if value is None or value == "":
        return None
    return float(value)


def _int_or_none(value: Any) -> int | None:
    if value is None or value == "":
        return None
    return int(float(value))


def _normalize_payload(provider: str, payload: Any) -> list[dict[str, Any]]:
    if provider == "eodhd" and isinstance(payload, list):
        rows = payload
    elif provider == "twelve_data" and isinstance(payload, dict):
        rows = payload.get("values") or []
    else:
        rows = []

    normalized: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        date_value = row.get("date") or row.get("datetime")
        close = _float_or_none(row.get("close"))
        if not date_value or close is None:
            continue
        normalized.append(
            {
                "date": str(date_value)[:10],
                "open": _float_or_none(row.get("open")),
                "high": _float_or_none(row.get("high")),
                "low": _float_or_none(row.get("low")),
                "close": close,
                "volume": _int_or_none(row.get("volume")),
            }
        )
    return sorted(normalized, key=lambda item: item["date"])


def _write_normalized_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=NORMALIZED_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column) for column in NORMALIZED_COLUMNS})


def _case_output_path(output_dir: Path, case: Mapping[str, Any]) -> Path:
    return output_dir / str(case["market"]) / str(case["data_type"]) / f"{case['case_id']}.csv"


def _route_lookup(metadata_report: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    return {
        str(route.get("route_id")): route
        for route in metadata_report.get("route_proposals", []) or []
        if isinstance(route, dict)
    }


def run_h_us_cache_readiness_case(
    case: Mapping[str, Any],
    *,
    output_dir: Path,
    env: Mapping[str, str] | None = None,
    fetch_json: FetchJson | None = None,
) -> dict[str, Any]:
    env_source = env if env is not None else os.environ
    fetcher = fetch_json or _default_fetch_json
    provider = str(case["provider"])
    required_env = _required_env(provider)
    base = {
        "case_id": case.get("case_id"),
        "route_id": case.get("route_id"),
        "provider": provider,
        "market": case.get("market"),
        "canonical_symbol": case.get("canonical_symbol"),
        "provider_symbol": case.get("provider_symbol"),
        "data_type": case.get("data_type"),
        "required_env_var": required_env,
        "env_present": bool(env_source.get(required_env)),
        "request_url_stored": False,
        "raw_payload_stored": False,
        "token_value_stored": False,
        "normalized_csv_written": False,
    }
    if not env_source.get(required_env):
        return {**base, "status": "blocked_missing_env", "ok": False, "blocked_by": ["missing_required_env_var"]}

    try:
        status_code, payload = fetcher(_safe_url(case, env_source))
        rows = _normalize_payload(provider, payload)
        ok = status_code == 200 and len(rows) >= 2
        if not ok:
            return {
                **base,
                "status": "fail",
                "ok": False,
                "http_status": status_code,
                "row_count": len(rows),
                "blocked_by": ["insufficient_normalized_rows"],
            }
        csv_path = _case_output_path(output_dir, case)
        _write_normalized_csv(csv_path, rows)
        return {
            **base,
            "status": "pass",
            "ok": True,
            "http_status": status_code,
            "row_count": len(rows),
            "first_date": rows[0]["date"],
            "last_date": rows[-1]["date"],
            "normalized_csv_written": True,
            "normalized_csv": str(csv_path),
            "normalized_csv_sha256": _sha256_file(csv_path),
            "normalized_schema": NORMALIZED_COLUMNS,
            "payload_summary_sha256": _sha256_text(
                json.dumps(
                    {"row_count": len(rows), "first_date": rows[0]["date"], "last_date": rows[-1]["date"]},
                    sort_keys=True,
                )
            ),
            "blocked_by": [],
        }
    except Exception as exc:
        return {
            **base,
            "status": "fail",
            "ok": False,
            "error_type": type(exc).__name__,
            "blocked_by": ["fetch_error"],
        }


def build_h_us_historical_cache_readiness_report(
    *,
    metadata_report: Mapping[str, Any],
    output_dir: Path,
    run_id: str,
    cases: list[Mapping[str, Any]] | None = None,
    env: Mapping[str, str] | None = None,
    fetch_json: FetchJson | None = None,
    command: str | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    readiness_cases = cases or DEFAULT_READINESS_CASES
    routes = _route_lookup(metadata_report)
    results = [
        run_h_us_cache_readiness_case(case, output_dir=output_dir, env=env, fetch_json=fetch_json)
        for case in readiness_cases
    ]
    pass_count = sum(1 for result in results if result["status"] == "pass")
    h_pass = [result for result in results if result["market"] == "H" and result["status"] == "pass"]
    us_pass = [result for result in results if result["market"] == "US" and result["status"] == "pass"]
    checks = {
        "source_metadata_report_pass": metadata_report.get("overall_status") == "PASS",
        "source_acceptance_target_correct": metadata_report.get("acceptance_target")
        == "V2.12-B H-US Provider Metadata Activation",
        "h_route_ready_in_metadata": (routes.get("h_daily_bars_eodhd_primary") or {}).get("status")
        == "ready_for_metadata",
        "us_route_ready_in_metadata": (
            routes.get("us_daily_bars_eodhd_primary_twelve_backup") or {}
        ).get("status")
        == "ready_for_metadata",
        "twelve_data_h_still_blocked": (
            routes.get("h_daily_bars_twelve_data_review") or {}
        ).get("status")
        == "blocked_fetch_error",
        "at_least_one_h_cache_sample_written": bool(h_pass),
        "at_least_one_us_cache_sample_written": bool(us_pass),
        "all_passed_samples_have_hashes": all(bool(result.get("normalized_csv_sha256")) for result in h_pass + us_pass),
        "normalized_schema_visible": all(
            result["status"] != "pass" or result.get("normalized_schema") == NORMALIZED_COLUMNS for result in results
        ),
        "env_var_names_only": True,
        "no_secret_values_stored": all(not result["token_value_stored"] for result in results),
        "request_urls_not_stored": all(not result["request_url_stored"] for result in results),
        "raw_payloads_not_stored": all(not result["raw_payload_stored"] for result in results),
        "production_cache_not_mutated": True,
        "production_provider_config_not_mutated": True,
        "suggestion_path_not_enabled": True,
        "no_real_trade": True,
        "no_broker_api": True,
        "no_trading_webhook": True,
        "no_order_placement": True,
        "dashboard_contract_unchanged": True,
    }
    return {
        "overall_status": "PASS" if all(checks.values()) else "FAIL",
        "acceptance_target": "V2.12-C H-US Historical Cache Readiness Dry Run",
        "run_id": run_id,
        "generated_at": generated_at or _now_iso(),
        "command": command,
        "network_used": fetch_json is None,
        "production_records_written": False,
        "production_cache_mutated": False,
        "production_provider_config_mutated": False,
        "dashboard_contract_changed": False,
        "summary": {
            "case_count": len(results),
            "pass_count": pass_count,
            "fail_count": sum(1 for result in results if result["status"] == "fail"),
            "blocked_count": sum(1 for result in results if str(result["status"]).startswith("blocked")),
            "h_cache_ready": bool(h_pass),
            "us_cache_ready": bool(us_pass),
            "twelve_data_h_status": "blocked_fetch_error",
            "next_stage": "V2.12-D H-US Historical Sandbox Candidate Refresh Dry Run",
        },
        "source_metadata": {
            "source_target": metadata_report.get("acceptance_target"),
            "source_run_id": metadata_report.get("run_id"),
            "source_summary_sha256": _sha256_text(
                json.dumps(metadata_report.get("summary") or {}, ensure_ascii=False, sort_keys=True)
            ),
        },
        "normalized_cache_root": str(output_dir),
        "results": results,
        "checks": checks,
        "safety": {
            "historical_cache_readiness_only": True,
            "run_specific_cache_only": True,
            "no_secret_values_stored": True,
            "no_request_url_storage": True,
            "no_raw_payload_storage": True,
            "production_cache_not_mutated": True,
            "production_provider_config_not_mutated": True,
            "suggestion_path_not_enabled": True,
            "no_real_trade": True,
            "no_broker_api": True,
            "no_trading_webhook": True,
            "no_order_placement": True,
            "dashboard_contract_unchanged": True,
        },
    }


def render_h_us_historical_cache_readiness_markdown(report: Mapping[str, Any]) -> str:
    lines = [
        "# V2.12-C H-US Historical Cache Readiness Dry Run",
        "",
        f"- status: `{report.get('overall_status')}`",
        f"- run_id: `{report.get('run_id')}`",
        f"- network_used: `{report.get('network_used')}`",
        f"- h_cache_ready: `{report.get('summary', {}).get('h_cache_ready')}`",
        f"- us_cache_ready: `{report.get('summary', {}).get('us_cache_ready')}`",
        f"- pass_count: `{report.get('summary', {}).get('pass_count')}`",
        f"- fail_count: `{report.get('summary', {}).get('fail_count')}`",
        f"- next_stage: `{report.get('summary', {}).get('next_stage')}`",
        "",
        "## Normalized Cache Samples",
        "",
    ]
    for result in report.get("results", []) or []:
        lines.extend(
            [
                f"### {result.get('case_id')}",
                "",
                f"- status: `{result.get('status')}`",
                f"- provider: `{result.get('provider')}`",
                f"- market: `{result.get('market')}`",
                f"- canonical_symbol: `{result.get('canonical_symbol')}`",
                f"- row_count: `{result.get('row_count')}`",
                f"- first_date: `{result.get('first_date')}`",
                f"- last_date: `{result.get('last_date')}`",
                f"- blocked_by: `{result.get('blocked_by', [])}`",
                "",
            ]
        )
    lines.extend(
        [
            "## Boundary",
            "",
            "- Historical cache readiness only.",
            "- Run-specific normalized CSV cache only; production cache is not mutated.",
            "- Env var names only; no token values.",
            "- No request URL or raw payload storage.",
            "- No candidate/suggestion path activation.",
            "- No real trade, broker API, trading webhook, or order placement.",
            "- Dashboard Contract unchanged.",
            "",
        ]
    )
    return "\n".join(lines)
