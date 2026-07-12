"""P1C tests for scripts/build_desktop_status.py.

Proves the desktop status builder only ever reads already-persisted
records/report files, never fetches live data, degrades to honest
"no_data" states when a source is missing, never fabricates P&L/
recommendations/market status, and never touches `dashboard/index.html`.
"""

from __future__ import annotations

import inspect
import json
from pathlib import Path

import pytest
import yaml

import scripts.build_desktop_status as build_desktop_status
from scripts.build_desktop_status import build_status, render_html

REPO_ROOT = Path(__file__).resolve().parents[1]


def _write_holdings(path: Path, holdings: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump({"holdings": holdings}), encoding="utf-8")


def test_all_sections_are_honest_no_data_when_nothing_exists(tmp_path: Path):
    status = build_status(
        holdings_path=tmp_path / "no_holdings.yaml",
        records_dir=tmp_path / "empty_records",
        provider_coverage_report=tmp_path / "no_coverage.json",
        provider_router_live_report=tmp_path / "no_report.json",
        market_snapshot_smoke_report=tmp_path / "no_smoke.json",
    )
    assert status["holdings"]["status"] == "no_data"
    assert status["provider_coverage"]["status"] == "no_data"
    assert status["recommendations"]["status"] == "no_data"
    assert status["paper_trading"]["status"] == "no_data"
    assert status["review"]["status"] == "no_data"
    assert status["data_gaps"]["status"] == "no_data"
    assert status["provider_router_live"]["status"] == "no_data"
    assert status["market_snapshot_smoke"]["status"] == "no_data"
    assert status["coverage"] == {"A": "unknown", "H": "unknown", "US": "unknown"}
    # Honest empty states, never a fabricated recommendation/P&L/market status.
    assert status["next_operational_action"]  # always some deterministic string
    # The page must still render without raising on a fully-empty status.
    html_text = render_html(status)
    assert "Project Aegis" in html_text


def test_holdings_summary_reads_real_holdings_with_no_fabricated_pnl(tmp_path: Path):
    holdings_path = tmp_path / "holdings.yaml"
    _write_holdings(
        holdings_path,
        [
            {
                "holding_id": "hold_US_CRCL_20260701",
                "symbol": "CRCL",
                "name": "Circle Internet Group",
                "market": "US",
                "shares": 254,
                "avg_cost": 109.157,
                "currency": "USD",
                "entry_date": "2026-07-01",
                "status": "open",
            }
        ],
    )
    status = build_status(
        holdings_path=holdings_path,
        records_dir=tmp_path / "records",
        provider_coverage_report=tmp_path / "no_coverage.json",
        provider_router_live_report=tmp_path / "no_report.json",
        market_snapshot_smoke_report=tmp_path / "no_smoke.json",
    )
    holdings = status["holdings"]
    assert holdings["status"] == "ok"
    assert holdings["count"] == 1
    assert holdings["holdings"][0]["symbol"] == "CRCL"
    # No price enrichment / no P&L fields at all — this builder never
    # fabricates market_value/unrealized_pnl.
    assert "market_value" not in holdings["holdings"][0]
    assert "unrealized_pnl" not in holdings["holdings"][0]


