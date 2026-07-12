"""MarketDataService — Master Spec §10.1 / Phase 1 §4.7.

Retrieves and caches raw market data. Explicitly NOT MarketSnapshot and NOT
Market Regime analysis (those read this service's output in Phase 2+, they
do not live here). On provider failure this service records a DataGap and
returns an empty/None result — it never raises out to the caller and never
fabricates data.

P1B.1: accepts either a single `provider` (a `MarketDataProvider`, e.g.
`TushareAdapter`) or a `provider_router` (`aegis.data.provider_router.ProviderRouter`).
Both expose the identical duck-typed method shape
(`get_daily_bars`/`get_index_bars`/...), so this service's own logic
below never needs to know which one it was given — routing (if any)
already happened before a result reached here. Existing callers that
pass `provider=` are completely unaffected.

P1B.3: when `self.provider` is a `ProviderRouter` (real config-driven
routing, per `config/providers.yaml`), `get_daily_bars_cached`/
`get_index_bars_cached` transparently consume its per-`(market,
data_type)` route — A stays Tushare-first, H/US go through the
`yahoo_finance` secondary route (confirmed real via P1B.2's local live
validation) — with zero branching added here, since the router already
duck-types identically to a plain provider. What P1B.3 actually adds:
- `DataGap` records now label *which* route/provider actually failed
  (via `ProviderRouter.route_name_for`, a non-raising diagnostic lookup)
  instead of a generic `"market_data_service"` string, and note the
  failing exception's type — so a H/US route failure is distinguishable
  from an A股 Tushare failure in `data/records/data_gaps.jsonl` without
  guessing.
- `consumer_impact` is now populated on every recorded gap, describing
  what a missing/empty result means for downstream code (still just
  diagnostic metadata — this service itself makes no decision based on
  it).
- Cache-key separation (`market`/`data_type`/`symbol`) was already
  correct in `DataCache.get_path` (P0) — P1B.3 adds tests proving H/US
  Yahoo results and A股 Tushare results never collide in the cache, but
  changes no cache logic.
This service still never constructs a `ProviderRouter`/`TushareAdapter`/
`YahooFinanceAdapter` itself — callers (or their own factories) decide
what `provider`/`provider_router` to pass in, exactly as before.
"""

from __future__ import annotations

from typing import Any, Optional

import pandas as pd

from aegis.data.cache import DataCache
from aegis.data.gaps import DataGapRegistry
from aegis.data.providers import MarketDataProvider, ProviderError

_DEFAULT_GAP_PROVIDER_LABEL = "market_data_service"


class MarketDataService:
    def __init__(
        self,
        provider: Optional[MarketDataProvider] = None,
        provider_router: Optional[Any] = None,
        cache: Optional[DataCache] = None,
        gaps: Optional[DataGapRegistry] = None,
    ):
        if provider is None and provider_router is None:
            raise ValueError("MarketDataService requires either `provider` or `provider_router`.")
        # Both are duck-typed identically (get_daily_bars/get_index_bars/
        # ...), so a router can simply stand in for `self.provider` below
        # without any branching logic.
        self.provider = provider if provider is not None else provider_router
        self.cache = cache
        self.gaps = gaps

    def _route_label(self, market: str, data_type: str) -> str:
        """Best-effort, non-raising description of which provider/route
        this call would use — diagnostic labeling only, never control
        flow. Falls back to a generic label when `self.provider` is a
        plain (non-router) provider that has no `route_name_for`."""
        describe = getattr(self.provider, "route_name_for", None)
        if callable(describe):
            try:
                name = describe(market, data_type)
            except Exception:  # noqa: BLE001 - diagnostic label only, must never raise
                name = None
            if name:
                return name
        return _DEFAULT_GAP_PROVIDER_LABEL

    def _record_gap(self, *, date: str, market: Optional[str], symbol: Optional[str],
                     data_type: str, message: str, severity: str = "warning",
                     provider: Optional[str] = None,
                     consumer_impact: Optional[list[str]] = None) -> None:
        if self.gaps is None:
            return
        self.gaps.record_gap(
            date=date,
            market=market,
            symbol=symbol,
            provider=provider or _DEFAULT_GAP_PROVIDER_LABEL,
            data_type=data_type,
            severity=severity,
            message=message,
            consumer_impact=consumer_impact or [],
        )

    def get_daily_bars_cached(self, symbol: str, market: str, start: str, end: str) -> pd.DataFrame:
        key = f"{symbol}_{start}_{end}"
        if self.cache is not None and self.cache.exists(market, "daily_bars", key):
            cached = self.cache.read_dataframe(market, "daily_bars", key)
            if cached is not None:
                return cached

        route = self._route_label(market, "daily_bars")
        impact = [f"daily_bars unavailable for {symbol} ({market}) — any consumer receives empty data, not real bars"]

        try:
            df = self.provider.get_daily_bars(symbol, market, start, end)
        except ProviderError as exc:
            self._record_gap(
                date=end, market=market, symbol=symbol, data_type="daily_bars",
                message=f"{type(exc).__name__} via provider_route={route!r}: {exc}",
                provider=route, consumer_impact=impact,
            )
            return pd.DataFrame()

        if df is None or df.empty:
            self._record_gap(
                date=end, market=market, symbol=symbol, data_type="daily_bars",
                message=(
                    f"No daily bars returned for {symbol} ({market}) via provider_route={route!r} "
                    f"between {start} and {end}."
                ),
                provider=route, consumer_impact=impact,
            )
            return pd.DataFrame()

        if self.cache is not None:
            self.cache.write_dataframe(df, market, "daily_bars", key)
        return df

    def get_index_bars_cached(self, index_code: str, market: str, start: str, end: str) -> pd.DataFrame:
        key = f"{index_code}_{start}_{end}"
        if self.cache is not None and self.cache.exists(market, "index_bars", key):
            cached = self.cache.read_dataframe(market, "index_bars", key)
            if cached is not None:
                return cached

        route = self._route_label(market, "index_bars")
        impact = [
            f"index_bars unavailable for {index_code} ({market}) — market regime/relative-strength "
            "consumers receive empty data, not real bars"
        ]

        try:
            df = self.provider.get_index_bars(index_code, market, start, end)
        except ProviderError as exc:
            self._record_gap(
                date=end, market=market, symbol=index_code, data_type="index_bars",
                message=f"{type(exc).__name__} via provider_route={route!r}: {exc}",
                provider=route, consumer_impact=impact,
            )
            return pd.DataFrame()

        if df is None or df.empty:
            self._record_gap(
                date=end, market=market, symbol=index_code, data_type="index_bars",
                message=(
                    f"No index bars returned for {index_code} ({market}) via provider_route={route!r} "
                    f"between {start} and {end}."
                ),
                provider=route, consumer_impact=impact,
            )
            return pd.DataFrame()

        if self.cache is not None:
            self.cache.write_dataframe(df, market, "index_bars", key)
        return df

    def get_latest_close(self, symbol: str, market: str, as_of: str) -> Optional[float]:
        df = self.get_daily_bars_cached(symbol, market, start=as_of, end=as_of)
        if df is None or df.empty or "close" not in df.columns:
            return None
        try:
            return float(df.iloc[0]["close"])
        except (ValueError, TypeError, IndexError, KeyError):
            return None
