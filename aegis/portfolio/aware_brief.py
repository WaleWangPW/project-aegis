"""Portfolio-aware recommendation explanations for V2.0-B.

This is a read-only explanation layer. It does not change recommendation
status, strategy thresholds, Dashboard Contract, or any trading behavior.
"""

from __future__ import annotations

from typing import Any

from aegis.models.recommendation import RecommendationRecord


def _holding_by_symbol(portfolio_report: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    return {
        (row.get("market"), row.get("symbol")): row
        for row in portfolio_report.get("holdings", [])
    }


def _portfolio_value(portfolio_report: dict[str, Any]) -> float:
    snapshot = portfolio_report.get("portfolio_snapshot", {})
    market_value = float(snapshot.get("total_market_value") or 0.0)
    cash = float(snapshot.get("cash") or 0.0)
    return market_value + cash


def _round(value: float, digits: int = 6) -> float:
    return round(value, digits)


def explain_recommendation_with_portfolio(
    *,
    recommendation: RecommendationRecord,
    portfolio_report: dict[str, Any],
    planned_position_value: float = 1000.0,
) -> dict[str, Any]:
    """Explain one recommendation against portfolio cash/exposure/risk budget."""
    snapshot = portfolio_report.get("portfolio_snapshot", {})
    risk_budget = portfolio_report.get("risk_budget", {})
    cash = float(portfolio_report.get("cash", {}).get("amount") or snapshot.get("cash") or 0.0)
    exposure_pct = float(snapshot.get("exposure_pct") or 0.0)
    max_exposure_pct = float(risk_budget.get("max_exposure_pct") or 0.8)
    max_single_position_pct = float(risk_budget.get("max_single_position_pct") or 0.35)
    portfolio_value = _portfolio_value(portfolio_report)
    holdings = _holding_by_symbol(portfolio_report)
    holding = holdings.get((recommendation.market, recommendation.symbol))

    blockers: list[str] = []
    evidence: list[str] = [
        f"cash={cash}",
        f"current_exposure_pct={_round(exposure_pct)}",
        f"max_exposure_pct={max_exposure_pct}",
        f"max_single_position_pct={max_single_position_pct}",
    ]
    if holding:
        evidence.append(f"existing_position_pct={holding.get('position_pct')}")
    else:
        evidence.append("existing_position_pct=0")

    if recommendation.status == "Exit":
        action = "exit_review_required"
        explanation = "Recommendation is Exit; portfolio context requires manual review of the existing position."
    elif recommendation.status == "Action":
        projected_exposure = (
            (float(snapshot.get("total_market_value") or 0.0) + planned_position_value) / portfolio_value
            if portfolio_value > 0
            else 0.0
        )
        evidence.append(f"planned_position_value={planned_position_value}")
        evidence.append(f"projected_exposure_pct={_round(projected_exposure)}")
        if cash < planned_position_value:
            blockers.append("insufficient_cash")
        if projected_exposure > max_exposure_pct:
            blockers.append("exposure_budget_exceeded")
        if holding and float(holding.get("position_pct") or 0.0) >= max_single_position_pct:
            blockers.append("single_position_budget_exceeded")
        if blockers:
            action = "wait_due_to_portfolio_risk"
            explanation = "Decision signal is Action, but portfolio cash/exposure/risk budget blocks adding exposure."
        else:
            action = "portfolio_allows_action"
            explanation = "Decision signal is Action and portfolio cash/exposure/risk budget allows a simulated entry."
    elif recommendation.status == "Ready":
        action = "ready_but_wait_for_trigger"
        explanation = "Recommendation is Ready; portfolio context is available, but this is not an entry order."
    elif holding:
        action = "hold"
        explanation = "Recommendation is Watch for an existing holding; portfolio context supports holding and monitoring."
    else:
        action = "wait"
        explanation = "Recommendation is Watch for a non-held symbol; portfolio context supports waiting."

    return {
        "recommendation_id": recommendation.recommendation_id,
        "symbol": recommendation.symbol,
        "market": recommendation.market,
        "recommendation_status": recommendation.status,
        "portfolio_action": action,
        "portfolio_blockers": sorted(set(blockers)),
        "explanation": explanation,
        "evidence": evidence,
        "safety": {
            "read_only": True,
            "simulation_only": True,
            "no_real_trade": True,
            "no_broker_api": True,
            "no_webhook": True,
            "no_strategy_mutation": True,
            "dashboard_contract_unchanged": True,
            "user_submitted_execution_facts_only": True,
        },
    }


def build_portfolio_aware_brief(
    *,
    recommendations: list[RecommendationRecord],
    portfolio_report: dict[str, Any],
    planned_position_value: float = 1000.0,
) -> dict[str, Any]:
    items = [
        explain_recommendation_with_portfolio(
            recommendation=rec,
            portfolio_report=portfolio_report,
            planned_position_value=planned_position_value,
        )
        for rec in recommendations
    ]
    action_counts: dict[str, int] = {}
    for item in items:
        action = item["portfolio_action"]
        action_counts[action] = action_counts.get(action, 0) + 1
    return {
        "brief_type": "portfolio_aware_daily_brief",
        "portfolio_snapshot_id": portfolio_report.get("portfolio_snapshot", {}).get("snapshot_id"),
        "recommendation_count": len(recommendations),
        "items": items,
        "action_counts": action_counts,
        "safety": {
            "read_only": True,
            "simulation_only": True,
            "no_real_trade": True,
            "no_broker_api": True,
            "no_webhook": True,
            "no_strategy_mutation": True,
            "dashboard_contract_unchanged": True,
        },
    }


def render_portfolio_aware_brief_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# V2.0-B Portfolio-Aware Daily Brief",
        "",
        f"- portfolio_snapshot_id: `{report.get('portfolio_snapshot_id')}`",
        f"- recommendation_count: `{report.get('recommendation_count')}`",
        f"- action_counts: `{report.get('action_counts')}`",
        "",
        "## Recommendations",
        "",
    ]
    for item in report.get("items", []):
        lines.extend(
            [
                f"### {item['symbol']} ({item['market']})",
                "",
                f"- recommendation_status: `{item['recommendation_status']}`",
                f"- portfolio_action: `{item['portfolio_action']}`",
                f"- blockers: `{', '.join(item['portfolio_blockers']) or 'none'}`",
                f"- explanation: {item['explanation']}",
                f"- evidence: `{'; '.join(item['evidence'])}`",
                "",
            ]
        )
    lines.extend(
        [
            "## Safety",
            "",
            "- Read-only explanation layer.",
            "- Simulation only.",
            "- No real trade.",
            "- No broker API.",
            "- Dashboard Contract unchanged.",
            "",
        ]
    )
    return "\n".join(lines)
