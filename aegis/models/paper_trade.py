"""PaperTrade — Master Spec §8.8.

A simulated (paper) position tied back to a recommendation. Never a real
brokerage order (Master Spec §4, ADR-004).
Produced by: PaperTradeService (Phase 6).
Storage: data/records/paper_trades.jsonl.

Acceptance: a PaperTrade must not be created without a real entry_price —
no fabricated prices (Master Spec §16.1).
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel

from .common import Market

Direction = Literal["long", "short"]
TradeStatus = Literal["open", "closed"]
TradeResult = Literal["target_hit", "stopped_out", "expired", "invalidated", "still_open"]


class PaperTrade(BaseModel):
    paper_trade_id: str
    recommendation_id: str
    symbol: str
    market: Market
    direction: Direction
    entry_date: str
    entry_price: float
    virtual_position_size: float
    exit_date: Optional[str] = None
    exit_price: Optional[float] = None
    status: TradeStatus
    return_5d: Optional[float] = None
    return_10d: Optional[float] = None
    return_20d: Optional[float] = None
    return_40d: Optional[float] = None
    max_drawdown: Optional[float] = None
    result: Optional[TradeResult] = None
    exit_reason: Optional[str] = None
    created_at: str
    updated_at: str
