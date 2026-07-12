"""Provider protocol — Master Spec §10.1 / Phase 1 §4.1.

Any market data source (Tushare now, others later) implements this shape.
Callers depend on the protocol, not on TushareAdapter directly, so a
different provider can be swapped in without touching aegis.market or
aegis.portfolio.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

import pandas as pd


class ProviderError(Exception):
    """A controlled, expected provider failure (missing package, missing
    token, upstream API error, unsupported market). Callers are expected to
    catch this and record a DataGap rather than letting it crash the run.
    """


class ProviderNotConfiguredError(ProviderError):
    """P1B.1 — raised by `ProviderRouter` when a (market, data_type) pair
    has no configured route (or is explicitly routed to the
    `"not_configured"` sentinel in `config/providers.yaml`). Distinct from
    a runtime provider failure: this is a known, deliberate gap, not an
    error talking to a real provider. `aegis.data.provider_diagnostics`
    maps this to `ProviderCheck.status == "not_configured"`.
    """


class ProviderUnsupportedError(ProviderError):
    """P1B.1 — raised when a provider/route is explicitly known not to
    support a capability at all (e.g. a secondary provider adapter with
    no full stock_basic universe, or a route explicitly marked
    `"unsupported"` in `config/providers.yaml`). Distinct from
    `ProviderNotConfiguredError` (no route decided yet) and from a plain
    `ProviderError` (an unexpected runtime failure). Maps to
    `ProviderCheck.status == "unsupported"`.
    """


@runtime_checkable
class MarketDataProvider(Protocol):
    def get_daily_bars(self, symbol: str, market: str, start: str, end: str) -> pd.DataFrame: ...

    def get_index_bars(self, index_code: str, market: str, start: str, end: str) -> pd.DataFrame: ...

    def get_stock_basic(self, market: str) -> pd.DataFrame: ...

    def get_sector_classification(self, market: str) -> pd.DataFrame: ...

    def get_fundamentals(self, symbol: str, market: str, as_of: str) -> pd.DataFrame: ...

    def get_trading_calendar(self, market: str, start: str, end: str) -> pd.DataFrame: ...
