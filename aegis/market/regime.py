"""MarketRegimeAnalyzer / MarketSnapshotService — Phase 2 §5.

Deterministic, rule-based market-regime classification. No LLM, no
composite score, no fabricated data. Every branch here maps directly to a
rule written out in Claude_Cowork_PHASE2_MARKET_UNIVERSE.md §5.2/§5.3; if a
rule below looks arbitrary, check that file first before "fixing" it.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Mapping, Optional

import pandas as pd

from aegis.data.gaps import DataGapRegistry
from aegis.market.service import MarketDataService
from aegis.models.common import DataQuality
from aegis.models.market_snapshot import IndexSummary, MarketSnapshot

# Minimum bars below which we refuse to compute anything (pure "unknown").
# Between MIN_BARS_FOR_ANY_SIGNAL and MIN_BARS_FOR_FULL_WINDOW we still
# produce a best-effort regime using whatever window is available, but mark
# data_quality as "partial" — this is the "insufficient bars -> unknown or
# partial, no crash" behavior required by §8.1 test case 4.
MIN_BARS_FOR_ANY_SIGNAL = 5
FULL_WINDOW = 20
RECENT_RETURN_LOOKBACK = 5

# Default primary index per market. Best-effort placeholders — Phase 2 has
# no real Tushare token to verify these codes against; a later phase with
# real network access should confirm/adjust.
DEFAULT_PRIMARY_INDEX = {
    "A": "000300.SH",
    "H": "HSI.HI",
    "US": "SPX",
}

_RISK_RANK = {"low": 0, "medium": 1, "high": 2}


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def _snapshot_id(market: str, date: str, session: str) -> str:
    return f"mkt_{date.replace('-', '')}_{market}_{session}"


class MarketRegimeAnalyzer:
    """Turns raw index bars into a MarketSnapshot using simple, deterministic
    rules (Phase 2 §5.2). Never raises; missing/insufficient data degrades to
    "unknown" states plus a DATA_GAP summary (§5.3).
    """

    def analyze_market(
        self,
        *,
        market: str,
        date: str,
        session: str,
        index_bars: Mapping[str, pd.DataFrame],
        data_quality: Optional[DataQuality | dict] = None,
    ) -> MarketSnapshot:
        primary_index_code, df = self._pick_primary(index_bars)
        metrics = self._compute_metrics(df) if df is not None else None

        if metrics is None:
            return self._unknown_snapshot(
                market=market,
                date=date,
                session=session,
                primary_index_code=primary_index_code,
                data_quality=data_quality,
                reason="No index bars available for this market/session.",
            )

        trend_state = self._trend_state(metrics)
        liquidity_state = self._liquidity_state(metrics)
        sentiment_state = self._sentiment_state(metrics, trend_state)
        risk_level = self._risk_level(trend_state, liquidity_state)

        dq = self._resolve_data_quality(data_quality)
        if metrics["partial_window"]:
            dq = DataQuality(
                status="partial" if dq.status == "complete" else dq.status,
                missing_fields=dq.missing_fields,
                warnings=list(dict.fromkeys(dq.warnings + ["insufficient_bars_for_full_20d_window"])),
            )

        summary = (
            f"{market} {session}: trend={trend_state}, liquidity={liquidity_state}, "
            f"sentiment={sentiment_state}, risk={risk_level} "
            f"(latest_close={metrics['latest_close']:.4f}, mean20={metrics['mean_window']:.4f})."
        )

        return MarketSnapshot(
            snapshot_id=_snapshot_id(market, date, session),
            date=date,
            session=session,
            market=market,
            index_summary=IndexSummary(
                primary_index=primary_index_code,
                primary_index_change_pct=metrics["recent_return_pct"],
            ),
            trend_state=trend_state,
            liquidity_state=liquidity_state,
            sentiment_state=sentiment_state,
            sector_rotation=[],
            risk_level=risk_level,
            summary=summary,
            data_quality=dq,
            created_at=_now_iso(),
        )

    # -- internals ---------------------------------------------------

    def _pick_primary(self, index_bars: Mapping[str, pd.DataFrame]):
        if not index_bars:
            return None, None
        # P0 simplification: one primary index per market snapshot. If the
        # caller supplied more than one, take the first deterministically
        # (sorted by key) rather than guessing which is "the" benchmark.
        primary_key = sorted(index_bars.keys())[0]
        df = index_bars.get(primary_key)
        return primary_key, df

    def _compute_metrics(self, df: Optional[pd.DataFrame]) -> Optional[dict]:
        if df is None or df.empty or "close" not in df.columns:
            return None
        if "trade_date" in df.columns:
            df = df.sort_values("trade_date")
        df = df.reset_index(drop=True)

        n = len(df)
        if n < MIN_BARS_FOR_ANY_SIGNAL:
            return None

        window = min(n, FULL_WINDOW)
        recent = df.tail(window)
        latest_close = float(recent["close"].iloc[-1])
        mean_window = float(recent["close"].mean())

        lookback = min(RECENT_RETURN_LOOKBACK, n - 1)
        if lookback < 1:
            recent_return_pct = None
        else:
            prior_close = float(df["close"].iloc[-1 - lookback])
            recent_return_pct = (
                (latest_close - prior_close) / prior_close if prior_close else None
            )

        latest_vol = None
        avg_vol_window = None
        if "vol" in df.columns:
            vol_recent = recent["vol"].dropna()
            if not vol_recent.empty:
                latest_vol = float(recent["vol"].iloc[-1]) if pd.notna(recent["vol"].iloc[-1]) else None
                avg_vol_window = float(vol_recent.mean())

        return {
            "latest_close": latest_close,
            "mean_window": mean_window,
            "recent_return_pct": recent_return_pct,
            "latest_vol": latest_vol,
            "avg_vol_window": avg_vol_window,
            "partial_window": n < FULL_WINDOW,
        }

    def _trend_state(self, m: dict) -> str:
        if m["recent_return_pct"] is None:
            return "unknown"
        if m["latest_close"] > m["mean_window"] and m["recent_return_pct"] > 0:
            return "uptrend"
        if m["latest_close"] < m["mean_window"] and m["recent_return_pct"] < 0:
            return "downtrend"
        return "sideways"

    def _liquidity_state(self, m: dict) -> str:
        if m["latest_vol"] is None or m["avg_vol_window"] is None or m["avg_vol_window"] == 0:
            return "unknown"
        if m["latest_vol"] > 1.2 * m["avg_vol_window"]:
            return "strong"
        if m["latest_vol"] < 0.8 * m["avg_vol_window"]:
            return "weak"
        return "normal"

    def _sentiment_state(self, m: dict, trend_state: str) -> str:
        if m["recent_return_pct"] is None:
            return "unknown"
        if m["recent_return_pct"] > 0 and trend_state != "downtrend":
            return "risk_on"
        if m["recent_return_pct"] < 0 and trend_state == "downtrend":
            return "risk_off"
        return "neutral"

    def _risk_level(self, trend_state: str, liquidity_state: str) -> str:
        if trend_state == "unknown" or liquidity_state == "unknown":
            # Liquidity being unknown alone doesn't necessarily mean the
            # whole snapshot is unknown (trend may still be known), but the
            # spec's risk_level rules are only defined in terms of
            # downtrend/weak/uptrend/normal-strong; anything involving an
            # unknown input falls back to "medium" as a conservative
            # default rather than an undefined state.
            if trend_state == "unknown":
                return "unknown"
            return "medium"
        if trend_state == "downtrend" and liquidity_state == "weak":
            return "high"
        if trend_state == "downtrend" or liquidity_state == "weak":
            return "medium"
        if trend_state == "uptrend" and liquidity_state in ("normal", "strong"):
            return "low"
        # Sideways + normal/strong, or other combinations not explicitly
        # covered by §5.2: default to "medium" as a conservative P0
        # fallback, not specified verbatim by the spec.
        return "medium"

    def _resolve_data_quality(self, data_quality: Optional[DataQuality | dict]) -> DataQuality:
        if data_quality is None:
            return DataQuality(status="complete", missing_fields=[], warnings=[])
        if isinstance(data_quality, DataQuality):
            return data_quality
        return DataQuality(**data_quality)

    def _unknown_snapshot(
        self,
        *,
        market: str,
        date: str,
        session: str,
        primary_index_code: Optional[str],
        data_quality: Optional[DataQuality | dict],
        reason: str,
    ) -> MarketSnapshot:
        dq = self._resolve_data_quality(data_quality)
        status = dq.status if dq.status in ("partial", "unavailable", "missing") else "partial"
        return MarketSnapshot(
            snapshot_id=_snapshot_id(market, date, session),
            date=date,
            session=session,
            market=market,
            index_summary=IndexSummary(
                primary_index=primary_index_code,
                primary_index_change_pct=None,
            ),
            trend_state="unknown",
            liquidity_state="unknown",
            sentiment_state="unknown",
            sector_rotation=[],
            risk_level="unknown",
            summary=f"DATA_GAP: {reason}",
            data_quality=DataQuality(
                status=status,
                missing_fields=dq.missing_fields or ["index_bars"],
                warnings=dq.warnings,
            ),
            created_at=_now_iso(),
        )


def _aggregate_risk(levels: list[str]) -> str:
    known = [lvl for lvl in levels if lvl in _RISK_RANK]
    if not known:
        return "unknown"
    return max(known, key=lambda lvl: _RISK_RANK[lvl])


def _mode(values: list[str]) -> str:
    """Most frequent value, ties broken by first-seen order. Deterministic,
    not a statistical model — this is just for the GLOBAL aggregate text.
    """
    if not values:
        return "unknown"
    counts: dict[str, int] = {}
    order: list[str] = []
    for v in values:
        if v not in counts:
            order.append(v)
        counts[v] = counts.get(v, 0) + 1
    return max(order, key=lambda v: counts[v])


class MarketSnapshotService:
    """Orchestrates MarketDataService (index bars) + MarketRegimeAnalyzer
    into a list of MarketSnapshot, one per requested market plus a GLOBAL
    aggregate. Never raises to the caller (Phase 2 §5.4 acceptance).
    """

    def __init__(
        self,
        market_data_service: MarketDataService,
        analyzer: Optional[MarketRegimeAnalyzer] = None,
        gaps: Optional[DataGapRegistry] = None,
        lookback_days: int = 120,
        primary_index_by_market: Optional[Mapping[str, str]] = None,
    ):
        self.market_data_service = market_data_service
        self.analyzer = analyzer or MarketRegimeAnalyzer()
        self.gaps = gaps
        self.lookback_days = lookback_days
        self.primary_index_by_market = dict(primary_index_by_market or DEFAULT_PRIMARY_INDEX)

    def build_snapshots(
        self,
        *,
        date: str,
        session: str,
        markets: list[str],
    ) -> list[MarketSnapshot]:
        from aegis.utils.dates import lookback_range

        start, end = lookback_range(date, self.lookback_days)

        snapshots: list[MarketSnapshot] = []
        for market in markets:
            index_code = self.primary_index_by_market.get(market)
            if not index_code:
                if self.gaps is not None:
                    self.gaps.record_gap(
                        date=date,
                        market=market,
                        symbol=None,
                        provider="market_snapshot_service",
                        data_type="index_bars",
                        severity="warning",
                        message=f"No primary index configured for market {market}.",
                    )
                snapshots.append(
                    self.analyzer.analyze_market(
                        market=market,
                        date=date,
                        session=session,
                        index_bars={},
                        data_quality={"status": "unavailable", "missing_fields": ["primary_index"]},
                    )
                )
                continue

            df = self.market_data_service.get_index_bars_cached(index_code, market, start, end)
            index_bars = {index_code: df} if df is not None and not df.empty else {}
            snapshots.append(
                self.analyzer.analyze_market(
                    market=market,
                    date=date,
                    session=session,
                    index_bars=index_bars,
                )
            )

        snapshots.append(self._build_global(snapshots, date=date, session=session))
        return snapshots

    def _build_global(self, component_snapshots: list[MarketSnapshot], *, date: str, session: str) -> MarketSnapshot:
        if not component_snapshots:
            return MarketSnapshot(
                snapshot_id=_snapshot_id("GLOBAL", date, session),
                date=date,
                session=session,
                market="GLOBAL",
                index_summary=IndexSummary(primary_index=None, primary_index_change_pct=None),
                trend_state="unknown",
                liquidity_state="unknown",
                sentiment_state="unknown",
                sector_rotation=[],
                risk_level="unknown",
                summary="DATA_GAP: no component market snapshots available.",
                data_quality=DataQuality(status="unavailable", missing_fields=["A", "H", "US"], warnings=[]),
                created_at=_now_iso(),
            )

        trend_state = _mode([s.trend_state for s in component_snapshots])
        liquidity_state = _mode([s.liquidity_state for s in component_snapshots])
        sentiment_state = _mode([s.sentiment_state for s in component_snapshots])
        risk_level = _aggregate_risk([s.risk_level for s in component_snapshots])

        any_partial = any(s.data_quality.status != "complete" for s in component_snapshots)
        missing = [s.market for s in component_snapshots if s.data_quality.status != "complete"]

        parts = "; ".join(f"{s.market}: {s.trend_state}/{s.risk_level}" for s in component_snapshots)
        summary = f"GLOBAL aggregate of {parts}."
        if any_partial:
            summary = f"DATA_GAP: partial component data ({', '.join(missing)}). {summary}"

        return MarketSnapshot(
            snapshot_id=_snapshot_id("GLOBAL", date, session),
            date=date,
            session=session,
            market="GLOBAL",
            index_summary=IndexSummary(primary_index=None, primary_index_change_pct=None),
            trend_state=trend_state,
            liquidity_state=liquidity_state,
            sentiment_state=sentiment_state,
            sector_rotation=[],
            risk_level=risk_level,
            summary=summary,
            data_quality=DataQuality(
                status="partial" if any_partial else "complete",
                missing_fields=missing,
                warnings=[],
            ),
            created_at=_now_iso(),
        )
