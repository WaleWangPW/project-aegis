from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

from scripts.build_a_share_full_year_coverage_plan import build_plan


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def _seed_cache(cache: Path, *, start: date, days: int, rows: int = 5200, stock_rows: int = 5300) -> None:
    open_dates = [(start + timedelta(days=i)).strftime("%Y%m%d") for i in range(days)]
    _seed_cache_with_open_dates(cache, open_dates=open_dates, rows=rows, stock_rows=stock_rows)


def _seed_cache_with_open_dates(
    cache: Path,
    *,
    open_dates: list[str],
    rows: int = 5200,
    stock_rows: int = 5300,
    omit_daily: set[str] | None = None,
) -> None:
    omit_daily = omit_daily or set()
    _write_json(cache / "trade_calendar.json", {"open_dates": open_dates, "rows": []})
    _write_json(
        cache / "stock_basic_all.json",
        {"rows": [{"ts_code": f"{i:06d}.SZ", "name": f"S{i}"} for i in range(stock_rows)]},
    )
    for trade_date in open_dates:
        if trade_date in omit_daily:
            continue
        _write_json(
            cache / "daily_by_trade_date" / f"{trade_date}.json",
            {"trade_date": trade_date, "row_count": rows, "rows": [{"ts_code": "000001.SZ"}]},
        )


def test_full_year_plan_blocks_stale_full_cross_section_cache(tmp_path: Path):
    cache = tmp_path / "cache"
    _seed_cache(cache, start=date(2023, 9, 1), days=220)

    report = build_plan(
        cache_dir=cache,
        as_of=date(2026, 7, 13),
        run_id="test",
        command="test",
    )

    assert report["answer_label"] == "NO"
    assert report["coverage_status"] == "PARTIAL_STALE_FULL_CROSS_SECTION_CACHE"
    assert "daily_cache_is_stale_for_current_past_year" in report["blockers"]
    assert report["current_cache"]["daily_file_count"] == 220
    assert report["safety"]["network_used"] is False
    assert report["safety"]["no_order_placement"] is True
    assert report["overnight_openclaw_plan"]["owner"] == "stock-agent"


def test_full_year_plan_allows_current_materialized_candidate(tmp_path: Path):
    cache = tmp_path / "cache"
    _seed_cache(cache, start=date(2025, 7, 13), days=366)

    report = build_plan(
        cache_dir=cache,
        as_of=date(2026, 7, 13),
        run_id="test",
        command="test",
    )

    assert report["answer_label"] == "YES"
    assert report["coverage_status"] == "MATERIALIZED_CURRENT_FULL_YEAR_CANDIDATE"
    assert report["blockers"] == []
    assert report["safety"]["user_facing_suggestion_allowed"] is False


def test_full_year_plan_distinguishes_waiting_for_current_trading_day_daily(tmp_path: Path):
    cache = tmp_path / "cache"
    open_dates = [(date(2025, 7, 13) + timedelta(days=i)).strftime("%Y%m%d") for i in range(366)]
    target = open_dates[-1]
    _seed_cache_with_open_dates(cache, open_dates=open_dates, omit_daily={target})

    report = build_plan(
        cache_dir=cache,
        as_of=date(2026, 7, 13),
        run_id="test",
        command="test",
    )

    assert report["answer_label"] == "NO"
    assert report["coverage_status"] == "WAITING_CURRENT_TRADING_DAY_DAILY"
    assert report["blockers"] == ["current_trading_day_daily_not_yet_available"]
    assert report["current_cache"]["latest_expected_trade_date"] == "20260713"
    assert report["current_cache"]["previous_open_date_before_as_of"] == "20260712"
    assert report["current_day_retry"]["needed"] is True
    assert report["current_day_retry"]["retry_not_before_local_time"] == "15:30 Asia/Shanghai"
    assert "build-p23-2-historical-market-cache" in report["current_day_retry"]["command"]
