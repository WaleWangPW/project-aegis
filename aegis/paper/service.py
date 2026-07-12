"""PaperTradeService — Phase 6 §5.1.

Turns an `Action`-status `RecommendationRecord` into a virtual (never real)
position, and later updates it with forward-return/drawdown data as trading
days actually elapse. Never places a real order, never talks to a broker,
never fabricates a price.

Date convention: per Master Spec §7.1 every other Phase 0-5 model/service in
this codebase represents dates as plain "YYYY-MM-DD" strings (never
`datetime.date` objects) — `RecommendationRecord.date`, `PaperTrade.
entry_date`, `MarketSnapshot.date`, etc. This module keeps that convention
for `as_of_date`/`exit_date` parameters (the PHASE6 doc's pseudocode shows
`date: date` type hints, but those are illustrative method signatures, not a
requirement to introduce a second date representation alongside the
string-based one every other module already uses).

"Trading-day horizon" is reckoned from actual price bars returned by the
data provider (via `MarketDataService`), not calendar days — there is no
trading-calendar service in this project (Phase 1 HANDOFF notes this as an
open gap), so "day 5" means "the 5th daily bar strictly after entry_date",
whatever calendar date that bar happens to fall on.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional, get_args

from aegis.data.gaps import DataGapRegistry
from aegis.market.service import MarketDataService
from aegis.models.paper_trade import PaperTrade, TradeResult
from aegis.models.recommendation import RecommendationRecord
from aegis.paper.metrics import compute_horizon_return, compute_max_drawdown
from aegis.paper.repository import PaperTradeRepository
from aegis.utils.dates import to_compact

HORIZONS = (5, 10, 20, 40)
_KNOWN_RESULTS = set(get_args(TradeResult))  # target_hit/stopped_out/expired/invalidated/still_open


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


class PaperTradeService:
    def __init__(
        self,
        repository: PaperTradeRepository,
        market_data_service: Optional[MarketDataService] = None,
        gaps: Optional[DataGapRegistry] = None,
        horizons: tuple[int, ...] = HORIZONS,
    ):
        self.repository = repository
        self.market_data_service = market_data_service
        self.gaps = gaps
        self.horizons = horizons

    def create_trade_from_recommendation(
        self, rec: RecommendationRecord, price_data: Optional[dict] = None
    ) -> Optional[PaperTrade]:
        """Only `status == "Action"` may create a virtual trade (rule 1/2).
        Idempotent: if a PaperTrade already links to this recommendation_id,
        the existing one is returned instead of creating a duplicate.
        """
        if rec.status != "Action":
            return None

        existing = self.repository.find_by_recommendation_id(rec.recommendation_id)
        if existing:
            return existing[0]

        entry_price = self._resolve_entry_price(rec, price_data)
        if entry_price is None or entry_price <= 0:
            if self.gaps is not None:
                self.gaps.record_gap(
                    date=rec.date,
                    market=rec.market,
                    symbol=rec.symbol,
                    provider="paper_trade_service",
                    data_type="entry_price",
                    severity="warning",
                    message=(
                        f"No real entry price available for Action recommendation "
                        f"{rec.recommendation_id}; PaperTrade was not created "
                        f"(never fabricated, per Master Spec §16.1)."
                    ),
                )
            return None

        now = _now_iso()
        trade = PaperTrade(
            paper_trade_id=f"ptr_{rec.date.replace('-', '')}_{rec.market}_{rec.symbol}",
            recommendation_id=rec.recommendation_id,
            symbol=rec.symbol,
            market=rec.market,
            direction="long",
            entry_date=rec.date,
            entry_price=float(entry_price),
            virtual_position_size=1.0,
            status="open",
            created_at=now,
            updated_at=now,
        )
        self.repository.append(trade)
        return trade

    def _resolve_entry_price(self, rec: RecommendationRecord, price_data: Optional[dict]) -> Optional[float]:
        if price_data is not None:
            value = price_data.get("entry_price")
            if value is None:
                value = price_data.get("close")
            if value is not None:
                return value
        if self.market_data_service is not None:
            # get_latest_close's `as_of` is passed straight through to the
            # provider as both start/end (see MarketDataService.
            # get_latest_close) — the provider/bars convention across this
            # codebase is compact "YYYYMMDD" (see lookback_range/to_compact
            # usage in scripts/run_pre_market.py), not "YYYY-MM-DD".
            return self.market_data_service.get_latest_close(rec.symbol, rec.market, to_compact(rec.date))
        return None

    def update_open_trades(self, date: str) -> list[PaperTrade]:
        """Recompute forward returns/drawdown for every currently-open
        trade as of `date`, persist each, and return the updated list."""
        updated: list[PaperTrade] = []
        for trade in self.repository.list_open():
            refreshed = self.compute_forward_returns(trade, date)
            self.repository.update(refreshed)
            updated.append(refreshed)
        return updated

    def compute_forward_returns(self, trade: PaperTrade, as_of_date: str) -> PaperTrade:
        """Fetch bars strictly after `trade.entry_date` up to `as_of_date`,
        fill in any newly-due 5/10/20/40 trading-day horizon return (rule
        7/8: only once that many trading-day bars actually exist), and
        refresh `max_drawdown` over the full entry->as_of price series.
        Never uses data beyond `as_of_date` (rule 10)."""
        if self.market_data_service is None:
            return trade  # no data source injected — honest no-op, not a guess

        start = to_compact(trade.entry_date)
        end = to_compact(as_of_date)
        bars = self.market_data_service.get_daily_bars_cached(trade.symbol, trade.market, start, end)
        if bars is None or bars.empty or "trade_date" not in bars.columns or "close" not in bars.columns:
            return trade

        entry_compact = to_compact(trade.entry_date)
        post_entry = bars[bars["trade_date"] > entry_compact].sort_values("trade_date")
        closes_after_entry = [float(c) for c in post_entry["close"].tolist()]
        elapsed = len(closes_after_entry)

        updates: dict = {}
        for horizon in self.horizons:
            field = f"return_{horizon}d"
            if getattr(trade, field) is None and elapsed >= horizon:
                horizon_price = closes_after_entry[horizon - 1]
                updates[field] = compute_horizon_return(trade.entry_price, horizon_price)

        price_series = [trade.entry_price] + closes_after_entry
        max_dd = compute_max_drawdown(price_series)
        if max_dd is not None:
            updates["max_drawdown"] = max_dd

        if not updates:
            return trade

        updates["updated_at"] = _now_iso()
        return trade.model_copy(update=updates)

    def close_trade(self, paper_trade_id: str, exit_date: str, exit_price: float, reason: str) -> PaperTrade:
        trade = self.repository.find_by_id(paper_trade_id)
        if trade is None:
            raise ValueError(f"No PaperTrade found for paper_trade_id={paper_trade_id!r}")

        # `reason` is free text (stored verbatim in exit_reason). It only
        # becomes the structured `result` enum when it matches one of the
        # model's known TradeResult values — never force-fit an unrecognized
        # reason into a fabricated classification.
        result = reason if reason in _KNOWN_RESULTS else None

        closed = trade.model_copy(
            update={
                "status": "closed",
                "exit_date": exit_date,
                "exit_price": float(exit_price),
                "exit_reason": reason,
                "result": result,
                "updated_at": _now_iso(),
            }
        )
        self.repository.update(closed)
        return closed

    def export_summary(self, date: Optional[str] = None) -> dict:
        """Honest summary shape matching the Dashboard v1 `paper_trading`
        schema (`{"new_today": [...], "open_positions_perf": [...]}`) —
        used by `DashboardBuilder`/`run_close.py`, never by the UI file
        itself (which is never touched)."""
        trades = self.repository.list_all()
        new_today = [t for t in trades if date is not None and t.entry_date == date]
        open_positions = [t for t in trades if t.status == "open"]
        return {
            "new_today": [self._trade_summary(t) for t in new_today],
            "open_positions_perf": [self._trade_summary(t) for t in open_positions],
        }

    def _trade_summary(self, trade: PaperTrade) -> dict:
        return {
            "ticker": trade.symbol,
            "market": trade.market,
            "entry_date": trade.entry_date,
            "entry_price": trade.entry_price,
            "status": trade.status,
            "return_5d": trade.return_5d,
            "return_10d": trade.return_10d,
            "return_20d": trade.return_20d,
            "return_40d": trade.return_40d,
            "max_drawdown": trade.max_drawdown,
        }
