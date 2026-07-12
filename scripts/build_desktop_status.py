#!/usr/bin/env python3
"""build_desktop_status.py — P1C Desktop Read-Only Bridge (polished P1C.1).

Builds a **read-only** desktop-viewable status page for Project Aegis by
reading only already-persisted, real records/report files:

- `config/holdings.yaml` (real holdings — no broker connection, no price
  enrichment here, so no fabricated P&L is ever shown);
- `data/records/recommendations.jsonl` (RecommendationRepository);
- `data/records/paper_trades.jsonl` (PaperTradeRepository);
- `data/records/reviews.jsonl` (ReviewRepository);
- `data/records/data_gaps.jsonl` (DataGapRegistry);
- `data/processed/provider_diagnostics/provider_coverage_report.json`
  (the latest `scripts/validate_real_data.py` result, if any — used only
  for A股's core Tushare coverage signal);
- `data/processed/provider_router/provider_router_live_report.json` (the
  latest `scripts/validate_provider_router_live.py` result, if any);
- `data/processed/market_snapshot_smoke/market_snapshot_smoke_report.json`
  (the latest `scripts/run_market_snapshot_smoke.py` result, if any).

This script **never** triggers a new live network call, a new smoke run,
or a new recommendation cycle itself — it only reads what already
exists on disk and reports it honestly. If a source file/record is
missing, the corresponding section is rendered with an explicit
"no_data" state — never a fake market status, fake recommendation, or
fake P&L. Never reads/prints `.env` or any token. Never touches
`dashboard/index.html` — this produces a completely separate file,
`data/desktop/aegis_status.html`.

P1C.1 desktop polish:
- The generated HTML marks the whole page `translate="no"` and wraps
  every market code / status token / run_id / timestamp in a
  `class="notranslate" translate="no"` element, so browser translation
  tools can no longer mangle `A`/`US`/`confirmed_live` into unrelated
  Chinese words (the reported bug: `A` -> `一个`, `US` -> `我们`,
  `confirmed_live` -> `已确认直播`). Machine-readable JSON output
  (`aegis_status.json`, and every gateway command) is **unchanged** —
  only the HTML rendering layer maps raw enum values to human labels;
  no field name or enum value in the underlying status dict changed.
- A股 core coverage (`daily_bars`/`index_bars`/`stock_basic`/
  `trading_calendar`) is now read from
  `data/processed/provider_diagnostics/provider_coverage_report.json`
  (P1A's `validate_real_data.py` output) instead of always showing
  `unknown`. Enhanced data (`sector_classification`/`fundamentals`) is
  tracked and shown separately — it never affects the core coverage
  verdict, per the task's explicit instruction to keep A股 core
  confirmed even though enhanced data remains unconfirmed.
- Data gaps are split into "current, unresolved" and "historical,
  superseded by a later pass" — `data/records/data_gaps.jsonl` is never
  deleted or rewritten, but an old dependency-missing gap for a market
  that a *later* ProviderRouter-live/MarketSnapshot-smoke/provider-
  coverage run confirmed as passing is shown in a separate, collapsed
  section rather than the main "current gaps" list.

Usage:
    python scripts/build_desktop_status.py
    python scripts/build_desktop_status.py --output-html /tmp/aegis_status.html
"""

from __future__ import annotations

import argparse
import html as html_lib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

# Allow running this file directly without having installed the package.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aegis.data.gaps import DataGapRegistry  # noqa: E402
from aegis.paper.repository import PaperTradeRepository  # noqa: E402
from aegis.portfolio.holdings_loader import HoldingLoader  # noqa: E402
from aegis.recommendation.repository import RecommendationRepository  # noqa: E402
from aegis.review.metrics import compute_action_success_rate, compute_win_loss_count  # noqa: E402
from aegis.review.repository import ReviewRepository  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_HOLDINGS_PATH = REPO_ROOT / "config" / "holdings.yaml"
DEFAULT_RECORDS_DIR = REPO_ROOT / "data" / "records"
DEFAULT_PROVIDER_COVERAGE_REPORT = (
    REPO_ROOT / "data" / "processed" / "provider_diagnostics" / "provider_coverage_report.json"
)
DEFAULT_PROVIDER_ROUTER_LIVE_REPORT = (
    REPO_ROOT / "data" / "processed" / "provider_router" / "provider_router_live_report.json"
)
DEFAULT_MARKET_SNAPSHOT_SMOKE_REPORT = (
    REPO_ROOT / "data" / "processed" / "market_snapshot_smoke" / "market_snapshot_smoke_report.json"
)
DEFAULT_OUTPUT_HTML = REPO_ROOT / "data" / "desktop" / "aegis_status.html"
DEFAULT_OUTPUT_JSON = REPO_ROOT / "data" / "desktop" / "aegis_status.json"

