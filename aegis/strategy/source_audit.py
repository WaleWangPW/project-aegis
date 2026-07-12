"""Public strategy research source reachability audit.

The audit verifies that catalogued A/H/US strategy research sources can be
checked through bounded public URL fetches. It stores metadata and hashes only,
never raw documents or full text.
"""

from __future__ import annotations

import hashlib
from collections import Counter
from datetime import datetime, timezone
from typing import Callable, Iterable
from urllib.request import Request, urlopen

from aegis.models.strategy_research import StrategyResearchRecord

FetchFn = Callable[[str, int], tuple[int, str, bytes]]

_SECRET_PATTERNS = ("token=", "secret=", "api_key=", "apikey=", "password=", "cookie=", "bearer ")


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _default_fetch(url: str, timeout: int) -> tuple[int, str, bytes]:
    request = Request(
        url,
        headers={
            "User-Agent": "ProjectAegis/0.1 strategy-source-audit",
            "Accept": "application/pdf,text/html,text/plain;q=0.8",
            "Range": "bytes=0-8191",
        },
    )
    with urlopen(request, timeout=timeout) as response:
        return response.status, response.headers.get("content-type", ""), response.read(8192)


def _url_is_secret_safe(url: str) -> bool:
    lowered = url.lower()
    return not any(pattern in lowered for pattern in _SECRET_PATTERNS)


def audit_strategy_research_sources(
    records: Iterable[StrategyResearchRecord],
    *,
    run_id: str,
    command: str | None = None,
    max_sources: int | None = None,
    timeout: int = 10,
    fetch_fn: FetchFn = _default_fetch,
    network_used: bool = True,
) -> dict:
    """Audit public strategy source URLs with metadata/hash-only retention."""

    record_list = list(records)
    selected = record_list[:max_sources] if max_sources is not None else record_list
    audited: list[dict] = []
    market_counts: Counter[str] = Counter()
    family_counts: Counter[str] = Counter()
    blocked_count = 0

    for record in selected:
        market_counts.update(record.markets)
        family_counts.update(record.strategy_families)
        if not _url_is_secret_safe(record.url):
            blocked_count += 1
            audited.append(
                {
                    "research_id": record.research_id,
                    "publisher": record.publisher,
                    "url": record.url,
                    "status": "blocked_secret_like_url",
                    "status_code": None,
                    "content_type": None,
                    "content_sample_hash": None,
                    "sample_bytes_stored": False,
                    "raw_text_stored": False,
                    "markets": record.markets,
                    "strategy_families": record.strategy_families,
                }
            )
            continue

        status_code, content_type, payload = fetch_fn(record.url, timeout)
        audited.append(
            {
                "research_id": record.research_id,
                "publisher": record.publisher,
                "url": record.url,
                "status": "reachable" if status_code < 400 else "http_error",
                "status_code": status_code,
                "content_type": content_type,
                "content_sample_hash": _sha256_bytes(payload),
                "sample_bytes_stored": False,
                "raw_text_stored": False,
                "markets": record.markets,
                "strategy_families": record.strategy_families,
            }
        )

    reachable = [item for item in audited if item["status"] == "reachable"]
    status_counts: Counter[str] = Counter(item["status"] for item in audited)
    return {
        "overall_status": "PASS" if audited and not blocked_count and len(reachable) == len(audited) else "FAIL",
        "acceptance_target": "V2.8-A Public Strategy Source Audit",
        "generated_at": _now_iso(),
        "run_id": run_id,
        "command": command,
        "network_used": network_used,
        "audited_count": len(audited),
        "reachable_count": len(reachable),
        "status_counts": dict(sorted(status_counts.items())),
        "market_coverage": dict(sorted(market_counts.items())),
        "strategy_family_coverage": dict(sorted(family_counts.items())),
        "audited_sources": audited,
        "checks": {
            "audited_at_least_one_source": bool(audited),
            "all_audited_sources_reachable": len(reachable) == len(audited) and bool(audited),
            "covers_a_h_us": all(market_counts.get(market, 0) > 0 for market in ["A", "H", "US"]),
            "content_hashes_recorded": all(bool(item["content_sample_hash"]) for item in reachable),
            "raw_text_not_stored": all(item["raw_text_stored"] is False for item in audited),
            "sample_bytes_not_stored": all(item["sample_bytes_stored"] is False for item in audited),
            "secret_like_urls_blocked": blocked_count == 0,
            "requires_sandbox_before_suggestion": True,
            "no_real_trade": True,
            "no_broker_api": True,
            "no_trading_webhook": True,
            "no_strategy_auto_mutation": True,
            "no_production_records_mutation": True,
        },
        "safety": {
            "metadata_hash_only": True,
            "raw_text_not_stored": True,
            "sample_bytes_not_stored": True,
            "no_secret_values_stored": True,
            "no_cookies": True,
            "no_api_keys": True,
            "requires_sandbox_before_suggestion": True,
            "no_real_trade": True,
            "no_broker_api": True,
            "no_trading_webhook": True,
            "no_strategy_auto_mutation": True,
            "no_production_records_mutation": True,
        },
    }


