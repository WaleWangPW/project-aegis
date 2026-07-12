"""Phase 5 tests for DashboardBuilder — PHASE5 doc §10.2."""

from __future__ import annotations

from pathlib import Path

import pytest

from aegis.dashboard.builder import DashboardBuilder
from aegis.utils.jsonl import append_jsonl

HOLDINGS_YAML = """
holdings:
  - holding_id: hold_US_CRCL_20260701
    symbol: CRCL
    name: Circle Internet Group
    market: US
    shares: 254
    avg_cost: 109.157
    currency: USD
    entry_date: "2026-07-01"
    status: open
    notes: "test fixture"
"""


def _recommendation(
    *,
    symbol="AAA",
    market="US",
    status="Watch",
    support_reasons=None,
    oppose_reasons=None,
    risks=None,
    invalidation_conditions=None,
    sector="Fintech",
    action_label="prepare_entry_plan",
    decision_summary="fixture decision summary",
) -> dict:
    return {
        "recommendation_id": f"rec_20260704_pre_market_{market}_{symbol}",
        "date": "2026-07-04",
        "session": "pre_market",
        "symbol": symbol,
        "name": None,
        "market": market,
        "sector": sector,
        "status": status,
        "action_label": action_label,
        "market_snapshot_id": f"mkt_20260704_{market}_pre_market",
        "candidate_id": f"cand_20260704_{market}_{symbol}",
        "expert_opinions": ["opn_1", "opn_2"],
        "support_reasons": support_reasons if support_reasons is not None else ["TrendAgent support: fixture (source_opinion_id=opn_1)"],
        "oppose_reasons": oppose_reasons if oppose_reasons is not None else [],
        "risks": risks if risks is not None else [],
        "invalidation_conditions": invalidation_conditions if invalidation_conditions is not None else ["fixture invalidation"],
        "confidence": 0.6,
        "decision_summary": decision_summary,
        "paper_trade_id": None,
        "review_id": None,
        "lifecycle_status": "open",
        "created_at": "2026-07-04T07:31:00-07:00",
        "updated_at": "2026-07-04T07:31:00-07:00",
    }


def _market_snapshot(market="US", summary="美股：test summary") -> dict:
    return {
        "snapshot_id": f"mkt_20260704_{market}_pre_market",
        "date": "2026-07-04",
        "session": "pre_market",
        "market": market,
        "index_summary": {"primary_index": "SPX", "primary_index_change_pct": 0.01},
        "trend_state": "uptrend",
        "liquidity_state": "normal",
        "sentiment_state": "risk_on",
        "sector_rotation": [],
        "risk_level": "low",
        "summary": summary,
        "data_quality": {"status": "complete", "missing_fields": [], "warnings": []},
        "created_at": "2026-07-04T07:31:00-07:00",
    }


def _setup(tmp_path: Path) -> tuple[Path, Path, Path]:
    records_dir = tmp_path / "records"
    holdings_path = tmp_path / "holdings.yaml"
    output_path = tmp_path / "dashboard" / "dashboard_data.json"
    holdings_path.write_text(HOLDINGS_YAML, encoding="utf-8")
    return records_dir, holdings_path, output_path


def test_no_records_but_crcl_holding_exists(tmp_path: Path):
    records_dir, holdings_path, output_path = _setup(tmp_path)
    builder = DashboardBuilder(records_dir=records_dir, holdings_config_path=holdings_path, output_path=output_path)

    payload = builder.build(date="2026-07-04", session="pre_market")

    assert payload["market_snapshot"]["A"].startswith("DATA_GAP")
    assert payload["market_snapshot"]["H"].startswith("DATA_GAP")
    assert payload["market_snapshot"]["US"].startswith("DATA_GAP")
    assert payload["recommendations"] == {"action": [], "ready": [], "watch": []}
    tickers = {h["ticker"] for h in payload["holdings"]}
    assert "CRCL" in tickers


