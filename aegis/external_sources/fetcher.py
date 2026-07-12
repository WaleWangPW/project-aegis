"""Official-source fetcher for V2.0-F.

Only sources allowed by the Source Policy Gate can be fetched. This module
does not support cookies, browser sessions, paywall bypass, broker access, or
secret-bearing headers.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Callable
from urllib.request import Request, urlopen

from aegis.external_sources.policy import evaluate_source_policy
from aegis.models.common import Market
from aegis.models.external_item import ExternalMarketItem
from aegis.models.external_source import ExternalSourcePolicy


class SourceFetchError(RuntimeError):
    pass


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _default_fetch(url: str, user_agent: str, timeout: int) -> tuple[int, str, bytes]:
    req = Request(
        url,
        headers={
            "User-Agent": user_agent,
            "Accept": "application/json,text/plain,text/html;q=0.8",
        },
    )
    with urlopen(req, timeout=timeout) as response:
        return response.status, response.headers.get("content-type", ""), response.read()


def _summarize(payload: bytes, content_type: str, max_chars: int = 420) -> str:
    text = payload.decode("utf-8", errors="replace")
    if "json" in content_type:
        try:
            data = json.loads(text)
            if isinstance(data, dict):
                keys = ", ".join(sorted(list(data.keys()))[:12])
                return f"JSON document with keys: {keys}."
        except json.JSONDecodeError:
            pass
    collapsed = " ".join(text.split())
    return collapsed[:max_chars]


def fetch_official_source_item(
    *,
    source: ExternalSourcePolicy,
    symbol: str,
    market: Market,
    url: str,
    publisher: str,
    user_agent: str,
    timeout: int = 10,
    fetch_fn: Callable[[str, str, int], tuple[int, str, bytes]] = _default_fetch,
) -> ExternalMarketItem:
    decision = evaluate_source_policy(source)
    if not decision.can_collect:
        raise SourceFetchError(f"source denied by policy gate: {source.source_id}: {', '.join(decision.reasons)}")
    if source.source_type not in {"official_company", "regulator", "public_web"}:
        raise SourceFetchError(f"source type not allowed for V2.0-F official fetcher: {source.source_type}")
    if source.requires_api_key:
        raise SourceFetchError("V2.0-F official fetcher does not accept API keys or secrets")
    if not user_agent or "@" not in user_agent:
        raise SourceFetchError("official fetch requires a contact-style User-Agent")

    status, content_type, payload = fetch_fn(url, user_agent, timeout)
    if status >= 400:
        raise SourceFetchError(f"official source returned HTTP {status}")

    return ExternalMarketItem(
        source_id=source.source_id,
        source_type=source.source_type,
        symbol=symbol,
        market=market,
        retrieved_at=_now_iso(),
        published_at=None,
        author_or_publisher=publisher,
        url_or_external_id=url,
        license_status=source.license_status,
        evidence_level=source.evidence_level,
        summary=_summarize(payload, content_type),
        quoted_excerpt=None,
        content_hash=_sha256_bytes(payload),
        retention_policy=source.retention_policy,
        raw_bytes_stored=False,
        safety_notes=[
            "policy_gate_allowed",
            "no_cookie_header",
            "no_secret_header",
            "metadata_summary_only",
        ],
    )
