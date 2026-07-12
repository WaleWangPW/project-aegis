"""P1D.3 tests for aegis/desktop/recommendation_details.py dedup/latest fixes.

Covers all 16 acceptance criteria from the P1D.3 task spec:
 1. duplicate recommendation_id: last appended record selected as latest
 2. older duplicate records retained, marked non-latest
 3. latest per symbol prefers later record over earlier same-date duplicate
 4. latest_status_counts counts latest records only
 5. historical / all-record counts remain available
 6. desktop status uses latest per symbol (not stale duplicate)
 7. stock-agent mirrored recommendation_details.json uses latest_recommendations
 8. stale yfinance-is-not-installed notes not attached to latest visible rec
 9. true current data gaps remain visible
10. no fake recommendation fields generated
11. no broker / real trading
12. no manual PaperTrade creation
13. no composite scoring
14. no token read / printed
15. dashboard/index.html unchanged
16. CRCL not special-cased beyond fixture usage

All tests use in-memory fixtures written to tmp_path — no real network calls.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

import scripts.build_desktop_status as bds
from aegis.desktop.recommendation_details import (
    _compute_latest_flags,
    _gaps_for_rec,
    _normalize_date,
    build_recommendation_details,
)


# ---------------------------------------------------------------------------
# JSONL fixture helpers
# ---------------------------------------------------------------------------

def _write_jsonl(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for r in records:
            fh.write(json.dumps(r) + "\n")


def _make_rec(
    symbol: str = "AAPL",
    status: str = "Exit",
    confidence: float = 0.25,
    created_at: str = "2026-07-06T10:00:00+08:00",
    date: str = "2026-07-06",
    market: str = "US",
    session: str = "pre_market",
    rec_id: str = "rec_20260706_pre_market_US_AAPL",
) -> dict:
    return {
        "recommendation_id": rec_id,
        "symbol": symbol,
        "name": f"{symbol} Inc.",
        "market": market,
        "date": date,
        "session": session,
        "status": status,
        "action_label": "exit_position" if status == "Exit" else "hold_and_monitor",
        "confidence": confidence,
        "decision_summary": f"status={status}",
        "support_reasons": [],
        "oppose_reasons": [],
        "risks": [],
        "invalidation_conditions": [],
        # Required by RecommendationRecord pydantic model (used in bds._recommendations_summary)
        "market_snapshot_id": f"snap_{date.replace('-', '')}_{session}_{market}",
        "candidate_id": f"cand_{date.replace('-', '')}_{session}_{market}_{symbol}",
        "lifecycle_status": "open",
        "created_at": created_at,
        "updated_at": created_at,
    }


def _make_dec(
    symbol: str = "AAPL",
    risk_veto: bool = False,
    neutral: int = 7,
    veto: int = 0,
    created_at: str = "2026-07-06T10:00:00+08:00",
    rec_id: str = "rec_20260706_pre_market_US_AAPL",
) -> dict:
    return {
        "decision_id": rec_id.replace("rec_", "dec_"),
        "recommendation_id": rec_id,
        "risk_veto_triggered": risk_veto,
        "risk_veto_reason": "liquidity_not_ok" if risk_veto else None,
        "support_count": 0,
        "oppose_count": 0,
        "neutral_count": neutral,
        "veto_count": veto,
        "why_not_action": "risk_veto_triggered" if risk_veto else "missing_critical_data",
        "created_at": created_at,
    }


def _make_gap(
    symbol: str = "AAPL",
    date: str = "20260706",
    market: str = "US",
    message: str = "No daily bars returned for AAPL",
    gap_id: str = "gap_001",
) -> dict:
    return {
        "gap_id": gap_id,
        "symbol": symbol,
        "date": date,
        "market": market,
        "data_type": "daily_bars",
        "provider": "yahoo_finance",
        "severity": "warning",
        "message": message,
        "created_at": f"{date[:4]}-{date[4:6]}-{date[6:]}T10:00:00+00:00" if len(date) == 8 else f"{date}T10:00:00+00:00",
    }


# ===========================================================================
# Test 1: duplicate recommendation_id → last appended record selected as latest
# ===========================================================================

def test_1_duplicate_rec_id_last_appended_is_latest(tmp_path: Path) -> None:
    """When multiple JSONL rows share the same recommendation_id, the last
    appended (highest created_at / highest file position) must be selected."""
    recs = [
        _make_rec(status="Exit", confidence=0.25, created_at="2026-07-06T10:00:00+08:00"),
        _make_rec(status="Watch", confidence=0.45, created_at="2026-07-06T12:10:00+08:00"),
        _make_rec(status="Exit", confidence=0.25, created_at="2026-07-06T12:16:00+08:00"),
    ]
    _write_jsonl(tmp_path / "recommendations.jsonl", recs)
    _write_jsonl(tmp_path / "decisions.jsonl", [])
    _write_jsonl(tmp_path / "expert_opinions.jsonl", [])
    _write_jsonl(tmp_path / "data_gaps.jsonl", [])

    out = build_recommendation_details(tmp_path, tmp_path / "out.json")

    latest = out["latest_recommendations"]
    assert len(latest) == 1
    # The last appended row (12:16, Exit) wins
    assert latest[0]["status"] == "Exit"
    assert latest[0]["record_index"] == 2
    assert latest[0]["is_latest_for_recommendation_id"] is True
    assert latest[0]["is_latest_for_symbol"] is True


# ===========================================================================
# Test 2: older duplicate records retained and marked non-latest
# ===========================================================================

def test_2_older_duplicates_retained_with_non_latest_flags(tmp_path: Path) -> None:
    """All raw records must appear in `recommendations`; older ones have
    is_latest_for_recommendation_id=False and is_latest_for_symbol=False."""
    recs = [
        _make_rec(status="Exit", created_at="2026-07-06T10:00:00+08:00"),
        _make_rec(status="Watch", created_at="2026-07-06T12:10:00+08:00"),
        _make_rec(status="Exit", created_at="2026-07-06T12:16:00+08:00"),
    ]
    _write_jsonl(tmp_path / "recommendations.jsonl", recs)
    for f in ("decisions.jsonl", "expert_opinions.jsonl", "data_gaps.jsonl"):
        _write_jsonl(tmp_path / f, [])

    out = build_recommendation_details(tmp_path, tmp_path / "out.json")

    all_recs = out["recommendations"]
    assert len(all_recs) == 3, "All 3 raw records must be present"
    # Indexes 0 and 1 are superseded
    for r in all_recs[:2]:
        assert r["is_latest_for_recommendation_id"] is False
        assert r["is_latest_for_symbol"] is False
    # Index 2 is latest
    assert all_recs[2]["is_latest_for_recommendation_id"] is True
    assert all_recs[2]["is_latest_for_symbol"] is True


# ===========================================================================
# Test 3: latest per symbol prefers later record over earlier same-date dup
# ===========================================================================

def test_3_latest_per_symbol_prefers_higher_created_at(tmp_path: Path) -> None:
    """Among is_latest_for_recommendation_id records, the one with the
    higher created_at is selected as is_latest_for_symbol=True."""
    rec_id_a = "rec_20260706_pre_market_US_AAPL"
    rec_id_b = "rec_20260705_pre_market_US_AAPL"  # earlier date
    recs = [
        _make_rec(status="Watch", confidence=0.45,
                  created_at="2026-07-05T10:00:00+08:00",
                  date="2026-07-05", rec_id=rec_id_b),
        _make_rec(status="Exit", confidence=0.25,
                  created_at="2026-07-06T12:16:00+08:00",
                  date="2026-07-06", rec_id=rec_id_a),
    ]
    _write_jsonl(tmp_path / "recommendations.jsonl", recs)
    for f in ("decisions.jsonl", "expert_opinions.jsonl", "data_gaps.jsonl"):
        _write_jsonl(tmp_path / f, [])

    out = build_recommendation_details(tmp_path, tmp_path / "out.json")

    latest = out["latest_recommendations"]
    assert len(latest) == 1
    # 2026-07-06 is later than 2026-07-05
    assert latest[0]["date"] == "2026-07-06"
    assert latest[0]["status"] == "Exit"


# ===========================================================================
# Test 4: latest_status_counts counts latest records only
# ===========================================================================

def test_4_latest_status_counts_counts_only_latest(tmp_path: Path) -> None:
    """summary.latest_status_counts must NOT count historical duplicates."""
    recs = [
        _make_rec(status="Exit", confidence=0.25, created_at="2026-07-06T10:00:00+08:00"),
        _make_rec(status="Watch", confidence=0.45, created_at="2026-07-06T12:10:00+08:00"),
        _make_rec(status="Exit", confidence=0.25, created_at="2026-07-06T12:16:00+08:00"),
    ]
    _write_jsonl(tmp_path / "recommendations.jsonl", recs)
    for f in ("decisions.jsonl", "expert_opinions.jsonl", "data_gaps.jsonl"):
        _write_jsonl(tmp_path / f, [])

    out = build_recommendation_details(tmp_path, tmp_path / "out.json")

    counts = out["summary"]["latest_status_counts"]
    # Only 1 latest record (Exit), not 3 total
    assert counts.get("Exit", 0) == 1
    assert counts.get("Watch", 0) == 0
    assert out["summary"]["latest_per_symbol_count"] == 1


# ===========================================================================
# Test 5: historical / all-record counts remain available
# ===========================================================================

def test_5_total_records_count_includes_all_history(tmp_path: Path) -> None:
    """summary.total_records must equal the raw JSONL line count."""
    recs = [
        _make_rec(status="Exit", created_at="2026-07-06T10:00:00+08:00"),
        _make_rec(status="Watch", created_at="2026-07-06T12:10:00+08:00"),
        _make_rec(status="Exit", created_at="2026-07-06T12:16:00+08:00"),
    ]
    _write_jsonl(tmp_path / "recommendations.jsonl", recs)
    for f in ("decisions.jsonl", "expert_opinions.jsonl", "data_gaps.jsonl"):
        _write_jsonl(tmp_path / f, [])

    out = build_recommendation_details(tmp_path, tmp_path / "out.json")

    assert out["summary"]["total_records"] == 3
    assert out["summary"]["historical_record_count"] == 2  # 3 total - 1 latest
    assert out["summary"]["unique_recommendation_ids"] == 1


# ===========================================================================
# Test 6: desktop status uses latest per symbol, not stale count
# ===========================================================================

def test_6_build_desktop_status_uses_latest_per_symbol(tmp_path: Path) -> None:
    """build_desktop_status._recommendations_summary must count latest per
    symbol, not all historical records."""
    records_dir = tmp_path / "records"
    recs = [
        _make_rec(status="Exit", created_at="2026-07-06T10:00:00+08:00"),
        _make_rec(status="Watch", created_at="2026-07-06T12:10:00+08:00"),
        _make_rec(status="Exit", created_at="2026-07-06T12:16:00+08:00"),
    ]
    _write_jsonl(records_dir / "recommendations.jsonl", recs)
    _write_jsonl(records_dir / "decisions.jsonl", [])

    summary = bds._recommendations_summary(records_dir)

    # count is latest-per-symbol (1), NOT total records (3)
    assert summary["count"] == 1
    # total_records must still be available for transparency
    assert summary["total_records"] == 3
    # status_counts reflects latest only
    assert summary["status_counts"].get("Exit", 0) == 1
    assert summary["status_counts"].get("Watch", 0) == 0


# ===========================================================================
# Test 7: stock-agent mirrored JSON contains latest_recommendations
# ===========================================================================

def test_7_output_json_contains_latest_recommendations_key(tmp_path: Path) -> None:
    """recommendation_details.json must have a top-level
    'latest_recommendations' list for the stock-agent to consume."""
    recs = [_make_rec(status="Exit", created_at="2026-07-06T12:16:00+08:00")]
    _write_jsonl(tmp_path / "recommendations.jsonl", recs)
    for f in ("decisions.jsonl", "expert_opinions.jsonl", "data_gaps.jsonl"):
        _write_jsonl(tmp_path / f, [])

    out_path = tmp_path / "out.json"
    build_recommendation_details(tmp_path, out_path)

    data = json.loads(out_path.read_text())
    assert "latest_recommendations" in data, (
        "recommendation_details.json must have top-level 'latest_recommendations'"
    )
    assert isinstance(data["latest_recommendations"], list)
    assert len(data["latest_recommendations"]) == 1


# ===========================================================================
# Test 8: stale yfinance notes not attached to latest visible recommendation
# ===========================================================================

def test_8_stale_yfinance_gaps_not_attached_to_latest(tmp_path: Path) -> None:
    """Data quality notes from a DIFFERENT date must never appear on the
    latest recommendation (e.g. 'yfinance is not installed' from 20260704
    should not appear on the 2026-07-06 recommendation)."""
    recs = [_make_rec(status="Exit", created_at="2026-07-06T12:16:00+08:00", date="2026-07-06")]
    gaps = [
        _make_gap(date="20260704", message="yfinance package is not installed", gap_id="gap_stale"),
        _make_gap(date="20260706", message="No daily bars returned for AAPL", gap_id="gap_current"),
    ]
    _write_jsonl(tmp_path / "recommendations.jsonl", recs)
    for f in ("decisions.jsonl", "expert_opinions.jsonl"):
        _write_jsonl(tmp_path / f, [])
    _write_jsonl(tmp_path / "data_gaps.jsonl", gaps)

    out = build_recommendation_details(tmp_path, tmp_path / "out.json")

    notes = out["latest_recommendations"][0]["data_quality_notes"]
    assert not any("yfinance package is not installed" in n for n in notes), (
        "Stale gap from 20260704 must not appear on 2026-07-06 recommendation"
    )
    assert any("No daily bars returned for AAPL" in n for n in notes), (
        "Current gap from 20260706 must still be visible"
    )


# ===========================================================================
# Test 9: true current data gaps remain visible
# ===========================================================================

def test_9_current_data_gaps_remain_visible(tmp_path: Path) -> None:
    """Gaps from the same date as the recommendation must appear in
    data_quality_notes."""
    recs = [_make_rec(status="Exit", date="2026-07-06", created_at="2026-07-06T12:00:00+08:00")]
    gaps = [
        _make_gap(date="20260706", message="No bars returned for AAPL via yahoo_finance", gap_id="gap_a"),
    ]
    _write_jsonl(tmp_path / "recommendations.jsonl", recs)
    for f in ("decisions.jsonl", "expert_opinions.jsonl"):
        _write_jsonl(tmp_path / f, [])
    _write_jsonl(tmp_path / "data_gaps.jsonl", gaps)

    out = build_recommendation_details(tmp_path, tmp_path / "out.json")

    notes = out["latest_recommendations"][0]["data_quality_notes"]
    assert any("No bars returned for AAPL" in n for n in notes)


# ===========================================================================
# Test 10: no fake recommendation fields generated
# ===========================================================================

def test_10_no_fake_recommendation_fields(tmp_path: Path) -> None:
    """The builder must not fabricate support_reasons, oppose_reasons, risks,
    or invalidation_conditions that were not in the source JSONL."""
    recs = [_make_rec(status="Watch", created_at="2026-07-06T12:00:00+08:00")]
    for f in ("recommendations.jsonl", "decisions.jsonl", "expert_opinions.jsonl", "data_gaps.jsonl"):
        _write_jsonl(tmp_path / f, recs if f == "recommendations.jsonl" else [])

    out = build_recommendation_details(tmp_path, tmp_path / "out.json")

    r = out["latest_recommendations"][0]
    assert r["support_reasons"] == []
    assert r["oppose_reasons"] == []
    assert r["risks"] == []
    assert r["invalidation_conditions"] == []


# ===========================================================================
# Test 11: no broker / real-trading code in recommendation_details.py
# ===========================================================================

def test_11_no_broker_real_trading() -> None:
    source = Path(__file__).resolve().parents[1] / "aegis" / "desktop" / "recommendation_details.py"
    code = source.read_text(encoding="utf-8")
    code_only = re.sub(r'""".*?"""', "", code, flags=re.DOTALL)
    code_only = re.sub(r"'''.*?'''", "", code_only, flags=re.DOTALL)
    for term in ("broker_api", "real_order", "place_order", "alpaca", "ibkr"):
        assert term not in code_only.lower()


# ===========================================================================
# Test 12: no manual PaperTrade creation in recommendation_details.py
# ===========================================================================

def test_12_no_paper_trade_creation() -> None:
    source = Path(__file__).resolve().parents[1] / "aegis" / "desktop" / "recommendation_details.py"
    code = source.read_text(encoding="utf-8")
    code_only = re.sub(r'""".*?"""', "", code, flags=re.DOTALL)
    code_only = re.sub(r"'''.*?'''", "", code_only, flags=re.DOTALL)
    assert re.search(r"\bPaperTrade\s*\(", code_only) is None, (
        "PaperTrade must not be manually constructed in recommendation_details.py"
    )


# ===========================================================================
# Test 13: no composite scoring
# ===========================================================================

def test_13_no_composite_scoring() -> None:
    for module_path in [
        Path(__file__).resolve().parents[1] / "aegis" / "desktop" / "recommendation_details.py",
        Path(__file__).resolve().parents[1] / "scripts" / "build_desktop_status.py",
    ]:
        code = module_path.read_text(encoding="utf-8")
        code_only = re.sub(r'""".*?"""', "", code, flags=re.DOTALL)
        code_only = re.sub(r"'''.*?'''", "", code_only, flags=re.DOTALL)
        for term in ("composite_score", "weighted_score", "final_score"):
            assert term not in code_only.lower(), (
                f"Composite scoring term '{term}' in {module_path.name}"
            )


# ===========================================================================
# Test 14: no token read / printed
# ===========================================================================

def test_14_no_token_read_or_printed() -> None:
    source = Path(__file__).resolve().parents[1] / "aegis" / "desktop" / "recommendation_details.py"
    code = source.read_text(encoding="utf-8")
    code_only = re.sub(r'""".*?"""', "", code, flags=re.DOTALL)
    code_only = re.sub(r"'''.*?'''", "", code_only, flags=re.DOTALL)
    for pattern in (r'open\(["\']\.env', r'getenv.*token', r'print.*token', r'print.*api_key'):
        assert not re.search(pattern, code_only, re.IGNORECASE)


# ===========================================================================
# Test 15: dashboard/index.html unchanged
# ===========================================================================

def test_15_dashboard_index_html_unchanged(tmp_path: Path) -> None:
    """build_recommendation_details must never write to dashboard/index.html."""
    dash_dir = tmp_path / "dashboard"
    dash_dir.mkdir()
    index_html = dash_dir / "index.html"
    original = "<html><!-- sentinel --></html>"
    index_html.write_text(original, encoding="utf-8")

    recs = [_make_rec(status="Exit", created_at="2026-07-06T12:00:00+08:00")]
    _write_jsonl(tmp_path / "recommendations.jsonl", recs)
    for f in ("decisions.jsonl", "expert_opinions.jsonl", "data_gaps.jsonl"):
        _write_jsonl(tmp_path / f, [])

    build_recommendation_details(tmp_path, tmp_path / "out.json")

    assert index_html.read_text(encoding="utf-8") == original


# ===========================================================================
# Test 16: CRCL not special-cased — same logic applies to any symbol
# ===========================================================================

def test_16_crcl_not_special_cased_any_symbol_follows_same_path(tmp_path: Path) -> None:
    """The latest-selection logic must work identically for MSFT as it does
    for CRCL — no symbol-specific branching in the builder."""
    msft_id = "rec_20260706_pre_market_US_MSFT"
    recs = [
        _make_rec(symbol="MSFT", status="Exit", confidence=0.25,
                  created_at="2026-07-06T10:00:00+08:00", rec_id=msft_id),
        _make_rec(symbol="MSFT", status="Watch", confidence=0.45,
                  created_at="2026-07-06T12:10:00+08:00", rec_id=msft_id),
        _make_rec(symbol="MSFT", status="Exit", confidence=0.25,
                  created_at="2026-07-06T12:16:00+08:00", rec_id=msft_id),
    ]
    _write_jsonl(tmp_path / "recommendations.jsonl", recs)
    for f in ("decisions.jsonl", "expert_opinions.jsonl", "data_gaps.jsonl"):
        _write_jsonl(tmp_path / f, [])

    out = build_recommendation_details(tmp_path, tmp_path / "out.json")

    latest = out["latest_recommendations"]
    assert len(latest) == 1
    assert latest[0]["symbol"] == "MSFT"
    # Last appended (12:16, Exit) wins — same logic as CRCL
    assert latest[0]["status"] == "Exit"
    assert latest[0]["record_index"] == 2
    assert latest[0]["is_latest_for_recommendation_id"] is True

    # Verify no special-case for symbol names anywhere in functional code
    source = Path(__file__).resolve().parents[1] / "aegis" / "desktop" / "recommendation_details.py"
    code = source.read_text(encoding="utf-8")
    code_only = re.sub(r'""".*?"""', "", code, flags=re.DOTALL)
    code_only = re.sub(r"'''.*?'''", "", code_only, flags=re.DOTALL)
    assert '"CRCL"' not in code_only, "CRCL must not be hardcoded in recommendation_details.py"
    assert "'CRCL'" not in code_only
