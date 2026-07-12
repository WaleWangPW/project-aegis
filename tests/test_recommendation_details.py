"""tests/test_recommendation_details.py — P1D.1 Recommendation Details Mirror tests.

17 test cases verifying:
1.  recommendation_details.json generated from fixture records
2.  support_reasons preserved
3.  oppose_reasons preserved
4.  risks preserved
5.  invalidation_conditions preserved
6.  why_not_action included from DecisionRecord when present
7.  expert opinions linked by recommendation_id
8.  missing detail fields produce empty arrays/nulls, not fake text
9.  repeated recommendations marked with is_latest_for_symbol
10. refresh script copies recommendation_details.json into stock-agent workspace
11. stock-agent README includes recommendation_details rules
12. dashboard/index.html unchanged
13. no broker/real trading code in builder
14. no manual PaperTrade creation in builder
15. no composite scoring in builder
16. no token read/printed in builder
17. CRCL not special-cased in builder
"""

from __future__ import annotations

import inspect
import json
import re
import shutil
import textwrap
from pathlib import Path

import pytest

# Allow running tests from the repo root
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aegis.desktop.recommendation_details import build_recommendation_details


def _code_only(source: str) -> str:
    """Strip all triple-quoted string literals from Python source so tests can
    check that *functional code* doesn't reference forbidden terms even though
    the module docstring legitimately mentions them as non-goals."""
    # Remove triple-double-quote strings
    stripped = re.sub(r'""".*?"""', "", source, flags=re.DOTALL)
    # Remove triple-single-quote strings
    stripped = re.sub(r"'''.*?'''", "", stripped, flags=re.DOTALL)
    return stripped


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

REC_ID = "rec_20260706_pre_market_US_TEST"
DEC_ID = "dec_20260706_pre_market_US_TEST"
SYM = "TEST"

_REC_BASE = {
    "recommendation_id": REC_ID,
    "date": "2026-07-06",
    "session": "pre_market",
    "symbol": SYM,
    "name": "Test Corp",
    "market": "US",
    "sector": None,
    "status": "Exit",
    "action_label": "exit_position",
    "support_reasons": ["signal_A_positive"],
    "oppose_reasons": ["RiskAgent veto: liquidity issue"],
    "risks": ["liquidity_not_ok"],
    "invalidation_conditions": ["price_above_ma200"],
    "confidence": 0.25,
    "decision_summary": "support=0, veto=1 -> Exit.",
    "created_at": "2026-07-06T10:00:00+08:00",
}

_DEC_BASE = {
    "decision_id": DEC_ID,
    "recommendation_id": REC_ID,
    "final_status": "Exit",
    "final_action": "exit_position",
    "support_count": 0,
    "oppose_count": 0,
    "neutral_count": 6,
    "veto_count": 1,
    "risk_veto_triggered": True,
    "confidence": 0.25,
    "why_not_action": "risk_veto_triggered",
    "invalidation_conditions": ["price_above_ma200"],
    "created_at": "2026-07-06T10:00:00+08:00",
}

_OP_RISK = {
    "opinion_id": f"opn_{SYM}_risk",
    "recommendation_id": REC_ID,
    "expert_name": "RiskAgent",
    "stance": "veto",
    "confidence": 0.7,
    "evidence": [],
    "risks": ["liquidity_not_ok"],
    "missing_data": ["risk_signal"],
    "summary": "Risk signal unavailable.",
    "created_at": "2026-07-06T10:00:00+08:00",
}

_OP_TREND = {
    "opinion_id": f"opn_{SYM}_trend",
    "recommendation_id": REC_ID,
    "expert_name": "TrendAgent",
    "stance": "neutral",
    "confidence": 0.4,
    "evidence": [],
    "risks": [],
    "missing_data": ["trend_signal"],
    "summary": "No trend data.",
    "created_at": "2026-07-06T10:00:00+08:00",
}

