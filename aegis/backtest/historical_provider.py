"""HistoricalDataProvider — Phase 7 §5.2.

Wraps any existing `MarketDataProvider`-shaped object (real `TushareAdapter`
or a test fake — duck-typed, same as every other provider consumer in this
codebase) and enforces point-in-time access during `stage="decision"`:
every read is capped to `freeze_date`, and the *served* rows are filtered
defensively even if the caller passes an uncapped `end` or the wrapped
provider ignores the `end` argument entirely. Nothing here ever fabricates
missing data — a capped/empty result is exactly that, never a guess.

An access log (`data_access_log`) records every call for testability, and
`violations` counts every case where a decision-stage request would have
served (or attempted to request) data beyond `freeze_date` — the single
number `TimeTravelEngine`/`scripts/run_backtest.py` surface as
`no_future_data_violations`.
"""

from __future__ import annotations

from typing import Any, Optional

import pandas as pd

from aegis.backtest.frozen_context import FrozenContext, FutureDataAccessError
from aegis.data.gaps import DataGapRegistry
from aegis.data.providers import ProviderError
from aegis.utils.dates import to_compact


def _max_trade_date(df: Optional[pd.DataFrame]) -> Optional[str]:
    if df is None or df.empty or "trade_date" not in df.columns:
        return None
    try:
        return str(df["trade_date"].astype(str).max())
    except (TypeError, ValueError):
        return None