def test_provider_router_live_and_smoke_reports_are_read_not_recomputed(tmp_path: Path):
    prl_path = tmp_path / "provider_router_live_report.json"
    prl_path.write_text(
        json.dumps({"run_id": "provider_router_live_TEST", "created_at": "2026-07-05T00:00:00+00:00",
                    "summary": {"pass_count": 4, "fail_count": 0}}),
        encoding="utf-8",
    )
    smoke_path = tmp_path / "market_snapshot_smoke_report.json"
    smoke_path.write_text(
        json.dumps({
            "run_id": "market_snapshot_smoke_TEST",
            "created_at": "2026-07-05T00:00:00+00:00",
            "date": "2026-07-04",
            "results": {
                "H": {"overall_status": "pass", "route_snapshot_consistency": "route_pass_snapshot_pass",
                      "index_bars_status": "pass", "daily_bars_status": "pass"},
                "US": {"overall_status": "partial", "route_snapshot_consistency": "route_pass_snapshot_partial",
                       "index_bars_status": "pass", "daily_bars_status": "pass"},
            },
            "summary": {"pass": 1, "partial": 1},
        }),
        encoding="utf-8",
    )
    status = build_status(
        holdings_path=tmp_path / "no_holdings.yaml",
        records_dir=tmp_path / "records",
        provider_coverage_report=tmp_path / "no_coverage.json",
        provider_router_live_report=prl_path,
        market_snapshot_smoke_report=smoke_path,
    )
    assert status["provider_router_live"]["run_id"] == "provider_router_live_TEST"
    assert status["market_snapshot_smoke"]["run_id"] == "market_snapshot_smoke_TEST"
    assert status["coverage"]["H"] == "confirmed_live"
    assert status["coverage"]["US"] == "confirmed_live"
    # Not a data_gap despite one market being "partial" — next-action logic
    # should not flag H/US as needing a re-run when both are pass/partial.
    assert "Re-run scripts/run_market_snapshot_smoke.py" not in status["next_operational_action"]


def test_malformed_report_json_is_treated_as_no_data_not_a_crash(tmp_path: Path):
    bad_path = tmp_path / "bad.json"
    bad_path.write_text("{not valid json", encoding="utf-8")
    result = build_desktop_status._safe_read_json(bad_path)
    assert result is None


def test_render_html_escapes_content_and_never_raises_on_missing_fields(tmp_path: Path):
    status = build_status(
        holdings_path=tmp_path / "no_holdings.yaml",
        records_dir=tmp_path / "records",
        provider_coverage_report=tmp_path / "no_coverage.json",
        provider_router_live_report=tmp_path / "no_report.json",
        market_snapshot_smoke_report=tmp_path / "no_smoke.json",
    )
    html_text = render_html(status)
    assert "<html" in html_text
    assert "No holdings recorded" in html_text


def test_dashboard_index_html_unchanged():
    repo_dashboard = REPO_ROOT / "dashboard" / "index.html"
    vault_dashboard = REPO_ROOT.parent / "dashboard" / "index.html"
    assert repo_dashboard.read_text(encoding="utf-8") == vault_dashboard.read_text(encoding="utf-8")


def test_build_desktop_status_never_touches_dotenv_or_token():
    # Check actual usage patterns, not a bare substring — the module's own
    # docstring legitimately *mentions* ProviderRouter/yfinance to explain
    # what this script deliberately does NOT do (same convention as the
    # P1B.2/P1B.3/P1B.4 token-check tests).
    source = inspect.getsource(build_desktop_status)
    assert "import dotenv" not in source
    assert "load_dotenv(" not in source
    assert "os.environ[" not in source
    assert "os.environ.get(" not in source
    assert "os.getenv(" not in source
    assert "TushareAdapter(" not in source
    assert "import yfinance" not in source
    assert "ProviderRouter(" not in source
    assert "from aegis.data.provider_router" not in source


def test_build_desktop_status_never_creates_paper_trades_or_broker_references():
    # Same convention: check actual call/construction patterns, not a bare
    # substring — the module's docstring legitimately explains it never
    # calls a broker.
    source = inspect.getsource(build_desktop_status)
    for forbidden in ("place_order(", "submit_order(", ".buy(", ".sell(", "broker_api", "import broker"):
        assert forbidden not in source.lower()
    assert "PaperTrade(" not in source


# -- P1C.1: desktop polish tests -------------------------------------------


