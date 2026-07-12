"""Refresh the daily action packet after Tushare-backed Suggestion Gate.

V2.11-E overlays V2.11-D blocked A-share strategy evidence onto the existing
simulation action packet. Any focus item whose strategy was blocked by the
Tushare-backed gate is removed from `today_focus` and represented in
`do_not_use` instead.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping

from aegis.paper.simulation_action_packet import (
    build_simulation_action_packet,
    render_simulation_action_packet_markdown,
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _blocked_strategy_ids(gate_report: Mapping[str, Any]) -> set[str]:
    return {
        str(item.get("strategy_id"))
        for item in gate_report.get("suggestions", []) or []
        if item.get("action") == "blocked"
    }


def _gate_blocked_actions(gate_report: Mapping[str, Any]) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    for item in gate_report.get("suggestions", []) or []:
        if item.get("action") != "blocked":
            continue
        actions.append(
            {
                "symbol": item.get("symbol"),
                "market": item.get("market"),
                "strategy_id": item.get("strategy_id"),
                "action_type": "do_not_use_for_entry",
                "blocked_by": list(item.get("blocked_by") or []),
                "why": list(item.get("reasons") or [])[:6],
                "risk_warnings": list(item.get("risk_warnings") or [])[:6],
                "source_gate": "V2.11-D Tushare-Backed A-Share Suggestion Gate Refresh",
                "evidence_refs": list(item.get("evidence_refs") or []),
                "simulation_only": True,
            }
        )
    return actions


def _dedupe_blocked(actions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[str | None, str | None]] = set()
    deduped: list[dict[str, Any]] = []
    for item in actions:
        key = (item.get("strategy_id"), item.get("symbol"))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def build_action_packet_after_tushare_gate(
    *,
    current_brief: Mapping[str, Any],
    api_backed_brief: Mapping[str, Any],
    tushare_gate_report: Mapping[str, Any],
    run_id: str,
    command: str | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    """Build a user-facing packet with V2.11-D A-share blocks applied."""

    base_packet = build_simulation_action_packet(
        current_brief=current_brief,
        api_backed_brief=api_backed_brief,
        run_id=run_id,
        command=command,
        generated_at=generated_at,
    )
    blocked_strategy_ids = _blocked_strategy_ids(tushare_gate_report)
    original_focus = list(base_packet.get("today_focus") or [])
    filtered_focus = [
        item for item in original_focus if str(item.get("strategy_id")) not in blocked_strategy_ids
    ]
    removed_focus = [
        item for item in original_focus if str(item.get("strategy_id")) in blocked_strategy_ids
    ]
    blocked_actions = _dedupe_blocked(
        list(base_packet.get("do_not_use") or []) + _gate_blocked_actions(tushare_gate_report)
    )
    candidate_markets = sorted({str(item.get("market")) for item in filtered_focus if item.get("market")})
    blocked_markets = sorted({str(item.get("market")) for item in blocked_actions if item.get("market")})

    checks = {
        "base_packet_pass": base_packet.get("overall_status") == "PASS",
        "tushare_gate_pass": tushare_gate_report.get("overall_status") == "PASS",
        "tushare_gate_is_v2_11_d": tushare_gate_report.get("acceptance_target")
        == "V2.11-D Tushare-Backed A-Share Suggestion Gate Refresh",
        "blocked_strategy_ids_present": bool(blocked_strategy_ids),
        "blocked_a_share_gate_visible": any(item.get("source_gate") for item in blocked_actions),
        "blocked_a_strategies_removed_from_focus": all(
            str(item.get("strategy_id")) not in blocked_strategy_ids for item in filtered_focus
        ),
        "removed_focus_recorded": bool(removed_focus),
        "non_a_focus_still_visible": {"H", "US"}.issubset({str(item.get("market")) for item in filtered_focus}),
        "a_share_blocked_visible": "A" in blocked_markets,
        "no_allowed_a_focus_from_blocked_strategy": not any(
            item.get("market") == "A" and str(item.get("strategy_id")) in blocked_strategy_ids
            for item in filtered_focus
        ),
        "every_focus_item_simulation_only": all(item.get("simulation_only") is True for item in filtered_focus),
        "manual_external_execution_only": all(
            item.get("manual_external_execution_only") is True for item in filtered_focus
        ),
        "every_blocked_item_simulation_only": all(item.get("simulation_only") is True for item in blocked_actions),
        "no_live_price": all("live_price" not in item for item in filtered_focus),
        "no_position_size": all("position_size" not in item for item in filtered_focus),
        "no_order_instruction": all("order_instruction" not in item for item in filtered_focus),
        "source_production_records_not_written": base_packet.get("production_records_written") is False
        and tushare_gate_report.get("production_records_written") is False,
        "dashboard_contract_unchanged": base_packet.get("dashboard_contract_changed") is False
        and tushare_gate_report.get("dashboard_contract_changed") is False,
        "network_not_used": base_packet.get("network_used") is False
        and tushare_gate_report.get("network_used") is False,
    }

    packet = {
        **base_packet,
        "overall_status": "PASS" if all(checks.values()) else "FAIL",
        "acceptance_target": "V2.11-E Current Action Packet After Tushare Gate",
        "packet_type": "current_action_packet_after_tushare_gate",
        "run_id": run_id,
        "generated_at": generated_at or _now_iso(),
        "command": command,
        "today_focus": filtered_focus,
        "do_not_use": blocked_actions,
        "removed_focus_due_to_tushare_gate": removed_focus,
        "summary": {
            **dict(base_packet.get("summary") or {}),
            "today_focus_count": len(filtered_focus),
            "blocked_count": len(blocked_actions),
            "candidate_markets": candidate_markets,
            "blocked_markets": blocked_markets,
            "removed_focus_count": len(removed_focus),
            "removed_focus_symbols": [item.get("symbol") for item in removed_focus],
            "tushare_gate_allowed_count": (tushare_gate_report.get("summary") or {}).get("allowed_count"),
            "tushare_gate_blocked_count": (tushare_gate_report.get("summary") or {}).get("blocked_count"),
            "top_candidate_symbols": [item.get("symbol") for item in filtered_focus],
        },
        "daily_answer": {
            **dict(base_packet.get("daily_answer") or {}),
            "tushare_gate_status": (
                "Tushare A股真实历史沙盘后的 Suggestion Gate 已阻断失败 A股策略；"
                "相关 A股不进入 today_focus，只进入 do_not_use。"
            ),
        },
        "checks": checks,
        "safety": {
            **dict(base_packet.get("safety") or {}),
            "tushare_blocked_a_share_strategies_not_in_focus": True,
            "blocked_gate_evidence_visible": True,
            "no_real_trade": True,
            "no_broker_api": True,
            "no_trading_webhook": True,
            "no_order_placement": True,
            "no_live_price": True,
            "no_position_size": True,
            "no_production_records_mutation": True,
            "no_strategy_mutation": True,
            "dashboard_contract_unchanged": True,
        },
    }
    return packet


def render_action_packet_after_tushare_gate_markdown(packet: Mapping[str, Any]) -> str:
    return render_simulation_action_packet_markdown(packet)
