"""Universe filter predicates — Phase 2 §6.3/§6.5.

Pure functions, no I/O, no scoring. Each function takes one row of
"stock basic + optional liquidity metrics" data (a plain dict — see
`aegis/universe/builder.py` for the expected optional column names) plus
the market's config block from `config/universe.yaml`, and returns a
(passes: bool, filter_reason: list[str], warnings: list[str]) tuple.

Deliberate P0 simplification: liquidity/volume metrics are read from
optional columns on the stock-basic row (e.g. `avg_turnover_amount`,
`avg_dollar_volume`) rather than a full per-symbol daily-bar fetch, to keep
this phase small, deterministic, and mockable without real network access.
A later phase can replace this with real volume computed via
MarketDataService without changing this module's public shape.
"""

from __future__ import annotations

from typing import Any


def passes_basic_filters(row: dict[str, Any], market: str, market_cfg: dict[str, Any]) -> tuple[bool, list[str], list[str]]:
    """Returns (passes, filter_reason, warnings)."""
    warnings: list[str] = []

    if market_cfg.get("exclude_suspended", True) and row.get("is_suspended"):
        return False, ["suspended"], warnings

    if market == "A" and market_cfg.get("exclude_st") and row.get("is_st"):
        return False, ["st_excluded"], warnings

    liquidity_ok, liquidity_warnings = _liquidity_ok(row, market, market_cfg)
    warnings.extend(liquidity_warnings)
    if not liquidity_ok:
        return False, ["liquidity_below_threshold"], warnings

    history_days = row.get("days_of_history")
    lookback = market_cfg.get("lookback_days", 120)
    min_history = min(20, lookback)
    if history_days is not None and history_days < min_history:
        return False, ["insufficient_history"], warnings

    return True, ["liquidity_ok"], warnings


def _liquidity_ok(row: dict[str, Any], market: str, market_cfg: dict[str, Any]) -> tuple[bool, list[str]]:
    warnings: list[str] = []

    if market == "US":
        dollar_volume = row.get("avg_dollar_volume")
        if dollar_volume is None:
            warnings.append("missing_dollar_volume_fallback_to_volume")
            volume = row.get("avg_volume")
            return (volume is not None and volume > 0), warnings
        threshold = market_cfg.get("min_dollar_volume", 0)
        return dollar_volume >= threshold, warnings

    # A / H: turnover-amount based threshold, market-specific value from config.
    turnover = row.get("avg_turnover_amount")
    if turnover is None:
        warnings.append("missing_turnover_amount")
        return False, warnings
    threshold = market_cfg.get("min_liquidity_amount", 0)
    return turnover >= threshold, warnings


def enrichment_reasons(row: dict[str, Any]) -> list[str]:
    """Best-effort, opportunistic tags from the allowed P0 vocabulary
    (Phase 2 §6.3). Only added when the underlying optional field is
    actually present — never guessed. Every tag here is additive context on
    top of `liquidity_ok`, not a score.
    """
    reasons: list[str] = []

    pct_chg_20d = row.get("pct_chg_20d")
    if pct_chg_20d is not None and pct_chg_20d > 0:
        reasons.append("trend_improving")

    volume_ratio = row.get("volume_ratio")
    if volume_ratio is not None and volume_ratio > 1.2:
        reasons.append("volume_expansion")

    relative_strength = row.get("relative_strength_vs_index")
    if relative_strength is not None and relative_strength > 0:
        reasons.append("relative_strength_basic")

    sector_momentum_rank = row.get("sector_momentum_rank")
    if sector_momentum_rank is not None and sector_momentum_rank <= 3:
        reasons.append("sector_strength_basic")

    if row.get("is_suspended") is False and row.get("is_st") is False:
        reasons.append("risk_acceptable_basic")

    return reasons
