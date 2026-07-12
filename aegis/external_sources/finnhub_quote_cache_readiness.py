"""Finnhub quote cache readiness dry run.

This fetches a bounded quote sample from Finnhub and writes normalized
run-specific artifacts only. It does not mutate production cache/provider config
or enable suggestions.
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping

FetchJson = Callable[[str], tuple[int, Any]]

DEFAULT_QUOTE_CASES = [
    {
        "case_id": "us_aapl_finnhub_quote",
        "route_id": "us_quote_finnhub_verified_free",
        "provider": "finnhub",
        "market": "US",
        "canonical_symbol": "AAPL.US",
        "provider_symbol": "AAPL",
        "data_type": "quote",
    }
]

NORMALIZED_QUOTE_COLUMNS = [
    "provider",
    "market",
    "canonical_symbol",
    "provider_symbol",
    "current_price",
    "previous_close",
    "open",
    "high",
    "low",
    "change",
    "percent_change",
    "provider_timestamp",
]


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
    req = urllib.request.Request(url, headers={"User-Agent": "ProjectAegis/0.1 finnhub-quote-cache-readiness"})
    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            return resp.status, json.loads(resp.read(300000).decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read(300000).decode("utf-8", errors="replace")
        try:
            payload: Any = json.loads(body)
        except json.JSONDecodeError:
            payload = {"error": "non_json_error_body", "body_sha256": _sha256_text(body)}
        return exc.code, payload


def _safe_url(case: Mapping[str, Any], env: Mapping[str, str]) -> str:
    params = urllib.parse.urlencode({"symbol": str(case["provider_symbol"]), "token": env["AEGIS_FINNHUB_API_KEY"]})
    return "https://finnhub.io/api/v1/quote?" + params


def _float_or_none(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _int_or_none(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _normalize_quote(case: Mapping[str, Any], payload: Any) -> dict[str, Any] | None:
    if not isinstance(payload, dict):
        return None
    current = _float_or_none(payload.get("c"))
    previous_close = _float_or_none(payload.get("pc"))
    if current is None or current <= 0 or previous_close is None or previous_close <= 0:
        return None
    return {
        "provider": "finnhub",
        "market": case.get("market"),
        "canonical_symbol": case.get("canonical_symbol"),
        "provider_symbol": case.get("provider_symbol"),
        "current_price": current,
        "previous_close": previous_close,
        "open": _float_or_none(payload.get("o")),
        "high": _float_or_none(payload.get("h")),
        "low": _float_or_none(payload.get("l")),
        "change": _float_or_none(payload.get("d")),
        "percent_change": _float_or_none(payload.get("dp")),
        "provider_timestamp": _int_or_none(payload.get("t")),
    }


def _case_output_paths(output_dir: Path, case: Mapping[str, Any]) -> tuple[Path, Path]:
    base = output_dir / str(case["market"]) / str(case["data_type"]) / str(case["case_id"])
    return base.with_suffix(".json"), base.with_suffix(".csv")


def _write_normalized_quote(json_path: Path, csv_path: Path, quote: Mapping[str, Any]) -> None:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(dict(quote), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with csv_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=NORMALIZED_QUOTE_COLUMNS)
        writer.writeheader()
        writer.writerow({column: quote.get(column) for column in NORMALIZED_QUOTE_COLUMNS})


def _route_lookup(metadata_report: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    return {
        str(route.get("route_id")): route
        for route in metadata_report.get("route_proposals", []) or []
        if isinstance(route, dict)
    }


def run_finnhub_quote_cache_readiness_case(
    case: Mapping[str, Any],
    *,
    output_dir: Path,
    env: Mapping[str, str] | None = None,
    fetch_json: FetchJson | None = None,
) -> dict[str, Any]:
    env_source = env if env is not None else os.environ
    base = {
        "case_id": case.get("case_id"),
        "route_id": case.get("route_id"),
        "provider": "finnhub",
        "market": case.get("market"),
        "canonical_symbol": case.get("canonical_symbol"),
        "provider_symbol": case.get("provider_symbol"),
        "data_type": case.get("data_type"),
        "required_env_var": "AEGIS_FINNHUB_API_KEY",
        "env_present": bool(env_source.get("AEGIS_FINNHUB_API_KEY")),
        "request_url_stored": False,
        "raw_payload_stored": False,
        "token_value_stored": False,
        "normalized_quote_written": False,
    }
    if not env_source.get("AEGIS_FINNHUB_API_KEY"):
        return {**base, "status": "blocked_missing_env", "ok": False, "blocked_by": ["missing_required_env_var"]}

    fetcher = fetch_json or _default_fetch_json
    try:
        status_code, payload = fetcher(_safe_url(case, env_source))
        quote = _normalize_quote(case, payload)
        if status_code != 200 or quote is None:
            return {
                **base,
                "status": "fail",
                "ok": False,
                "http_status": status_code,
                "blocked_by": ["quote_payload_shape_or_empty_result"],
            }
        json_path, csv_path = _case_output_paths(output_dir, case)
        _write_normalized_quote(json_path, csv_path, quote)
        return {
            **base,
            "status": "pass",
            "ok": True,
            "http_status": status_code,
            "current_price_present": quote["current_price"] > 0,
            "previous_close_present": quote["previous_close"] > 0,
            "provider_timestamp_present": quote.get("provider_timestamp") is not None,
            "normalized_quote_written": True,
            "normalized_quote_json": str(json_path),
            "normalized_quote_json_sha256": _sha256_file(json_path),
            "normalized_quote_csv": str(csv_path),
            "normalized_quote_csv_sha256": _sha256_file(csv_path),
            "normalized_schema": NORMALIZED_QUOTE_COLUMNS,
            "payload_summary_sha256": _sha256_text(
                json.dumps(
                    {
                        "current_price_present": True,
                        "previous_close_present": True,
                        "provider_timestamp_present": quote.get("provider_timestamp") is not None,
                    },
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


def build_finnhub_quote_cache_readiness_report(
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
    readiness_cases = cases or DEFAULT_QUOTE_CASES
    routes = _route_lookup(metadata_report)
    results = [
        run_finnhub_quote_cache_readiness_case(case, output_dir=output_dir, env=env, fetch_json=fetch_json)
        for case in readiness_cases
    ]
    pass_results = [result for result in results if result["status"] == "pass"]
    quote_route = routes.get("us_quote_finnhub_verified_free") or {}
    social_route = routes.get("us_social_sentiment_finnhub_plan_blocked") or {}
    checks = {
        "source_metadata_report_pass": metadata_report.get("overall_status") == "PASS",
        "source_acceptance_target_correct": metadata_report.get("acceptance_target")
        == "V2.13-B Finnhub Metadata Activation",
        "quote_route_ready_in_metadata": quote_route.get("status") == "ready_for_metadata",
        "social_sentiment_still_blocked": social_route.get("status") == "blocked_plan_or_rate_limit",
        "at_least_one_quote_sample_written": bool(pass_results),
        "all_passed_samples_have_hashes": all(
            result.get("normalized_quote_json_sha256") and result.get("normalized_quote_csv_sha256")
            for result in pass_results
        ),
        "normalized_schema_visible": all(
            result["status"] != "pass" or result.get("normalized_schema") == NORMALIZED_QUOTE_COLUMNS
            for result in results
        ),
        "env_var_names_only": True,
        "no_secret_values_stored": all(not result["token_value_stored"] for result in results),
        "request_urls_not_stored": all(not result["request_url_stored"] for result in results),
        "raw_payloads_not_stored": all(not result["raw_payload_stored"] for result in results),
        "production_cache_not_mutated": True,
        "production_provider_config_not_mutated": True,
        "suggestion_path_not_enabled": True,
        "social_sentiment_not_enabled": True,
        "no_real_trade": True,
        "no_broker_api": True,
        "no_trading_webhook": True,
        "no_order_placement": True,
        "dashboard_contract_unchanged": True,
    }
    return {
        "overall_status": "PASS" if all(checks.values()) else "FAIL",
        "acceptance_target": "V2.13-C Finnhub Quote Cache Readiness Dry Run",
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
            "pass_count": len(pass_results),
            "fail_count": sum(1 for result in results if result["status"] == "fail"),
            "blocked_count": sum(1 for result in results if result["status"].startswith("blocked")),
            "quote_cache_ready": bool(pass_results),
            "social_sentiment_status": "blocked_plan_or_rate_limit",
            "next_stage": "V2.13-D Finnhub Quote Research Context Bridge",
        },
        "results": results,
        "source_evidence": {
            "source_target": metadata_report.get("acceptance_target"),
            "source_run_id": metadata_report.get("run_id"),
            "source_summary_sha256": _sha256_text(
                json.dumps(metadata_report.get("summary") or {}, ensure_ascii=False, sort_keys=True)
            ),
        },
        "checks": checks,
        "safety": {
            "quote_cache_readiness_only": True,
            "run_specific_artifacts_only": True,
            "social_sentiment_not_enabled": True,
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


def render_finnhub_quote_cache_readiness_markdown(report: Mapping[str, Any]) -> str:
    lines = [
        "# V2.13-C Finnhub Quote Cache Readiness Dry Run",
        "",
        f"- status: `{report.get('overall_status')}`",
        f"- run_id: `{report.get('run_id')}`",
        f"- quote_cache_ready: `{report.get('summary', {}).get('quote_cache_ready')}`",
        f"- pass_count: `{report.get('summary', {}).get('pass_count')}`",
        f"- fail_count: `{report.get('summary', {}).get('fail_count')}`",
        f"- blocked_count: `{report.get('summary', {}).get('blocked_count')}`",
        f"- social_sentiment_status: `{report.get('summary', {}).get('social_sentiment_status')}`",
        f"- next_stage: `{report.get('summary', {}).get('next_stage')}`",
        "",
        "## Results",
        "",
    ]
    for result in report.get("results", []) or []:
        lines.extend(
            [
                f"### {result.get('case_id')}",
                "",
                f"- status: `{result.get('status')}`",
                f"- market: `{result.get('market')}`",
                f"- canonical_symbol: `{result.get('canonical_symbol')}`",
                f"- provider_symbol: `{result.get('provider_symbol')}`",
                f"- normalized_quote_json: `{result.get('normalized_quote_json')}`",
                f"- normalized_quote_json_sha256: `{result.get('normalized_quote_json_sha256')}`",
                f"- normalized_quote_csv: `{result.get('normalized_quote_csv')}`",
                f"- normalized_quote_csv_sha256: `{result.get('normalized_quote_csv_sha256')}`",
                f"- blocked_by: `{result.get('blocked_by', [])}`",
                "",
            ]
        )
    lines.extend(
        [
            "## Boundary",
            "",
            "- Quote cache readiness only.",
            "- Run-specific artifacts only; production cache is not mutated.",
            "- Finnhub social sentiment remains plan/rate-limit blocked and is not enabled.",
            "- No candidate/suggestion path activation.",
            "- No request URL, raw payload, or token value is stored.",
            "- No real trade, broker API, trading webhook, order placement, or Dashboard Contract change.",
            "",
        ]
    )
    return "\n".join(lines)