def test_desktop_html_has_translate_no_and_notranslate_wrapping(tmp_path: Path):
    """Required test #1: the generated HTML marks the document
    untranslatable at both the document/body level and per-element, so a
    browser translation tool can no longer mangle `A`/`US`/status tokens."""
    status = build_status(
        holdings_path=tmp_path / "no_holdings.yaml",
        records_dir=tmp_path / "records",
        provider_coverage_report=tmp_path / "no_coverage.json",
        provider_router_live_report=tmp_path / "no_report.json",
        market_snapshot_smoke_report=tmp_path / "no_smoke.json",
    )
    html_text = render_html(status)
    assert '<html lang="zh-CN" translate="no">' in html_text
    assert '<meta name="google" content="notranslate">' in html_text
    assert 'body translate="no" class="notranslate"' in html_text
    # Per-element wrapping on the raw market codes shown in the coverage table.
    assert 'class="notranslate" translate="no"' in html_text


def test_market_labels_render_as_human_chinese(tmp_path: Path):
    """Required test #2: market codes render as A股/H股/美股, not the bare
    ambiguous `A`/`US` tokens that browsers mistranslate."""
    status = build_status(
        holdings_path=tmp_path / "no_holdings.yaml",
        records_dir=tmp_path / "records",
        provider_coverage_report=tmp_path / "no_coverage.json",
        provider_router_live_report=tmp_path / "no_report.json",
        market_snapshot_smoke_report=tmp_path / "no_smoke.json",
    )
    html_text = render_html(status)
    assert "A股" in html_text
    assert "H股" in html_text
    assert "美股" in html_text


def test_status_tokens_render_as_human_labels_not_raw(tmp_path: Path):
    """Required test #3: status tokens render as human Chinese labels
    (e.g. `confirmed_live` -> 已验证), with the raw enum value preserved
    only in a non-translated `title=` attribute for debugging, never as
    visible bare text a translator could grab onto."""
    from scripts.build_desktop_status import _badge, _status_label

    assert _status_label("confirmed_live") == "已验证"
    assert _status_label("confirmed_tushare") == "已验证"
    assert _status_label("unknown") == "未确认"
    assert _status_label("no_data") == "暂无数据"
    assert _status_label("pass") == "通过"
    assert _status_label("partial") == "部分通过"
    assert _status_label("dependency_missing") == "依赖缺失"
    assert _status_label("network_unavailable") == "网络不可用"
    assert _status_label("not_configured") == "未配置"

    badge_html = _badge("confirmed_live")
    assert "已验证" in badge_html
    assert 'title="confirmed_live"' in badge_html
    assert 'class="notranslate" translate="no"' in badge_html


def _write_provider_coverage_report(path: Path, *, a_statuses: dict[str, str], enhanced_statuses: dict[str, str]) -> None:
    checks = []
    for data_type, status_value in a_statuses.items():
        checks.append({"market": "A", "data_type": data_type, "status": status_value})
    for data_type, status_value in enhanced_statuses.items():
        checks.append({"market": "A", "data_type": data_type, "status": status_value})
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({
            "run_id": "provider_diag_TEST",
            "created_at": "2026-07-04T23:43:32.323182+08:00",
            "checks": checks,
        }),
        encoding="utf-8",
    )


def test_a_core_coverage_confirmed_when_provider_coverage_report_passes(tmp_path: Path):
    """Required test #4: A-share core coverage shows 已验证/confirmed_tushare
    when provider_coverage_report.json's A daily_bars/index_bars/
    stock_basic/trading_calendar checks are all `pass` — even though
    sector_classification/fundamentals remain unconfirmed."""
    coverage_path = tmp_path / "provider_coverage_report.json"
    _write_provider_coverage_report(
        coverage_path,
        a_statuses={
            "daily_bars": "pass",
            "index_bars": "pass",
            "stock_basic": "pass",
            "trading_calendar": "pass",
        },
        enhanced_statuses={"sector_classification": "unknown", "fundamentals": "unknown"},
    )
    status = build_status(
        holdings_path=tmp_path / "no_holdings.yaml",
        records_dir=tmp_path / "records",
        provider_coverage_report=coverage_path,
        provider_router_live_report=tmp_path / "no_report.json",
        market_snapshot_smoke_report=tmp_path / "no_smoke.json",
    )
    assert status["coverage"]["A"] == "confirmed_tushare"
    assert status["provider_coverage"]["a_core_confirmed"] is True
    assert status["provider_coverage"]["a_enhanced_confirmed"] is False
    html_text = render_html(status)
    assert "A股核心数据" in html_text
    assert "增强数据未确认" in html_text


