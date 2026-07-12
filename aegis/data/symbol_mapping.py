"""SymbolMapper — P1B.1 §6.3.

Explicit, provider-specific symbol/index-code translation. Aegis's own
canonical symbols/index codes (e.g. `"00700.HK"`, `"HSI.HI"`, `"SPX"`) are
not guaranteed to match a given secondary provider's own naming
convention (e.g. Yahoo Finance uses `"0700.HK"`, `"^HSI"`, `"^GSPC"`).
This module is the single place that translation happens — never
hard-coded inline in an adapter or in `ProviderRouter`.

Rules (per `Claude_Cowork_P1B1_PROVIDER_ROUTER_HUS_ADAPTERS.md` §6.3):
- Mapping must be explicit, sourced from `config/providers.yaml`'s
  `symbol_mapping` section — never guessed at runtime.
- If a provider has no mapping table configured at all (e.g. Tushare,
  which already speaks Aegis's own canonical symbol convention), symbols
  pass through unchanged (identity) for every market.
- If a provider *does* have a mapping table, but a specific market/code
  pair isn't in it: US may still fall back to identity (many US tickers
  are already Yahoo-compatible, e.g. `"CRCL"`); H must not — an
  unconfigured H symbol raises `SymbolMappingError` rather than silently
  guessing a translation that might be wrong.
- CRCL is never hard-coded here — it only ever appears as a config
  sample/test fixture value, the same as any other symbol.
"""

from __future__ import annotations

from typing import Optional

from aegis.data.providers import ProviderError

# Markets where an unconfigured symbol may safely fall back to identity
# (no translation needed/available) rather than raising. H requires an
# explicit mapping because Yahoo's HK ticker convention (e.g. "0700.HK")
# differs from Aegis's own (e.g. "00700.HK") in a way that cannot be
# safely guessed.
_IDENTITY_DEFAULT_MARKETS = {"US"}


class SymbolMappingError(ProviderError):
    """Raised when a market/code has no configured mapping and no safe
    identity default applies."""


class SymbolMapper:
    """`config` shape (the `symbol_mapping` section of `config/providers.yaml`):

    ```yaml
    symbol_mapping:
      yahoo_finance:
        H:
          symbols:
            "00700.HK": "0700.HK"
          indexes:
            "HSI.HI": "^HSI"
        US:
          symbols:
            "CRCL": "CRCL"
          indexes:
            "SPX": "^GSPC"
    ```
    """

    def __init__(self, config: Optional[dict] = None):
        self._config = config or {}

    @classmethod
    def from_providers_config(cls, providers_config: dict) -> "SymbolMapper":
        """Build a mapper from the full `config/providers.yaml` dict (as
        opposed to just its `symbol_mapping` sub-section)."""
        return cls(providers_config.get("symbol_mapping", {}))

    def map_symbol(self, provider: str, market: str, symbol: str) -> str:
        return self._map(provider, market, symbol, "symbols")

    def map_index(self, provider: str, market: str, index_code: str) -> str:
        return self._map(provider, market, index_code, "indexes")

    def _map(self, provider: str, market: str, code: str, kind: str) -> str:
        provider_cfg = self._config.get(provider)
        if provider_cfg is None:
            # This provider has no mapping table at all — it already
            # speaks Aegis's own canonical symbol convention (e.g.
            # Tushare). Pass through unchanged.
            return code

        table = (provider_cfg.get(market) or {}).get(kind) or {}
        if code in table:
            return table[code]

        if market in _IDENTITY_DEFAULT_MARKETS:
            return code

        kind_singular = kind[:-1] if kind.endswith("s") else kind
        raise SymbolMappingError(
            f"No {kind_singular} mapping configured for provider={provider!r} "
            f"market={market!r} code={code!r} — this market requires an "
            "explicit mapping entry, no safe identity default applies."
        )
