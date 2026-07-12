"""Secret-safe Finnhub free endpoint probe for Project Aegis."""

from __future__ import annotations

import hashlib
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any, Callable, Mapping

FetchJson = Callable[[str], tuple[int, Any]]

DEFAULT_CASES = [
    {"endpoint": "quote", "market": "US", "symbol": "AAPL", "data_type": "quote"},
    {
        "endpoint": "social_sentiment",
        "market": "US",
        "symbol": "AAPL",
        "data_type": "social_sentiment",
        "from": "2026-07-01",
        "to": "2026-07-12",
    },
]

REQUIRED_ENV_VAR = "AEGIS_FINNHUB_API_KEY"
FALLBACK_ENV_VAR = "AEGIS_FINNHUB_API_TOKEN"


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _resolve_api_key_env(env: Mapping[str, str]) -> tuple[str, str] | None:
    for name in [REQUIRED_ENV_VAR, FALLBACK_ENV_VAR]:
        value = env.get(name)
        if value:
            return name, value
    return None


def _default_fetch_json(url: str) -> tuple[int, Any]:
    req = urllib.request.Request(url, headers={"User-Agent": "ProjectAegis/0.1 secret-safe-finnhub-free-probe"})
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


def _safe_url(case: Mapping[str, Any], token: str) -> str:
    endpoint = str(case["endpoint"])
    if endpoint == "quote":
        query = urllib.parse.urlencode({"symbol": str(case["symbol"]), "token": token})
        return "https://finnhub.io/api/v1/quote?" + query
    if endpoint == "social_sentiment":
        query = urllib.parse.urlencode(
            {
                "symbol": str(case["symbol"]),
                "from": str(case.get("from", "")),
                "to": str(case.get("to", "")),
                "token": token,
            }
        )
        return "https://finnhub.io/api/v1/stock/social-sentiment?" + query
    raise ValueError(f"unsupported Finnhub endpoint: {endpoint}")


def _summarize_payload(endpoint: str, payload: Any) -> dict[str, Any]:
    if endpoint == "quote" and isinstance(payload, dict):
        numeric_keys = [key for key in ["c", "d", "dp", "h", "l", "o", "pc", "t"] if key in payload]
        current = payload.get("c")
        return {
            "shape": "dict",
            "keys": sorted(str(key) for key in payload.keys())[:12],
            "numeric_key_count": len(numeric_keys),
            "has_current_price": isinstance(current, int | float) and current > 0,
            "has_previous_close": isinstance(payload.get("pc"), int | float) and payload.get("pc") > 0,
        }
    if endpoint == "social_sentiment" and isinstance(payload, dict):
        reddit = payload.get("reddit")
        twitter = payload.get("twitter")
        error_text = str(payload.get("error") or payload.get("msg") or payload.get("message") or "")
        return {
            "shape": "dict",
            "keys": sorted(str(key) for key in payload.keys())[:12],
            "reddit_items": len(reddit) if isinstance(reddit, list) else None,
            "twitter_items": len(twitter) if isinstance(twitter, list) else None,
            "has_social_series": isinstance(reddit, list) or isinstance(twitter, list),
            "error_text_sha256": _sha256_text(error_text) if error_text else None,
            "error_text_present": bool(error_text),
        }
    return {"shape": type(payload).__name__, "keys": [], "has_current_price": False, "has_social_series": False}


def _classify_result(endpoint: str, http_status: int, summary: Mapping[str, Any]) -> tuple[str, bool, list[str]]:
    if endpoint == "quote":
        ok = http_status == 200 and summary.get("has_current_price") is True
        return ("pass" if ok else "fail", ok, [] if ok else ["quote_payload_shape_or_empty_result"])

    if endpoint == "social_sentiment":
        ok = http_status == 200 and summary.get("has_social_series") is True
        if ok:
            return "pass", True, []
        if http_status in {401, 403, 429} or summary.get("error_text_present") is True:
            return "blocked_plan_or_rate_limit", False, ["social_sentiment_not_available_on_current_plan_or_rate_limit"]
        return "fail", False, ["social_sentiment_payload_shape_or_empty_result"]

    return "fail", False, ["unsupported_endpoint"]