def test_a_core_coverage_not_confirmed_when_a_core_check_fails(tmp_path: Path):
    coverage_path = tmp_path / "provider_coverage_report.json"
    _write_provider_coverage_report(
        coverage_path,
        a_statuses={
            "daily_bars": "pass",
            "index_bars": "pass",
            "stock_basic": "fail",
            "trading_calendar": "pass",
        },
        enhanced_statuses={},
    )
    status = build_status(
        holdings_path=tmp_path / "no_holdings.yaml",
        records_dir=tmp_path / "records",
        provider_coverage_report=coverage_path,
        provider_router_live_report=tmp_path / "no_report.json",
        market_snapshot_smoke_report=tmp_path / "no_smoke.json",
    )
    assert status["coverage"]["A"] == "unknown"


def test_h_us_coverage_still_confirmed_from_provider_router_live_and_smoke(tmp_path: Path):
    """Required test #5: H/US coverage is unaffected by the new
    provider_coverage_report param — still derived only from
    provider_router_live + market_snapshot_smoke."""
    prl_path = tmp_path / "provider_router_live_report.json"
    prl_path.write_text(
        json.dumps({"run_id": "prl_TEST", "created_at": "2026-07-05T00:00:00+08:00",
                    "summary": {"pass_count": 2, "fail_count": 0}}),
        encoding="utf-8",
    )
    smoke_path = tmp_path / "market_snapshot_smoke_report.json"
    smoke_path.write_text(
        json.dumps({
            "run_id": "smoke_TEST", "created_at": "2026-07-05T00:00:00+08:00", "date": "2026-07-04",
            "results": {
                "H": {"overall_status": "pass", "route_snapshot_consistency": "route_pass_snapshot_pass"},
                "US": {"overall_status": "pass", "route_snapshot_consistency": "route_pass_snapshot_pass"},
            },
        }),
        encoding="utf-8",
    )
    status = build_status(
        holdings_path=tmp_path / "no_holdings.yaml",
        records_dir=tmp_path / "records",
        provider_coverage_report=tmp_path / "no_coverage.json",
        provider_router_live_report=prl_path,
        market_snapshot_smoke_report=smoke_path,
    )
    assert status["coverage"]["H"] == "confirmed_live"
    assert status["coverage"]["US"] == "confirmed_live"


def _append_gap_line(path: Path, gap: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(gap) + "\n")


