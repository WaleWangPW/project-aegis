"""P1B.1 tests for aegis/data/symbol_mapping.py."""

from __future__ import annotations

import pytest

from aegis.data.symbol_mapping import SymbolMapper, SymbolMappingError

_CONFIG = {
    "yahoo_finance": {
        "H": {
            "symbols": {"00700.HK": "0700.HK"},
            "indexes": {"HSI.HI": "^HSI"},
        },
        "US": {
            "symbols": {"CRCL": "CRCL"},
            "indexes": {"SPX": "^GSPC", "NDX": "^IXIC"},
        },
    }
}


def test_configured_h_symbol_maps_correctly():
    mapper = SymbolMapper(_CONFIG)
    assert mapper.map_symbol("yahoo_finance", "H", "00700.HK") == "0700.HK"


def test_configured_h_index_maps_correctly():
    mapper = SymbolMapper(_CONFIG)
    assert mapper.map_index("yahoo_finance", "H", "HSI.HI") == "^HSI"


def test_configured_us_index_maps_correctly():
    mapper = SymbolMapper(_CONFIG)
    assert mapper.map_index("yahoo_finance", "US", "SPX") == "^GSPC"
    assert mapper.map_index("yahoo_finance", "US", "NDX") == "^IXIC"


def test_us_symbol_with_explicit_identity_entry():
    mapper = SymbolMapper(_CONFIG)
    assert mapper.map_symbol("yahoo_finance", "US", "CRCL") == "CRCL"


def test_us_unconfigured_symbol_falls_back_to_identity():
    mapper = SymbolMapper(_CONFIG)
    # "AAPL" has no explicit entry under US/symbols, but US may safely
    # default to identity — many US tickers are already Yahoo-compatible.
    assert mapper.map_symbol("yahoo_finance", "US", "AAPL") == "AAPL"


def test_h_unconfigured_symbol_raises_instead_of_guessing():
    mapper = SymbolMapper(_CONFIG)
    # H requires an explicit mapping — no safe identity default (Yahoo's
    # HK ticker convention differs from Aegis's own in a way that cannot
    # be guessed).
    with pytest.raises(SymbolMappingError):
        mapper.map_symbol("yahoo_finance", "H", "9999.HK")


def test_provider_with_no_mapping_table_passes_through_identity():
    mapper = SymbolMapper(_CONFIG)
    # "tushare" has no entry in the config at all — it already speaks
    # Aegis's own canonical symbol convention, so every market/symbol
    # passes through unchanged, including H (no raise).
    assert mapper.map_symbol("tushare", "A", "000001.SZ") == "000001.SZ"
    assert mapper.map_symbol("tushare", "H", "00700.HK") == "00700.HK"


def test_from_providers_config_extracts_symbol_mapping_section():
    full_config = {"routing": {"daily_bars": {"A": "tushare"}}, "symbol_mapping": _CONFIG}
    mapper = SymbolMapper.from_providers_config(full_config)
    assert mapper.map_symbol("yahoo_finance", "H", "00700.HK") == "0700.HK"


def test_empty_config_is_safe():
    mapper = SymbolMapper()
    assert mapper.map_symbol("tushare", "A", "000001.SZ") == "000001.SZ"
    assert mapper.map_symbol("anything", "US", "CRCL") == "CRCL"