class HistoricalDataProvider:
    def __init__(
        self,
        base_provider: Any,
        frozen_context: FrozenContext,
        gaps: Optional[DataGapRegistry] = None,
    ):
        self.base_provider = base_provider
        self.frozen_context = frozen_context
        self.gaps = gaps
        self.data_access_log: list[dict] = []
        self.violations: int = 0

    # -- stage control ---------------------------------------------------

    def enter_evaluation_stage(self) -> None:
        self.frozen_context = self.frozen_context.as_evaluation_stage()

    # -- logging -----------------------------------------------------------

    def _log(
        self,
        *,
        data_type: str,
        symbol: Optional[str],
        market: Optional[str],
        requested_end: Optional[str],
        served_max_date: Optional[str],
        violation: bool,
    ) -> None:
        self.data_access_log.append(
            {
                "stage": self.frozen_context.stage,
                "symbol": symbol,
                "market": market,
                "data_type": data_type,
                "requested_end": requested_end,
                "served_max_date": served_max_date,
                "violation": violation,
            }
        )
        if violation:
            self.violations += 1
            if self.gaps is not None:
                self.gaps.record_gap(
                    date=self.frozen_context.freeze_date,
                    market=market,
                    symbol=symbol,
                    provider="historical_data_provider",
                    data_type=data_type,
                    severity="error",
                    message=(
                        f"Decision-stage request for {data_type} would have served data beyond "
                        f"freeze_date={self.frozen_context.freeze_date} (requested_end={requested_end}, "
                        f"served_max_date={served_max_date}) — blocked, no future data leaked."
                    ),
                )

    # -- capped decision-stage reads ---------------------------------------

    def _capped_end(self, end: str) -> tuple[str, bool]:
        """Returns (capped_end, requested_beyond_freeze). Comparison is done
        on compact "YYYYMMDD" strings, the same convention `end` already
        arrives in from every existing caller (`lookback_range`/
        `to_compact`), so no reformatting of `end` itself is needed."""
        freeze_compact = to_compact(self.frozen_context.freeze_date)
        if end > freeze_compact:
            return freeze_compact, True
        return end, False

    def get_daily_bars(self, symbol: str, market: str, start: str, end: str) -> pd.DataFrame:
        if self.frozen_context.is_decision_stage():
            capped_end, requested_beyond = self._capped_end(end)
        else:
            capped_end, requested_beyond = end, False

        df = self.base_provider.get_daily_bars(symbol, market, start, capped_end)
        df, served_beyond = self._enforce_and_filter(df)
        served_max = _max_trade_date(df)
        self._log(
            data_type="daily_bars",
            symbol=symbol,
            market=market,
            requested_end=end,
            served_max_date=served_max,
            violation=self.frozen_context.is_decision_stage() and (requested_beyond or served_beyond),
        )
        return df

    def get_index_bars(self, index_code: str, market: str, start: str, end: str) -> pd.DataFrame:
        if self.frozen_context.is_decision_stage():
            capped_end, requested_beyond = self._capped_end(end)
        else:
            capped_end, requested_beyond = end, False

        df = self.base_provider.get_index_bars(index_code, market, start, capped_end)
        df, served_beyond = self._enforce_and_filter(df)
        served_max = _max_trade_date(df)
        self._log(
            data_type="index_bars",
            symbol=index_code,
            market=market,
            requested_end=end,
            served_max_date=served_max,
            violation=self.frozen_context.is_decision_stage() and (requested_beyond or served_beyond),
        )
        return df

    def _enforce_and_filter(self, df: Optional[pd.DataFrame]) -> tuple[pd.DataFrame, bool]:
        """Defense-in-depth: even if the wrapped provider ignored our capped
        `end`, never let a row past `freeze_date` actually get served
        during decision stage. Returns (filtered_df, served_beyond_before_filter)."""
        if df is None:
            return pd.DataFrame(), False
        if not self.frozen_context.is_decision_stage():
            return df, False
        if df.empty or "trade_date" not in df.columns:
            return df, False

        freeze_compact = to_compact(self.frozen_context.freeze_date)
        beyond_mask = df["trade_date"].astype(str) > freeze_compact
        served_beyond = bool(beyond_mask.any())
        if served_beyond:
            df = df[~beyond_mask]
        return df, served_beyond

    def get_stock_basic(self, market: str) -> pd.DataFrame:
        """Stock-list membership has no reliable per-row as-of date in this
        project (no historical universe-membership snapshots exist) — per
        PHASE7 doc §5.2, this returns the current list plus a DATA_GAP
        warning rather than blocking universe construction entirely."""
        try:
            df = self.base_provider.get_stock_basic(market)
        except ProviderError:
            df = pd.DataFrame()

        if self.gaps is not None:
            self.gaps.record_gap(
                date=self.frozen_context.freeze_date,
                market=market,
                symbol=None,
                provider="historical_data_provider",
                data_type="stock_basic",
                severity="info",
                message=(
                    "stock_basic has no historical as-of snapshot in this project — using the "
                    "current/base provider list as a best-effort universe for this freeze_date."
                ),
            )
        self._log(
            data_type="stock_basic",
            symbol=None,
            market=market,
            requested_end=None,
            served_max_date=None,
            violation=False,
        )
        return df if df is not None else pd.DataFrame()

    def get_sector_classification(self, market: str) -> pd.DataFrame:
        try:
            df = self.base_provider.get_sector_classification(market)
        except (ProviderError, AttributeError):
            df = None

        if df is None or df.empty:
            if self.gaps is not None:
                self.gaps.record_gap(
                    date=self.frozen_context.freeze_date,
                    market=market,
                    symbol=None,
                    provider="historical_data_provider",
                    data_type="sector_classification",
                    severity="warning",
                    message="No historical sector classification available for this freeze_date/market.",
                )
            df = pd.DataFrame()
        self._log(
            data_type="sector_classification",
            symbol=None,
            market=market,
            requested_end=None,
            served_max_date=None,
            violation=False,
        )
        return df

    def get_fundamentals(self, symbol: str, market: str, as_of: str) -> pd.DataFrame:
        """`as_of` is always the caller's own point-in-time date (the same
        pattern `scripts/run_pre_market.py`'s `_fetch_fundamentals` already
        uses — the live pipeline passes its own `date`, never a range). In
        decision stage this provider is only ever constructed with
        `as_of == freeze_date` by `TimeTravelEngine`, so the point-in-time
        boundary is enforced by construction; this method additionally caps
        `as_of` defensively in case a caller ever passes something later."""
        if self.frozen_context.is_decision_stage():
            freeze_compact = to_compact(self.frozen_context.freeze_date)
            as_of_compact = to_compact(as_of)
            requested_beyond = as_of_compact > freeze_compact
            effective_as_of = self.frozen_context.freeze_date if requested_beyond else as_of
        else:
            requested_beyond = False
            effective_as_of = as_of

        try:
            df = self.base_provider.get_fundamentals(symbol, market, effective_as_of)
        except (ProviderError, AttributeError):
            df = None

        self._log(
            data_type="fundamentals",
            symbol=symbol,
            market=market,
            requested_end=as_of,
            served_max_date=effective_as_of,
            violation=self.frozen_context.is_decision_stage() and requested_beyond,
        )
        return df if df is not None else pd.DataFrame()

    def get_trading_calendar(self, market: str, start: str, end: str) -> pd.DataFrame:
        if self.frozen_context.is_decision_stage():
            capped_end, requested_beyond = self._capped_end(end)
        else:
            capped_end, requested_beyond = end, False

        try:
            df = self.base_provider.get_trading_calendar(market, start, capped_end)
        except (ProviderError, AttributeError):
            df = None

        self._log(
            data_type="trading_calendar",
            symbol=None,
            market=market,
            requested_end=end,
            served_max_date=capped_end,
            violation=self.frozen_context.is_decision_stage() and requested_beyond,
        )
        return df if df is not None else pd.DataFrame()

    def get_future_bars_for_evaluation(self, symbol: str, market: str, start: str, end: str) -> pd.DataFrame:
        """The one deliberate escape hatch from the freeze — only usable
        once the context has switched to `stage="evaluation"` (i.e. after
        every recommendation for this freeze_date has already been
        finalized). Calling this during decision stage is a programming
        error, not a normal degrade-to-DataGap situation, so it raises
        `FutureDataAccessError` rather than silently returning anything."""
        if self.frozen_context.is_decision_stage():
            self._log(
                data_type="future_bars_for_evaluation",
                symbol=symbol,
                market=market,
                requested_end=end,
                served_max_date=None,
                violation=True,
            )
            raise FutureDataAccessError(
                f"get_future_bars_for_evaluation({symbol!r}, {market!r}) called during stage="
                f"'decision' (freeze_date={self.frozen_context.freeze_date}) — only allowed once "
                "the FrozenContext has switched to stage='evaluation'."
            )

        df = self.base_provider.get_daily_bars(symbol, market, start, end)
        served_max = _max_trade_date(df)
        self._log(
            data_type="future_bars_for_evaluation",
            symbol=symbol,
            market=market,
            requested_end=end,
            served_max_date=served_max,
            violation=False,
        )
        return df if df is not None else pd.DataFrame()