def test_stale_yfinance_gap_superseded_by_later_pass_is_not_shown_as_current(tmp_path: Path):
    """Required test #6: an old `yfinance package is not installed` gap for
    a market that a *later* ProviderRouter-live/smoke pass has since
    confirmed is excluded from the current-gaps count/list and appears
    only in the collapsed historical section. `data/records/data_gaps.jsonl`
    itself is never rewritten by this — only the display splits it."""
    records_dir = tmp_path / "records"
    gaps_path = records_dir / "data_gaps.jsonl"
    _append_gap_line(gaps_path, {
        "gap_id": "gap_20260601_H_yfinance", "date": "2026-06-01", "market": "H", "symbol": None,
        "provider": "yahoo_finance", "data_type": "daily_bars", "severity": "warning",
        "message": "yfinance package is not installed", "consumer_impact": [],
        "created_at": "2026-06-01T00:00:00+08:00",
    })
    _append_gap_line(gaps_path, {
        "gap_id": "gap_20260704_H_nodata", "date": "2026-07-04", "market": "H", "symbol": "0700.HK",
        "provider": "yahoo_finance", "data_type": "daily_bars", "severity": "warning",
        "message": "No daily bars returned for 0700.HK", "consumer_impact": [],
        "created_at": "2026-07-04T00:00:00+08:00",
    })
    prl_path = tmp_path / "provider_router_live_report.json"
    prl_path.write_text(
        json.dumps({"run_id": "prl_TEST", "created_at": "2026-07-05T00:00:00+08:00",
                    "summary": {"pass_count": 2, "fail_count": 0}}),
        encoding="utf-8",
    )
    status = build_status(
        holdings_path=tmp_path / "no_holdings.yaml",
        records_dir=records_dir,
        provider_coverage_report=tmp_path / "no_coverage.json",
        provider_router_live_report=prl_path,
        market_snapshot_smoke_report=tmp_path / "no_smoke.json",
    )
    gaps = status["data_gaps"]
    assert gaps["count"] == 2
    assert gaps["current_count"] == 1
    assert gaps["historical_count"] == 1
    current_messages = [g["message"] for g in gaps["recent"]]
    assert "yfinance package is not installed" not in current_messages
    assert "No daily bars returned for 0700.HK" in current_messages
    historical_messages = [g["message"] for g in gaps["historical_recent"]]
    assert "yfinance package is not installed" in historical_messages
    # The raw JSONL file on disk is untouched — both lines still present.
    assert len(gaps_path.read_text(encoding="utf-8").strip().splitlines()) == 2

    html_text = render_html(status)
    assert "历史数据缺口" in html_text
    assert "<details>" in html_text


def test_p1c3_no_bars_returned_yahoo_route_gap_superseded_by_later_smoke_pass(tmp_path: Path):
    """Required P1C.3 test #1: the real ProviderRouter "No {daily|index}
    bars returned for {symbol} ({market}) via provider_route=
    'yahoo_finance' between ... and ..." message shape (distinct from
    the older "yfinance package is not installed" wording) is also
    recognized as a superseded stale gap once a later MarketSnapshot
    smoke pass confirms that market/route. Mirrors the real 4 gaps
    found in data/records/data_gaps.jsonl for HSI.HI/SPX/00700.HK/CRCL."""
    records_dir = tmp_path / "records"
    gaps_path = records_dir / "data_gaps.jsonl"
    _append_gap_line(gaps_path, {
        "gap_id": "gap_20260704_H_HSI.HI_index_bars", "date": "20260704", "market": "H",
        "symbol": "HSI.HI", "provider": "yahoo_finance", "data_type": "index_bars",
        "severity": "warning",
        "message": "No index bars returned for HSI.HI (H) via provider_route='yahoo_finance' "
        "between 20260306 and 20260704.",
        "consumer_impact": [], "created_at": "2026-07-05T11:23:43.414866+08:00",
    })
    _append_gap_line(gaps_path, {
        "gap_id": "gap_20260704_US_CRCL_daily_bars", "date": "20260704", "market": "US",
        "symbol": "CRCL", "provider": "yahoo_finance", "data_type": "daily_bars",
        "severity": "warning",
        "message": "No daily bars returned for CRCL (US) via provider_route='yahoo_finance' "
        "between 20260306 and 20260704.",
        "consumer_impact": [], "created_at": "2026-07-05T11:23:43.458302+08:00",
    })
    smoke_path = tmp_path / "market_snapshot_smoke_report.json"
    smoke_path.write_text(
        json.dumps({
            "run_id": "smoke_TEST", "created_at": "2026-07-05T13:46:04.407841+08:00",
            "date": "2026-07-04",
            "results": {
                "H": {"overall_status": "pass", "route_snapshot_consistency": "route_pass_snapshot_pass",
                      "index_bars_status": "pass", "daily_bars_status": "pass"},
                "US": {"overall_status": "pass", "route_snapshot_consistency": "route_pass_snapshot_pass",
                       "index_bars_status": "pass", "daily_bars_status": "pass"},
            },
        }),
        encoding="utf-8",
    )
    status = build_status(
        holdings_path=tmp_path / "no_holdings.yaml",
        records_dir=records_dir,
        provider_coverage_report=tmp_path / "no_coverage.json",
        provider_router_live_report=tmp_path / "no_prl.json",
        market_snapshot_smoke_report=smoke_path,
    )
    gaps = status["data_gaps"]
    assert gaps["count"] == 2
    assert gaps["current_count"] == 0
    assert gaps["historical_count"] == 2
    assert len(gaps_path.read_text(encoding="utf-8").strip().splitlines()) == 2


