"""HoldingLoader — Master Spec §10.1 / Phase 1 §4.6.

Reads config/holdings.yaml (the single source of truth for real holdings —
see Master Spec §8.2 acceptance: "CRCL 必须无需再次输入即可被读取并进入分析")
and optionally enriches each Holding with a latest price from a provider
that exposes `get_latest_close` (i.e. a MarketDataService, not a raw
TushareAdapter). No broker connection of any kind.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

import yaml

from aegis.models.holding import Holding


class LatestCloseProvider(Protocol):
    def get_latest_close(self, symbol: str, market: str, as_of: str) -> float | None: ...


class HoldingLoader:
    def __init__(self, holdings_path: str | Path):
        self.holdings_path = Path(holdings_path)

    def load_holdings(self) -> list[Holding]:
        if not self.holdings_path.exists():
            return []
        with self.holdings_path.open("r", encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}
        return [Holding(**item) for item in raw.get("holdings", [])]

    def enrich_prices(
        self,
        holdings: list[Holding],
        provider: LatestCloseProvider,
        date: str,
    ) -> list[Holding]:
        enriched: list[Holding] = []
        for holding in holdings:
            price: float | None = None
            try:
                price = provider.get_latest_close(holding.symbol, holding.market, date)
            except Exception:
                # A provider failure here is a data gap, not a Holding-level
                # crash. The caller (or the provider itself) is responsible
                # for recording the DataGap; this loader just degrades
                # gracefully to "no current price" for this holding.
                price = None

            if price is None:
                enriched.append(holding)
                continue

            market_value = price * holding.shares
            cost_basis = holding.avg_cost * holding.shares
            unrealized_pnl = market_value - cost_basis
            unrealized_pnl_pct = (
                (price - holding.avg_cost) / holding.avg_cost if holding.avg_cost else None
            )
            enriched.append(
                holding.model_copy(
                    update={
                        "current_price": price,
                        "market_value": market_value,
                        "unrealized_pnl": unrealized_pnl,
                        "unrealized_pnl_pct": unrealized_pnl_pct,
                    }
                )
            )
        return enriched