def audit_strategy_research_sources_lenient(
    records: Iterable[StrategyResearchRecord],
    *,
    run_id: str,
    command: str | None = None,
    max_sources: int | None = None,
    timeout: int = 10,
    fetch_fn: FetchFn = _default_fetch,
    network_used: bool = True,
) -> dict:
    """Audit public URLs without failing on individual network errors.

    Live public sources may block bots, redirect, rate-limit, or temporarily
    fail. For live audit acceptance, the important evidence is that every
    selected source was attempted, classified, and retained safely.
    """

    record_list = list(records)
    selected = record_list[:max_sources] if max_sources is not None else record_list
    audited: list[dict] = []
    market_counts: Counter[str] = Counter()
    family_counts: Counter[str] = Counter()
    blocked_count = 0

    for record in selected:
        market_counts.update(record.markets)
        family_counts.update(record.strategy_families)
        base_item = {
            "research_id": record.research_id,
            "publisher": record.publisher,
            "url": record.url,
            "sample_bytes_stored": False,
            "raw_text_stored": False,
            "markets": record.markets,
            "strategy_families": record.strategy_families,
        }
        if not _url_is_secret_safe(record.url):
            blocked_count += 1
            audited.append(
                {
                    **base_item,
                    "status": "blocked_secret_like_url",
                    "status_code": None,
                    "content_type": None,
                    "content_sample_hash": None,
                    "error_type": None,
                    "error_message": None,
                }
            )
            continue
        try:
            status_code, content_type, payload = fetch_fn(record.url, timeout)
        except Exception as exc:  # network evidence should be recorded, not hidden
            audited.append(
                {
                    **base_item,
                    "status": "fetch_error",
                    "status_code": getattr(exc, "code", None),
                    "content_type": None,
                    "content_sample_hash": None,
                    "error_type": exc.__class__.__name__,
                    "error_message": str(exc)[:240],
                }
            )
            continue
        audited.append(
            {
                **base_item,
                "status": "reachable" if status_code < 400 else "http_error",
                "status_code": status_code,
                "content_type": content_type,
                "content_sample_hash": _sha256_bytes(payload),
                "error_type": None,
                "error_message": None,
            }
        )

    reachable = [item for item in audited if item["status"] == "reachable"]
    attempted = [item for item in audited if item["status"] != "blocked_secret_like_url"]
    status_counts: Counter[str] = Counter(item["status"] for item in audited)
    return {
        "overall_status": "PASS" if audited and blocked_count == 0 else "FAIL",
        "acceptance_target": "V2.8-B Live Public Strategy Source Audit",
        "generated_at": _now_iso(),
        "run_id": run_id,
        "command": command,
        "network_used": network_used,
        "audited_count": len(audited),
        "attempted_count": len(attempted),
        "reachable_count": len(reachable),
        "status_counts": dict(sorted(status_counts.items())),
        "market_coverage": dict(sorted(market_counts.items())),
        "strategy_family_coverage": dict(sorted(family_counts.items())),
        "audited_sources": audited,
        "checks": {
            "audited_at_least_one_source": bool(audited),
            "all_selected_sources_classified": all(bool(item["status"]) for item in audited),
            "all_safe_sources_attempted": len(attempted) + blocked_count == len(audited),
            "covers_a_h_us": all(market_counts.get(market, 0) > 0 for market in ["A", "H", "US"]),
            "reachable_sources_have_hashes": all(bool(item["content_sample_hash"]) for item in reachable),
            "fetch_errors_are_recorded": all(
                item["status"] != "fetch_error" or bool(item["error_type"]) for item in audited
            ),
            "raw_text_not_stored": all(item["raw_text_stored"] is False for item in audited),
            "sample_bytes_not_stored": all(item["sample_bytes_stored"] is False for item in audited),
            "secret_like_urls_blocked": blocked_count == 0,
            "requires_sandbox_before_suggestion": True,
            "no_real_trade": True,
            "no_broker_api": True,
            "no_trading_webhook": True,
            "no_strategy_auto_mutation": True,
            "no_production_records_mutation": True,
        },
        "safety": {
            "metadata_hash_only": True,
            "raw_text_not_stored": True,
            "sample_bytes_not_stored": True,
            "no_secret_values_stored": True,
            "no_cookies": True,
            "no_api_keys": True,
            "requires_sandbox_before_suggestion": True,
            "no_real_trade": True,
            "no_broker_api": True,
            "no_trading_webhook": True,
            "no_strategy_auto_mutation": True,
            "no_production_records_mutation": True,
        },
    }
