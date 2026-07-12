"""Pure date-arithmetic helpers over a known set of trading days for one
market — P1A §2.2.

No provider/cache/fallback logic here — that is `TradingCalendarService`'s
job. Operates on plain "YYYY-MM-DD" strings only, consistent with every
other date convention in this codebase. `trading_days` is always a
sorted, de-duplicated list — callers normalize via
`normalize_trading_days` first.
"""

from __future__ import annotations

from typing import Iterable, Optional


def normalize_trading_days(days: Iterable[str]) -> list[str]:
    return sorted(set(days))


def is_trading_day(date: str, trading_days: list[str]) -> bool:
    return date in trading_days


def next_trading_day(date: str, trading_days: list[str]) -> Optional[str]:
    for day in trading_days:
        if day > date:
            return day
    return None


def previous_trading_day(date: str, trading_days: list[str]) -> Optional[str]:
    for day in reversed(trading_days):
        if day < date:
            return day
    return None


def add_n_trading_days(date: str, n: int, trading_days: list[str]) -> Optional[str]:
    """`n` may be positive, negative, or zero.

    `n == 0` returns `date` itself only if `date` is a trading day,
    `None` otherwise (there is no meaningful "0th trading day" from a
    non-trading date).

    `n > 0` counts forward from (but not including) `date` — this holds
    even when `date` itself is not a trading day, consistent with
    `next_trading_day`'s own semantics: "add 1 trading day" from a
    non-trading date returns the next trading day after it.

    `n < 0` counts backward from (but not including) `date`, symmetric
    with the forward case.

    Returns `None` if `trading_days` doesn't contain enough days in the
    requested direction to satisfy `n` — never a guessed/extrapolated
    date.
    """
    if n == 0:
        return date if date in trading_days else None
    if n > 0:
        candidates = [day for day in trading_days if day > date]
        if len(candidates) < n:
            return None
        return candidates[n - 1]
    candidates = [day for day in reversed(trading_days) if day < date]
    if len(candidates) < abs(n):
        return None
    return candidates[abs(n) - 1]


def trading_days_in_range(start: str, end: str, trading_days: list[str]) -> list[str]:
    return [day for day in trading_days if start <= day <= end]