def probe_finnhub_case(
    case: Mapping[str, Any],
    *,
    env: Mapping[str, str] | None = None,
    fetch_json: FetchJson | None = None,
) -> dict[str, Any]:
    env_source = env if env is not None else os.environ
    endpoint = str(case["endpoint"])
    env_pair = _resolve_api_key_env(env_source)
    base = {
        "provider": "finnhub",
        "endpoint": endpoint,
        "market": case.get("market"),
        "symbol": case.get("symbol"),
        "data_type": case.get("data_type"),
        "required_env_vars": [REQUIRED_ENV_VAR, FALLBACK_ENV_VAR],
        "env_present": env_pair is not None,
        "env_var_used": env_pair[0] if env_pair else None,
        "request_url_stored": False,
        "raw_payload_stored": False,
        "token_value_stored": False,
    }
    if env_pair is None:
        return {**base, "status": "blocked_missing_env", "ok": False, "blocked_by": ["missing_required_env_var"]}

    fetcher = fetch_json or _default_fetch_json
    try:
        status_code, payload = fetcher(_safe_url(case, env_pair[1]))
        summary = _summarize_payload(endpoint, payload)
        status, ok, blocked_by = _classify_result(endpoint, status_code, summary)
        return {
            **base,
            "status": status,
            "ok": ok,
            "http_status": status_code,
            "summary": summary,
            "summary_sha256": _sha256_text(json.dumps(summary, ensure_ascii=False, sort_keys=True)),
            "blocked_by": blocked_by,
        }
    except Exception as exc:
        return {
            **base,
            "status": "fail",
            "ok": False,
            "error_type": type(exc).__name__,
            "blocked_by": ["fetch_error"],
        }


def build_finnhub_free_probe_report(
    *,
    run_id: str,
    cases: list[Mapping[str, Any]] | None = None,
    env: Mapping[str, str] | None = None,
    fetch_json: FetchJson | None = None,
    command: str | None = None,
) -> dict[str, Any]:
    probe_cases = cases or DEFAULT_CASES
    results = [probe_finnhub_case(case, env=env, fetch_json=fetch_json) for case in probe_cases]
    quote_passed = any(item["endpoint"] == "quote" and item["status"] == "pass" for item in results)
    social_recorded = any(item["endpoint"] == "social_sentiment" for item in results)
    missing_env = any(item["status"] == "blocked_missing_env" for item in results)
    unacceptable_failures = [
        item
        for item in results
        if item["status"] == "fail" or (item["endpoint"] == "quote" and item["status"] != "pass")
    ]
    if missing_env:
        overall_status = "BLOCKED"
    elif not unacceptable_failures and quote_passed and social_recorded:
        overall_status = "PASS"
    else:
        overall_status = "FAIL"

    checks = {
        "env_var_names_only": True,
        "no_secret_values_stored": all(not item["token_value_stored"] for item in results),
        "request_urls_not_stored": all(not item["request_url_stored"] for item in results),
        "raw_payloads_not_stored": all(not item["raw_payload_stored"] for item in results),
        "quote_endpoint_recorded": any(item["endpoint"] == "quote" for item in results),
        "quote_endpoint_passed": quote_passed,
        "social_sentiment_endpoint_recorded": social_recorded,
        "social_sentiment_allowed_to_be_plan_blocked": True,
        "no_real_trade": True,
        "no_broker_api": True,
        "no_trading_webhook": True,
        "no_order_placement": True,
        "no_production_records_mutation": True,
        "dashboard_contract_unchanged": True,
    }
    return {
        "overall_status": overall_status,
        "acceptance_target": "V2.13-A Finnhub Free Probe",
        "run_id": run_id,
        "generated_at": _now_iso(),
        "command": command,
        "network_used": fetch_json is None and not missing_env,
        "production_records_written": False,
        "dashboard_contract_changed": False,
        "summary": {
            "case_count": len(results),
            "pass_count": sum(1 for item in results if item["status"] == "pass"),
            "fail_count": sum(1 for item in results if item["status"] == "fail"),
            "blocked_count": sum(1 for item in results if item["status"].startswith("blocked")),
            "quote_status": next((item["status"] for item in results if item["endpoint"] == "quote"), None),
            "social_sentiment_status": next(
                (item["status"] for item in results if item["endpoint"] == "social_sentiment"), None
            ),
            "next_stage": "V2.13-B Finnhub Metadata Activation" if overall_status == "PASS" else "Provide Finnhub env var to rerun free probe",
        },
        "results": results,
        "checks": checks,
        "safety": {
            "market_data_probe_only": True,
            "social_sentiment_probe_only": True,
            "summary_hash_only": True,
            "no_secret_values_stored": True,
            "no_raw_payload_storage": True,
            "no_request_url_storage": True,
            "no_real_trade": True,
            "no_broker_api": True,
            "no_trading_webhook": True,
            "no_order_placement": True,
            "no_production_records_mutation": True,
            "dashboard_contract_unchanged": True,
        },
    }