GAP_DISPLAY_LIMIT = 20

# P1A's ProviderCoverageReport data_type vocabulary that counts as A股's
# "core" data path (Master Spec §... / P1A_PROVIDER_COVERAGE_DECISION.md).
# Deliberately excludes sector_classification/fundamentals — those are
# tracked separately as "enhanced" and never gate the core verdict.
_A_CORE_DATA_TYPES = {"daily_bars", "index_bars", "stock_basic", "trading_calendar"}
_A_ENHANCED_DATA_TYPES = {"sector_classification", "fundamentals"}

# Markers identifying the exact stale-gap shape this task calls out —
# matched case-insensitively against a DataGap's own `message` (never
# guessed from anything else). These alone are sufficient to call a gap
# a dependency-missing marker regardless of route text.
_STALE_GAP_MESSAGE_MARKERS = (
    "yfinance package is not installed",
    "yfinance client/package is not available",
    "dependency_missing",
    "network_unavailable",
)

# P1C.3: a second, narrower marker shape for the yahoo_finance H/US
# index_bars/daily_bars route specifically — matched only when the
# message *also* names the yahoo_finance route explicitly
# (`via provider_route='yahoo_finance'`), so a generic/unrelated
# "no bars returned" message (e.g. from a different provider, or a
# hand-written test message that never names the route) is never
# swept in by accident.
_STALE_GAP_EMPTY_ROUTE_MARKERS = (
    "no daily bars returned",
    "no index bars returned",
    "empty result",
)
_STALE_GAP_ROUTE_TEXT = "via provider_route='yahoo_finance'"

# P1C.3: the structural shape this task's stale-gap cleanup is scoped
# to — only H/US yahoo_finance index_bars/daily_bars gaps are ever
# eligible to be superseded this way. A股 gaps, stock_basic gaps, or
# gaps from any other provider are never touched by this logic.
_STALE_GAP_PROVIDER = "yahoo_finance"
_STALE_GAP_DATA_TYPES = {"index_bars", "daily_bars"}
_STALE_GAP_MARKETS = {"H", "US"}


def _safe_read_json(path: Path) -> Optional[dict]:
    """Read-only, never raises — a missing or malformed file is an honest
    "no data" state, never a crash and never a fabricated fallback."""
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001 - a corrupt report is "no data", not a crash
        return None


def _holdings_summary(holdings_path: Path) -> dict[str, Any]:
    holdings = HoldingLoader(holdings_path).load_holdings()
    if not holdings:
        return {"status": "no_data", "count": 0, "holdings": []}
    return {
        "status": "ok",
        "count": len(holdings),
        "holdings": [
            {
                "symbol": h.symbol,
                "name": h.name,
                "market": h.market,
                "shares": h.shares,
                "avg_cost": h.avg_cost,
                "currency": h.currency,
                "entry_date": h.entry_date,
                "status": h.status,
            }
            for h in holdings
        ],
    }


def _recommendations_summary(records_dir: Path) -> dict[str, Any]:
    recs = RecommendationRepository(records_dir).list_recommendations()
    if not recs:
        return {
            "status": "no_data",
            "count": 0,
            "total_records": 0,
            "status_counts": {},
            "latest": None,
        }

    # P1D.3: compute latest-per-symbol so status_counts reflects current state,
    # not an all-history tally that counts duplicate pipeline runs separately.
    # Selection rule: highest (created_at, file_position) per recommendation_id,
    # then highest (date, session_order, created_at) per symbol.
    _session_order = {"pre_market": 0, "midday": 1, "close": 2}

    # Step 1: latest per recommendation_id
    best_per_rec_id: dict[str, Any] = {}
    for i, r in enumerate(recs):
        key = (r.created_at, i)
        if r.recommendation_id not in best_per_rec_id or key > best_per_rec_id[r.recommendation_id][0]:
            best_per_rec_id[r.recommendation_id] = (key, r)
    latest_per_rec_id = [v for _, v in best_per_rec_id.values()]

    # Step 2: latest per symbol
    best_per_symbol: dict[str, Any] = {}
    for r in latest_per_rec_id:
        sym = r.symbol
        if sym is None:
            continue
        sort_key = (r.date or "", _session_order.get(r.session or "", 99), r.created_at or "")
        if sym not in best_per_symbol or sort_key > best_per_symbol[sym][0]:
            best_per_symbol[sym] = (sort_key, r)
    latest_per_symbol = [v for _, v in best_per_symbol.values()]

    # Status counts are based on latest per symbol only
    status_counts: dict[str, int] = {}
    for r in latest_per_symbol:
        status_counts[r.status] = status_counts.get(r.status, 0) + 1

    # "latest" shown in desktop is the single most-recent record across all symbols
    overall_latest = sorted(latest_per_symbol, key=lambda r: r.created_at or "")[-1]

    return {
        "status": "ok",
        "count": len(latest_per_symbol),
        "total_records": len(recs),
        "status_counts": status_counts,
        "latest": {
            "recommendation_id": overall_latest.recommendation_id,
            "date": overall_latest.date,
            "symbol": overall_latest.symbol,
            "market": overall_latest.market,
            "status": overall_latest.status,
            "action_label": overall_latest.action_label,
            "confidence": overall_latest.confidence,
            "created_at": overall_latest.created_at,
        },
    }