def test_p1c3_current_unresolved_gaps_exclude_superseded_h_us_yahoo_rows(tmp_path: Path):
    """Required P1C.3 test #2: once superseded, the covered H/US yahoo
    route gaps never appear in `recent` (the current-unresolved list),
    even when a genuinely new, unrelated gap for the same market is
    also on file — that new gap stays current."""
    records_dir = tmp_path / "records"
    gaps_path = records_dir / "data_gaps.jsonl"
    _append_gap_line(gaps_path, {
        "gap_id": "gap_stale", "date": "20260704", "market": "H", "symbol": "00700.HK",
        "provider": "yahoo_finance", "data_type": "daily_bars", "severity": "warning",
        "message": "No daily bars returned for 00700.HK (H) via provider_route='yahoo_finance' "
        "between 20260306 and 20260704.",
        "consumer_impact": [], "created_at": "2026-07-05T11:23:43.444181+08:00",
    })
    _append_gap_line(gaps_path, {
        "gap_id": "gap_new", "date": "20260706", "market": "H", "symbol": "00700.HK",
        "provider": "yahoo_finance", "data_type": "daily_bars", "severity": "warning",
        "message": "No daily bars returned for 00700.HK (H) via provider_route='yahoo_finance' "
        "between 20260706 and 20260706.",
        "consumer_impact": [], "created_at": "2026-07-06T09:00:00.000000+08:00",
    })
    smoke_path = tmp_path / "market_snapshot_smoke_report.json"
    smoke_path.write_text(
        json.dumps({
            "run_id": "smoke_TEST", "created_at": "2026-07-05T13:46:04.407841+08:00", "date": "2026-07-04",
            "results": {"H": {"overall_status": "pass", "route_snapshot_consistency": "route_pass_snapshot_pass",
                               "index_bars_status": "pass", "daily_bars_status": "pass"}},
        }),
        encoding="utf-8",
    )
    status = build_status(
        holdings_path=tmp_path / "no_holdings.yaml",
        records_dir=records_dir,
        provider_coverage_report=tmp_path / "no_coverage.json",
        provider_router_live_report=tmp_path / "no_prl.json",
        market_snapshot_smoke_report=smoke_path,
    )
    gaps = status["data_gaps"]
    assert gaps["current_count"] == 1
    assert gaps["historical_count"] == 1
    current_ids = [g["gap_id"] for g in gaps["recent"]]
    assert current_ids == ["gap_new"]
    historical_ids = [g["gap_id"] for g in gaps["historical_recent"]]
    assert historical_ids == ["gap_stale"]


