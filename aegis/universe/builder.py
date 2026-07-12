"""UniverseBuilder — Phase 2 §6.

Turns a stock list (from the provider) plus current holdings into a
`list[Candidate]`. No composite score, no recommendation status — only
pass/fail filters plus a small, opportunistic set of additive reason tags
(Phase 2 §6.3). Current holdings are always forced in, even when the
market's own data is missing (§6.4).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from aegis.data.gaps import DataGapRegistry
from aegis.data.providers import ProviderError
from aegis.models.candidate import Candidate
from aegis.models.common import DataQuality
from aegis.models.holding import Holding
from aegis.universe.filters import enrichment_reasons, passes_basic_filters

DEFAULT_MAX_CANDIDATES_BY_MARKET = {"A": 50, "H": 30, "US": 30}


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def _candidate_id(date: str, market: str, symbol: str) -> str:
    return f"cand_{date.replace('-', '')}_{market}_{symbol}"


class UniverseBuilder:
    def __init__(
        self,
        provider: Any,
        config: Optional[dict] = None,
        gaps: Optional[DataGapRegistry] = None,
    ):
        self.provider = provider
        self.config = config or {}
        self.gaps = gaps

    def build_candidates(
        self,
        *,
        date: str,
        session: str,
        markets: list[str],
        holdings: list[Holding],
        market_snapshots: Optional[list] = None,
    ) -> list[Candidate]:
        holdings_by_market: dict[str, list[Holding]] = {}
        for holding in holdings:
            holdings_by_market.setdefault(holding.market, []).append(holding)

        all_candidates: list[Candidate] = []
        for market in markets:
            all_candidates.extend(
                self._build_for_market(
                    market=market,
                    date=date,
                    holdings=holdings_by_market.get(market, []),
                )
            )
        return all_candidates

    # -- internals ---------------------------------------------------

    def _market_cfg(self, market: str) -> dict:
        markets_cfg = self.config.get("markets", {})
        cfg = dict(markets_cfg.get(market, {}))
        cfg.setdefault("lookback_days", self.config.get("default", {}).get("lookback_days", 120))
        return cfg

    def _max_candidates(self, market: str) -> int:
        markets_cfg = self.config.get("markets", {})
        if market in markets_cfg and "max_candidates" in markets_cfg[market]:
            return int(markets_cfg[market]["max_candidates"])
        if market in DEFAULT_MAX_CANDIDATES_BY_MARKET:
            return DEFAULT_MAX_CANDIDATES_BY_MARKET[market]
        return int(self.config.get("default", {}).get("max_candidates_per_market", 30))

    def _record_gap(self, *, date: str, market: str, data_type: str, message: str) -> None:
        if self.gaps is None:
            return
        self.gaps.record_gap(
            date=date,
            market=market,
            symbol=None,
            provider="universe_builder",
            data_type=data_type,
            severity="warning",
            message=message,
        )

    def _holding_candidate(
        self,
        holding: Holding,
        date: str,
        has_market_data: bool,
        force_liquidity_ok: bool = False,
    ) -> Candidate:
        """Build a forced-in Candidate for a confirmed holding.

        `has_market_data` — True iff the stock-list row was found for this
        symbol in the provider's stock_basic response. Controls data_quality
        status (partial vs complete).

        `force_liquidity_ok` (P1D.2) — when stock_basic is not configured for
        this market (e.g. US/H), we have no information about liquidity, but
        the position is a confirmed real holding. In that case pass
        `force_liquidity_ok=True` so RiskAgent does not veto the candidate for
        `liquidity_not_ok` solely because of a missing stock-list row.
        data_quality still reflects the real gap (partial / warning).
        """
        warnings = []
        status = "complete"
        if not has_market_data:
            status = "partial"
            warnings = ["holding_forced_into_candidates_even_with_missing_market_data"]

        return Candidate(
            candidate_id=_candidate_id(date, holding.market, holding.symbol),
            symbol=holding.symbol,
            name=holding.name,
            market=holding.market,
            sector=None,
            source="holding",
            filter_reason=["current_real_holding", "must_analyze_holdings"],
            liquidity_ok=force_liquidity_ok or has_market_data,
            data_quality=DataQuality(status=status, missing_fields=[], warnings=warnings),
            created_at=_now_iso(),
        )

    def _build_for_market(self, *, market: str, date: str, holdings: list[Holding]) -> list[Candidate]:
        market_cfg = self._market_cfg(market)
        max_candidates = self._max_candidates(market)
        holding_symbols = {h.symbol for h in holdings}

        stock_rows: list[dict] = []
        got_stock_data = False
        try:
            df = self.provider.get_stock_basic(market)
        except ProviderError as exc:
            self._record_gap(
                date=date, market=market, data_type="stock_basic",
                message=f"get_stock_basic failed for {market}: {exc}",
            )
            df = None

        if df is not None and not df.empty:
            got_stock_data = True
            stock_rows = df.to_dict("records")
        elif df is not None and df.empty:
            self._record_gap(
                date=date, market=market, data_type="stock_basic",
                message=f"No stock list returned for market {market}.",
            )

        # Holdings are always included, regardless of whether the general
        # market data is available (§6.4). Whether we "have market data"
        # for a specific holding's own row is judged separately below.
        rows_by_symbol = {}
        for row in stock_rows:
            symbol = row.get("symbol") or row.get("ts_code")
            if symbol:
                rows_by_symbol[symbol] = row

        # P1D.2: when stock_basic is not configured for this market (US/H),
        # `got_stock_data=False` and `rows_by_symbol={}`. The holding is a
        # confirmed real position, so we must not veto it for `liquidity_not_ok`
        # just because stock_basic is unavailable. Pass `force_liquidity_ok=True`
        # so `liquidity_ok=True` regardless of the missing stock-list row.
        # `has_market_data` is still False in this scenario, so data_quality
        # status remains 'partial' and the warning is preserved (honest reporting).
        holding_candidates = [
            self._holding_candidate(
                h,
                date,
                has_market_data=h.symbol in rows_by_symbol,
                force_liquidity_ok=not got_stock_data,
            )
            for h in holdings
        ]

        if not got_stock_data:
            # §6.5: "If a market has no stock list or bars: record DataGap,
            # return forced holding candidates only if any holding belongs
            # to that market, no fake candidates."
            return holding_candidates

        non_holding_candidates: list[Candidate] = []
        for symbol, row in sorted(rows_by_symbol.items()):
            if symbol in holding_symbols:
                continue
            passes, filter_reason, warnings = passes_basic_filters(row, market, market_cfg)
            if not passes:
                continue
            reasons = list(filter_reason) + enrichment_reasons(row)
            non_holding_candidates.append(
                Candidate(
                    candidate_id=_candidate_id(date, market, symbol),
                    symbol=symbol,
                    name=row.get("name"),
                    market=market,
                    sector=row.get("industry") or row.get("sector"),
                    source="universe_builder",
                    filter_reason=reasons,
                    liquidity_ok=True,
                    data_quality=DataQuality(
                        status="complete" if not warnings else "partial",
                        missing_fields=[],
                        warnings=warnings,
                    ),
                    created_at=_now_iso(),
                )
            )

        # Holdings are exempt from the cap; only non-holding candidates are
        # truncated (§6.6). Ordering is alphabetical (deterministic), not a
        # score.
        remaining_slots = max(0, max_candidates - len(holding_candidates))
        return holding_candidates + non_holding_candidates[:remaining_slots]
