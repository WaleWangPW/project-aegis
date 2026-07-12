"""ProviderRouter — P1B.1 §6.1.

Routes each `(market, data_type)` request to a named provider instance,
per an explicit `config/providers.yaml`-shaped routing table — instead of
every consumer assuming a single Tushare-backed provider covers every
market and every data category (the assumption P1B.1 exists to remove).

Implements the same duck-typed `MarketDataProvider` method shape
(`get_daily_bars`/`get_index_bars`/`get_stock_basic`/`get_fundamentals`/
`get_sector_classification`/`get_trading_calendar`) as `TushareAdapter`
and `YahooFinanceAdapter`, so it is a drop-in replacement anywhere a
single provider was previously passed (`MarketDataService`,
`aegis.data.provider_diagnostics.run_checks_for_market`, etc.) — no
caller needs to know routing happened.

Hard rules (per the task spec):
- No silent fallback. A `(market, data_type)` pair with no configured
  route raises `ProviderNotConfiguredError`; a pair explicitly routed to
  the `"unsupported"` sentinel raises `ProviderUnsupportedError`. Neither
  is ever satisfied by quietly reusing another market's provider or data
  — this is exactly the H/US `stock_basic` bug P1A.1 hardened the
  diagnostics against (see `docs/P1A_PROVIDER_COVERAGE_DECISION.md`),
  now prevented structurally at the routing layer instead of only
  detected after the fact.
- Symbol/index-code translation (via `SymbolMapper`) is applied before
  delegating to the resolved provider — never inline, never guessed.
"""

from __future__ import annotations

from typing import Any, Optional

import pandas as pd

from aegis.data.providers import ProviderError, ProviderNotConfiguredError, ProviderUnsupportedError
from aegis.data.symbol_mapping import SymbolMapper

_SENTINEL_NOT_CONFIGURED = "not_configured"
_SENTINEL_UNSUPPORTED = "unsupported"


class ProviderRouter:
    def __init__(
        self,
        providers: dict[str, Any],
        routing_config: dict,
        symbol_mapper: Optional[SymbolMapper] = None,
    ):
        """
        `providers`: provider-name -> provider instance, e.g.
            {"tushare": TushareAdapter(...), "yahoo_finance": YahooFinanceAdapter(...)}
        `routing_config`: the full `config/providers.yaml` dict (or just
            its `routing` sub-section — both accepted for convenience).
        `symbol_mapper`: defaults to one built from `routing_config`'s
            `symbol_mapping` section, if present.
        """
        self._providers = providers
        self._routing: dict[str, dict[str, str]] = routing_config.get("routing", routing_config) or {}
        self._symbol_mapper = symbol_mapper or SymbolMapper.from_providers_config(routing_config)

    def route_name_for(self, market: str, data_type: str) -> Optional[str]:
        """P1B.3 — a small, **non-raising** diagnostic lookup of the
        configured route name for `(market, data_type)`: the provider
        name (e.g. `"tushare"`/`"yahoo_finance"`), the `"not_configured"`/
        `"unsupported"` sentinel, or `None` if no route is configured at
        all. Unlike `_route_name`/`provider_for`, this never raises —
        it exists purely so callers like `MarketDataService` can label a
        `DataGap` with *which* route actually failed, without needing to
        catch and re-inspect an exception just to find that out. Never
        used for control flow; routing decisions still go entirely
        through `_route_name`/`provider_for`'s raising behavior."""
        by_market = self._routing.get(data_type)
        if not by_market:
            return None
        return by_market.get(market)

    def route_table(self) -> list[dict[str, str]]:
        """A flat, printable route table — used by
        `scripts/check_provider_router.py`. Never includes provider
        instances or any secret/config value beyond the provider name."""
        rows = []
        for data_type, by_market in self._routing.items():
            for market, provider_name in by_market.items():
                rows.append({"data_type": data_type, "market": market, "provider": provider_name})
        return rows

    def _route_name(self, market: str, data_type: str) -> str:
        by_market = self._routing.get(data_type)
        if not by_market or market not in by_market:
            raise ProviderNotConfiguredError(
                f"No route configured for market={market!r}, data_type={data_type!r} — "
                "add an entry to config/providers.yaml's `routing` section."
            )
        return by_market[market]

    def provider_for(self, market: str, data_type: str) -> Any:
        """Resolves the actual provider instance for a `(market,
        data_type)` pair — never silently falls back to a different
        market's provider or data."""
        name = self._route_name(market, data_type)
        if name == _SENTINEL_NOT_CONFIGURED:
            raise ProviderNotConfiguredError(
                f"{data_type} for market={market!r} is explicitly routed to \"not_configured\" — "
                "no real provider has been approved for this capability yet."
            )
        if name == _SENTINEL_UNSUPPORTED:
            raise ProviderUnsupportedError(
                f"{data_type} for market={market!r} is explicitly routed to \"unsupported\" — "
                "no provider is expected to ever satisfy this capability for this market."
            )
        provider = self._providers.get(name)
        if provider is None:
            raise ProviderError(
                f"Route for market={market!r}, data_type={data_type!r} names provider "
                f"{name!r}, but no provider instance was registered under that name."
            )
        return provider

    # -- MarketDataProvider-shaped methods -----------------------------

    def get_daily_bars(self, symbol: str, market: str, start: str, end: str) -> pd.DataFrame:
        name = self._route_name(market, "daily_bars")
        provider = self.provider_for(market, "daily_bars")
        mapped_symbol = self._symbol_mapper.map_symbol(name, market, symbol)
        return provider.get_daily_bars(mapped_symbol, market, start, end)

    def get_index_bars(self, index_code: str, market: str, start: str, end: str) -> pd.DataFrame:
        name = self._route_name(market, "index_bars")
        provider = self.provider_for(market, "index_bars")
        mapped_index = self._symbol_mapper.map_index(name, market, index_code)
        return provider.get_index_bars(mapped_index, market, start, end)

    def get_stock_basic(self, market: str) -> pd.DataFrame:
        # Deliberately no symbol mapping here — stock_basic takes no
        # symbol argument. Routing this to "not_configured" for H/US (the
        # P1B.1-recommended default in config/providers.yaml) is what
        # structurally prevents the P1A.1 bug (H/US stock_basic silently
        # satisfied by A股's list) from ever recurring: this line raises
        # before any provider is even called.
        provider = self.provider_for(market, "stock_basic")
        return provider.get_stock_basic(market)

    def get_sector_classification(self, market: str) -> pd.DataFrame:
        provider = self.provider_for(market, "sector_classification")
        return provider.get_sector_classification(market)

    def get_fundamentals(self, symbol: str, market: str, as_of: str) -> pd.DataFrame:
        name = self._route_name(market, "fundamentals")
        provider = self.provider_for(market, "fundamentals")
        mapped_symbol = self._symbol_mapper.map_symbol(name, market, symbol)
        return provider.get_fundamentals(mapped_symbol, market, as_of)

    def get_trading_calendar(self, market: str, start: str, end: str) -> pd.DataFrame:
        provider = self.provider_for(market, "trading_calendar")
        return provider.get_trading_calendar(market, start, end)


def build_router_from_config(routing_config: dict, providers: dict[str, Any]) -> ProviderRouter:
    """Small convenience factory — mirrors the shape callers already use
    elsewhere in this codebase (e.g. `TushareAdapter.from_env()`)."""
    return ProviderRouter(providers=providers, routing_config=routing_config)
