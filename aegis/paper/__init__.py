"""Paper Trading — Phase 6 §5.1-5.3.

Simulated (virtual) positions tied back to a `RecommendationRecord`. Never a
real brokerage order (Master Spec §4 / ADR-004) — no broker integration, no
real trading, no automatic order placement.
"""

from __future__ import annotations

from aegis.paper.metrics import compute_horizon_return, compute_max_drawdown, compute_return
from aegis.paper.repository import PaperTradeRepository
from aegis.paper.service import PaperTradeService

__all__ = [
    "PaperTradeRepository",
    "PaperTradeService",
    "compute_return",
    "compute_max_drawdown",
    "compute_horizon_return",
]
