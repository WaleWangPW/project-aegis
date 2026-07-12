"""Build a multi-symbol expansion plan for Finnhub quote candidates.

V2.13-Q is a planning bridge, not a network probe. It turns the accepted
single-symbol Finnhub quote brief into a routed queue: US candidates may enter
the Finnhub quote route, while A-share and H-share candidates are explicitly
routed to their own provider branches.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping


ACCEPTANCE_TARGET = "V2.13-Q Finnhub Quote Multi-Symbol Candidate Expansion Plan"
SOURCE_REFRESH_TARGET = "V2.13-P Finnhub Quote Current Usable Simulation Brief Refresh With Review/Memory Context"
SOURCE_DECISION_TARGET = "V2.9-A Current User Decision Packet"


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _infer_market(symbol: str, explicit_market: str | None = None) -> str:
    if explicit_market in {"A", "H", "US"}:
        return explicit_market
    if symbol.endswith((".SH", ".SZ")):
        return "A"
    if symbol.endswith(".HK"):
        return "H"
    return "US"


def _canonical_symbol(symbol: str, market: str) -> str:
    if market == "US" and "." not in symbol:
        return f"{symbol}.US"
    return symbol


def _provider_symbol(symbol: str, market: str) -> str:
    canonical = _canonical_symbol(symbol, market)
    if market == "US" and canonical.endswith(".US"):
        return canonical.removesuffix(".US")
    return canonical


def _candidate_items(decision_packet: Mapping[str, Any]) -> list[dict[str, Any]]:
    items = [
        item
        for item in decision_packet.get("items", []) or []
        if isinstance(item, dict) and item.get("decision_packet_status") == "simulation_candidate"
    ]
    if items:
        return items

    symbols = decision_packet.get("summary", {}).get("candidate_symbols") or []
    return [{"symbol": symbol, "market": _infer_market(str(symbol))} for symbol in symbols]


def _refresh_symbols(refresh_report: Mapping[str, Any]) -> set[str]:
    symbols = set()
    for item in refresh_report.get("items", []) or []:
        symbol = item.get("symbol")
        market = _infer_market(str(symbol), item.get("market")) if symbol else None
        if symbol and market:
            symbols.add(_canonical_symbol(str(symbol), market))
    for symbol in refresh_report.get("summary", {}).get("candidate_symbols") or []:
        symbols.add(_canonical_symbol(str(symbol), _infer_market(str(symbol))))
    return symbols


def _build_queue_item(item: Mapping[str, Any], already_processed_symbols: set[str]) -> dict[str, Any]:
    raw_symbol = str(item.get("symbol"))
    market = _infer_market(raw_symbol, item.get("market"))
    canonical = _canonical_symbol(raw_symbol, market)
    provider_symbol = _provider_symbol(raw_symbol, market)
    already_processed = canonical in already_processed_symbols

    if market == "US":
        route_status = "already_has_review_memory_context" if already_processed else "queued_for_finnhub_quote_probe"
        provider_route = "finnhub_quote"
        next_stage = "V2.13-R Finnhub Quote Multi-Symbol Live Probe Dry Run"
        blocked_by: list[str] = []
    elif market == "H":
        route_status = "routed_to_h_us_provider_branch"
        provider_route = "eodhd_or_twelve_data_h_quote_or_daily_bar"
        next_stage = "V2.12 provider route refresh for H-share candidates"
        blocked_by = ["not_a_finnhub_quote_scope_candidate"]
    else:
        route_status = "routed_to_tushare_branch"
        provider_route = "tushare_a_share_daily_bar_or_snapshot"
        next_stage = "Tushare A-share candidate refresh before simulation suggestion"
        blocked_by = ["not_a_finnhub_quote_scope_candidate"]

    return {
        "symbol": canonical,
        "source_symbol": raw_symbol,
        "name": item.get("name"),
        "market": market,
        "strategy_id": item.get("strategy_id"),
        "candidate_score": item.get("candidate_score"),
        "candidate_status": item.get("candidate_status"),
        "decision_packet_status": item.get("decision_packet_status", "simulation_candidate"),
        "provider_route": provider_route,
        "provider_symbol": provider_symbol,
        "route_status": route_status,
        "next_stage": next_stage,
        "already_processed_in_v2_13_p": already_processed,
        "blocked_by": blocked_by,
        "evidence_refs": item.get("evidence_refs") or [],
        "simulation_only": True,
        "manual_external_execution_only": True,
        "requires_future_live_quote_probe": market == "US" and not already_processed,
        "requires_historical_sandbox_before_suggestion": not already_processed,
        "social_sentiment_not_enabled": True,
        "no_real_trade": True,
        "no_broker_api": True,
        "no_webhook": True,
        "no_order_placement": True,
        "no_live_price": True,
        "no_position_size": True,
        "no_live_order_signal": True,
        "no_strategy_mutation": True,
        "no_dashboard_contract_change": True,
    }


def build_finnhub_quote_multi_symbol_expansion_plan(
    refresh_report: Mapping[str, Any],
    decision_packet: Mapping[str, Any],
    *,
    run_id: str,
    command: str | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    already_processed = _refresh_symbols(refresh_report)
    queue_items = [_build_queue_item(item, already_processed) for item in _candidate_items(decision_packet)]
    us_items = [item for item in queue_items if item["market"] == "US"]
    finnhub_probe_queue = [
        item for item in us_items if item["route_status"] == "queued_for_finnhub_quote_probe"
    ]
    already_context_items = [
        item for item in us_items if item["route_status"] == "already_has_review_memory_context"
    ]
    source_context_symbols = sorted(already_processed)
    routed_away_items = [item for item in queue_items if item["market"] in {"A", "H"}]

    checks = {
        "source_refresh_is_v2_13_p": refresh_report.get("acceptance_target") == SOURCE_REFRESH_TARGET,
        "source_decision_packet_is_v2_9_a": decision_packet.get("acceptance_target") == SOURCE_DECISION_TARGET,
        "source_refresh_pass": refresh_report.get("overall_status") == "PASS",
        "source_decision_packet_pass": decision_packet.get("overall_status") == "PASS",
        "source_refresh_has_review_memory_context": bool(refresh_report.get("summary", {}).get("review_memory_context_count")),
        "source_social_sentiment_still_blocked": refresh_report.get("summary", {}).get("social_sentiment_status")
        == "blocked_plan_or_rate_limit",
        "has_source_context_symbol": bool(source_context_symbols),
        "has_new_us_finnhub_probe_candidates": len(finnhub_probe_queue) >= 2,
        "all_us_candidates_have_provider_symbol": all(item.get("provider_symbol") for item in us_items),
        "all_non_us_candidates_routed_away_from_finnhub": all(
            item["provider_route"] != "finnhub_quote" and item["blocked_by"] for item in routed_away_items
        ),
        "all_items_simulation_only": all(item["simulation_only"] is True for item in queue_items),
        "all_items_manual_external_execution_only": all(
            item["manual_external_execution_only"] is True for item in queue_items
        ),
        "all_items_no_real_trade": all(item["no_real_trade"] is True for item in queue_items),
        "all_items_no_broker_api": all(item["no_broker_api"] is True for item in queue_items),
        "all_items_no_webhook": all(item["no_webhook"] is True for item in queue_items),
        "all_items_no_order_placement": all(item["no_order_placement"] is True for item in queue_items),
        "all_items_no_live_price": all(item["no_live_price"] is True for item in queue_items),
        "all_items_no_position_size": all(item["no_position_size"] is True for item in queue_items),
        "all_items_no_live_order_signal": all(item["no_live_order_signal"] is True for item in queue_items),
        "all_items_no_strategy_mutation": all(item["no_strategy_mutation"] is True for item in queue_items),
        "network_not_used": True,
        "production_records_not_written": True,
        "dashboard_contract_unchanged": True,
    }

    return {
        "overall_status": "PASS" if all(checks.values()) else "FAIL",
        "acceptance_target": ACCEPTANCE_TARGET,
        "source_refresh_acceptance_target": refresh_report.get("acceptance_target"),
        "source_decision_acceptance_target": decision_packet.get("acceptance_target"),
        "plan_type": "finnhub_quote_multi_symbol_candidate_expansion",
        "run_id": run_id,
        "generated_at": generated_at or _now_iso(),
        "command": command,
        "network_used": False,
        "production_records_written": False,
        "dashboard_contract_changed": False,
        "summary": {
            "candidate_count": len(queue_items),
            "us_candidate_count": len(us_items),
            "finnhub_probe_queue_count": len(finnhub_probe_queue),
            "already_context_count": len(already_context_items),
            "routed_away_count": len(routed_away_items),
            "candidate_symbols": [item["symbol"] for item in queue_items],
            "finnhub_probe_symbols": [item["symbol"] for item in finnhub_probe_queue],
            "already_context_symbols": [item["symbol"] for item in already_context_items],
            "source_context_symbols": source_context_symbols,
            "routed_away_symbols": [item["symbol"] for item in routed_away_items],
            "social_sentiment_status": "blocked_plan_or_rate_limit",
            "next_stage": "V2.13-R Finnhub Quote Multi-Symbol Live Probe Dry Run",
        },
        "provider_routes": {
            "finnhub_quote": {
                "market_scope": ["US"],
                "status": "ready_for_next_probe_dry_run",
                "symbols": [item["symbol"] for item in finnhub_probe_queue],
            },
            "h_us_provider_branch": {
                "market_scope": ["H"],
                "status": "handoff_required",
                "symbols": [item["symbol"] for item in routed_away_items if item["market"] == "H"],
            },
            "tushare_branch": {
                "market_scope": ["A"],
                "status": "handoff_required",
                "symbols": [item["symbol"] for item in routed_away_items if item["market"] == "A"],
            },
        },
        "queue_items": queue_items,
        "finnhub_probe_queue": finnhub_probe_queue,
        "checks": checks,
        "safety": {
            "expansion_plan_only": True,
            "simulation_only": True,
            "manual_external_execution_only": True,
            "social_sentiment_not_enabled": True,
            "no_real_trade": True,
            "no_broker_api": True,
            "no_webhook": True,
            "no_order_placement": True,
            "no_live_price": True,
            "no_position_size": True,
            "no_live_order_signal": True,
            "no_strategy_mutation": True,
            "no_production_records_mutation": True,
            "dashboard_contract_unchanged": True,
        },
    }


def render_finnhub_quote_multi_symbol_expansion_markdown(report: Mapping[str, Any]) -> str:
    lines = [
        "# V2.13-Q Finnhub Quote Multi-Symbol Candidate Expansion Plan",
        "",
        f"- status: `{report.get('overall_status')}`",
        f"- run_id: `{report.get('run_id')}`",
        f"- candidate_count: `{report.get('summary', {}).get('candidate_count')}`",
        f"- finnhub_probe_queue_count: `{report.get('summary', {}).get('finnhub_probe_queue_count')}`",
        f"- already_context_count: `{report.get('summary', {}).get('already_context_count')}`",
        f"- routed_away_count: `{report.get('summary', {}).get('routed_away_count')}`",
        f"- social_sentiment_status: `{report.get('summary', {}).get('social_sentiment_status')}`",
        f"- next_stage: `{report.get('summary', {}).get('next_stage')}`",
        "",
        "## Finnhub Quote Queue",
        "",
    ]
    for item in report.get("finnhub_probe_queue", []) or []:
        lines.extend(
            [
                f"### {item.get('symbol')}",
                "",
                f"- provider_symbol: `{item.get('provider_symbol')}`",
                f"- strategy_id: `{item.get('strategy_id')}`",
                f"- route_status: `{item.get('route_status')}`",
                "- boundary: simulation-only; manual external execution only; no broker API, webhook, order, live price, or position size.",
                "",
            ]
        )

    lines.extend(["## Provider Routing", ""])
    for name, route in (report.get("provider_routes") or {}).items():
        lines.extend(
            [
                f"### {name}",
                "",
                f"- status: `{route.get('status')}`",
                f"- market_scope: `{route.get('market_scope')}`",
                f"- symbols: `{route.get('symbols')}`",
                "",
            ]
        )

    lines.extend(
        [
            "## Boundary",
            "",
            "- This is an expansion plan and probe queue only.",
            "- It does not fetch live quotes in this stage.",
            "- It does not write production Recommendation, PaperTrade, Review, or Memory records.",
            "- Finnhub social sentiment remains blocked and is not used.",
            "- Aegis does not connect broker APIs, webhooks, or place orders.",
            "",
        ]
    )
    return "\n".join(lines)
