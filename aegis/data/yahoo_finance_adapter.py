"""YahooFinanceAdapter — P1B.1 §6.2.

A thin, secondary `MarketDataProvider`-shaped adapter for H/US daily bars
and index bars, behind the same duck-typed interface as `TushareAdapter`
(`aegis/data/tushare_adapter.py`) so `ProviderRouter` and every existing
consumer (`MarketDataService`, `aegis.data.provider_diagnostics`) can use
it interchangeably.

This is explicitly a **personal research / diagnostics-grade** data
source, not official exchange data:
- Every normalized row is labeled with `source="yahoo_finance"`.
- Every result honestly reflects what the underlying client returned —
  an empty result produces an empty DataFrame, never fabricated bars.
- Full stock universe (`get_stock_basic`), fundamentals, sector
  classification, and trading calendar are explicitly **not
  implemented** by this skeleton adapter — they raise
  `ProviderUnsupportedError` rather than guessing or reusing another
  market's data (this is exactly the class of bug P1A.1 hardened the
  diagnostics against — see `docs/P1A_PROVIDER_COVERAGE_DECISION.md`).

The `yfinance` package is imported lazily/defensively, the same
convention `TushareAdapter` already uses for `tushare` — so the rest of
the codebase (and its tests) work even where `yfinance` isn't installed
or reachable (this Cowork sandbox has no outbound network and does not
have `yfinance` installed). Tests always inject a fake client — this
module never makes a real network call from `pytest`.

P1B.4 local smoke failure triage: `get_daily_bars`/`get_index_bars` now
normalize `start`/`end` date strings before ever calling
`client.download(...)`. Root cause: the real `yfinance` package parses
string `start`/`end` args via a strict `datetime.strptime(dt, "%Y-%m-%d")`
internally (see `yfinance.utils._parse_user_dt`) — a compact `YYYYMMDD`
string (the Tushare-oriented convention produced by
`aegis.utils.dates.lookback_range`, which `MarketSnapshotService` and
`scripts/run_market_snapshot_smoke.py` both use to compute a lookback
window) fails that strict parse. `yfinance`'s own internal
`_download_one` swallows that `ValueError` and quietly substitutes an
empty DataFrame instead of raising — so callers never see an exception,
only zero rows, indistinguishable from "no data available." This is why
`scripts/validate_provider_router_live.py` (which builds its own window
with dashed `YYYY-MM-DD` strings) already worked, while anything routed
through `lookback_range`'s compact format silently got nothing.
`_normalize_date_str` accepts either convention and always passes
`yfinance` the dashed format it actually requires.

P1B.4.1 smoke consistency fix: `_normalize_ohlcv` now flattens MultiIndex
columns (a real `yfinance` response shape for some installed versions)
before alias-matching, so a real, non-empty response with genuine rows
can no longer silently end up with zero usable OHLCV columns while still
reporting `len(df) > 0` to a naive row-count check. See `_normalize_ohlcv`
docstring for the full story.
"""

from __future__ import annotations

import re
from typing import Any, Optional

import pandas as pd

from .providers import ProviderError, ProviderUnsupportedError

try:  # pragma: no cover - exercised indirectly; no real yfinance here
    import yfinance as yf
except ImportError:  # pragma: no cover
    yf = None

SOURCE_LABEL = "yahoo_finance"

_OHLCV_COLUMN_ALIASES = {
    "date": "trade_date",
    "datetime": "trade_date",
    "open": "open",
    "high": "high",
    "low": "low",
    "close": "close",
    "adj close": "adj_close",
    "volume": "vol",
}