def _paper_summary(records_dir: Path) -> dict[str, Any]:
    trades = PaperTradeRepository(records_dir).list_all()
    if not trades:
        return {"status": "no_data", "count": 0, "open_count": 0, "closed_count": 0}
    open_count = sum(1 for t in trades if t.status == "open")
    closed_count = sum(1 for t in trades if t.status == "closed")
    return {"status": "ok", "count": len(trades), "open_count": open_count, "closed_count": closed_count}


def _review_summary(records_dir: Path) -> dict[str, Any]:
    reviews = ReviewRepository(records_dir).list_all()
    if not reviews:
        return {"status": "no_data", "count": 0, "success_rate": None, "win_loss": None}
    return {
        "status": "ok",
        "count": len(reviews),
        "success_rate": compute_action_success_rate(reviews),
        "win_loss": compute_win_loss_count(reviews),
    }


def _split_stale_gaps(
    gaps: list[dict], coverage: dict[str, str], confirming_created_at: dict[str, str]
) -> tuple[list[dict], list[dict]]:
    """Splits gaps into (current_unresolved, historical_superseded).

    A gap is only ever classified as historical/superseded if **all**
    of: (1) its `provider`/`data_type`/`market` match the yahoo_finance
    H/US index_bars/daily_bars route shape this cleanup is scoped to,
    (2) its `message` matches a known dependency-missing/network/
    empty-route marker for that route (P1C.3 broadens this beyond the
    original "yfinance package is not installed" wording to also catch
    the ProviderRouter's own "No {daily|index} bars returned for ...
    via provider_route='yahoo_finance' ..." message shape — matched
    only when the route text is present, so an unrelated "no bars
    returned"-style message from a different provider is never swept
    in by accident), (3) its `market` is *currently* confirmed
    (`confirmed_live`/`confirmed_tushare`) by a later report, and
    (4) the gap's own `created_at` predates that confirming report's
    `created_at`. A brand-new gap recorded *after* the latest pass is
    never hidden — this only retires genuinely old, already-superseded
    warnings, never masks a real regression. `data/records/data_gaps.jsonl`
    itself is never rewritten — only this display-layer split changes."""
    current: list[dict] = []
    historical: list[dict] = []
    for g in gaps:
        market = g.get("market")
        message = (g.get("message") or "").lower()
        is_dependency_marker = any(marker in message for marker in _STALE_GAP_MESSAGE_MARKERS)
        is_empty_route_marker = _STALE_GAP_ROUTE_TEXT in message and any(
            marker in message for marker in _STALE_GAP_EMPTY_ROUTE_MARKERS
        )
        is_stale_marker = is_dependency_marker or is_empty_route_marker
        is_stale_route_shape = (
            g.get("provider") == _STALE_GAP_PROVIDER
            and g.get("data_type") in _STALE_GAP_DATA_TYPES
            and market in _STALE_GAP_MARKETS
        )
        confirmed_now = coverage.get(market) in ("confirmed_live", "confirmed_tushare")
        confirming_at = confirming_created_at.get(market)
        gap_created_at = g.get("created_at")
        is_superseded = bool(confirming_at) and bool(gap_created_at) and gap_created_at < confirming_at
        if is_stale_marker and is_stale_route_shape and confirmed_now and is_superseded:
            historical.append(g)
        else:
            current.append(g)
    return current, historical


