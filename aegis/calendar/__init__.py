"""Trading Calendar foundation — P1A §2.2.

A standalone `TradingCalendarService` answering is-trading-day/next/
previous/add-N-trading-days/list-range questions for A/H/US markets
separately. Prefers cached/provider-sourced real calendar data; falls
back to a conservative Mon-Fri assumption only when explicitly enabled
via `allow_fallback=True`, always marked `source="fallback"` /
`data_quality.status="partial"` — never presented as exchange-confirmed.

This module does not alter `DecisionEngine`, `PaperTradeService`, or
`TimeTravelEngine` — it is a foundation service only. Wiring it into
those consumers' forward-return horizon math is left for a future,
separately-approved task (see `docs/HANDOFF.md`'s known-gaps section).
"""

from aegis.calendar.market_calendar import (
    add_n_trading_days,
    is_trading_day,
    next_trading_day,
    normalize_trading_days,
    previous_trading_day,
    trading_days_in_range,
)
from aegis.calendar.repository import TradingCalendarRepository
from aegis.calendar.service import TradingCalendarService

__all__ = [
    "add_n_trading_days",
    "is_trading_day",
    "next_trading_day",
    "normalize_trading_days",
    "previous_trading_day",
    "trading_days_in_range",
    "TradingCalendarRepository",
    "TradingCalendarService",
]
