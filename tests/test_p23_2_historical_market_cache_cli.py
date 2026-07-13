from __future__ import annotations

import argparse
from pathlib import Path

import pytest

from scripts.build_p23_2_historical_market_cache import target_cache_completeness, valid_compact_date


def test_valid_compact_date_accepts_yyyymmdd():
    assert valid_compact_date("20260710") == "20260710"


def test_valid_compact_date_rejects_bad_format():
    with pytest.raises(argparse.ArgumentTypeError):
        valid_compact_date("2026-07-10")


def test_target_cache_completeness_allows_extra_cached_dates():
    report = target_cache_completeness(
        ["20260710", "20260713"],
        [
            Path("20250102.json"),
            Path("20260710.json"),
            Path("20260713.json"),
        ],
    )

    assert report["target_expected_count"] == 2
    assert report["target_available_count"] == 2
    assert report["target_missing_count"] == 0
    assert report["target_missing_dates"] == []
    assert report["target_complete"] is True


def test_target_cache_completeness_reports_missing_target_dates():
    report = target_cache_completeness(
        ["20260710", "20260713"],
        [Path("20260710.json")],
    )

    assert report["target_available_count"] == 1
    assert report["target_missing_count"] == 1
    assert report["target_missing_dates"] == ["20260713"]
    assert report["target_complete"] is False