def _data_gaps_summary(
    records_dir: Path,
    *,
    coverage: Optional[dict[str, str]] = None,
    confirming_created_at: Optional[dict[str, str]] = None,
) -> dict[str, Any]:
    gaps = DataGapRegistry(records_dir / "data_gaps.jsonl").list_gaps()
    if not gaps:
        return {
            "status": "no_data",
            "count": 0,
            "current_count": 0,
            "historical_count": 0,
            "by_severity": {},
            "recent": [],
            "historical_recent": [],
        }
    by_severity: dict[str, int] = {}
    for g in gaps:
        by_severity[g["severity"]] = by_severity.get(g["severity"], 0) + 1

    if coverage is not None:
        current, historical = _split_stale_gaps(gaps, coverage, confirming_created_at or {})
    else:
        # Standalone call (e.g. the gateway's bare `data-gaps` command) —
        # no coverage context available, so nothing is hidden; this is
        # the same behavior this function had before P1C.1.
        current, historical = gaps, []

    return {
        "status": "ok",
        "count": len(gaps),
        "current_count": len(current),
        "historical_count": len(historical),
        "by_severity": by_severity,
        "recent": current[-GAP_DISPLAY_LIMIT:],
        "historical_recent": historical[-GAP_DISPLAY_LIMIT:],
    }


def _provider_router_live_summary(path: Path) -> dict[str, Any]:
    data = _safe_read_json(path)
    if data is None:
        return {"status": "no_data"}
    return {"status": "ok", "run_id": data.get("run_id"), "created_at": data.get("created_at"), "summary": data.get("summary")}


def _market_snapshot_smoke_summary(path: Path) -> dict[str, Any]:
    data = _safe_read_json(path)
    if data is None:
        return {"status": "no_data"}
    results = data.get("results", {}) or {}
    per_market = {
        market: {
            "overall_status": entry.get("overall_status"),
            "route_snapshot_consistency": entry.get("route_snapshot_consistency"),
            "index_bars_status": entry.get("index_bars_status"),
            "daily_bars_status": entry.get("daily_bars_status"),
        }
        for market, entry in results.items()
    }
    return {
        "status": "ok",
        "run_id": data.get("run_id"),
        "created_at": data.get("created_at"),
        "date": data.get("date"),
        "markets": per_market,
        "summary": data.get("summary"),
    }


def _provider_coverage_summary(path: Path) -> dict[str, Any]:
    """A股 core/enhanced Tushare coverage, read from P1A's
    `validate_real_data.py` output. Only ever reads `market == "A"`
    checks — H/US coverage in this same file predates P1B's H/US
    ProviderRouter route and is never used as their coverage signal
    (that comes from `_coverage_summary`'s provider_router_live/
    market_snapshot_smoke inputs instead)."""
    data = _safe_read_json(path)
    if data is None:
        return {"status": "no_data"}
    checks = data.get("checks", []) or []
    a_checks = [c for c in checks if c.get("market") == "A"]
    core_checks = [c for c in a_checks if c.get("data_type") in _A_CORE_DATA_TYPES]
    enhanced_checks = [c for c in a_checks if c.get("data_type") in _A_ENHANCED_DATA_TYPES]
    core_confirmed = bool(core_checks) and all(c.get("status") == "pass" for c in core_checks)
    enhanced_confirmed = bool(enhanced_checks) and all(c.get("status") == "pass" for c in enhanced_checks)
    return {
        "status": "ok",
        "run_id": data.get("run_id"),
        "created_at": data.get("created_at"),
        "a_core_confirmed": core_confirmed,
        "a_core_checks": [{"data_type": c.get("data_type"), "status": c.get("status")} for c in core_checks],
        "a_enhanced_confirmed": enhanced_confirmed,
        "a_enhanced_checks": [{"data_type": c.get("data_type"), "status": c.get("status")} for c in enhanced_checks],
    }


def _coverage_summary(provider_router_live: dict, market_snapshot_smoke: dict, provider_coverage: dict) -> dict[str, str]:
    """A/H/US data coverage summary derived only from the three report
    summaries above — never a new live call, never fabricated. Raw enum
    values only (`unknown`/`confirmed_tushare`/`confirmed_live`/...) —
    HTML rendering maps these to human labels separately; this function
    (and every gateway command built on it) never changes its output
    shape for display purposes."""
    coverage: dict[str, str] = {"A": "unknown", "H": "unknown", "US": "unknown"}
    if provider_coverage.get("status") == "ok" and provider_coverage.get("a_core_confirmed"):
        coverage["A"] = "confirmed_tushare"
    if provider_router_live.get("status") == "ok":
        summary = provider_router_live.get("summary") or {}
        if summary.get("pass_count", 0) > 0:
            coverage["H"] = "confirmed_live"
            coverage["US"] = "confirmed_live"
    if market_snapshot_smoke.get("status") == "ok":
        for market, entry in market_snapshot_smoke.get("markets", {}).items():
            if market not in coverage:
                continue
            if entry.get("overall_status") in ("pass", "partial"):
                coverage[market] = "confirmed_live"
            elif coverage[market] == "unknown":
                coverage[market] = entry.get("overall_status") or "unknown"
    return coverage


