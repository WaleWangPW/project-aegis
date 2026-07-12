from __future__ import annotations

import argparse

import pytest

from scripts.build_p23_2_historical_market_cache import valid_compact_date


def test_valid_compact_date_accepts_yyyymmdd():
    assert valid_compact_date("20260710") == "20260710"


def test_valid_compact_date_rejects_bad_format():
    with pytest.raises(argparse.ArgumentTypeError):
        valid_compact_date("2026-07-10")
