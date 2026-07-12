"""P1A tests for aegis/calendar/ — TradingCalendarService.

Fake provider / CSV cache fixtures only, no real Tushare/network.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from aegis.calendar.repository import TradingCalendarRepository
from aegis.calendar.service import TradingCalendarService
from aegis.data.gaps import DataGapRegistry


def _write_cache(repo: TradingCalendarRepository, market: str, open_dates: list[str], closed_dates: list[str]) -> None:
    rows = [{"date": d, "is_trading_day": 1} for d in open_dates] + [
        {"date": d, "is_trading_day": 0} for d in closed_dates
    ]
    df = pd.DataFrame(rows)
    repo.write(market, df)


class _FakeCalendarProvider:
    def __init__(self, open_dates: list[str], closed_dates: list[str]):
        self._open = open_dates
        self._closed = closed_dates

    def get_trading_calendar(self, market, start, end):
        dates = sorted(self._open + self._closed)
        is_open = [1 if d in self._open else 0 for d in dates]
        return pd.DataFrame({"cal_date": dates, "is_open": is_open})


def test_trading_calendar_is_trading_day_from_cache(tmp_path: Path):
    repo = TradingCalendarRepository(tmp_path / "cache")
    _write_cache(
        repo,
        "A",
        open_dates=["2026-07-06", "2026-07-07", "2026-07-08"],
        closed_dates=["2026-07-04", "2026-07-05"],  # weekend
    )
    service = TradingCalendarService(repository=repo)

    result = service.is_trading_day("A", "2026-07-06")
    assert result["is_trading_day"] is True
    assert result["source"] == "cache"
    assert result["data_quality"]["status"] == "complete"

    result2 = service.is_trading_day("A", "2026-07-04")
    assert result2["is_trading_day"] is False
    assert result2["source"] == "cache"


def test_trading_calendar_next_previous_day(tmp_path: Path):
    repo = TradingCalendarRepository(tmp_path / "cache")
    _write_cache(
        repo,
        "US",
        open_dates=["2026-07-02", "2026-07-06", "2026-07-07"],
        closed_dates=["2026-07-03", "2026-07-04", "2026-07-05"],
    )
    service = TradingCalendarService(repository=repo)

    nxt = service.next_trading_day("US", "2026-07-03")
    assert nxt["date"] == "2026-07-06"
    assert nxt["is_trading_day"] is True

    prev = service.previous_trading_day("US", "2026-07-05")
    assert prev["date"] == "2026-07-02"


def test_trading_calendar_add_n_trading_days(tmp_path: Path):
    repo = TradingCalendarRepository(tmp_path / "cache")
    _write_cache(
        repo,
        "H",
        open_dates=["2026-07-01", "2026-07-02", "2026-07-06", "2026-07-07", "2026-07-08"],
        closed_dates=["2026-07-03", "2026-07-04", "2026-07-05"],
    )
    service = TradingCalendarService(repository=repo)

    forward = service.add_n_trading_days("H", "2026-07-01", 2)
    assert forward["date"] == "2026-07-06"

    backward = service.add_n_trading_days("H", "2026-07-08", -2)
    assert backward["date"] == "2026-07-06"

    too_far = service.add_n_trading_days("H", "2026-07-08", 10)
    assert too_far is None


def test_trading_calendar_market_separation(tmp_path: Path):
    repo = TradingCalendarRepository(tmp_path / "cache")
    # A is open on 2026-07-03 (e.g. no US-style holiday); US is closed
    # that same date (e.g. July 4th observed).
    _write_cache(repo, "A", open_dates=["2026-07-03"], closed_dates=[])
    _write_cache(repo, "US", open_dates=[], closed_dates=["2026-07-03"])
    service = TradingCalendarService(repository=repo)

    a_result = service.is_trading_day("A", "2026-07-03")
    us_result = service.is_trading_day("US", "2026-07-03")

    assert a_result["is_trading_day"] is True
    assert us_result["is_trading_day"] is False


def test_trading_calendar_missing_provider_records_data_gap(tmp_path: Path):
    gaps = DataGapRegistry(tmp_path / "data_gaps.jsonl")
    service = TradingCalendarService(repository=None, provider=None, gaps=gaps, allow_fallback=False)

    result = service.is_trading_day("A", "2026-07-06")

    assert result["source"] == "unknown"
    assert result["data_quality"]["status"] == "unknown"
    logged = gaps.list_gaps()
    assert any(g["severity"] == "error" and g["data_type"] == "trading_calendar" for g in logged)


def test_trading_calendar_fallback_is_marked_partial(tmp_path: Path):
    gaps = DataGapRegistry(tmp_path / "data_gaps.jsonl")
    service = TradingCalendarService(repository=None, provider=None, gaps=gaps, allow_fallback=True)

    result = service.is_trading_day("US", "2026-07-06")  # a Monday

    assert result["source"] == "fallback"
    assert result["data_quality"]["status"] == "partial"
    assert result["data_quality"]["warnings"]
    assert result["is_trading_day"] is True  # Monday under Mon-Fri fallback

    weekend_result = service.is_trading_day("US", "2026-07-04")  # a Saturday
    assert weekend_result["is_trading_day"] is False
    assert weekend_result["source"] == "fallback"


def test_trading_calendar_builds_cache_from_provider(tmp_path: Path):
    repo = TradingCalendarRepository(tmp_path / "cache")
    provider = _FakeCalendarProvider(
        open_dates=["20260706", "20260707"], closed_dates=["20260704", "20260705"]
    )
    service = TradingCalendarService(provider=provider, repository=repo)

    result = service.is_trading_day("A", "2026-07-06")
    assert result["source"] == "tushare"
    assert result["is_trading_day"] is True

    # The provider-sourced calendar should now be cached to disk.
    assert repo.exists("A")
    cached = repo.read("A")
    assert set(cached["date"]) == {"2026-07-04", "2026-07-05", "2026-07-06", "2026-07-07"}


def test_trading_calendar_trading_days_in_range_lists_only_open_days(tmp_path: Path):
    repo = TradingCalendarRepository(tmp_path / "cache")
    _write_cache(
        repo,
        "A",
        open_dates=["2026-07-06", "2026-07-07", "2026-07-08"],
        closed_dates=["2026-07-04", "2026-07-05"],
    )
    service = TradingCalendarService(repository=repo)

    days = service.trading_days_in_range("A", "2026-07-04", "2026-07-08")
    assert days == ["2026-07-06", "2026-07-07", "2026-07-08"]