def _confirming_timestamps(
    coverage: dict[str, str], provider_router_live: dict, market_snapshot_smoke: dict, provider_coverage: dict
) -> dict[str, str]:
    """For each market currently shown as confirmed, the most recent
    report `created_at` that actually confirmed it — used only to decide
    whether an *older* stale DataGap has since been superseded. Never
    used for anything else (not a control-flow input to any other
    section)."""
    out: dict[str, str] = {}
    prl_pass = (
        provider_router_live.get("status") == "ok"
        and (provider_router_live.get("summary") or {}).get("pass_count", 0) > 0
    )
    for market in ("H", "US"):
        candidates: list[str] = []
        if prl_pass and provider_router_live.get("created_at"):
            candidates.append(provider_router_live["created_at"])
        smoke_markets = market_snapshot_smoke.get("markets", {}) if market_snapshot_smoke.get("status") == "ok" else {}
        smoke_entry = smoke_markets.get(market)
        if smoke_entry and smoke_entry.get("overall_status") in ("pass", "partial") and market_snapshot_smoke.get("created_at"):
            candidates.append(market_snapshot_smoke["created_at"])
        if candidates:
            out[market] = max(candidates)
    if provider_coverage.get("status") == "ok" and coverage.get("A") == "confirmed_tushare" and provider_coverage.get("created_at"):
        out["A"] = provider_coverage["created_at"]
    return out


def _next_operational_action(status: dict[str, Any]) -> str:
    """A single, deterministic, rule-based suggestion derived only from
    the sections above — never an LLM call, never a fabricated
    recommendation. Priority: fix a known data problem first, then note
    if there simply isn't any data yet, then fall back to "nothing
    urgent"."""
    smoke = status["market_snapshot_smoke"]
    if smoke["status"] == "no_data":
        return "Run scripts/run_market_snapshot_smoke.py locally to produce a MarketSnapshot smoke result."
    bad_markets = sorted(
        m for m, e in smoke.get("markets", {}).items() if e.get("overall_status") not in ("pass", "partial")
    )
    if bad_markets:
        return (
            f"Re-run scripts/run_market_snapshot_smoke.py locally — {', '.join(bad_markets)} "
            "not yet pass/partial (see market_snapshot_smoke section above)."
        )
    if status["recommendations"]["status"] == "no_data":
        return "No recommendations recorded yet — run the recommendation pipeline (scripts/run_pre_market.py) when ready."
    if status["data_gaps"].get("current_count", status["data_gaps"]["count"]) > 0:
        return f"Review {status['data_gaps'].get('current_count', status['data_gaps']['count'])} current data gap(s) in data/records/data_gaps.jsonl."
    return "No outstanding gaps detected from persisted records — nothing urgent to act on."


def build_status(
    *,
    holdings_path: Path = DEFAULT_HOLDINGS_PATH,
    records_dir: Path = DEFAULT_RECORDS_DIR,
    provider_coverage_report: Path = DEFAULT_PROVIDER_COVERAGE_REPORT,
    provider_router_live_report: Path = DEFAULT_PROVIDER_ROUTER_LIVE_REPORT,
    market_snapshot_smoke_report: Path = DEFAULT_MARKET_SNAPSHOT_SMOKE_REPORT,
) -> dict[str, Any]:
    """The single source of truth behind both the HTML page and every
    read-only gateway command that reports on status — built once here
    so `scripts/aegis_agent_gateway.py` never re-implements this logic."""
    provider_coverage = _provider_coverage_summary(provider_coverage_report)
    provider_router_live = _provider_router_live_summary(provider_router_live_report)
    market_snapshot_smoke = _market_snapshot_smoke_summary(market_snapshot_smoke_report)
    coverage = _coverage_summary(provider_router_live, market_snapshot_smoke, provider_coverage)
    confirming_created_at = _confirming_timestamps(coverage, provider_router_live, market_snapshot_smoke, provider_coverage)

    status: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(),
        "coverage": coverage,
        "provider_coverage": provider_coverage,
        "provider_router_live": provider_router_live,
        "market_snapshot_smoke": market_snapshot_smoke,
        "holdings": _holdings_summary(holdings_path),
        "recommendations": _recommendations_summary(records_dir),
        "paper_trading": _paper_summary(records_dir),
        "review": _review_summary(records_dir),
        "data_gaps": _data_gaps_summary(records_dir, coverage=coverage, confirming_created_at=confirming_created_at),
    }
    status["next_operational_action"] = _next_operational_action(status)
    return status


