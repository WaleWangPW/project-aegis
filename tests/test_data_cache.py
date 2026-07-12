"""Phase 1 tests for DataCache (Phase 1 spec §5.2)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from aegis.data.cache import DataCache


def test_write_then_read_roundtrip(tmp_path: Path):
    cache = DataCache(tmp_path)
    df = pd.DataFrame({"trade_date": ["20260701", "20260702"], "close": [109.5, 111.2]})
    cache.write_dataframe(df, market="US", data_type="daily_bars", key="CRCL_20260601_20260701")

    loaded = cache.read_dataframe(market="US", data_type="daily_bars", key="CRCL_20260601_20260701")
    assert loaded is not None
    assert list(loaded["close"]) == [109.5, 111.2]


def test_missing_cache_returns_none_consistently(tmp_path: Path):
    cache = DataCache(tmp_path)
    assert cache.read_dataframe(market="US", data_type="daily_bars", key="does_not_exist") is None
    assert cache.exists(market="US", data_type="daily_bars", key="does_not_exist") is False


def test_directories_auto_created(tmp_path: Path):
    cache = DataCache(tmp_path / "nested" / "cache_root")
    df = pd.DataFrame({"a": [1]})
    path = cache.write_dataframe(df, market="A", data_type="index_bars", key="000300")
    assert path.exists()
    assert path.parent.exists()


def test_no_secrets_in_path_or_content(tmp_path: Path):
    cache = DataCache(tmp_path)
    df = pd.DataFrame({"close": [1.0]})
    path = cache.write_dataframe(df, market="US", data_type="daily_bars", key="CRCL")
    content = path.read_text(encoding="utf-8")
    assert "TUSHARE_TOKEN" not in content
    assert "token" not in content.lower()