def test_action_recommendation_appears_in_action_bucket(tmp_path: Path):
    records_dir, holdings_path, output_path = _setup(tmp_path)
    append_jsonl(records_dir / "recommendations.jsonl", _recommendation(symbol="AAA", status="Action"))
    builder = DashboardBuilder(records_dir=records_dir, holdings_config_path=holdings_path, output_path=output_path)

    payload = builder.build(date="2026-07-04", session="pre_market")

    assert len(payload["recommendations"]["action"]) == 1
    assert payload["recommendations"]["action"][0]["ticker"] == "AAA"
    assert payload["recommendations"]["ready"] == []
    assert payload["recommendations"]["watch"] == []


def test_ready_recommendation_appears_in_ready_bucket(tmp_path: Path):
    records_dir, holdings_path, output_path = _setup(tmp_path)
    append_jsonl(records_dir / "recommendations.jsonl", _recommendation(symbol="BBB", status="Ready"))
    builder = DashboardBuilder(records_dir=records_dir, holdings_config_path=holdings_path, output_path=output_path)

    payload = builder.build(date="2026-07-04", session="pre_market")

    assert len(payload["recommendations"]["ready"]) == 1
    assert payload["recommendations"]["ready"][0]["ticker"] == "BBB"


def test_watch_recommendation_appears_in_watch_bucket(tmp_path: Path):
    records_dir, holdings_path, output_path = _setup(tmp_path)
    append_jsonl(records_dir / "recommendations.jsonl", _recommendation(symbol="CCC", status="Watch"))
    builder = DashboardBuilder(records_dir=records_dir, holdings_config_path=holdings_path, output_path=output_path)

    payload = builder.build(date="2026-07-04", session="pre_market")

    assert len(payload["recommendations"]["watch"]) == 1
    assert payload["recommendations"]["watch"][0]["ticker"] == "CCC"


def test_exit_recommendation_for_holding_appears_in_today_focus_not_buckets(tmp_path: Path):
    records_dir, holdings_path, output_path = _setup(tmp_path)
    append_jsonl(
        records_dir / "recommendations.jsonl",
        _recommendation(symbol="CRCL", market="US", status="Exit", decision_summary="risk veto on holding"),
    )
    builder = DashboardBuilder(records_dir=records_dir, holdings_config_path=holdings_path, output_path=output_path)

    payload = builder.build(date="2026-07-04", session="pre_market")

    assert payload["recommendations"] == {"action": [], "ready": [], "watch": []}
    assert any("CRCL" in item["text"] and "Exit" in item["text"] for item in payload["today_focus"])
    crcl_holding = next(h for h in payload["holdings"] if h["ticker"] == "CRCL")
    assert crcl_holding["action"] == "exit"


def test_missing_support_oppose_risk_fields_use_honest_fallback_text(tmp_path: Path):
    records_dir, holdings_path, output_path = _setup(tmp_path)
    append_jsonl(
        records_dir / "recommendations.jsonl",
        _recommendation(
            symbol="DDD",
            status="Watch",
            support_reasons=[],
            oppose_reasons=[],
            risks=[],
            invalidation_conditions=[],
            decision_summary="",
        ),
    )
    builder = DashboardBuilder(records_dir=records_dir, holdings_config_path=holdings_path, output_path=output_path)

    payload = builder.build(date="2026-07-04", session="pre_market")

    item = payload["recommendations"]["watch"][0]
    assert item["reason"] == "暂无明确支持理由"
    assert item["counter_reason"] == "暂无明确反对理由"
    assert item["risk"] == "暂无明确风险记录"
    assert item["invalidation_condition"] == "暂无失效条件记录"


def test_write_json_produces_a_readable_file(tmp_path: Path):
    records_dir, holdings_path, output_path = _setup(tmp_path)
    builder = DashboardBuilder(records_dir=records_dir, holdings_config_path=holdings_path, output_path=output_path)

    payload = builder.build(date="2026-07-04", session="pre_market")
    written_path = builder.write_json(payload)

    assert written_path == output_path
    assert output_path.exists()
