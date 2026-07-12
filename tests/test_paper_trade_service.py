"""Phase 6 tests for PaperTradeService — PHASE6 doc §5.1/§7.1.

Fake provider only, tmp_path-isolated repository, no real Tushare/network.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from aegis.data.gaps import DataGapRegistry
from aegis.market.service import MarketDataService
from aegis.models.recommendation import RecommendationRecord
from aegis.paper.repository import PaperTradeRepository
from aegis.paper.service import PaperTradeService


class _FakeProvider:
    """Returns a fixed daily-bars series per symbol so tests can control
    exactly how many "trading days" have elapsed since entry."""

    def __init__(self, bars_by_symbol: dict[str, pd.DataFrame]):
        self._bars_by_symbol = bars_by_symbol

    def get_daily_bars(self, symbol, market, start, end):
        df = self._bars_by_symbol.get(symbol)
        if df is None:
            return pd.DataFrame()
        return df[(df["trade_date"] >= start) & (df["trade_date"] <= end)]


def _bars(start_compact: str, closes: list[float]) -> pd.DataFrame:
    """`closes[0]` lands on `start_compact`, subsequent entries are the
    following calendar days (fine for tests — only ordering/count matters,
    the service does not do calendar-day arithmetic itself)."""
    from datetime import datetime, timedelta

    base = datetime.strptime(start_compact, "%Y%m%d")
    trade_dates = [(base + timedelta(days=i)).strftime("%Y%m%d") for i in range(len(closes))]
    return pd.DataFrame({"trade_date": trade_dates, "close": closes, "vol": [1000.0] * len(closes)})


def _recommendation(*, symbol="AAA", market="US", status="Action", date="2026-07-01") -> RecommendationRecord:
    return RecommendationRecord(
        recommendation_id=f"rec_{date.replace('-', '')}_pre_market_{market}_{symbol}",
        date=date,
        session="pre_market",
        symbol=symbol,
        market=market,
        sector="Fintech",
        status=status,
        action_label="prepare_entry_plan" if status == "Action" else "watch",
        market_snapshot_id=f"mkt_{date.replace('-', '')}_{market}_pre_market",
        candidate_id=f"cand_{date.replace('-', '')}_{market}_{symbol}",
        expert_opinions=["opn_1"],
        support_reasons=["TrendAgent support: fixture (source_opinion_id=opn_1)"],
        oppose_reasons=[],
        risks=[],
        invalidation_conditions=["fixture invalidation"] if status == "Action" else [],
        confidence=0.7,
        decision_summary="fixture decision summary",
        lifecycle_status="open",
        created_at="2026-07-01T07:00:00-07:00",
        updated_at="2026-07-01T07:00:00-07:00",
    )


def _service(tmp_path: Path, bars_by_symbol: dict[str, pd.DataFrame] | None = None, with_gaps: bool = True):
    records_dir = tmp_path / "records"
    repository = PaperTradeRepository(records_dir)
    market_data_service = None
    if bars_by_symbol is not None:
        market_data_service = MarketDataService(provider=_FakeProvider(bars_by_symbol), cache=None, gaps=None)
    gaps = DataGapRegistry(records_dir / "data_gaps.jsonl") if with_gaps else None
    service = PaperTradeService(repository=repository, market_data_service=market_data_service, gaps=gaps)
    return service, repository, gaps


def test_action_recommendation_creates_paper_trade_with_valid_entry_price(tmp_path: Path):
    rec = _recommendation(status="Action")
    bars = {"AAA": _bars("20260701", [100.0])}
    service, repository, _ = _service(tmp_path, bars)

    trade = service.create_trade_from_recommendation(rec)

    assert trade is not None
    assert trade.entry_price == 100.0
    assert trade.status == "open"
    assert trade.recommendation_id == rec.recommendation_id
    assert repository.find_by_id(trade.paper_trade_id) is not None


def test_ready_and_watch_do_not_create_paper_trade(tmp_path: Path):
    bars = {"AAA": _bars("20260701", [100.0])}
    service, repository, _ = _service(tmp_path, bars)

    for status in ("Ready", "Watch"):
        rec = _recommendation(symbol="AAA", status=status)
        trade = service.create_trade_from_recommendation(rec)
        assert trade is None

    assert repository.list_all() == []


def test_missing_entry_price_does_not_create_fake_open_trade(tmp_path: Path):
    rec = _recommendation(status="Action")
    service, repository, gaps = _service(tmp_path, bars_by_symbol={})  # no bars for AAA at all

    trade = service.create_trade_from_recommendation(rec)

    assert trade is None
    assert repository.list_all() == []
    assert len(gaps.list_gaps()) == 1
    assert gaps.list_gaps()[0]["data_type"] == "entry_price"


def test_paper_trade_links_to_recommendation_id(tmp_path: Path):
    rec = _recommendation(status="Action")
    bars = {"AAA": _bars("20260701", [100.0])}
    service, _, _ = _service(tmp_path, bars)

    trade = service.create_trade_from_recommendation(rec)

    assert trade.recommendation_id == rec.recommendation_id


def test_create_trade_is_idempotent_per_recommendation(tmp_path: Path):
    rec = _recommendation(status="Action")
    bars = {"AAA": _bars("20260701", [100.0])}
    service, repository, _ = _service(tmp_path, bars)

    first = service.create_trade_from_recommendation(rec)
    second = service.create_trade_from_recommendation(rec)

    assert first.paper_trade_id == second.paper_trade_id
    assert len(repository.list_all()) == 1


def test_horizon_returns_only_compute_when_due(tmp_path: Path):
    # entry + 4 more trading days = 4 elapsed trading days after entry.
    # 5d should NOT be due yet; nothing should be due yet at all.
    closes = [100.0, 101.0, 102.0, 103.0, 104.0]
    bars = {"AAA": _bars("20260701", closes)}
    service, repository, _ = _service(tmp_path, bars)
    rec = _recommendation(status="Action")
    trade = service.create_trade_from_recommendation(rec)

    updated = service.compute_forward_returns(trade, as_of_date="2026-07-05")
    assert updated.return_5d is None
    assert updated.return_10d is None

    # Now extend to exactly 5 elapsed trading days after entry -> 5d due.
    closes_due = [100.0, 101.0, 102.0, 103.0, 104.0, 105.0]
    bars_due = {"AAA": _bars("20260701", closes_due)}
    service_due, _, _ = _service(tmp_path, bars_due)
    updated_due = service_due.compute_forward_returns(trade, as_of_date="2026-07-06")
    assert updated_due.return_5d is not None
    assert round(updated_due.return_5d, 4) == round((105.0 - 100.0) / 100.0, 4)
    assert updated_due.return_10d is None  # not due yet


def test_max_drawdown_computation_works(tmp_path: Path):
    closes = [100.0, 110.0, 95.0, 88.0, 100.0]
    bars = {"AAA": _bars("20260701", [100.0] + closes[1:])}
    # entry itself is day 0 (close=100.0), remaining closes are post-entry bars
    service, _, _ = _service(tmp_path, bars)
    rec = _recommendation(status="Action")
    trade = service.create_trade_from_recommendation(rec)

    updated = service.compute_forward_returns(trade, as_of_date="2026-07-05")
    assert updated.max_drawdown is not None
    assert updated.max_drawdown < 0


def test_update_open_trades_persists_and_returns_updated_trades(tmp_path: Path):
    closes = [100.0, 101.0, 102.0, 103.0, 104.0, 105.0]
    bars = {"AAA": _bars("20260701", closes)}
    service, repository, _ = _service(tmp_path, bars)
    rec = _recommendation(status="Action")
    service.create_trade_from_recommendation(rec)

    updated = service.update_open_trades("2026-07-06")

    assert len(updated) == 1
    assert updated[0].return_5d is not None
    persisted = repository.find_by_recommendation_id(rec.recommendation_id)[0]
    assert persisted.return_5d == updated[0].return_5d


def test_close_trade_sets_status_and_exit_fields(tmp_path: Path):
    bars = {"AAA": _bars("20260701", [100.0])}
    service, repository, _ = _service(tmp_path, bars)
    rec = _recommendation(status="Action")
    trade = service.create_trade_from_recommendation(rec)

    closed = service.close_trade(trade.paper_trade_id, exit_date="2026-07-10", exit_price=95.0, reason="stopped_out")

    assert closed.status == "closed"
    assert closed.exit_price == 95.0
    assert closed.exit_reason == "stopped_out"
    assert closed.result == "stopped_out"
    persisted = repository.find_by_id(trade.paper_trade_id)
    assert persisted.status == "closed"


def test_close_trade_with_unrecognized_reason_keeps_result_none(tmp_path: Path):
    bars = {"AAA": _bars("20260701", [100.0])}
    service, _, _ = _service(tmp_path, bars)
    rec = _recommendation(status="Action")
    trade = service.create_trade_from_recommendation(rec)

    closed = service.close_trade(trade.paper_trade_id, exit_date="2026-07-10", exit_price=95.0, reason="manual close per user request")

    assert closed.exit_reason == "manual close per user request"
    assert closed.result is None  # never force-fit free text into the enum


def test_close_trade_missing_id_raises(tmp_path: Path):
    service, _, _ = _service(tmp_path, {})
    with pytest.raises(ValueError):
        service.close_trade("ptr_does_not_exist", exit_date="2026-07-10", exit_price=1.0, reason="expired")


def test_export_summary_shape(tmp_path: Path):
    bars = {"AAA": _bars("20260701", [100.0])}
    service, _, _ = _service(tmp_path, bars)
    rec = _recommendation(status="Action", date="2026-07-01")
    service.create_trade_from_recommendation(rec)

    summary = service.export_summary(date="2026-07-01")
    assert len(summary["new_today"]) == 1
    assert len(summary["open_positions_perf"]) == 1
    assert summary["new_today"][0]["ticker"] == "AAA"