# -- HTML rendering ---------------------------------------------------------

_STATUS_BADGE_COLORS = {
    "ok": "#1a7f37",
    "pass": "#1a7f37",
    "confirmed_live": "#1a7f37",
    "confirmed_tushare": "#1a7f37",
    "partial": "#9a6700",
    "no_data": "#57606a",
    "unknown": "#57606a",
    "data_gap": "#9a6700",
    "dependency_missing": "#9a6700",
    "network_unavailable": "#9a6700",
    "not_configured": "#57606a",
    "skipped": "#57606a",
}

# P1C.1: human-readable Chinese labels for market codes and status
# tokens, so browser translation tools have nothing ambiguous left to
# "helpfully" mistranslate (`A` -> `一个`, `US` -> `我们`,
# `confirmed_live` -> `已确认直播` were all observed). These are a
# **display-only** mapping — every underlying JSON field keeps its raw
# enum value; `notranslate`/`translate="no"` on top is a second,
# independent layer of protection in case an unmapped token appears.
_MARKET_LABELS = {"A": "A股", "H": "H股", "US": "美股", "GLOBAL": "全球"}
_STATUS_LABELS = {
    "confirmed_live": "已验证",
    "confirmed_tushare": "已验证",
    "unknown": "未确认",
    "no_data": "暂无数据",
    "pass": "通过",
    "partial": "部分通过",
    "dependency_missing": "依赖缺失",
    "network_unavailable": "网络不可用",
    "not_configured": "未配置",
    "ok": "正常",
    "data_gap": "数据缺口",
    "skipped": "已跳过",
    "fail": "失败",
}


def _market_label(code: Optional[str]) -> str:
    if code is None:
        return "未知"
    return _MARKET_LABELS.get(code, code)


def _status_label(value: Optional[str]) -> str:
    text = value if value else "unknown"
    return _STATUS_LABELS.get(text, text)


def _market_cell(code: Optional[str]) -> str:
    """A market code rendered as its human label, wrapped so browser
    translation tools leave it alone."""
    label = _market_label(code)
    return f'<span class="notranslate" translate="no">{html_lib.escape(label)}</span>'


def _badge(value: Optional[str]) -> str:
    text = value if value else "unknown"
    color = _STATUS_BADGE_COLORS.get(text, "#57606a")
    label = html_lib.escape(_status_label(text))
    raw = html_lib.escape(str(text))
    return (
        f'<span class="notranslate" translate="no" title="{raw}" '
        f'style="background:{color};color:#fff;padding:2px 8px;border-radius:10px;font-size:0.8em;">{label}</span>'
    )


def _esc(value: Any) -> str:
    return html_lib.escape("" if value is None else str(value))


def _code(value: Any) -> str:
    """Like `<code>{_esc(value)}</code>`, but also protected from
    browser translation — run_ids/timestamps/raw tokens should never be
    auto-translated."""
    return f'<code class="notranslate" translate="no">{_esc(value)}</code>'


def _gap_row(g: dict[str, Any]) -> str:
    return (
        f"<tr><td>{_esc(g.get('date'))}</td><td>{_market_cell(g.get('market'))}</td>"
        f"<td>{_code(g.get('symbol'))}</td><td>{_code(g.get('data_type'))}</td>"
        f"<td>{_esc(g.get('severity'))}</td><td>{_esc(g.get('message'))}</td></tr>"
    )


