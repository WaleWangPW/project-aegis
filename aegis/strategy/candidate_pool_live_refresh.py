"""Refresh the candidate pool from approved routes after blocked candidates."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Mapping

ACCEPTANCE_TARGET = "V2.14-B Candidate Pool Live Refresh From Approved Routes"
SOURCE_TARGET = "V2.14-A Post-Blocked Candidate Pool Refresh Plan"


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _normalize_symbol(symbol: str) -> str:
    value = symbol.strip().upper()
    if value.endswith(".US"):
        return value[:-3]
    return value


def _candidate_id(symbol: str, market: str) -> str:
    normalized = symbol.lower().replace(".", "_").replace("-", "_")
    return f"v2_14_b_{market.lower()}_{normalized}"


def _route_by_market(source_plan: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    return {str(item.get("market")): item for item in source_plan.get("route_plan", []) or []}


def _refresh_status_for_market(route: Mapping[str, Any]) -> str:
    market = route.get("market")
    if market == "A":
        return "refreshed_pending_historical_sandbox"
    if market == "H":
        return "refreshed_pending_historical_sandbox"
    return "blocked_until_replacement_candidates_found"


def _refreshed_candidate(item: Mapping[str, Any], route: Mapping[str, Any], *, evidence_ref: str) -> dict[str, Any]:
    symbol = str(item.get("symbol"))
    market = str(item.get("market"))
    return {
        "candidate_id": _candidate_id(symbol, market),
        "symbol": symbol,
        "market": market,
        "strategy_id": item.get("strategy_id"),
        "source_route_id": route.get("route_id"),
        "provider": route.get("provider"),
        "refresh_status": _refresh_status_for_market(route),
        "requires_historical_sandbox": True,
        "requires_suggestion_gate": True,
        "user_facing_suggestion_allowed": False,
        "evidence_refs": [evidence_ref],
        "notes": [
            "Candidate summary only; not a recommendation.",
            "Manual external execution boundary remains active.",
        ],
    }


def build_candidate_pool_live_refresh_report(
    *,
    source_plan: Mapping[str, Any],
    run_id: str,
    command: str | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    routes = _route_by_market(source_plan)
    blocked_symbols = {
        _normalize_symbol(str(symbol))
        for symbol in (source_plan.get("summary", {}) or {}).get("source_blocked_symbols", []) or []
    }
    retained = [dict(item) for item in source_plan.get("retained_candidates", []) or []]
    eligible_retained = [item for item in retained if item.get("market") in {"A", "H"}]
    evidence_ref = f"v2_14_a_refresh_plan:{source_plan.get('run_id')}:{_sha256_text(json.dumps(source_plan.get('summary') or {}, ensure_ascii=False, sort_keys=True))}"
    refreshed_candidates = [
        _refreshed_candidate(item, routes[str(item.get("market"))], evidence_ref=evidence_ref)
        for item in eligible_retained
        if str(item.get("market")) in routes
    ]
    refreshed_by_market = {
        market: [item for item in refreshed_candidates if item.get("market") == market]
        for market in ["A", "H", "US"]
    }
    replacement_requests = [
        {
            **dict(request),
            "refresh_status": "open_pending_replacement_candidates",
            "user_facing_suggestion_allowed": False,
        }
        for request in source_plan.get("replacement_requests", []) or []
    ]

    revived_blocked_symbols = sorted(
        {
            _normalize_symbol(str(item.get("symbol")))
            for item in refreshed_candidates
            if _normalize_symbol(str(item.get("symbol"))) in blocked_symbols
        }
    )
    route_statuses = [
        {
            "market": market,
            "route_id": route.get("route_id"),
            "provider": route.get("provider"),
            "source_refresh_status": route.get("refresh_status"),
            "output_status": _refresh_status_for_market(route),
            "refreshed_candidate_count": len(refreshed_by_market.get(market, [])),
            "requires_historical_sandbox": route.get("requires_sandbox") is True,
            "requires_suggestion_gate": route.get("requires_suggestion_gate") is True,
        }
        for market, route in routes.items()
    ]
    checks = {
        "source_plan_pass": source_plan.get("overall_status") == "PASS",
        "source_plan_target_correct": source_plan.get("acceptance_target") == SOURCE_TARGET,
        "blocked_symbols_present": len(blocked_symbols) >= 3,
        "a_route_present": "A" in routes,
        "h_route_present": "H" in routes,
        "us_replacement_route_present": "US" in routes,
        "a_candidates_refreshed": len(refreshed_by_market["A"]) >= 1,
        "h_candidates_refreshed": len(refreshed_by_market["H"]) >= 1,
        "us_candidates_not_refreshed_from_blocked_pool": len(refreshed_by_market["US"]) == 0,
        "blocked_symbols_not_revived": not revived_blocked_symbols,
        "replacement_request_kept_open": any(request.get("market") == "US" for request in replacement_requests),
        "all_refreshed_candidates_require_sandbox": all(
            item["requires_historical_sandbox"] is True for item in refreshed_candidates
        ),
        "all_refreshed_candidates_require_suggestion_gate": all(
            item["requires_suggestion_gate"] is True for item in refreshed_candidates
        ),
        "not_user_facing_suggestion": all(
            item["user_facing_suggestion_allowed"] is False for item in refreshed_candidates
        ),
        "network_not_used_this_stage": True,
        "production_records_not_written": True,
        "production_cache_not_mutated": True,
        "production_provider_config_not_mutated": True,
        "no_secret_values_stored": True,
        "request_urls_not_stored": True,
        "raw_payloads_not_stored": True,
        "no_real_trade": True,
        "no_broker_api": True,
        "no_webhook": True,
        "no_order_placement": True,
        "no_position_size": True,
        "no_live_order_signal": True,
        "dashboard_contract_unchanged": True,
    }
    return {
        "overall_status": "PASS" if all(checks.values()) else "FAIL",
        "acceptance_target": ACCEPTANCE_TARGET,
        "run_id": run_id,
        "generated_at": generated_at or _now_iso(),
        "command": command,
        "network_used": False,
        "production_records_written": False,
        "production_cache_mutated": False,
        "production_provider_config_mutated": False,
        "dashboard_contract_changed": False,
        "summary": {
            "refreshed_candidate_count": len(refreshed_candidates),
            "refreshed_markets": sorted(market for market, items in refreshed_by_market.items() if items),
            "blocked_symbols_not_reused": sorted(blocked_symbols),
            "replacement_required_markets": ["US"],
            "replacement_request_count": len(replacement_requests),
            "user_facing_suggestion_allowed": False,
            "next_stage": "V2.14-C Refreshed Candidate Historical Sandbox",
        },
        "route_statuses": route_statuses,
        "refreshed_candidates": refreshed_candidates,
        "replacement_requests": replacement_requests,
        "revived_blocked_symbols": revived_blocked_symbols,
        "source_evidence": {
            "source_target": source_plan.get("acceptance_target"),
            "source_run_id": source_plan.get("run_id"),
            "source_summary_sha256": _sha256_text(
                json.dumps(source_plan.get("summary") or {}, ensure_ascii=False, sort_keys=True)
            ),
            "source_route_plan_sha256": _sha256_text(
                json.dumps(source_plan.get("route_plan") or [], ensure_ascii=False, sort_keys=True)
            ),
        },
        "checks": checks,
        "safety": {
            "candidate_pool_refresh_only": True,
            "not_user_facing_suggestion": True,
            "historical_sandbox_required": True,
            "suggestion_gate_required": True,
            "blocked_candidates_not_reused": True,
            "network_not_used_this_stage": True,
            "production_records_not_written": True,
            "production_cache_not_mutated": True,
            "production_provider_config_not_mutated": True,
            "no_secret_values_stored": True,
            "request_urls_not_stored": True,
            "raw_payloads_not_stored": True,
            "no_real_trade": True,
            "no_broker_api": True,
            "no_webhook": True,
            "no_order_placement": True,
            "no_position_size": True,
            "no_live_order_signal": True,
            "dashboard_contract_unchanged": True,
        },
    }


def render_candidate_pool_live_refresh_markdown(report: Mapping[str, Any]) -> str:
    lines = [
        "# V2.14-B Candidate Pool Live Refresh From Approved Routes",
        "",
        f"- status: `{report.get('overall_status')}`",
        f"- run_id: `{report.get('run_id')}`",
        f"- refreshed_candidate_count: `{report.get('summary', {}).get('refreshed_candidate_count')}`",
        f"- refreshed_markets: `{report.get('summary', {}).get('refreshed_markets')}`",
        f"- replacement_required_markets: `{report.get('summary', {}).get('replacement_required_markets')}`",
        f"- next_stage: `{report.get('summary', {}).get('next_stage')}`",
        "",
        "## Refreshed Candidates",
        "",
    ]
    for item in report.get("refreshed_candidates", []) or []:
        lines.append(
            f"- `{item.get('symbol')}` / `{item.get('market')}` via `{item.get('source_route_id')}` "
            f"status=`{item.get('refresh_status')}`"
        )
    lines.extend(["", "## Replacement Requests", ""])
    for item in report.get("replacement_requests", []) or []:
        lines.append(
            f"- `{item.get('market')}`: `{item.get('request_id')}` "
            f"status=`{item.get('refresh_status')}` blocked=`{item.get('blocked_symbols')}`"
        )
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "- Candidate pool refresh only.",
            "- Not a user-facing suggestion.",
            "- Historical sandbox and Suggestion Gate remain required.",
            "- Blocked symbols from V2.13-W are not reused.",
            "- No real trade, broker API, webhook, order placement, live order signal, or position size.",
            "",
        ]
    )
    return "\n".join(lines)
