"""Paper Trading pure metric functions — Phase 6 §5.3.

Deliberately pure and dependency-free (no I/O, no service state) so they can
be unit-tested in isolation. Returns are decimals, e.g. `0.052` for `+5.2%`.
No annualized/Sharpe/Sortino metrics in P0 (explicitly out of scope per
PHASE6 doc §5.3) — just simple point-to-point and drawdown arithmetic.

Every function returns `None` on missing/invalid input rather than raising
or fabricating a number — consistent with the project-wide "no fabricated
data" rule (Master Spec §4/§16.1).
"""

from __future__ import annotations

from typing import Optional, Sequence


def compute_return(entry_price: Optional[float], current_price: Optional[float]) -> Optional[float]:
    """(current - entry) / entry, or None if either input is missing/invalid."""
    if entry_price is None or current_price is None:
        return None
    try:
        entry = float(entry_price)
        current = float(current_price)
    except (TypeError, ValueError):
        return None
    if entry == 0:
        return None
    return (current - entry) / entry


def compute_max_drawdown(price_series: Optional[Sequence[Optional[float]]]) -> Optional[float]:
    """Largest peak-to-trough decline across `price_series`, as a negative
    decimal (or 0.0 if the series never declines from its running peak).
    None entries are skipped. Returns None if there is no usable price."""
    if not price_series:
        return None
    prices = [float(p) for p in price_series if p is not None]
    if not prices:
        return None

    peak = prices[0]
    max_dd = 0.0
    for price in prices:
        if price > peak:
            peak = price
        if peak > 0:
            drawdown = (price - peak) / peak
            if drawdown < max_dd:
                max_dd = drawdown
    return max_dd


def compute_horizon_return(entry_price: Optional[float], horizon_price: Optional[float]) -> Optional[float]:
    """Same arithmetic as `compute_return` — kept as a separate named
    function per PHASE6 doc §5.3 so call sites read as "the return at this
    specific horizon" rather than a generic point-to-point return."""
    return compute_return(entry_price, horizon_price)
