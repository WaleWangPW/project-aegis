"""Backtest metrics — Phase 7 §5.5/§9.4.

Pure aggregation functions over a `list[BacktestResult]`. No Sharpe/
Sortino, no ML, no composite/weighted scoring — simple counts and
averages, same spirit as `aegis/paper/metrics.py`/`aegis/review/metrics.py`
(Phase 6). Every function returns an honest `None`/`0`/empty dict when
there is nothing to aggregate, never a fabricated number.
"""

from __future__ import annotations

from typing import Optional, Sequence

from aegis.backtest.models import BacktestResult

_HORIZON_KEYS = ("5d", "10d", "20d", "40d")


def compute_status_counts(results: Sequence[BacktestResult]) -> dict[str, int]:
    counts = {"Watch": 0, "Ready": 0, "Action": 0, "Exit": 0}
    for result in results:
        for rec in result.recommendations:
            status = rec.get("status")
            if status in counts:
                counts[status] += 1
    return counts


def _action_recommendation_ids(results: Sequence[BacktestResult]) -> set[str]:
    ids: set[str] = set()
    for result in results:
        for rec in result.recommendations:
            if rec.get("status") == "Action":
                ids.add(rec.get("recommendation_id"))
    return ids


def compute_action_success_rate(results: Sequence[BacktestResult], horizon_key: str) -> Optional[float]:
    """Fraction of Action-status recommendations with a positive return at
    `horizon_key` (e.g. "5d"), counted only over recommendations where that
    horizon actually resolved (not `None`)."""
    action_ids = _action_recommendation_ids(results)
    returns: list[float] = []
    for result in results:
        for rec_id, forward in result.forward_returns.items():
            if rec_id not in action_ids:
                continue
            value = forward.get(horizon_key)
            if value is not None:
                returns.append(value)
    if not returns:
        return None
    return sum(1 for v in returns if v > 0) / len(returns)


def compute_average_return_by_horizon(results: Sequence[BacktestResult]) -> dict[str, Optional[float]]:
    averages: dict[str, Optional[float]] = {}
    for horizon_key in _HORIZON_KEYS:
        values = [
            forward.get(horizon_key)
            for result in results
            for forward in result.forward_returns.values()
            if forward.get(horizon_key) is not None
        ]
        averages[horizon_key] = sum(values) / len(values) if values else None
    return averages


def compute_max_drawdown_summary(results: Sequence[BacktestResult]) -> dict:
    drawdowns = [
        forward.get("max_drawdown")
        for result in results
        for forward in result.forward_returns.values()
        if forward.get("max_drawdown") is not None
    ]
    if not drawdowns:
        return {"worst": None, "count": 0}
    return {"worst": min(drawdowns), "count": len(drawdowns)}


def compute_market_breakdown(results: Sequence[BacktestResult]) -> dict:
    breakdown: dict[str, dict] = {}
    for result in results:
        for rec in result.recommendations:
            market = rec.get("market", "未知")
            entry = breakdown.setdefault(market, {"count": 0, "action_count": 0})
            entry["count"] += 1
            if rec.get("status") == "Action":
                entry["action_count"] += 1
    return breakdown


def compute_sector_breakdown(results: Sequence[BacktestResult]) -> dict:
    breakdown: dict[str, dict] = {}
    for result in results:
        for rec in result.recommendations:
            sector = rec.get("sector") or "未知行业"
            entry = breakdown.setdefault(sector, {"count": 0, "action_count": 0})
            entry["count"] += 1
            if rec.get("status") == "Action":
                entry["action_count"] += 1
    return breakdown


def compute_data_gap_count(results: Sequence[BacktestResult]) -> int:
    return sum(len(result.data_gaps) for result in results)


def compute_no_future_data_violations(results: Sequence[BacktestResult]) -> int:
    return sum(result.no_future_data_violations for result in results)
