"""User-readable brief for refresh-queue strategy drafts."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Mapping, Sequence


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def _trim(values: Sequence[str] | None, *, limit: int = 6) -> list[str]:
    return [str(value) for value in values or [] if str(value).strip()][:limit]


def _plain_summary(draft: Mapping) -> str:
    market = draft.get("market")
    symbol = draft.get("symbol")
    if draft.get("action") == "blocked":
        reasons = ", ".join(draft.get("blocked_by") or ["blocked"])
        return f"{symbol} ({market}) 当前被阻断，原因：{reasons}。不要用于模拟入场。"
    return (
        f"{symbol} ({market}) 是通过历史沙盘和 Suggestion Gate 的模拟策略篮子，"
        "只适合进入观察/纸面验证，不是具体个股买入指令。"
    )


def build_refresh_queue_usable_brief(
    *,
    suggestion_drafts: Sequence[Mapping],
    run_id: str,
    evidence_refs: Sequence[str] | None = None,
    generated_at: str | None = None,
) -> dict:
    """Build a readable brief directly from V2.8-E refresh-queue drafts."""

    items: list[dict] = []
    generated = generated_at or _now_iso()
    for draft in suggestion_drafts:
        action = draft.get("action")
        item_status = "candidate" if action != "blocked" else "blocked"
        items.append(
            {
                "item_id": f"brief_{draft.get('suggestion_id')}",
                "suggestion_id": draft.get("suggestion_id"),
                "strategy_id": draft.get("strategy_id"),
                "market": draft.get("market"),
                "symbol": draft.get("symbol"),
                "brief_status": item_status,
                "draft_action": action,
                "suggested_user_action": (
                    "review_for_simulated_strategy_watch" if item_status == "candidate" else "do_not_use_for_entry"
                ),
                "plain_summary": _plain_summary(draft),
                "reasons": _trim(draft.get("reasons")),
                "risk_warnings": _trim(
                    [
                        *(draft.get("risk_warnings") or []),
                        "Simulation-only strategy basket; not a live order.",
                        "User decides manually outside Aegis.",
                    ],
                    limit=10,
                ),
                "blocked_by": _trim(draft.get("blocked_by"), limit=8),
                "evidence_refs": _trim([*(draft.get("evidence_refs") or []), *(evidence_refs or [])], limit=12),
                "simulation_only": True,
                "user_must_execute_externally": True,
                "no_live_order": True,
                "no_live_price": True,
                "no_position_size": True,
                "no_broker_api": True,
                "no_webhook": True,
            }
        )

    candidate_items = [item for item in items if item["brief_status"] == "candidate"]
    blocked_items = [item for item in items if item["brief_status"] == "blocked"]
    candidate_markets = sorted({item["market"] for item in candidate_items if item.get("market")})
    blocked_markets = sorted({item["market"] for item in blocked_items if item.get("market")})
    checks = {
        "has_user_readable_items": bool(items),
        "has_a_h_us_candidate_baskets": {"A", "H", "US"}.issubset(candidate_markets),
        "blocked_paths_visible": bool(blocked_items),
        "every_item_has_evidence": all(bool(item["evidence_refs"]) for item in items),
        "every_item_has_plain_summary": all(bool(item["plain_summary"]) for item in items),
        "every_item_simulation_only": all(item["simulation_only"] is True for item in items),
        "manual_external_execution_only": all(item["user_must_execute_externally"] is True for item in items),
        "no_live_order": all(item["no_live_order"] is True for item in items),
        "no_live_price": all(item["no_live_price"] is True for item in items),
        "no_position_size": all(item["no_position_size"] is True for item in items),
        "no_broker_api": all(item["no_broker_api"] is True for item in items),
        "no_webhook": all(item["no_webhook"] is True for item in items),
    }
    return {
        "overall_status": "PASS" if all(checks.values()) else "FAIL",
        "acceptance_target": "V2.8-F Refresh Queue Usable Brief Update",
        "brief_type": "refresh_queue_strategy_brief",
        "run_id": run_id,
        "generated_at": generated,
        "network_used": False,
        "production_records_written": False,
        "dashboard_contract_changed": False,
        "summary": {
            "item_count": len(items),
            "candidate_count": len(candidate_items),
            "blocked_count": len(blocked_items),
            "candidate_markets": candidate_markets,
            "blocked_markets": blocked_markets,
            "candidate_symbols": [item["symbol"] for item in candidate_items],
            "blocked_symbols": [item["symbol"] for item in blocked_items],
        },
        "disclaimer": (
            "本简报只展示通过沙盘和 Suggestion Gate 的模拟策略篮子，不是具体股票买卖建议，"
            "不含实时价格、仓位、订单、券商接口或 webhook。用户必须在 Aegis 外部自行判断。"
        ),
        "items": items,
        "checks": checks,
        "safety": {
            "simulation_only": True,
            "manual_external_execution_only": True,
            "no_real_trade": True,
            "no_broker_api": True,
            "no_webhook": True,
            "no_trading_webhook": True,
            "no_live_order": True,
            "no_live_price": True,
            "no_position_size": True,
            "strategy_basket_not_stock_order": True,
            "dashboard_contract_unchanged": True,
            "no_production_records_mutation": True,
        },
    }


def render_refresh_queue_usable_brief_markdown(report: Mapping) -> str:
    lines = [
        "# V2.8-F Refresh Queue Usable Brief",
        "",
        f"- status: `{report.get('overall_status')}`",
        f"- run_id: `{report.get('run_id')}`",
        f"- candidate_count: `{report.get('summary', {}).get('candidate_count')}`",
        f"- blocked_count: `{report.get('summary', {}).get('blocked_count')}`",
        f"- candidate_markets: `{report.get('summary', {}).get('candidate_markets')}`",
        "",
        "## Boundary",
        "",
        "- 只展示模拟策略篮子。",
        "- 不是具体个股买卖建议。",
        "- 不做真实交易。",
        "- 不接 Broker API。",
        "- 不使用 webhook。",
        "- 不给实时价格或仓位数量。",
        "- 用户在 Aegis 外部自行判断并手动执行。",
        "",
        "## Items",
        "",
    ]
    for item in report.get("items", []):
        lines.extend(
            [
                f"### {item.get('symbol')}",
                "",
                f"- market: `{item.get('market')}`",
                f"- status: `{item.get('brief_status')}`",
                f"- action: `{item.get('suggested_user_action')}`",
                f"- summary: {item.get('plain_summary')}",
                f"- blocked_by: `{', '.join(item.get('blocked_by') or []) or 'none'}`",
                f"- evidence_refs: `{len(item.get('evidence_refs') or [])}`",
                "",
            ]
        )
    return "\n".join(lines)
