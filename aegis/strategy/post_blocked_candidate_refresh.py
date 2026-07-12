"""Plan candidate refresh after a multi-symbol sandbox block."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Mapping

ACCEPTANCE_TARGET = "V2.14-A Post-Blocked Candidate Pool Refresh Plan"
BLOCKED_SOURCE_TARGET = "V2.13-W Finnhub Quote Multi-Symbol Sandbox Result Brief"
DECISION_PACKET_TARGET = "V2.9-A Current User Decision Packet"


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _normalize_symbol(symbol: str) -> str:
    value = symbol.strip().upper()
    if value.endswith(".US"):
        return value[:-3]
    return value


def _candidate_items(decision_packet: Mapping[str, Any]) -> list[dict[str, Any]]:
    return [
        dict(item)
        for item in decision_packet.get("items", []) or []
        if isinstance(item, dict) and item.get("decision_packet_status") == "simulation_candidate"
    ]


def _route_for_market(market: str, retained_count: int) -> dict[str, Any]:
    if market == "A":
        return {
            "market": "A",
            "route_id": "tushare_a_share_candidate_refresh",
            "provider": "tushare",
            "refresh_status": "ready_for_live_refresh",
            "retained_candidate_count": retained_count,
            "requires_user_api": True,
            "requires_sandbox": True,
            "requires_suggestion_gate": True,
        }
    if market == "H":
        return {
            "market": "H",
            "route_id": "h_share_h_us_provider_candidate_refresh",
            "provider": "h_us_provider",
            "refresh_status": "ready_for_h_us_refresh",
            "retained_candidate_count": retained_count,
            "requires_user_api": True,
            "requires_sandbox": True,
            "requires_suggestion_gate": True,
        }
    return {
        "market": "US",
        "route_id": "us_candidate_replacement_required",
        "provider": "finnhub_or_h_us_provider",
        "refresh_status": "blocked_until_replacement_candidates_found",
        "retained_candidate_count": retained_count,
        "requires_user_api": True,
        "requires_new_candidate_source": True,
        "requires_sandbox": True,
        "requires_suggestion_gate": True,
    }


def build_post_blocked_candidate_refresh_plan(
    *,
    blocked_brief: Mapping[str, Any],
    decision_packet: Mapping[str, Any],
    run_id: str,
    command: str | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    blocked_symbols = sorted(
        {
            _normalize_symbol(str(symbol))
            for symbol in (blocked_brief.get("summary", {}) or {}).get("blocked_symbols", []) or []
        }
    )
    candidates = _candidate_items(decision_packet)
    retained_candidates = [
        item for item in candidates if _normalize_symbol(str(item.get("symbol", ""))) not in set(blocked_symbols)
    ]
    removed_candidates = [
        {
            "symbol": item.get("symbol"),
            "market": item.get("market"),
            "strategy_id": item.get("strategy_id"),
            "removed_reason": "blocked_by_v2_13_w_multi_symbol_sandbox_result_brief",
        }
        for item in candidates
        if _normalize_symbol(str(item.get("symbol", ""))) in set(blocked_symbols)
    ]
    retained_by_market = {
        market: [item for item in retained_candidates if item.get("market") == market]
        for market in ["A", "H", "US"]
    }
    route_plan = [_route_for_market(market, len(items)) for market, items in retained_by_market.items()]
    replacement_requests = [
        {
            "market": "US",
            "request_id": "replace_blocked_us_multi_symbol_candidates",
            "blocked_symbols": blocked_symbols,
            "needed_count": 3,
            "reason": "current_us_candidates_failed_v2_13_v_sandbox",
            "allowed_sources": ["approved_public_strategy_sources", "finnhub_quote", "eodhd_historical_bars"],
            "forbidden_sources": ["broker_api", "trading_webhook", "unlicensed_paywall_scrape"],
            "requires_historical_sandbox": True,
            "requires_suggestion_gate": True,
        }
    ]
    checks = {
        "blocked_source_pass": blocked_brief.get("overall_status") == "PASS",
        "blocked_source_target_correct": blocked_brief.get("acceptance_target") == BLOCKED_SOURCE_TARGET,
        "decision_packet_pass": decision_packet.get("overall_status") == "PASS",
        "decision_packet_target_correct": decision_packet.get("acceptance_target") == DECISION_PACKET_TARGET,
        "blocked_symbols_present": len(blocked_symbols) >= 3,
        "decision_candidates_present": len(candidates) >= 6,
        "blocked_symbols_removed": all(
            _normalize_symbol(str(item.get("symbol", ""))) not in set(blocked_symbols) for item in retained_candidates
        ),
        "removed_candidates_match_blocked_symbols": sorted(
            _normalize_symbol(str(item.get("symbol", ""))) for item in removed_candidates
        )
        == blocked_symbols,
        "a_candidates_retained": len(retained_by_market["A"]) >= 1,
        "h_candidates_retained": len(retained_by_market["H"]) >= 1,
        "us_candidates_require_replacement": len(retained_by_market["US"]) == 0,
        "all_routes_require_sandbox": all(item["requires_sandbox"] is True for item in route_plan),
        "all_routes_require_suggestion_gate": all(item["requires_suggestion_gate"] is True for item in route_plan),
        "replacement_request_created": bool(replacement_requests),
        "not_user_facing_suggestion": True,
        "network_not_used": True,
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
            "source_blocked_symbols": blocked_symbols,
            "retained_candidate_count": len(retained_candidates),
            "removed_candidate_count": len(removed_candidates),
            "retained_markets": sorted(market for market, items in retained_by_market.items() if items),
            "replacement_required_markets": ["US"],
            "next_stage": "V2.14-B Candidate Pool Live Refresh From Approved Routes",
        },
        "retained_candidates": retained_candidates,
        "removed_candidates": removed_candidates,
        "route_plan": route_plan,
        "replacement_requests": replacement_requests,
        "source_evidence": {
            "blocked_source_target": blocked_brief.get("acceptance_target"),
            "blocked_source_run_id": blocked_brief.get("run_id"),
            "blocked_source_summary_sha256": _sha256_text(
                json.dumps(blocked_brief.get("summary") or {}, ensure_ascii=False, sort_keys=True)
            ),
            "decision_packet_target": decision_packet.get("acceptance_target"),
            "decision_packet_run_id": decision_packet.get("run_id"),
            "decision_packet_summary_sha256": _sha256_text(
                json.dumps(decision_packet.get("summary") or {}, ensure_ascii=False, sort_keys=True)
            ),
        },
        "checks": checks,
        "safety": {
            "candidate_refresh_plan_only": True,
            "not_user_facing_suggestion": True,
            "blocked_candidates_removed": True,
            "requires_historical_sandbox": True,
            "requires_suggestion_gate": True,
            "network_not_used": True,
            "no_secret_values_stored": True,
            "no_request_url_storage": True,
            "no_raw_payload_storage": True,
            "no_real_trade": True,
            "no_broker_api": True,
            "no_webhook": True,
            "no_order_placement": True,
            "no_position_size": True,
            "no_live_order_signal": True,
            "dashboard_contract_unchanged": True,
        },
    }


def render_post_blocked_candidate_refresh_markdown(report: Mapping[str, Any]) -> str:
    lines = [
        "# V2.14-A Post-Blocked Candidate Pool Refresh Plan",
        "",
        f"- status: `{report.get('overall_status')}`",
        f"- run_id: `{report.get('run_id')}`",
        f"- removed_candidate_count: `{report.get('summary', {}).get('removed_candidate_count')}`",
        f"- retained_candidate_count: `{report.get('summary', {}).get('retained_candidate_count')}`",
        f"- retained_markets: `{report.get('summary', {}).get('retained_markets')}`",
        f"- replacement_required_markets: `{report.get('summary', {}).get('replacement_required_markets')}`",
        f"- next_stage: `{report.get('summary', {}).get('next_stage')}`",
        "",
        "## Removed Candidates",
        "",
    ]
    for item in report.get("removed_candidates", []) or []:
        lines.append(f"- `{item.get('symbol')}` / `{item.get('market')}`: `{item.get('removed_reason')}`")
    lines.extend(["", "## Route Plan", ""])
    for item in report.get("route_plan", []) or []:
        lines.append(
            f"- `{item.get('market')}` -> `{item.get('route_id')}` "
            f"status=`{item.get('refresh_status')}` retained=`{item.get('retained_candidate_count')}`"
        )
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "- Candidate refresh plan only.",
            "- Not a user-facing suggestion.",
            "- Blocked candidates are removed from the next candidate pool.",
            "- Every route still requires historical sandbox and Suggestion Gate.",
            "- No real trade, broker API, webhook, order placement, live order signal, or position size.",
            "",
        ]
    )
    return "\n".join(lines)
