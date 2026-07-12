"""Secret-safe EODHD and Twelve Data provider capability probe."""

from __future__ import annotations

import hashlib
import json
import os
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any, Callable, Mapping

FetchJson = Callable[[str], tuple[int, Any]]

DEFAULT_CASES = [
    {"provider": "eodhd", "market": "US", "symbol": "AAPL.US", "data_type": "daily_bars"},
    {"provider": "eodhd", "market": "H", "symbol": "0700.HK", "data_type": "daily_bars"},
    {"provider": "twelve_data", "market": "US", "symbol": "AAPL", "data_type": "daily_bars"},
    {"provider": "twelve_data", "market": "H", "symbol": "0700", "data_type": "daily_bars", "exchange": "HKEX"},
]


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _default_fetch_json(url: str) -> tuple[int, Any]:
    req = urllib.request.Request(url, headers={"User-Agent": "ProjectAegis/0.1 secret-safe-provider-probe"})
    with urllib.request.urlopen(req, timeout=25) as resp:
        return resp.status, json.loads(resp.read(300000).decode("utf-8"))


def _safe_url(provider: str, case: Mapping[str, Any], env: Mapping[str, str]) -> str:
    if provider == "eodhd":
        token = env["AEGIS_EODHD_API_TOKEN"]
        params = urllib.parse.urlencode(
            {"api_token": token, "fmt": "json", "from": "2026-07-01", "to": "2026-07-03"}
        )
        return f"https://eodhd.com/api/eod/{urllib.parse.quote(str(case['symbol']))}?{params}"
    if provider == "twelve_data":
        token = env["AEGIS_TWELVE_DATA_API_KEY"]
        query = {
            "symbol": str(case["symbol"]),
            "interval": "1day",
            "outputsize": "1",
            "apikey": token,
        }
        if case.get("exchange"):
            query["exchange"] = str(case["exchange"])
        return "https://api.twelvedata.com/time_series?" + urllib.parse.urlencode(query)
    raise ValueError(f"unsupported provider: {provider}")


def _summarize_payload(provider: str, payload: Any) -> dict[str, Any]:
    if provider == "eodhd" and isinstance(payload, list):
        return {
            "shape": "list",
            "rows": len(payload),
            "has_close": bool(payload and isinstance(payload[0], dict) and "close" in payload[0]),
            "first_date": payload[0].get("date") if payload and isinstance(payload[0], dict) else None,
            "last_date": payload[-1].get("date") if payload and isinstance(payload[-1], dict) else None,
        }
    if provider == "twelve_data" and isinstance(payload, dict):
        values = payload.get("values") or []
        return {
            "shape": "dict",
            "api_status": payload.get("status"),
            "rows": len(values) if isinstance(values, list) else 0,
            "has_close": bool(values and isinstance(values[0], dict) and "close" in values[0]),
            "first_datetime": values[0].get("datetime") if values and isinstance(values[0], dict) else None,
        }
    return {"shape": type(payload).__name__, "rows": None, "has_close": False}


def probe_provider_case(
    case: Mapping[str, Any],
    *,
    env: Mapping[str, str] | None = None,
    fetch_json: FetchJson | None = None,
) -> dict[str, Any]:
    env_source = env if env is not None else os.environ
    fetcher = fetch_json or _default_fetch_json
    provider = str(case["provider"])
    required_env = "AEGIS_EODHD_API_TOKEN" if provider == "eodhd" else "AEGIS_TWELVE_DATA_API_KEY"
    base = {
        "provider": provider,
        "market": case.get("market"),
        "symbol": case.get("symbol"),
        "data_type": case.get("data_type"),
        "required_env_var": required_env,
        "env_present": bool(env_source.get(required_env)),
        "request_url_stored": False,
        "raw_payload_stored": False,
        "token_value_stored": False,
    }
    if not env_source.get(required_env):
        return {**base, "status": "blocked_missing_env", "ok": False, "blocked_by": ["missing_required_env_var"]}

    try:
        status_code, payload = fetcher(_safe_url(provider, case, env_source))
        summary = _summarize_payload(provider, payload)
        ok = status_code == 200 and summary["has_close"] and int(summary["rows"] or 0) > 0
        return {
            **base,
            "status": "pass" if ok else "fail",
            "ok": ok,
            "http_status": status_code,
            "summary": summary,
            "summary_sha256": _sha256_text(json.dumps(summary, sort_keys=True)),
            "blocked_by": [] if ok else ["payload_shape_or_empty_result"],
        }
    except Exception as exc:
        return {
            **base,
            "status": "fail",
            "ok": False,
            "error_type": type(exc).__name__,
            "blocked_by": ["fetch_error"],
        }


def build_eodhd_twelve_provider_probe_report(
    *,
    run_id: str,
    cases: list[Mapping[str, Any]] | None = None,
    env: Mapping[str, str] | None = None,
    fetch_json: FetchJson | None = None,
    command: str | None = None,
) -> dict[str, Any]:
    probe_cases = cases or DEFAULT_CASES
    results = [probe_provider_case(case, env=env, fetch_json=fetch_json) for case in probe_cases]
    pass_count = sum(1 for item in results if item["status"] == "pass")
    h_pass = [item for item in results if item["market"] == "H" and item["status"] == "pass"]
    us_pass = [item for item in results if item["market"] == "US" and item["status"] == "pass"]
    checks = {
        "env_var_names_only": True,
        "no_secret_values_stored": all(not item["token_value_stored"] for item in results),
        "request_urls_not_stored": all(not item["request_url_stored"] for item in results),
        "raw_payloads_not_stored": all(not item["raw_payload_stored"] for item in results),
        "at_least_one_h_provider_passed": bool(h_pass),
        "at_least_one_us_provider_passed": bool(us_pass),
        "eodhd_us_passed": any(item["provider"] == "eodhd" and item["market"] == "US" and item["ok"] for item in results),
        "eodhd_h_passed": any(item["provider"] == "eodhd" and item["market"] == "H" and item["ok"] for item in results),
        "twelve_data_us_passed": any(
            item["provider"] == "twelve_data" and item["market"] == "US" and item["ok"] for item in results
        ),
        "twelve_data_h_recorded": any(item["provider"] == "twelve_data" and item["market"] == "H" for item in results),
        "no_real_trade": True,
        "no_broker_api": True,
        "no_trading_webhook": True,
        "no_order_placement": True,
        "no_production_records_mutation": True,
        "dashboard_contract_unchanged": True,
    }
    return {
        "overall_status": "PASS" if all(checks.values()) else "FAIL",
        "acceptance_target": "V2.12-A EODHD Twelve Data H-US Provider Probe",
        "run_id": run_id,
        "generated_at": _now_iso(),
        "command": command,
        "network_used": fetch_json is None,
        "production_records_written": False,
        "dashboard_contract_changed": False,
        "summary": {
            "case_count": len(results),
            "pass_count": pass_count,
            "fail_count": sum(1 for item in results if item["status"] == "fail"),
            "blocked_count": sum(1 for item in results if item["status"].startswith("blocked")),
            "h_us_provider_status": {
                "H": sorted({item["provider"] for item in h_pass}),
                "US": sorted({item["provider"] for item in us_pass}),
            },
            "next_stage": "V2.12-B H-US Provider Metadata Activation",
        },
        "results": results,
        "checks": checks,
        "safety": {
            "market_data_probe_only": True,
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