def render_html(status: dict[str, Any]) -> str:
    coverage_rows = "".join(
        f"<tr><td>{_market_cell(market)}</td><td>{_badge(state)}</td></tr>" for market, state in status["coverage"].items()
    )

    provider_coverage = status.get("provider_coverage", {"status": "no_data"})
    if provider_coverage.get("status") != "ok":
        coverage_note_html = (
            '<p class="note">未找到 A 股 Provider Coverage 报告 '
            f"({_code('data/processed/provider_diagnostics/provider_coverage_report.json')})。</p>"
        )
    else:
        core_state = "已验证" if provider_coverage.get("a_core_confirmed") else "未确认"
        enhanced_state = "已验证" if provider_coverage.get("a_enhanced_confirmed") else "增强数据未确认（板块分类/基本面）"
        coverage_note_html = (
            f'<p class="note">A股核心数据（daily_bars/index_bars/stock_basic/trading_calendar）：{core_state}；'
            f"A股增强数据（sector_classification/fundamentals）：{enhanced_state}。</p>"
        )

    prl = status["provider_router_live"]
    if prl["status"] == "no_data":
        prl_html = "<p>No ProviderRouter live validation result found yet.</p>"
    else:
        s = prl.get("summary") or {}
        prl_html = (
            f"<p>run_id: {_code(prl.get('run_id'))} ({_code(prl.get('created_at'))})</p>"
            f"<p>pass={_esc(s.get('pass_count'))} fail={_esc(s.get('fail_count'))} "
            f"unknown={_esc(s.get('unknown_count'))} not_configured={_esc(s.get('not_configured_count'))} "
            f"dependency_missing={_esc(s.get('dependency_missing_count'))} "
            f"network_unavailable={_esc(s.get('network_unavailable_count'))}</p>"
        )

    smoke = status["market_snapshot_smoke"]
    if smoke["status"] == "no_data":
        smoke_html = "<p>No MarketSnapshot smoke result found yet.</p>"
    else:
        rows = "".join(
            f"<tr><td>{_market_cell(market)}</td><td>{_badge(entry.get('overall_status'))}</td>"
            f"<td>{_code(entry.get('route_snapshot_consistency'))}</td></tr>"
            for market, entry in smoke.get("markets", {}).items()
        )
        smoke_html = (
            f"<p>run_id: {_code(smoke.get('run_id'))} date={_esc(smoke.get('date'))} "
            f"({_code(smoke.get('created_at'))})</p>"
            f"<table><tr><th>Market</th><th>Overall</th><th>Consistency</th></tr>{rows}</table>"
        )

    holdings = status["holdings"]
    if holdings["status"] == "no_data":
        holdings_html = "<p>No holdings recorded in config/holdings.yaml.</p>"
    else:
        rows = "".join(
            f"<tr><td>{_code(h['symbol'])}</td><td>{_market_cell(h['market'])}</td><td>{_esc(h['shares'])}</td>"
            f"<td>{_esc(h['avg_cost'])} {_esc(h['currency'])}</td><td>{_esc(h['status'])}</td></tr>"
            for h in holdings["holdings"]
        )
        holdings_html = (
            f"<p>{holdings['count']} holding(s). No price enrichment or P&amp;L is computed by this page — "
            "facts only.</p>"
            f"<table><tr><th>Symbol</th><th>Market</th><th>Shares</th><th>Avg cost</th><th>Status</th></tr>{rows}</table>"
        )

    recs = status["recommendations"]
    if recs["status"] == "no_data":
        recs_html = "<p>No recommendations recorded yet.</p>"
    else:
        latest = recs["latest"]
        recs_html = (
            f"<p>{recs['count']} recommendation(s). By status: {_esc(recs['status_counts'])}</p>"
            f"<p>Latest: {_code(latest['symbol'])} ({_market_cell(latest['market'])}) — "
            f"{_badge(latest['status'])} — {_esc(latest['action_label'])} "
            f"(confidence={_esc(latest['confidence'])}, {_esc(latest['date'])})</p>"
        )

    paper = status["paper_trading"]
    paper_html = (
        "<p>No paper trades recorded yet.</p>"
        if paper["status"] == "no_data"
        else f"<p>{paper['count']} paper trade(s) — open={paper['open_count']}, closed={paper['closed_count']}.</p>"
    )

    review = status["review"]
    if review["status"] == "no_data":
        review_html = "<p>No reviews recorded yet.</p>"
    else:
        review_html = (
            f"<p>{review['count']} review(s). success_rate={_esc(review['success_rate'])}. "
            f"win/loss: {_esc(review['win_loss'])}</p>"
        )

    gaps = status["data_gaps"]
    if gaps["status"] == "no_data":
        gaps_html = "<p>No data gaps recorded.</p>"
    else:
        current_rows = "".join(_gap_row(g) for g in reversed(gaps["recent"]))
        current_count = gaps.get("current_count", gaps["count"])
        gaps_html = (
            f"<p>{current_count} 条当前未解决缺口（共记录 {gaps['count']} 条，按严重程度：{_esc(gaps['by_severity'])}）。"
            f"显示最近 {len(gaps['recent'])} 条：</p>"
            f"<table><tr><th>Date</th><th>Market</th><th>Symbol</th><th>Type</th><th>Severity</th><th>Message</th></tr>{current_rows}</table>"
        )
        historical = gaps.get("historical_recent", [])
        historical_count = gaps.get("historical_count", 0)
        if historical:
            historical_rows = "".join(_gap_row(g) for g in reversed(historical))
            gaps_html += (
                f"<details><summary>历史数据缺口 / 已被后续验证覆盖（{historical_count} 条，默认折叠）</summary>"
                f"<table><tr><th>Date</th><th>Market</th><th>Symbol</th><th>Type</th><th>Severity</th><th>Message</th></tr>{historical_rows}</table>"
                "</details>"
            )

    return f"""<!DOCTYPE html>
<html lang="zh-CN" translate="no">
<head>
<meta charset="utf-8">
<meta name="google" content="notranslate">
<title>Project Aegis — 桌面状态页（只读）</title>
<style>
body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; margin: 2em; color: #1f2328; background: #fff; }}
h1 {{ font-size: 1.4em; }}
h2 {{ font-size: 1.1em; margin-top: 1.6em; border-bottom: 1px solid #d0d7de; padding-bottom: 0.2em; }}
table {{ border-collapse: collapse; width: 100%; margin: 0.5em 0; }}
th, td {{ border: 1px solid #d0d7de; padding: 4px 8px; text-align: left; font-size: 0.9em; }}
th {{ background: #f6f8fa; }}
code {{ background: #f6f8fa; padding: 1px 4px; border-radius: 4px; }}
.note {{ color: #57606a; font-size: 0.85em; }}
.action {{ background: #ddf4ff; border: 1px solid #54aeff; padding: 0.8em; border-radius: 6px; }}
details {{ margin-top: 0.5em; }}
summary {{ cursor: pointer; color: #57606a; }}
</style>
</head>
<body translate="no" class="notranslate">
<h1>Project Aegis — 桌面状态页（只读 / Desktop Status, read-only）</h1>
<p class="note">Generated at {_code(status['generated_at'])}. This page only reads already-persisted records/report
files — it never fetches live market data, never fabricates P&amp;L/recommendations/market status, and never
modifies <code class="notranslate" translate="no">dashboard/index.html</code>. Regenerate with
<code class="notranslate" translate="no">python scripts/build_desktop_status.py</code>.</p>

<h2>Next operational action</h2>
<div class="action">{_esc(status['next_operational_action'])}</div>

<h2>A股 / H股 / 美股 数据覆盖</h2>
<table><tr><th>Market</th><th>Coverage</th></tr>{coverage_rows}</table>
{coverage_note_html}

<h2>Latest ProviderRouter live validation</h2>
{prl_html}

<h2>Latest MarketSnapshot smoke result</h2>
{smoke_html}

<h2>Holdings summary</h2>
{holdings_html}

<h2>Latest recommendations summary</h2>
{recs_html}

<h2>Paper trading summary</h2>
{paper_html}

<h2>Review summary</h2>
{review_html}

<h2>Current data gaps</h2>
{gaps_html}

</body>
</html>
"""


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build the read-only Project Aegis desktop status page (P1C/P1C.1). "
        "Never fetches live data, never modifies dashboard/index.html, never reads a token."
    )
    parser.add_argument("--holdings-path", default=str(DEFAULT_HOLDINGS_PATH))
    parser.add_argument("--records-dir", default=str(DEFAULT_RECORDS_DIR))
    parser.add_argument("--provider-coverage-report", default=str(DEFAULT_PROVIDER_COVERAGE_REPORT))
    parser.add_argument("--provider-router-live-report", default=str(DEFAULT_PROVIDER_ROUTER_LIVE_REPORT))
    parser.add_argument("--market-snapshot-smoke-report", default=str(DEFAULT_MARKET_SNAPSHOT_SMOKE_REPORT))
    parser.add_argument("--output-html", default=str(DEFAULT_OUTPUT_HTML))
    parser.add_argument("--output-json", default=str(DEFAULT_OUTPUT_JSON))
    args = parser.parse_args(argv)

    status = build_status(
        holdings_path=Path(args.holdings_path),
        records_dir=Path(args.records_dir),
        provider_coverage_report=Path(args.provider_coverage_report),
        provider_router_live_report=Path(args.provider_router_live_report),
        market_snapshot_smoke_report=Path(args.market_snapshot_smoke_report),
    )
    html_text = render_html(status)

    out_html = Path(args.output_html)
    out_html.parent.mkdir(parents=True, exist_ok=True)
    out_html.write_text(html_text, encoding="utf-8")

    out_json = Path(args.output_json)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(status, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

    print(f"Desktop status page written to {out_html}")
    print(f"Status JSON written to {out_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
