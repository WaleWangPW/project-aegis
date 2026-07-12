"""Phase 1 tests for HoldingLoader (Phase 1 spec §5.4)."""

from __future__ import annotations

from pathlib import Path

from aegis.portfolio.holdings_loader import HoldingLoader

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_loads_crcl_from_real_config():
    loader = HoldingLoader(REPO_ROOT / "config" / "holdings.yaml")
    holdings = loader.load_holdings()
    assert len(holdings) == 1
    crcl = holdings[0]
    assert crcl.symbol == "CRCL"
    assert crcl.market == "US"
    assert crcl.shares == 254
    assert crcl.avg_cost == 109.157
    # Not yet enriched -> no current price.
    assert crcl.current_price is None


def test_missing_price_stays_none_without_provider():
    loader = HoldingLoader(REPO_ROOT / "config" / "holdings.yaml")
    holdings = loader.load_holdings()

    class _NoDataProvider:
        def get_latest_close(self, symbol, market, as_of):
            return None

    enriched = loader.enrich_prices(holdings, _NoDataProvider(), date="2026-07-04")
    assert enriched[0].current_price is None
    assert enriched[0].market_value is None
    assert enriched[0].unrealized_pnl is None


def test_mocked_provider_enriches_market_value_and_pnl():
    loader = HoldingLoader(REPO_ROOT / "config" / "holdings.yaml")
    holdings = loader.load_holdings()

    class _FixedPriceProvider:
        def get_latest_close(self, symbol, market, as_of):
            return 120.0

    enriched = loader.enrich_prices(holdings, _FixedPriceProvider(), date="2026-07-04")
    crcl = enriched[0]
    assert crcl.current_price == 120.0
    assert crcl.market_value == 120.0 * 254
    expected_pnl = 120.0 * 254 - 109.157 * 254
    assert crcl.unrealized_pnl == expected_pnl
    assert crcl.unrealized_pnl_pct == (120.0 - 109.157) / 109.157


def test_provider_exception_degrades_to_none_not_crash():
    loader = HoldingLoader(REPO_ROOT / "config" / "holdings.yaml")
    holdings = loader.load_holdings()

    class _BrokenProvider:
        def get_latest_close(self, symbol, market, as_of):
            raise RuntimeError("upstream failure")

    enriched = loader.enrich_prices(holdings, _BrokenProvider(), date="2026-07-04")
    assert enriched[0].current_price is None


def test_missing_holdings_file_returns_empty_list(tmp_path):
    loader = HoldingLoader(tmp_path / "does_not_exist.yaml")
    assert loader.load_holdings() == []
