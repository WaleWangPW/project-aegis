"""Approved external API dry-run fetcher."""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from typing import Callable, Mapping
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from aegis.external_sources.api_connector import evaluate_api_connector
from aegis.models.external_api import ExternalAPIConnectorSpec, ExternalAPIFetchItem


class APIFetchError(RuntimeError):
    pass


FetchFn = Callable[[str, Mapping[str, str], int], tuple[int, str, bytes]]


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _summarize_payload(payload: bytes, content_type: str, max_chars: int = 420) -> str:
    text = payload.decode("utf-8", errors="replace")
    if "json" in content_type:
        try:
            data = json.loads(text)
            if isinstance(data, dict):
                keys = ", ".join(sorted(list(data.keys()))[:12])
                details: list[str] = []
                items = data.get("items")
                if isinstance(items, list) and items and isinstance(items[0], dict):
                    first = items[0]
                    if first.get("market"):
                        details.append(f"market={first['market']}")
                    if first.get("strategy_family"):
                        details.append(f"strategy_family={first['strategy_family']}")
                    if first.get("symbol"):
                        details.append(f"symbol={first['symbol']}")
                suffix = " " + " ".join(details) + "." if details else ""
                return f"JSON document with keys: {keys}.{suffix}"
            if isinstance(data, list):
                return f"JSON array with {len(data)} items."
        except json.JSONDecodeError:
            pass
    return " ".join(text.split())[:max_chars]


def _default_fetch(url: str, headers: Mapping[str, str], timeout: int) -> tuple[int, str, bytes]:
    req = Request(url, headers=dict(headers))
    with urlopen(req, timeout=timeout) as response:
        return response.status, response.headers.get("content-type", ""), response.read()


def _build_url(base_url: str, endpoint_path: str, query: Mapping[str, str] | None) -> str:
    base = base_url.rstrip("/")
    endpoint = endpoint_path.lstrip("/")
    url = f"{base}/{endpoint}" if endpoint else base
    if query:
        url = f"{url}?{urlencode(dict(query))}"
    return url


def fetch_external_api_summary(
    *,
    spec: ExternalAPIConnectorSpec,
    endpoint_path: str = "",
    query: Mapping[str, str] | None = None,
    env: Mapping[str, str] | None = None,
    timeout: int = 10,
    fetch_fn: FetchFn = _default_fetch,
) -> ExternalAPIFetchItem:
    decision = evaluate_api_connector(spec)
    if not decision.can_connect:
        raise APIFetchError(f"connector denied by policy gate: {spec.connector_id}: {', '.join(decision.reasons)}")
    if any(key.lower() in {"token", "secret", "api_key", "password", "cookie"} for key in (query or {})):
        raise APIFetchError("query parameters must not include secret-bearing keys")

    env_source = env if env is not None else os.environ
    headers: dict[str, str] = {
        "Accept": "application/json,text/plain,text/html;q=0.8",
        "User-Agent": "ProjectAegis/0.1 api-dry-run",
    }
    auth_env_vars_used: list[str] = []
    if spec.auth_method == "env_var":
        missing = [name for name in spec.required_env_vars if not env_source.get(name)]
        if missing:
            raise APIFetchError("missing required env vars: " + ", ".join(missing))
        first_env_var = spec.required_env_vars[0]
        headers["Authorization"] = "Bearer " + str(env_source[first_env_var])
        auth_env_vars_used = spec.required_env_vars

    status, content_type, payload = fetch_fn(_build_url(spec.base_url, endpoint_path, query), headers, timeout)
    if status >= 400:
        raise APIFetchError(f"approved API returned HTTP {status}")

    return ExternalAPIFetchItem(
        connector_id=spec.connector_id,
        retrieved_at=_now_iso(),
        endpoint_path=endpoint_path,
        status_code=status,
        content_type=content_type,
        summary=_summarize_payload(payload, content_type),
        content_hash=_sha256_bytes(payload),
        raw_bytes_stored=False,
        auth_env_vars_used=auth_env_vars_used,
        request_headers_stored=False,
        safety_notes=[
            "policy_gate_allowed",
            "secret_values_not_stored",
            "request_headers_not_stored",
            "raw_bytes_not_stored",
            "summary_hash_only",
            "no_broker_api",
            "no_trading_webhook",
        ],
    )
