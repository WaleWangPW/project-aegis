"""TushareAdapter — Master Spec §10.1 / Phase 1 §4.2.

Thin wrapper around the Tushare Pro API. No candidate, recommendation, or
scoring logic lives here — only raw data retrieval. Never logs, returns, or
otherwise exposes the token itself.

The `tushare` package is imported lazily/defensively so that the rest of
the codebase (and its tests) work even in environments where the package
cannot be installed or reached (e.g. this Cowork sandbox has no outbound
access to Tushare's real servers).
"""

from __future__ import annotations

import os
from typing import Optional

import pandas as pd
from dotenv import load_dotenv

from .providers import ProviderError

try:  # pragma: no cover - exercised indirectly via is_configured()/_require_client()
    import tushare as ts
except ImportError:  # pragma: no cover
    ts = None


class TushareAdapter:
    """See Phase 1 spec §4.2 for the required method list."""

    def __init__(self, token: Optional[str] = None):
        self._token = token or None
        self._pro = None
        self._init_error: Optional[str] = None
        if self._token and ts is not None:
            try:
                self._pro = ts.pro_api(self._token)
            except Exception as exc:  # pragma: no cover - defensive, no network in CI
                self._pro = None
                self._init_error = str(exc)

    @classmethod
    def from_env(cls) -> "TushareAdapter":
        load_dotenv()
        token = os.environ.get("TUSHARE_TOKEN") or None
        return cls(token=token)

    def is_configured(self) -> bool:
        """True iff a token string is present. Does NOT guarantee the token
        is valid or that the `tushare` package is installed — those are
        checked lazily on the first real data call via `_require_client`."""
        return bool(self._token)

    def _require_client(self):
        if ts is None:
            raise ProviderError("tushare package is not installed")
        if not self._token:
            raise ProviderError("TUSHARE_TOKEN is not configured")
        if self._pro is None:
            detail = f": {self._init_error}" if self._init_error else ""
            raise ProviderError(f"TushareAdapter failed to initialize a client{detail}")
        return self._pro

    @staticmethod
    def _empty_or(df) -> pd.DataFrame:
        return df if isinstance(df, pd.DataFrame) else pd.DataFrame()

    def get_daily_bars(self, symbol: str, market: str, start: str, end: str) -> pd.DataFrame:
        pro = self._require_client()
        try:
            df = pro.daily(ts_code=symbol, start_date=start, end_date=end)
        except Exception as exc:
            raise ProviderError(f"tushare daily() failed for {symbol} ({market}): {exc}") from exc
        return self._empty_or(df)

    def get_index_bars(self, index_code: str, market: str, start: str, end: str) -> pd.DataFrame:
        pro = self._require_client()
        try:
            df = pro.index_daily(ts_code=index_code, start_date=start, end_date=end)
        except Exception as exc:
            raise ProviderError(f"tushare index_daily() failed for {index_code} ({market}): {exc}") from exc
        return self._empty_or(df)

    def get_stock_basic(self, market: str) -> pd.DataFrame:
        pro = self._require_client()
        try:
            df = pro.stock_basic(exchange="", list_status="L")
        except Exception as exc:
            raise ProviderError(f"tushare stock_basic() failed for market {market}: {exc}") from exc
        return self._empty_or(df)

    def get_sector_classification(self, market: str) -> pd.DataFrame:
        pro = self._require_client()
        try:
            df = pro.index_classify(level="L1", src="SW")
        except Exception as exc:
            raise ProviderError(f"tushare index_classify() failed for market {market}: {exc}") from exc
        return self._empty_or(df)

    def get_fundamentals(self, symbol: str, market: str, as_of: str) -> pd.DataFrame:
        pro = self._require_client()
        try:
            df = pro.fina_indicator(ts_code=symbol, period=as_of)
        except Exception as exc:
            raise ProviderError(f"tushare fina_indicator() failed for {symbol} ({market}): {exc}") from exc
        return self._empty_or(df)

    def get_trading_calendar(self, market: str, start: str, end: str) -> pd.DataFrame:
        pro = self._require_client()
        try:
            df = pro.trade_cal(exchange="", start_date=start, end_date=end)
        except Exception as exc:
            raise ProviderError(f"tushare trade_cal() failed for market {market}: {exc}") from exc
        return self._empty_or(df)