def test_p1c3_historical_gaps_still_retained_in_status_payload(tmp_path: Path):
    """Required P1C.3 test #3: superseded gaps are never dropped from the
    status payload — they remain visible in `historical_recent`, and the
    on-disk JSONL keeps every line."""
    records_dir = tmp_path / "records"
    gaps_path = records_dir / "data_gaps.jsonl"
    for i in range(3):
        _append_gap_line(gaps_path, {
            "gap_id": f"gap_{i}", "date": "20260704", "market": "US", "symbol": "CRCL",
            "provider": "yahoo_finance", "data_type": "daily_bars", "severity": "warning",
            "message": "No daily bars returned for CRCL (US) via provider_route='yahoo_finance' "
            "between 20260306 and 20260704.",
            "consumer_impact": [], "created_at": f"2026-07-05T11:23:4{i}.000000+08:00",
        })
    prl_path = tmp_path / "provider_router_live_report.json"
    prl_path.write_text(
        json.dumps({"run_id": "prl_TEST", "created_at": "2026-07-06T00:00:00+08:00",
                    "summary": {"pass_count": 4, "fail_count": 0}}),
        encoding="utf-8",
    )
    status = build_status(
        holdings_path=tmp_path / "no_holdings.yaml",
        records_dir=records_dir,
        provider_coverage_report=tmp_path / "no_coverage.json",
        provider_router_live_report=prl_path,
        market_snapshot_smoke_report=tmp_path / "no_smoke.json",
    )
    gaps = status["data_gaps"]
    assert gaps["count"] == 3
    assert gaps["current_count"] == 0
    assert gaps["historical_count"] == 3
    assert len(gaps["historical_recent"]) == 3
    assert len(gaps_path.read_text(encoding="utf-8").strip().splitlines()) == 3


def test_p1c3_real_repo_coverage_is_a_tushare_h_us_confirmed_live(tmp_path: Path):
    """Required P1C.3 test #4: sanity-checks against the *real* repo
    report files (not a fixture) that A/H/US coverage still reads
    A=confirmed_tushare, H=confirmed_live, US=confirmed_live, and that
    the 28 originally-superseded gaps (24 old "yfinance package is not
    installed" + 4 "no bars returned" rows for HSI.HI/SPX/00700.HK/CRCL)
    are still classified historical/superseded — matching what the
    stock-agent should see through the mirrored status file.

    P1D note: a real pipeline/smoke run performed after P1C.3 may
    legitimately append brand-new yahoo_finance H/US gaps dated *after*
    the last confirming MarketSnapshot-smoke pass (e.g. this Cowork
    sandbox's own `run_market_snapshot_smoke.py`/`run_pre_market.py`
    runs, honestly reporting `yfinance` still isn't installed here) —
    those are correctly still "current" (a fresh event is never hidden),
    so `historical_count`/`current_count` are no longer pinned to exact
    frozen numbers. What must still hold: historical_count only ever
    grows (never loses the original 28), and no gap dated *before* the
    known confirming smoke pass is ever shown as current — i.e. nothing
    already-superseded ever resurfaces."""
    status = build_status()
    assert status["coverage"]["A"] == "confirmed_tushare"
    assert status["coverage"]["H"] == "confirmed_live"
    assert status["coverage"]["US"] == "confirmed_live"
    gaps = status["data_gaps"]
    assert gaps["historical_count"] >= 28
    confirming_smoke_pass_at = "2026-07-05T13:46:04.407841+08:00"
    for g in gaps["recent"]:
        if g.get("market") in ("H", "US") and g.get("provider") == "yahoo_finance":
            assert g["created_at"] > confirming_smoke_pass_at, (
                f"gap {g['gap_id']} dated {g['created_at']} predates the "
                "confirming smoke pass and should have been superseded"
            )


def test_main_writes_html_and_json_and_creates_data_desktop_dir(tmp_path: Path, monkeypatch):
    holdings_path = tmp_path / "holdings.yaml"
    _write_holdings(holdings_path, [])
    out_html = tmp_path / "desktop" / "aegis_status.html"
    out_json = tmp_path / "desktop" / "aegis_status.json"

    exit_code = build_desktop_status.main([
        "--holdings-path", str(holdings_path),
        "--records-dir", str(tmp_path / "records"),
        "--provider-coverage-report", str(tmp_path / "no_coverage.json"),
        "--provider-router-live-report", str(tmp_path / "no_report.json"),
        "--market-snapshot-smoke-report", str(tmp_path / "no_smoke.json"),
        "--output-html", str(out_html),
        "--output-json", str(out_json),
    ])
    assert exit_code == 0
    assert out_html.exists()
    assert out_json.exists()
    data = json.loads(out_json.read_text(encoding="utf-8"))
    assert "generated_at" in data
