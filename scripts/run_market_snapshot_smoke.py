#!/usr/bin/env python3
"""run_market_snapshot_smoke.py — P1B.4.

Smoke-run CLI proving the already-implemented MarketSnapshot layer
(`MarketSnapshotService` + `MarketRegimeAnalyzer`, Phase 2) can actually
consume H/US daily/index bars through `MarketDataService` +
`ProviderRouter`'s verified `yahoo_finance` route (P1B.2 local live
validation, P1B.3 wiring) and produce honest `MarketSnapshot` output for
H and US.

Scope: H/US only (mirrors `scripts/validate_provider_router_live.py`'s
restriction). This script deliberately never constructs a
`TushareAdapter` and never reads `.env`/`TUSHARE_TOKEN` — A股 already has
its own proven Tushare-first pipeline via `scripts/run_pre_market.py`,
which this script does not touch or duplicate.

Does NOT implement H/US universe/stock_basic, does NOT touch
UniverseBuilder/Signal Library/Expert Agents/Decision Engine/
Recommendation/Paper Trading/Dashboard — this is a narrow smoke check of
the MarketSnapshot layer alone.

No future data: for a given `--date`, `_DateBoundedMarketDataService`
(a script-local subclass — `aegis/market/service.py` itself is
untouched) filters every bars DataFrame returned by the real
`MarketDataService` to rows with `trade_date <= date` before it can ever
reach `MarketSnapshotService`/`MarketRegimeAnalyzer`. If a live route
happens to return bars dated after `--date`, they are dropped and an
info-level DataGap explains why — never silently dropped without a
trace, never fabricated.

P1B.4.1 smoke consistency fix: this script's own "did the route probe
pass" status now uses `_bars_are_usable()` — the *same* non-empty +
`"close"`-column + minimum-bar-count check `MarketRegimeAnalyzer.
_compute_metrics()` itself requires before it will compute anything —
instead of a naive `len(df) > 0`. Root cause of the original
inconsistency: a DataFrame can have real rows but zero usable columns
(`df.empty` is `True` when either axis has length 0, including the
column axis), which `len(df)` alone can't detect. Since the exact same
`filtered` DataFrame object that this script logs is what
`MarketSnapshotService.build_snapshots()` feeds to the analyzer (no
second, separate fetch — `_DateBoundedMarketDataService.
get_index_bars_cached()` is the *only* place index bars are ever
fetched for this smoke run), `_bars_are_usable()` mirroring the
analyzer's own check makes "route pass" and "snapshot has real data"
provably agree. The report now also carries a
`route_snapshot_consistency` field per market
(`route_pass_snapshot_pass` / `route_pass_snapshot_partial` /
`route_fail_snapshot_unknown`, or an explicitly labeled
`inconsistent_*` state that should never occur but is never silently
hidden as "pass" if it ever does). CLI exit code is now `0` only when
**every** requested market is `pass`/`partial` *and* no market reports
an `inconsistent_*` state; otherwise `1`.

Usage:
    python scripts/run_market_snapshot_smoke.py --date 2026-07-04
    python scripts/run_market_snapshot_smoke.py --date 2026-07-04 --markets H,US
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import pandas as pd

# Allow running this file directly without having installed the package.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aegis.data.gaps import DataGapRegistry  # noqa: E402
from aegis.data.provider_router import ProviderRouter  # noqa: E402
from aegis.data.provider_router_live_validation import DEFAULT_SAMPLES  # noqa: E402
from aegis.data.yahoo_finance_adapter import YahooFinanceAdapter  # noqa: E402
from aegis.market.regime import (  # noqa: E402
    DEFAULT_PRIMARY_INDEX,
    MIN_BARS_FOR_ANY_SIGNAL,
    MarketRegimeAnalyzer,
    MarketSnapshotService,
)
from aegis.market.service import MarketDataService  # noqa: E402
from aegis.utils.dates import lookback_range, to_compact  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROVIDERS_CONFIG = REPO_ROOT / "config" / "providers.yaml"
DEFAULT_OUTPUT = REPO_ROOT / "data" / "processed" / "market_snapshot_smoke" / "market_snapshot_smoke_report.json"
DEFAULT_GAPS_PATH = REPO_ROOT / "data" / "records" / "data_gaps.jsonl"

VALID_MARKETS = {"H", "US"}
LOOKBACK_DAYS = 120

# Only used to classify an *empty* bars result honestly from the DataGap
# message MarketDataService (or this script's own future-data filter)
# already recorded — never guessed from anything else, never used to
# change control flow.
_DEPENDENCY_ERROR_KEYWORDS = ("not installed", "no module named", "is not available in this environment")
_NETWORK_ERROR_KEYWORDS = (
    "network", "connection", "timeout", "timed out", "resolve", "dns",
    "proxy", "unreachable", "refused", "getaddrinfo", "temporary failure",
    "name resolution",
)
_EMPTY_RESULT_MARKERS = (
    "no index bars returned", "no daily bars returned", "returned zero rows",
)


class MarketSnapshotSmokeArgumentError(ValueError):
    """A controlled, expected CLI input error — never a raw traceback."""


def _validate_markets(markets: list[str]) -> None:
    if not markets:
        raise MarketSnapshotSmokeArgumentError("--markets must name at least one market.")
    unknown = [m for m in markets if m not in VALID_MARKETS]
    if unknown:
        raise MarketSnapshotSmokeArgumentError(
            f"Unknown market(s) {unknown} — this smoke run validates only H/US MarketSnapshot "
            f"generation through ProviderRouter's yahoo_finance route; valid markets are "
            f"{sorted(VALID_MARKETS)}. A股 already has its own proven Tushare-first pipeline "
            "via scripts/run_pre_market.py, out of scope here."
        )


def load_providers_config(config_path: str | Path) -> dict:
    import yaml

    path = Path(config_path)
    if not path.exists():
        raise MarketSnapshotSmokeArgumentError(f"Config file not found: {path}")
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def build_default_router(providers_config: dict, yahoo_adapter: Optional[YahooFinanceAdapter] = None) -> ProviderRouter:
    """Wired with **only** the `yahoo_finance` secondary provider — mirrors
    `aegis.data.provider_router_live_validation.build_default_router`.
    Deliberately never constructs a `TushareAdapter` or reads a token;
    this smoke run is scoped to H/US only."""
    return ProviderRouter(
        providers={"yahoo_finance": yahoo_adapter or YahooFinanceAdapter()},
        routing_config=providers_config,
    )


def _classify_empty_reason(message: Optional[str]) -> str:
    """Honest, read-only classification of *why* a bars fetch came back
    empty, based solely on the DataGap message already recorded for this
    exact call. Never fabricated, never guessed from timing/heuristics."""
    if not message:
        return "unknown"
    lowered = message.lower()
    if any(keyword in lowered for keyword in _DEPENDENCY_ERROR_KEYWORDS):
        return "dependency_missing"
    if any(keyword in lowered for keyword in _NETWORK_ERROR_KEYWORDS):
        return "network_unavailable"
    if any(marker in lowered for marker in _EMPTY_RESULT_MARKERS):
        return "unknown"
    return "data_gap"


def _bars_are_usable(df: Optional[pd.DataFrame]) -> bool:
    """P1B.4.1: the single source of truth for "does this provider
    response actually count as real data" — mirrors exactly what
    `MarketRegimeAnalyzer._compute_metrics()` itself requires before it
    will compute anything: non-empty, has a `"close"` column, and at
    least `MIN_BARS_FOR_ANY_SIGNAL` rows. Using this (instead of a naive
    `len(df) > 0`) for this script's own "route pass" status guarantees
    the smoke report can never again claim "pass" for a route whose bars
    the analyzer would itself reject as unusable — which is exactly what
    happened in the original bug: a real response had rows (`len(df) >
    0`) but zero usable OHLCV columns (`df.empty` was `True`, since
    `.empty` accounts for the column axis too), so `MarketSnapshotService`
    correctly treated it as no data while this script's old `len()`-based
    check reported a false "pass"."""
    if df is None or df.empty or "close" not in df.columns:
        return False
    return len(df) >= MIN_BARS_FOR_ANY_SIGNAL


def _filter_future_rows(df: pd.DataFrame, as_of_compact: str) -> tuple[pd.DataFrame, int]:
    """Filters a bars DataFrame to rows with `trade_date <= as_of_compact`.
    Only ever removes rows — never fabricates or reorders any."""
    if df is None or df.empty or "trade_date" not in df.columns:
        return (df if df is not None else pd.DataFrame()), 0
    before = len(df)
    filtered = df[df["trade_date"].astype(str) <= as_of_compact].reset_index(drop=True)
    return filtered, before - len(filtered)


def _safe_route_name(router: Any, market: str, data_type: str) -> Optional[str]:
    describe = getattr(router, "route_name_for", None)
    if not callable(describe):
        return None
    try:
        return describe(market, data_type)
    except Exception:  # noqa: BLE001 - diagnostic label only, must never raise
        return None


class _DateBoundedMarketDataService(MarketDataService):
    """Script-local wrapper — does **not** modify `aegis/market/service.py`.
    Enforces "no future data" for this smoke run only, and records
    per-call diagnostics (`call_log`) so the smoke report can state
    exactly how many rows came back and via which route, without a
    second, duplicate fetch."""

    def __init__(self, *args: Any, as_of_compact: str, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self._as_of_compact = as_of_compact
        self.call_log: dict[tuple[str, str, str], dict[str, Any]] = {}

    def _log_call(self, data_type: str, market: str, key: Optional[str], gaps_before: int, filtered: pd.DataFrame) -> None:
        rows = 0 if filtered is None else len(filtered)
        has_columns = filtered is not None and not filtered.empty and "close" in filtered.columns
        usable = _bars_are_usable(filtered)
        if usable:
            status = "pass"
        elif has_columns:
            # Real rows, a real "close" column, but fewer than
            # MIN_BARS_FOR_ANY_SIGNAL — MarketRegimeAnalyzer would also
            # refuse to compute anything from this, so this is an honest
            # data_gap, not a false "pass".
            status = "data_gap"
        else:
            status = _classify_empty_reason(self._new_gap_message(gaps_before, market, key, data_type))
        route = self._route_label(market, data_type)
        self.call_log[(data_type, market, key)] = {"rows": rows, "usable": usable, "route": route, "status": status}

    def _new_gap_message(self, gaps_before: int, market: str, symbol: Optional[str], data_type: str) -> Optional[str]:
        if self.gaps is None:
            return None
        new_gaps = self.gaps.list_gaps()[gaps_before:]
        matching = [
            g for g in new_gaps
            if g.get("market") == market and g.get("symbol") == symbol and g.get("data_type") == data_type
        ]
        return matching[-1]["message"] if matching else None

    def _record_future_data_gap(self, *, market: str, symbol: str, data_type: str, dropped: int, end: str) -> None:
        if self.gaps is None or not dropped:
            return
        self.gaps.record_gap(
            date=end, market=market, symbol=symbol, data_type=data_type,
            provider="market_snapshot_smoke", severity="info",
            message=(
                f"Dropped {dropped} {data_type} row(s) for {symbol} ({market}) dated after "
                f"{self._as_of_compact} to enforce no-future-data for this smoke run."
            ),
            consumer_impact=["market_snapshot smoke run excludes any bar dated after --date"],
        )

    def get_index_bars_cached(self, index_code: str, market: str, start: str, end: str) -> pd.DataFrame:
        gaps_before = len(self.gaps.list_gaps()) if self.gaps is not None else 0
        df = super().get_index_bars_cached(index_code, market, start, end)
        filtered, dropped = _filter_future_rows(df, self._as_of_compact)
        self._record_future_data_gap(market=market, symbol=index_code, data_type="index_bars", dropped=dropped, end=end)
        self._log_call("index_bars", market, index_code, gaps_before, filtered)
        return filtered

    def get_daily_bars_cached(self, symbol: str, market: str, start: str, end: str) -> pd.DataFrame:
        gaps_before = len(self.gaps.list_gaps()) if self.gaps is not None else 0
        df = super().get_daily_bars_cached(symbol, market, start, end)
        filtered, dropped = _filter_future_rows(df, self._as_of_compact)
        self._record_future_data_gap(market=market, symbol=symbol, data_type="daily_bars", dropped=dropped, end=end)
        self._log_call("daily_bars", market, symbol, gaps_before, filtered)
        return filtered


def _summarize(results: dict[str, Any]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for entry in results.values():
        status = entry["overall_status"]
        counts[status] = counts.get(status, 0) + 1
    return counts


def run_market_snapshot_smoke(
    *,
    date: str,
    markets: list[str],
    output_path: str | Path = DEFAULT_OUTPUT,
    config_path: str | Path = DEFAULT_PROVIDERS_CONFIG,
    router: Optional[ProviderRouter] = None,
    gaps_path: str | Path = DEFAULT_GAPS_PATH,
    lookback_days: int = LOOKBACK_DAYS,
) -> dict[str, Any]:
    """Testable core behind the CLI. `router` is injectable for tests
    (fake `yahoo_finance` adapter only — never a real network call from
    pytest). Never reads `.env`/`os.environ`; never constructs a
    `TushareAdapter` or requires a token."""
    _validate_markets(markets)
    as_of_compact = to_compact(date)
    start, end = lookback_range(date, lookback_days)

    providers_config = None if router is not None else load_providers_config(config_path)
    if router is None:
        router = build_default_router(providers_config)

    gaps = DataGapRegistry(gaps_path)
    market_data_service = _DateBoundedMarketDataService(
        provider_router=router, cache=None, gaps=gaps, as_of_compact=as_of_compact,
    )
    snapshot_service = MarketSnapshotService(
        market_data_service=market_data_service, gaps=gaps, lookback_days=lookback_days,
    )

    # The real, unmodified MarketSnapshotService/MarketRegimeAnalyzer
    # build the actual MarketSnapshot for each requested market — this is
    # the "already-implemented layer" this smoke run verifies.
    snapshots = snapshot_service.build_snapshots(date=date, session="pre_market", markets=markets)
    snapshot_by_market = {s.market: s for s in snapshots if s.market in markets}

    results: dict[str, Any] = {}
    for market in markets:
        index_code = DEFAULT_PRIMARY_INDEX.get(market)
        index_info = market_data_service.call_log.get(
            ("index_bars", market, index_code),
            {"rows": 0, "usable": False, "route": _safe_route_name(router, market, "index_bars"), "status": "skipped"},
        )

        # Daily bars are not part of MarketSnapshot's own computation, but
        # the task asks this smoke run to also prove the daily route
        # works end to end — using the same sample symbols already
        # established in P1B.2 (CRCL only ever appears here as an
        # ordinary US sample symbol, never as a market index).
        daily_sample = DEFAULT_SAMPLES.get(market, {}).get("daily_bars")
        if daily_sample:
            market_data_service.get_daily_bars_cached(daily_sample, market, start, end)
            daily_info = market_data_service.call_log.get(
                ("daily_bars", market, daily_sample),
                {"rows": 0, "usable": False, "route": _safe_route_name(router, market, "daily_bars"), "status": "unknown"},
            )
        else:
            daily_info = {"rows": 0, "usable": False, "route": None, "status": "skipped"}

        snapshot = snapshot_by_market.get(market)
        snapshot_dump = snapshot.model_dump() if snapshot is not None else None

        # P1B.4.1: classify (route, snapshot) into one of the three
        # expected consistency states, or an explicitly labeled
        # "inconsistent_*" state that should be structurally impossible
        # now that index_info["status"]=="pass" and "the analyzer got real
        # data" both derive from the exact same _bars_are_usable() check
        # applied to the exact same DataFrame — but is never silently
        # reported as a false "pass" if it somehow still occurs.
        route_pass = index_info["status"] == "pass"
        snapshot_is_data_gap = snapshot is None or snapshot.trend_state == "unknown"
        snapshot_is_complete = (not snapshot_is_data_gap) and snapshot.data_quality.status == "complete"
        snapshot_is_partial = (not snapshot_is_data_gap) and not snapshot_is_complete

        if route_pass and snapshot_is_complete:
            consistency = "route_pass_snapshot_pass"
            overall_status = "pass"
        elif route_pass and snapshot_is_partial:
            consistency = "route_pass_snapshot_partial"
            overall_status = "partial"
        elif (not route_pass) and snapshot_is_data_gap:
            consistency = "route_fail_snapshot_unknown"
            overall_status = index_info["status"]
        elif route_pass and snapshot_is_data_gap:
            consistency = "inconsistent_route_pass_snapshot_data_gap"
            overall_status = "partial"
        else:
            consistency = "inconsistent_route_fail_snapshot_has_data"
            overall_status = index_info["status"]

        results[market] = {
            "market": market,
            "primary_index_internal_code": index_code,
            "index_bars_provider_route": index_info["route"],
            "index_bars_rows_returned": index_info["rows"],
            "index_bars_usable": index_info["usable"],
            "index_bars_status": index_info["status"],
            "daily_bars_sample_symbol": daily_sample,
            "daily_bars_provider_route": daily_info["route"],
            "daily_bars_rows_returned": daily_info["rows"],
            "daily_bars_usable": daily_info["usable"],
            "daily_bars_status": daily_info["status"],
            "market_snapshot": snapshot_dump,
            "route_snapshot_consistency": consistency,
            "overall_status": overall_status,
        }

    report = {
        "run_id": f"market_snapshot_smoke_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}",
        "created_at": datetime.now(timezone.utc).astimezone().isoformat(),
        "date": date,
        "markets": markets,
        "lookback_days": lookback_days,
        "fetch_window": {"start": start, "end": end},
        "results": results,
        "summary": _summarize(results),
        "note": (
            "H/US-only smoke run of the existing MarketSnapshot layer "
            "(MarketRegimeAnalyzer + MarketSnapshotService) against MarketDataService + "
            "ProviderRouter's yahoo_finance route. Never constructs a TushareAdapter, never "
            "reads a token. Bars dated after --date are filtered out before analysis; "
            "dropped rows are recorded as an info-level DataGap, never silently discarded. "
            "fetch_window is the (start, end) range actually requested from the provider "
            "(bounded by --lookback-days ending at --date); as_of_compact filtering is a "
            "separate, always-applied no-future-data guarantee on top of it. "
            "P1B.4.1: per-market route_snapshot_consistency is one of "
            "route_pass_snapshot_pass / route_pass_snapshot_partial / "
            "route_fail_snapshot_unknown, or an explicitly labeled inconsistent_* state "
            "that should never occur (index_bars_status now reflects the same "
            "usable-bars check MarketRegimeAnalyzer itself applies, not a raw row count) "
            "but is never silently reported as a false pass if it ever does. CLI exit "
            "code is 0 only when every requested market is pass/partial and no market "
            "reports an inconsistent_* state; otherwise 1."
        ),
    }
    write_report(report, output_path)
    return report


def write_report(report: dict[str, Any], output_path: str | Path) -> None:
    out_path = Path(output_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


def _print_summary(report: dict[str, Any], output_path: str) -> None:
    print(f"Market snapshot smoke run_id: {report['run_id']}")
    print(f"date: {report['date']}  markets: {','.join(report['markets'])}")
    for market, entry in report["results"].items():
        snapshot = entry["market_snapshot"] or {}
        print(
            f"  [{entry['overall_status']}] {market}: "
            f"index={entry['index_bars_status']} ({entry['index_bars_rows_returned']} rows via {entry['index_bars_provider_route']}), "
            f"daily={entry['daily_bars_status']} ({entry['daily_bars_rows_returned']} rows via {entry['daily_bars_provider_route']}), "
            f"trend_state={snapshot.get('trend_state')}, "
            f"consistency={entry.get('route_snapshot_consistency')}"
        )
    print(f"summary: {report['summary']}")
    print(f"Output: {output_path}")


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Project Aegis P1B.4 H/US MarketSnapshot smoke run "
        "(never constructs a TushareAdapter, never reads a token)."
    )
    parser.add_argument("--date", required=True, help="YYYY-MM-DD")
    parser.add_argument("--markets", default="H,US", help="Comma-separated, e.g. H,US")
    parser.add_argument("--config", default=str(DEFAULT_PROVIDERS_CONFIG))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--gaps-path", default=str(DEFAULT_GAPS_PATH))
    parser.add_argument(
        "--lookback-days", type=int, default=LOOKBACK_DAYS,
        help=f"Calendar days to fetch before --date (default: {LOOKBACK_DAYS}). A wide window "
        "naturally survives a weekend/holiday --date, since it's the window that must contain "
        "at least one real trading day, not the --date itself.",
    )
    args = parser.parse_args(argv)

    markets = [m.strip().upper() for m in args.markets.split(",") if m.strip()]

    try:
        report = run_market_snapshot_smoke(
            date=args.date,
            markets=markets,
            output_path=args.output,
            config_path=args.config,
            gaps_path=args.gaps_path,
            lookback_days=args.lookback_days,
        )
    except MarketSnapshotSmokeArgumentError as exc:
        print(f"run_market_snapshot_smoke argument error: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001 - controlled, never a raw traceback; never prints secrets
        print(f"run_market_snapshot_smoke failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1

    _print_summary(report, args.output)

    # P1B.4.1: deterministic exit policy — 0 only when *every* requested
    # market is pass/partial and none reports a structurally-should-never-
    # happen inconsistent_* consistency state; non-zero when any requested
    # market fails/reports unknown due to no data/dependency/network, or
    # when a route/snapshot inconsistency is detected (never silently
    # treated as success).
    all_pass_or_partial = all(e["overall_status"] in ("pass", "partial") for e in report["results"].values())
    any_inconsistent = any(
        str(e.get("route_snapshot_consistency", "")).startswith("inconsistent") for e in report["results"].values()
    )
    return 0 if (all_pass_or_partial and not any_inconsistent) else 1


if __name__ == "__main__":
    raise SystemExit(main())
