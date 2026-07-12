"""Data quality validators — Master Spec §10.1 / Phase 1 §4.5.

Pure data-completeness checks. These never decide whether a stock is a
good investment — that would be scoring/recommendation logic, which does
not belong here (Master Spec §5.6 / ADR-002).
"""

from __future__ import annotations

from typing import Any

import pandas as pd

DAILY_BAR_REQUIRED_COLUMNS = ["trade_date", "open", "high", "low", "close", "vol"]


def _result(status: str, missing_fields: list[str], warnings: list[str]) -> dict[str, Any]:
    return {"status": status, "missing_fields": missing_fields, "warnings": warnings}


def normalize_empty_dataframe(df: pd.DataFrame | None) -> dict[str, Any]:
    if df is None:
        return _result("unavailable", [], ["provider returned None"])
    if df.empty:
        return _result("unavailable", [], ["provider returned an empty result"])
    return _result("complete", [], [])


def validate_required_columns(df: pd.DataFrame | None, required: list[str]) -> dict[str, Any]:
    base = normalize_empty_dataframe(df)
    if base["status"] == "unavailable":
        return _result("unavailable", list(required), base["warnings"])
    missing = [c for c in required if c not in df.columns]  # type: ignore[union-attr]
    if missing:
        return _result("partial", missing, [])
    return _result("complete", [], [])


def validate_daily_bars(df: pd.DataFrame | None) -> dict[str, Any]:
    return validate_required_columns(df, DAILY_BAR_REQUIRED_COLUMNS)
