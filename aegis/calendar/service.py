"""TradingCalendarService — P1A §2.2.

Answers trading-day questions (`is_trading_day` / `next_trading_day` /
`previous_trading_day` / `add_n_trading_days` / `trading_days_in_range`)
for A/H/US markets separately. Resolution order per market:

1. `TradingCalendarRepository` cache (`data/cache/calendar/{market}/
   trading_calendar.csv`), if it already holds trading days.
2. The wrapped provider's `get_trading_calendar` (real `TushareAdapter` or
   a fake, duck-typed), which — on success — is written back into the
   repository cache for next time.
3. A conservative Mon-Fri fallback (`_weekday_fallback`), used ONLY when
   `allow_fallback=True` was passed at construction time. This is NOT
   exchange-confirmed (no holiday awareness at all) and is always marked
   `source="fallback"` / `data_quality.status="partial"` with an explicit
   warning — never presented as real calendar data.
4. If none of the above are available and fallback is disabled, results
   report `source="unknown"` / `data_quality.status="unknown"` and an
   "error"-severity `DataGap` is recorded — never a guessed date.

Every provider/fallback miss is recorded via an injected `DataGapRegistry`
when one is supplied, same convention as every other data-access module
in this project.

This service does not alter `DecisionEngine`, `PaperTradeService`, or
`TimeTravelEngine` — see this module's package docstring
(`aegis/calendar/__init__.py`) for why wiring it into those consumers is
explicitly deferred.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Optional

import pandas as pd

from aegis.calendar.market_calendar import (
    add_n_trading_days as _add_n_trading_days,
    is_trading_day as _is_trading_day,
    next_trading_day as _next_trading_day,
    normalize_trading_days,
    previous_trading_day as _previous_trading_day,
    trading_days_in_range as _trading_days_in_range,
)
from aegis.calendar.repository import TradingCalendarRepository
from aegis.data.gaps import DataGapRegistry
from aegis.data.providers import ProviderError
from aegis.utils.dates import to_compact

_WINDOW_DAYS = 120  # generous lookback/lookahead window so add/next/prev have enough room


def _weekday_fallback(start: str, end: str) -> list[str]:
    """Conservative Mon-Fri fallback — NOT exchange-confirmed, no holiday
    awareness. Only ever used when explicitly enabled and no real
    calendar data exists."""
    start_dt = datetime.strptime(start, "%Y-%m-%d")
    end_dt = datetime.strptime(end, "%Y-%m-%d")
    days: list[str] = []
    current = start_dt
    while current <= end_dt:
        if current.weekday() < 5:
            days.append(current.strftime("%Y-%m-%d"))
        current += timedelta(days=1)
    return days


def _to_dashed(compact: str) -> str:
    return f"{compact[0:4]}-{compact[4:6]}-{compact[6:8]}"


class TradingCalendarService:
    def __init__(
        self,
        *,
        provider: Optional[Any] = None,
        repository: Optional[TradingCalendarRepository] = None,
        gaps: Optional[DataGapRegistry] = None,
        allow_fallback: bool = False,
    ):
        self.provider = provider
        self.repository = repository
        self.gaps = gaps
        self.allow_fallback = allow_fallback
        self._cache: dict[str, tuple[list[str], str]] = {}

    # -- resolution ---------------------------------------------------

    def _window(self, date: str) -> tuple[str, str]:
        center = datetime.strptime(date, "%Y-%m-%d")
        start = (center - timedelta(days=_WINDOW_DAYS)).strftime("%Y-%m-%d")
        end = (center + timedelta(days=_WINDOW_DAYS)).strftime("%Y-%m-%d")
        return start, end

    def _from_repository(self, market: str) -> Optional[list[str]]:
        if self.repository is None:
            return None
        cached_df = self.repository.read(market)
        if cached_df is None or cached_df.empty or "is_trading_day" not in cached_df.columns:
            return None
        open_days = cached_df.loc[cached_df["is_trading_day"].astype(int).astype(bool), "date"].astype(str).tolist()
        days = normalize_trading_days(open_days)
        return days or None

    def _from_provider(self, market: str, start: str, end: str) -> Optional[list[str]]:
        if self.provider is None:
            return None
        try:
            df = self.provider.get_trading_calendar(market, to_compact(start), to_compact(end))
        except (ProviderError, AttributeError) as exc:
            if self.gaps is not None:
                self.gaps.record_gap(
                    date=start,
                    market=market,
                    symbol=None,
                    provider="trading_calendar_service",
                    data_type="trading_calendar",
                    severity="warning",
                    message=f"provider trading calendar unavailable: {exc}",
                )
            return None

        if df is None or df.empty or "cal_date" not in df.columns or "is_open" not in df.columns:
            if self.gaps is not None:
                self.gaps.record_gap(
                    date=start,
                    market=market,
                    symbol=None,
                    provider="trading_calendar_service",
                    data_type="trading_calendar",
                    severity="warning",
                    message="provider returned no usable trading-calendar rows (missing cal_date/is_open).",
                )
            return None

        normalized = pd.DataFrame(
            {
                "date": [_to_dashed(str(d)) for d in df["cal_date"]],
                "is_trading_day": df["is_open"].astype(int),
            }
        )
        if self.repository is not None:
            self.repository.write(market, normalized)

        open_days = normalized.loc[normalized["is_trading_day"].astype(bool), "date"].tolist()
        return normalize_trading_days(open_days) or None

    def _load_trading_days(self, market: str, start: str, end: str) -> tuple[list[str], str]:
        if market in self._cache:
            return self._cache[market]

        days = self._from_repository(market)
        if days:
            result = (days, "cache")
            self._cache[market] = result
            return result

        days = self._from_provider(market, start, end)
        if days:
            result = (days, "tushare")
            self._cache[market] = result
            return result

        if self.allow_fallback:
            if self.gaps is not None:
                self.gaps.record_gap(
                    date=start,
                    market=market,
                    symbol=None,
                    provider="trading_calendar_service",
                    data_type="trading_calendar",
                    severity="warning",
                    message="using conservative Mon-Fri fallback calendar — NOT exchange-confirmed, no holiday awareness.",
                )
            result = (_weekday_fallback(start, end), "fallback")
            self._cache[market] = result
            return result

        if self.gaps is not None:
            self.gaps.record_gap(
                date=start,
                market=market,
                symbol=None,
                provider="trading_calendar_service",
                data_type="trading_calendar",
                severity="error",
                message="no trading calendar data available (no cache, no provider, fallback disabled).",
            )
        result: tuple[list[str], str] = ([], "unknown")
        self._cache[market] = result
        return result

    # -- result shaping (P1A §2.2 suggested object shape) -------------

    def _result(self, *, market: str, date: str, is_trading: bool, source: str) -> dict:
        if source in ("cache", "tushare"):
            status, warnings = "complete", []
        elif source == "fallback":
            status, warnings = "partial", ["Mon-Fri fallback calendar — not exchange-confirmed, no holiday awareness"]
        else:
            status, warnings = "unknown", ["no trading calendar data available"]
        return {
            "market": market,
            "date": date,
            "is_trading_day": is_trading,
            "source": source,
            "data_quality": {"status": status, "warnings": warnings},
        }

    # -- public API -----------------------------------------------------

    def is_trading_day(self, market: str, date: str) -> dict:
        start, end = self._window(date)
        days, source = self._load_trading_days(market, start, end)
        return self._result(market=market, date=date, is_trading=_is_trading_day(date, days), source=source)

    def next_trading_day(self, market: str, date: str) -> Optional[dict]:
        start, end = self._window(date)
        days, source = self._load_trading_days(market, start, end)
        nxt = _next_trading_day(date, days)
        if nxt is None:
            return None
        return self._result(market=market, date=nxt, is_trading=True, source=source)

    def previous_trading_day(self, market: str, date: str) -> Optional[dict]:
        start, end = self._window(date)
        days, source = self._load_trading_days(market, start, end)
        prev = _previous_trading_day(date, days)
        if prev is None:
            return None
        return self._result(market=market, date=prev, is_trading=True, source=source)

    def add_n_trading_days(self, market: str, date: str, n: int) -> Optional[dict]:
        start, end = self._window(date)
        days, source = self._load_trading_days(market, start, end)
        target = _add_n_trading_days(date, n, days)
        if target is None:
            return None
        return self._result(market=market, date=target, is_trading=True, source=source)

    def trading_days_in_range(self, market: str, start: str, end: str) -> list[str]:
        days, _source = self._load_trading_days(market, start, end)
        return _trading_days_in_range(start, end, days)
