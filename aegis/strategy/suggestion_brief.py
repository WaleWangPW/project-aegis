"""User-readable suggestion brief for simulation-only candidates."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Mapping, Sequence


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def _drafts_by_id(suggestion_drafts: Sequence[Mapping] | None) -> dict[str, Mapping]:
    return {str(item.get("suggestion_id")): item for item in suggestion_drafts or []}


def _trim(values: Sequence[str] | None, *, limit: int = 5) -> list[str]:
    cleaned = [str(value) for value in values or [] if str(value).strip()]
    return cleaned[:limit]


def build_usable_suggestion_brief(
    *,
    bindings: Sequence[Mapping],
    suggestion_drafts: Sequence[Mapping] | None = None,
    run_id: str,
    evidence_refs: Sequence[str] | None = None,
    generated_at: str | None = None,
) -> dict:
    """Build a concise, user-readable brief from candidate bindings.

    This function does not create RecommendationRecords, prices, position
    sizes, orders, broker calls, or production mutations. It only summarizes
    already-gated simulation candidates and their evidence.
    """

    generated = generated_at or _now_iso()
    drafts = _drafts_by_id(suggestion_drafts)
    items: list[dict] = []

    for binding in bindings:
        suggestion_id = str(binding.get("suggestion_id"))
        draft = drafts.get(suggestion_id, {})
        base = {
            "suggestion_id": suggestion_id,
            "strategy_id": binding.get("strategy_id"),
            "market": binding.get("market"),
            "simulation_only": True,
            "user_must_execute_externally": True,
            "no_live_order": True,
            "no_broker_api": True,
            "no_webhook": True,
            "evidence_refs": _trim(
                [
                    *(draft.get("evidence_refs") or []),
                    *(binding.get("evidence_refs") or []),
                    *(evidence_refs or []),
                ],
                limit=12,
            ),
            "risk_warnings": _trim(
                [
                    *(draft.get("risk_warnings") or []),
                    *(binding.get("warnings") or []),
                    "This is a simulation-only candidate, not an order.",
                    "The user must decide and execute manually outside Aegis.",
                ],
                limit=10,
            ),
        }

        if binding.get("binding_status") == "blocked":
            items.append(
                {
                    **base,
                    "item_id": f"brief_{suggestion_id}",
                    "brief_status": "blocked",
                    "symbol": draft.get("symbol"),
                    "name": draft.get("name"),
                    "candidate_source": None,
                    "candidate_score": None,
                    "suggested_user_action": "do_not_use_for_entry",
                    "plain_summary": "这条策略路径已被阻断，不能作为可用入场候选。",
                    "reasons": _trim(draft.get("reasons"), limit=5),
                    "blocked_by": _trim(binding.get("blocked_by") or draft.get("blocked_by"), limit=8),
                }
            )
            continue

        for candidate in binding.get("bound_candidates") or []:
            symbol = candidate.get("symbol")
            market = candidate.get("market") or binding.get("market")
            name = candidate.get("name")
            source = candidate.get("source")
            items.append(
                {
                    **base,
                    "item_id": f"brief_{suggestion_id}_{symbol}",
                    "brief_status": "candidate",
                    "symbol": symbol,
                    "name": name,
                    "candidate_source": source,
                    "candidate_score": candidate.get("score"),
                    "candidate_status": candidate.get("status"),
                    "suggested_user_action": "review_for_simulated_paper_entry",
                    "plain_summary": (
                        f"{symbol} ({market}) 是基于已批准证据生成的模拟候选。"
                        "请先查看证据和风险，再由你在外部软件中自行决定是否手动操作。"
                    ),
                    "reasons": _trim(draft.get("reasons"), limit=5),
                    "blocked_by": [],
                }
            )

    candidate_items = [item for item in items if item["brief_status"] == "candidate"]
    blocked_items = [item for item in items if item["brief_status"] == "blocked"]
    candidate_markets = sorted({item["market"] for item in candidate_items if item.get("market")})
    blocked_markets = sorted({item["market"] for item in blocked_items if item.get("market")})
    checks = {
        "has_user_readable_items": len(items) > 0,
        "has_a_h_us_candidates": {"A", "H", "US"}.issubset(set(candidate_markets)),
        "blocked_paths_visible": len(blocked_items) > 0,
        "every_item_has_evidence": all(bool(item.get("evidence_refs")) for item in items),
        "every_item_simulation_only": all(item["simulation_only"] is True for item in items),
        "manual_external_execution_only": all(item["user_must_execute_externally"] is True for item in items),
        "no_live_order": all(item["no_live_order"] is True for item in items),
        "no_broker_api": all(item["no_broker_api"] is True for item in items),
        "no_webhook": all(item["no_webhook"] is True for item in items),
        "no_live_price_or_position_size": all(
            "live_price" not in item and "position_size" not in item and "order" not in item for item in items
        ),
    }

    return {
        "overall_status": "PASS" if all(checks.values()) else "FAIL",
        "acceptance_target": "V2.6-A Usable Suggestion Brief",
        "brief_type": "usable_simulation_suggestion_brief",
        "run_id": run_id,
        "generated_at": generated,
        "production_records_written": False,
        "dashboard_contract_changed": False,
        "network_used": False,
        "summary": {
            "item_count": len(items),
            "candidate_count": len(candidate_items),
            "blocked_count": len(blocked_items),
            "candidate_markets": candidate_markets,
            "blocked_markets": blocked_markets,
            "candidate_symbols": [item["symbol"] for item in candidate_items],
        },
        "disclaimer": (
            "Aegis 只提供模拟研究候选，不做真实交易，不连接券商，不下单。"
            "任何最终判断和手动执行都由用户在 Aegis 之外完成。"
        ),
        "items": items,
        "checks": checks,
        "safety": {
            "simulation_only": True,
            "manual_external_execution_only": True,
            "no_real_trade": True,
            "no_broker_api": True,
            "no_webhook": True,
            "no_live_order": True,
            "no_live_price": True,
            "no_position_size": True,
            "candidate_binding_not_recommendation_record": True,
            "dashboard_contract_unchanged": True,
            "no_production_records_mutation": True,
        },
    }


def render_usable_suggestion_brief_markdown(report: Mapping) -> str:
    lines = [
        "# V2.6-A Usable Suggestion Brief",
        "",
        f"- status: `{report.get('overall_status')}`",
        f"- run_id: `{report.get('run_id')}`",
        f"- candidate_count: `{report.get('summary', {}).get('candidate_count')}`",
        f"- blocked_count: `{report.get('summary', {}).get('blocked_count')}`",
        f"- candidate_markets: `{report.get('summary', {}).get('candidate_markets')}`",
        "",
        "## Boundary",
        "",
        "- 仅模拟建议。",
        "- 不做真实交易。",
        "- 不接 Broker API。",
        "- 不使用 webhook。",
        "- 不给实时价格或仓位数量。",
        "- 用户在 Aegis 外部自行判断并手动执行。",
        "",
        "## Candidates",
        "",
    ]
    for item in report.get("items", []):
        title = item.get("symbol") or item.get("suggestion_id")
        if item.get("name"):
            title = f"{title} - {item['name']}"
        lines.extend(
            [
                f"### {title}",
                "",
                f"- market: `{item.get('market')}`",
                f"- status: `{item.get('brief_status')}`",
                f"- action: `{item.get('suggested_user_action')}`",
                f"- source: `{item.get('candidate_source') or 'none'}`",
                f"- summary: {item.get('plain_summary')}",
                f"- blocked_by: `{', '.join(item.get('blocked_by') or []) or 'none'}`",
                f"- evidence_refs: `{len(item.get('evidence_refs') or [])}`",
                "",
            ]
        )
    return "\n".join(lines)
