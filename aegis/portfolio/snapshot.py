"""Read-only portfolio snapshot building for V2.0-A.

This module aggregates manually supplied holdings and cash into a portfolio
view. It never connects to a broker, never places orders, and never treats
user-submitted external execution facts as permission to trade.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from aegis.models.holding import Holding
from aegis.models.portfolio_snapshot import PortfolioSnapshot


@dataclass(frozen=True)
class RiskBudget:
    max_exposure_pct: float = 0.8
    max_single_position_pct: float = 0.35


def _round(value: float | None, digits: int = 6) -> float | None:
    if value is None:
        return None
    return round(value, digits)


def _holding_value(holding: Holding) -> float:
    if holding.market_value is not None:
        return holding.market_value
    if holding.current_price is not None:
        return holding.current_price * holding.shares
    return holding.avg_cost * holding.shares


def _snapshot_id(date: str) -> str:
    return f"psnap_{date.replace('-', '')}_v2_0_a"


def build_portfolio_snapshot(
    *,
    holdings: list[Holding],
    date: str,
    cash: float,
    risk_budget: RiskBudget | None = None,
) -> dict[str, Any]:
    """Build a hashable portfolio snapshot report from local inputs."""
    risk_budget = risk_budget or RiskBudget()
    open_holdings = [holding for holding in holdings if holding.status == "open"]

    holding_rows: list[dict[str, Any]] = []
    total_cost = 0.0
    total_market_value = 0.0
    market_values: dict[str, float] = {}
    sector_values: dict[str, float] = {}

    for holding in open_holdings:
        cost_basis = holding.avg_cost * holding.shares
        market_value = _holding_value(holding)
        total_cost += cost_basis
        total_market_value += market_value
        market_values[holding.market] = market_values.get(holding.market, 0.0) + market_value
        sector_values["UNKNOWN"] = sector_values.get("UNKNOWN", 0.0) + market_value
        holding_rows.append(
            {
                "holding_id": holding.holding_id,
                "symbol": holding.symbol,
                "name": holding.name,
                "market": holding.market,
                "shares": holding.shares,
                "avg_cost": holding.avg_cost,
                "current_price": holding.current_price,
                "cost_basis": _round(cost_basis),
                "market_value": _round(market_value),
                "position_pct": None,
                "data_quality": "priced" if holding.current_price is not None or holding.market_value is not None else "cost_basis_fallback",
                "source": "manual_holding_record",
            }
        )

    portfolio_value = total_market_value + cash
    exposure_pct = total_market_value / portfolio_value if portfolio_value > 0 else 0.0
    blockers: list[str] = []
    if exposure_pct > risk_budget.max_exposure_pct:
        blockers.append("exposure_above_budget")

    for row in holding_rows:
        position_pct = (row["market_value"] or 0.0) / portfolio_value if portfolio_value > 0 else 0.0
        row["position_pct"] = _round(position_pct)
        if position_pct > risk_budget.max_single_position_pct:
            blockers.append(f"single_position_above_budget:{row['symbol']}")

    if exposure_pct > risk_budget.max_exposure_pct:
        risk_level = "high"
    elif exposure_pct > risk_budget.max_exposure_pct * 0.75:
        risk_level = "medium"
    else:
        risk_level = "low"

    market_allocation = {
        market: _round(value / portfolio_value if portfolio_value > 0 else 0.0)
        for market, value in sorted(market_values.items())
    }
    sector_allocation = {
        sector: _round(value / portfolio_value if portfolio_value > 0 else 0.0)
        for sector, value in sorted(sector_values.items())
    }
    unrealized_pnl = total_market_value - total_cost
    summary = (
        f"{len(open_holdings)} open holdings, exposure "
        f"{_round(exposure_pct * 100, 2)}%, risk_level={risk_level}."
    )
    snapshot = PortfolioSnapshot(
        snapshot_id=_snapshot_id(date),
        date=date,
        total_cost=_round(total_cost, 2) or 0.0,
        total_market_value=_round(total_market_value, 2),
        cash=_round(cash, 2),
        exposure_pct=_round(exposure_pct),
        market_allocation=market_allocation,
        sector_allocation=sector_allocation,
        unrealized_pnl=_round(unrealized_pnl, 2),
        risk_level=risk_level,
        summary=summary,
    )
    return {
        "portfolio_snapshot": snapshot.model_dump(),
        "holdings": holding_rows,
        "cash": {
            "amount": _round(cash, 2),
            "source": "manual_cash_record",
        },
        "risk_budget": {
            "max_exposure_pct": risk_budget.max_exposure_pct,
            "max_single_position_pct": risk_budget.max_single_position_pct,
        },
        "risk": {
            "level": risk_level,
            "blockers": sorted(set(blockers)),
        },
        "safety": {
            "read_only": True,
            "simulation_only": True,
            "no_real_trade": True,
            "no_broker_api": True,
            "no_webhook": True,
            "no_secrets": True,
            "manual_external_execution_only": True,
            "user_submitted_execution_facts_only": True,
        },
    }


def render_portfolio_snapshot_markdown(report: dict[str, Any]) -> str:
    snapshot = report["portfolio_snapshot"]
    lines = [
        "# V2.0-A Portfolio Snapshot",
        "",
        f"- snapshot_id: `{snapshot['snapshot_id']}`",
        f"- date: `{snapshot['date']}`",
        f"- total_cost: `{snapshot['total_cost']}`",
        f"- total_market_value: `{snapshot['total_market_value']}`",
        f"- cash: `{snapshot['cash']}`",
        f"- exposure_pct: `{snapshot['exposure_pct']}`",
        f"- risk_level: `{snapshot['risk_level']}`",
        f"- blockers: `{', '.join(report['risk']['blockers']) or 'none'}`",
        "",
        "## Holdings",
        "",
    ]
    for holding in report["holdings"]:
        lines.append(
            "- "
            f"{holding['symbol']} "
            f"market_value=`{holding['market_value']}` "
            f"position_pct=`{holding['position_pct']}` "
            f"data_quality=`{holding['data_quality']}`"
        )
    lines.extend(
        [
            "",
            "## Safety",
            "",
            "- Simulation only.",
            "- No real trade.",
            "- No broker API.",
            "- No webhook.",
            "- User-submitted external execution facts are evidence inputs only.",
            "",
        ]
    )
    return "\n".join(lines)