class YahooFinanceAdapter:
    """See P1B.1 §6.2 for the required method list."""

    def __init__(self, client: Optional[Any] = None):
        # `client` is injectable for tests (any object exposing a
        # `.download(symbol, start=..., end=..., progress=...)` method
        # shaped like the real `yfinance` module) — never a real network
        # call from pytest. Defaults to the real `yfinance` module if
        # installed, mirroring `TushareAdapter`'s lazy-import convention.
        self._client = client if client is not None else yf

    def is_configured(self) -> bool:
        """True iff a client (real or injected) is available. Does not
        guarantee real network reachability — that is only known once an
        actual call is attempted."""
        return self._client is not None

    def _require_client(self):
        if self._client is None:
            raise ProviderError("yfinance package is not installed")
        return self._client

    @staticmethod
    def _empty_or(df: Any) -> pd.DataFrame:
        return df if isinstance(df, pd.DataFrame) else pd.DataFrame()

    @staticmethod
    def _normalize_date_str(value: Any) -> Any:
        """Real `yfinance` only accepts a `"YYYY-MM-DD"`-formatted date
        string (it calls `datetime.strptime(dt, "%Y-%m-%d")` internally,
        see this module's docstring for the full story) — a compact
        `"YYYYMMDD"` string (the Tushare-oriented convention produced by
        `aegis.utils.dates.lookback_range`) silently causes `yfinance` to
        swallow the resulting `ValueError` and return an empty result
        instead of raising. This accepts either an 8-digit compact string
        or an already-dashed string (passed through unchanged) or any
        non-string value (e.g. `None`, a `datetime`/`date` — also passed
        through unchanged; `yfinance` itself handles those). Never
        raises — an unrecognized string format is passed through as-is
        and left for `yfinance`'s own call to report honestly."""
        if not isinstance(value, str):
            return value
        text = value.strip()
        if re.fullmatch(r"\d{8}", text):
            return f"{text[0:4]}-{text[4:6]}-{text[6:8]}"
        return text

    @staticmethod
    def _normalize_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
        """Normalizes a yfinance-shaped frame (Date-indexed,
        Open/High/Low/Close/Volume columns) to Aegis's own
        `trade_date`/`open`/`high`/`low`/`close`/`vol`[/`amount`]
        convention. Date formatting is deterministic (`YYYYMMDD` compact
        strings, same convention as `TushareAdapter`'s bars).

        P1B.4.1 smoke consistency fix: real `yfinance` (recent versions)
        can return **MultiIndex columns** from `.download()` even for a
        single symbol (e.g. top level `Close`/`Open`/... , second level the
        ticker) depending on the installed version/defaults. Before this
        fix, that shape silently defeated the alias-based rename below —
        `str(col).strip().lower()` on a tuple never matches
        `_OHLCV_COLUMN_ALIASES`, so `rename_map` stayed empty and the
        returned frame kept its original row count (`len(df) > 0`) but had
        **no usable OHLCV columns at all** (only the `source` column added
        below survived the `keep` filter). That is exactly the shape that
        caused P1B.4.1's observed bug: a route probe reporting real rows
        returned (`len(df)`) while `MarketSnapshotService`/
        `MarketRegimeAnalyzer` — which correctly check `df.empty` (a
        DataFrame with rows but zero columns *is* `.empty`) and
        `"close" in df.columns` — treated the same data as unavailable.
        Flattening MultiIndex columns to their first level before matching
        aliases makes normalization robust regardless of which shape
        `yfinance` actually returns."""
        if df is None or df.empty:
            return pd.DataFrame()

        out = df.copy()
        if isinstance(out.columns, pd.MultiIndex):
            out.columns = [str(level0) for level0, *_rest in out.columns]
        if out.index.name is not None or "Date" not in out.columns:
            out = out.reset_index()

        rename_map: dict[str, str] = {}
        for col in out.columns:
            key = str(col).strip().lower()
            if key in _OHLCV_COLUMN_ALIASES:
                rename_map[col] = _OHLCV_COLUMN_ALIASES[key]
        out = out.rename(columns=rename_map)

        if "trade_date" in out.columns:
            out["trade_date"] = pd.to_datetime(out["trade_date"]).dt.strftime("%Y%m%d")

        out["source"] = SOURCE_LABEL

        keep = [c for c in ("trade_date", "open", "high", "low", "close", "vol", "amount", "source") if c in out.columns]
        return out[keep].reset_index(drop=True)

    def get_daily_bars(self, symbol: str, market: str, start: str, end: str) -> pd.DataFrame:
        client = self._require_client()
        start_n, end_n = self._normalize_date_str(start), self._normalize_date_str(end)
        try:
            raw = client.download(symbol, start=start_n, end=end_n, progress=False)
        except Exception as exc:  # noqa: BLE001 - normalized into a controlled ProviderError
            raise ProviderError(f"yahoo_finance daily bars failed for {symbol} ({market}): {exc}") from exc
        return self._normalize_ohlcv(self._empty_or(raw))

    def get_index_bars(self, index_code: str, market: str, start: str, end: str) -> pd.DataFrame:
        client = self._require_client()
        start_n, end_n = self._normalize_date_str(start), self._normalize_date_str(end)
        try:
            raw = client.download(index_code, start=start_n, end=end_n, progress=False)
        except Exception as exc:  # noqa: BLE001
            raise ProviderError(f"yahoo_finance index bars failed for {index_code} ({market}): {exc}") from exc
        return self._normalize_ohlcv(self._empty_or(raw))

    def get_stock_basic(self, market: str) -> pd.DataFrame:
        raise ProviderUnsupportedError(
            "yahoo_finance does not provide a full stock_basic universe in this skeleton adapter — "
            "H/US stock_basic must not be satisfied by this provider (P1B.1 §4.3)."
        )

    def get_fundamentals(self, symbol: str, market: str, as_of: str) -> pd.DataFrame:
        raise ProviderUnsupportedError("yahoo_finance fundamentals are not implemented by this skeleton adapter.")

    def get_sector_classification(self, market: str) -> pd.DataFrame:
        raise ProviderUnsupportedError("yahoo_finance sector classification is not implemented by this skeleton adapter.")

    def get_trading_calendar(self, market: str, start: str, end: str) -> pd.DataFrame:
        raise ProviderUnsupportedError("yahoo_finance trading calendar is not implemented by this skeleton adapter.")