_GAP = {
    "gap_id": f"gap_20260706_US_{SYM}_daily_bars",
    "date": "20260706",
    "market": "US",
    "symbol": SYM,
    "provider": "yahoo_finance",
    "data_type": "daily_bars",
    "severity": "warning",
    "message": "No daily bars returned for TEST.",
    "consumer_impact": ["daily_bars unavailable for TEST"],
    "created_at": "2026-07-06T10:00:00+08:00",
}


def _write_jsonl(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for r in records:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")


@pytest.fixture()
def fixture_dir(tmp_path: Path) -> Path:
    """Write standard fixture JSONL files and return the records dir."""
    records = tmp_path / "data" / "records"
    _write_jsonl(records / "recommendations.jsonl", [_REC_BASE])
    _write_jsonl(records / "decisions.jsonl", [_DEC_BASE])
    _write_jsonl(records / "expert_opinions.jsonl", [_OP_RISK, _OP_TREND])
    _write_jsonl(records / "data_gaps.jsonl", [_GAP])
    return records


@pytest.fixture()
def built(fixture_dir: Path, tmp_path: Path) -> dict:
    output = tmp_path / "data" / "desktop" / "recommendation_details.json"
    return build_recommendation_details(records_dir=fixture_dir, output_path=output)


# ---------------------------------------------------------------------------
# Test 1 — file is generated from fixture records
# ---------------------------------------------------------------------------

def test_1_json_file_generated(fixture_dir: Path, tmp_path: Path) -> None:
    output = tmp_path / "data" / "desktop" / "recommendation_details.json"
    assert not output.exists()
    build_recommendation_details(records_dir=fixture_dir, output_path=output)
    assert output.exists()
    data = json.loads(output.read_text())
    assert "recommendations" in data
    assert len(data["recommendations"]) == 1


# ---------------------------------------------------------------------------
# Test 2 — support_reasons preserved
# ---------------------------------------------------------------------------

def test_2_support_reasons_preserved(built: dict) -> None:
    rec = built["recommendations"][0]
    assert rec["support_reasons"] == ["signal_A_positive"]


# ---------------------------------------------------------------------------
# Test 3 — oppose_reasons preserved
# ---------------------------------------------------------------------------

def test_3_oppose_reasons_preserved(built: dict) -> None:
    rec = built["recommendations"][0]
    assert rec["oppose_reasons"] == ["RiskAgent veto: liquidity issue"]


# ---------------------------------------------------------------------------
# Test 4 — risks preserved
# ---------------------------------------------------------------------------

def test_4_risks_preserved(built: dict) -> None:
    rec = built["recommendations"][0]
    assert rec["risks"] == ["liquidity_not_ok"]


# ---------------------------------------------------------------------------
# Test 5 — invalidation_conditions preserved
# ---------------------------------------------------------------------------

def test_5_invalidation_conditions_preserved(built: dict) -> None:
    rec = built["recommendations"][0]
    assert rec["invalidation_conditions"] == ["price_above_ma200"]


# ---------------------------------------------------------------------------
# Test 6 — why_not_action included from DecisionRecord
# ---------------------------------------------------------------------------

def test_6_why_not_action_from_decision(built: dict) -> None:
    rec = built["recommendations"][0]
    assert rec["why_not_action"] == "risk_veto_triggered"
    assert rec["decision_record"]["risk_veto_triggered"] is True


# ---------------------------------------------------------------------------
# Test 7 — expert opinions linked by recommendation_id
# ---------------------------------------------------------------------------

def test_7_expert_opinions_linked(built: dict) -> None:
    rec = built["recommendations"][0]
    names = {op["expert_name"] for op in rec["expert_opinions"]}
    assert "RiskAgent" in names
    assert "TrendAgent" in names
    assert len(rec["expert_opinions"]) == 2


# ---------------------------------------------------------------------------
# Test 8 — missing detail fields → empty arrays/nulls, not fabricated text
# ---------------------------------------------------------------------------

def test_8_missing_fields_are_honest(tmp_path: Path) -> None:
    """A recommendation with no matching decision or opinions: fields are
    empty/null — never fabricated."""
    records = tmp_path / "records"
    bare_rec = dict(
        _REC_BASE,
        recommendation_id="rec_bare",
        symbol="BARE",
        support_reasons=[],
        oppose_reasons=[],
        risks=[],
        invalidation_conditions=[],
    )
    bare_rec.pop("decision_summary", None)
    _write_jsonl(records / "recommendations.jsonl", [bare_rec])
    _write_jsonl(records / "decisions.jsonl", [])
    _write_jsonl(records / "expert_opinions.jsonl", [])
    _write_jsonl(records / "data_gaps.jsonl", [])

    output = tmp_path / "out" / "recommendation_details.json"
    result = build_recommendation_details(records_dir=records, output_path=output)
    rec = result["recommendations"][0]

    assert rec["support_reasons"] == []
    assert rec["oppose_reasons"] == []
    assert rec["risks"] == []
    assert rec["invalidation_conditions"] == []
    assert rec["why_not_action"] is None
    assert rec["expert_opinions"] == []
    assert rec["data_quality_notes"] == []
    assert rec["decision_record"]["decision_id"] is None


# ---------------------------------------------------------------------------
# Test 9 — repeated recommendations marked with is_latest_for_symbol
# ---------------------------------------------------------------------------

def test_9_is_latest_for_symbol_deduplication(tmp_path: Path) -> None:
    """Two records with the same recommendation_id (smoke-run duplicate):
    P1D.3: ALL raw records are preserved in `recommendations`; only flags
    mark which one is the latest.  The newer record (higher created_at /
    last appended) gets is_latest_for_symbol=True; the older one gets False.
    `latest_recommendations` contains exactly one entry (the newer record).
    """
    records = tmp_path / "records"
    older = dict(_REC_BASE, created_at="2026-07-06T08:00:00+08:00")
    newer = dict(_REC_BASE, created_at="2026-07-06T11:00:00+08:00")
    _write_jsonl(records / "recommendations.jsonl", [older, newer])
    _write_jsonl(records / "decisions.jsonl", [])
    _write_jsonl(records / "expert_opinions.jsonl", [])
    _write_jsonl(records / "data_gaps.jsonl", [])

    output = tmp_path / "out" / "recommendation_details.json"
    result = build_recommendation_details(records_dir=records, output_path=output)

    recs = result["recommendations"]
    # P1D.3: history is preserved — both raw records appear
    assert len(recs) == 2, "P1D.3: all raw records must be preserved in recommendations"
    # The last-appended (newer) record is the latest
    assert recs[1]["is_latest_for_symbol"] is True
    assert recs[0]["is_latest_for_symbol"] is False
    # latest_recommendations contains exactly one entry
    assert len(result["latest_recommendations"]) == 1
    assert result["latest_recommendations"][0]["is_latest_for_symbol"] is True
    # summary uses new P1D.3 key names
    assert result["summary"]["total_records"] == 2
    assert result["summary"]["latest_per_symbol_count"] == 1


# ---------------------------------------------------------------------------
# Test 10 — refresh script copies recommendation_details.json into workspace
# ---------------------------------------------------------------------------

def test_10_refresh_copies_rec_details(tmp_path: Path) -> None:
    from scripts.refresh_stock_agent_aegis_status import refresh
    from scripts.build_desktop_status import (
        DEFAULT_HOLDINGS_PATH,
        DEFAULT_RECORDS_DIR,
        DEFAULT_MARKET_SNAPSHOT_SMOKE_REPORT,
        DEFAULT_PROVIDER_COVERAGE_REPORT,
        DEFAULT_PROVIDER_ROUTER_LIVE_REPORT,
    )

    workspace = tmp_path / "stock-agent" / "workspace" / "project-aegis"
    rec_details = tmp_path / "data" / "desktop" / "recommendation_details.json"

    result = refresh(
        output_html=tmp_path / "data" / "desktop" / "aegis_status.html",
        output_json=tmp_path / "data" / "desktop" / "aegis_status.json",
        rec_details_path=rec_details,
        stock_agent_workspace=workspace,
    )

    copied_names = [Path(f).name for f in result["copied_files"]]
    assert "recommendation_details.json" in copied_names
    assert (workspace / "recommendation_details.json").exists()


# ---------------------------------------------------------------------------
# Test 11 — stock-agent README includes recommendation_details rules
# ---------------------------------------------------------------------------

def test_11_readme_mentions_recommendation_details(tmp_path: Path) -> None:
    from scripts.refresh_stock_agent_aegis_status import refresh

    workspace = tmp_path / "workspace"
    refresh(
        output_html=tmp_path / "aegis_status.html",
        output_json=tmp_path / "aegis_status.json",
        rec_details_path=tmp_path / "recommendation_details.json",
        stock_agent_workspace=workspace,
    )
    readme = (workspace / "README_FOR_STOCK_AGENT.md").read_text()
    assert "recommendation_details.json" in readme
    assert "data/records/*.jsonl" in readme


# ---------------------------------------------------------------------------
# Test 12 — dashboard/index.html is NOT touched by the builder
# ---------------------------------------------------------------------------

def test_12_dashboard_index_html_unchanged() -> None:
    """Verify that neither the builder nor the refresh script ever write
    to dashboard/index.html — the file is a completely separate artifact.
    We check *code* only (stripping docstrings, which may mention index.html
    as a non-goal for documentation purposes)."""
    import aegis.desktop.recommendation_details as mod

    code = _code_only(inspect.getsource(mod))
    assert "index.html" not in code, (
        "recommendation_details.py code must not reference dashboard/index.html"
    )

    from scripts import refresh_stock_agent_aegis_status as rmod

    rcode = _code_only(inspect.getsource(rmod))
    assert "index.html" not in rcode, (
        "refresh_stock_agent_aegis_status.py code must not reference dashboard/index.html"
    )


# ---------------------------------------------------------------------------
# Test 13 — no broker / real-trading code in the builder
# ---------------------------------------------------------------------------

def test_13_no_broker_code_in_builder() -> None:
    import aegis.desktop.recommendation_details as mod

    code = _code_only(inspect.getsource(mod)).lower()
    forbidden = ["execute_trade", "place_order", "alpaca", "ibkr", "schwab",
                 "import broker", "from broker"]
    for term in forbidden:
        assert term not in code, f"builder code must not reference broker term: {term}"


# ---------------------------------------------------------------------------
# Test 14 — no manual PaperTrade creation in the builder
# ---------------------------------------------------------------------------

def test_14_no_paper_trade_creation_in_builder() -> None:
    import aegis.desktop.recommendation_details as mod

    source = inspect.getsource(mod)
    # Should never write paper_trades.jsonl or instantiate PaperTrade
    assert "paper_trades" not in source
    assert "PaperTrade(" not in source


# ---------------------------------------------------------------------------
# Test 15 — no composite scoring in the builder
# ---------------------------------------------------------------------------

def test_15_no_composite_scoring_in_builder() -> None:
    import aegis.desktop.recommendation_details as mod

    source = inspect.getsource(mod)
    forbidden = ["composite_score", "weighted_score", "score_weight"]
    for term in forbidden:
        assert term not in source.lower(), (
            f"builder must not add composite scoring term: {term}"
        )


# ---------------------------------------------------------------------------
# Test 16 — no token value read or printed in the builder
# ---------------------------------------------------------------------------

def test_16_no_token_read_in_builder() -> None:
    import aegis.desktop.recommendation_details as mod

    code = _code_only(inspect.getsource(mod))
    # Check code (not docstrings) for token-reading patterns
    forbidden_patterns = ["os.environ", "os.getenv", "dotenv", "load_dotenv",
                          "API_KEY =", "SECRET =", "TOKEN ="]
    for pat in forbidden_patterns:
        assert pat not in code, (
            f"builder code must not read/print tokens; found: {pat}"
        )


# ---------------------------------------------------------------------------
# Test 17 — CRCL not special-cased in the builder
# ---------------------------------------------------------------------------

def test_17_crcl_not_special_cased() -> None:
    import aegis.desktop.recommendation_details as mod

    code = _code_only(inspect.getsource(mod))
    assert "CRCL" not in code, (
        "builder code must not special-case CRCL; it is treated like any other symbol"
    )
