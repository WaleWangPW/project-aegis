"""P1D.9 tests for formal recommendation_details metrics.

Covers:
1. latest_recommendations is not empty.
2. risk_veto_details.metrics is built from signals.jsonl.
3. refresh_stock_agent_aegis_status preserves metrics in stock-agent workspace.
"""

from __future__ import annotations

import json
from pathlib import Path

from aegis.desktop.recommendation_details import build_recommendation_details
from scripts.refresh_stock_agent_aegis_status import refresh


REC_ID = "rec_20260706_pre_market_US_TEST"
DEC_ID = "dec_20260706_pre_market_US_TEST"
CREATED_AT = "2026-07-06T13:38:13+08:00"


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def _seed_records(records: Path) -> None:
    rec = {
        "recommendation_id": REC_ID,
        "date": "2026-07-06",
        "session": "pre_market",
        "symbol": "TEST",
        "name": "Test Corp",
        "market": "US",
        "sector": None,
        "status": "Exit",
        "action_label": "exit_position",
        "market_snapshot_id": "mkt_20260706_US_pre_market",
        "candidate_id": "cand_20260706_US_TEST",
        "expert_opinions": [
            "opn_20260706_US_TEST_risk",
            "opn_20260706_US_TEST_trend",
            "opn_20260706_US_TEST_capital_flow",
        ],
        "support_reasons": ["CapitalFlowAgent support"],
        "oppose_reasons": ["RiskAgent veto"],
        "risks": ["high_volatility", "severe_drawdown", "liquidity_risk"],
        "invalidation_conditions": ["RiskAgent stance reverses from veto"],
        "confidence": 0.25,
        "decision_summary": "support=1, oppose=1, veto=1 -> Exit.",
        "paper_trade_id": None,
        "review_id": None,
        "lifecycle_status": "open",
        "created_at": CREATED_AT,
        "updated_at": CREATED_AT,
    }

    dec = {
        "decision_id": DEC_ID,
        "recommendation_id": REC_ID,
        "final_status": "Exit",
        "final_action": "exit_position",
        "support_count": 1,
        "oppose_count": 1,
        "neutral_count": 0,
        "veto_count": 1,
        "risk_veto_triggered": True,
        "confidence": 0.25,
        "why_not_action": "risk_veto_triggered",
        "created_at": CREATED_AT,
    }

    ops = [
        {
            "opinion_id": "opn_20260706_US_TEST_risk",
            "recommendation_id": REC_ID,
            "expert_name": "RiskAgent",
            "stance": "veto",
            "confidence": 0.75,
            "evidence": ["signal:sig_20260706_US_TEST_risk_volatility_drawdown"],
            "risks": ["high_volatility", "severe_drawdown", "liquidity_risk"],
            "missing_data": [],
            "summary": "Unacceptable risk detected.",
            "created_at": CREATED_AT,
        },
        {
            "opinion_id": "opn_20260706_US_TEST_trend",
            "recommendation_id": REC_ID,
            "expert_name": "TrendAgent",
            "stance": "oppose",
            "confidence": 0.6,
            "evidence": [
                "signal:sig_20260706_US_TEST_trend_ma_alignment",
                "signal:sig_20260706_US_TEST_relative_strength_vs_index",
            ],
            "risks": ["trend_down"],
            "missing_data": [],
            "summary": "Trend direction=downtrend.",
            "created_at": CREATED_AT,
        },
        {
            "opinion_id": "opn_20260706_US_TEST_capital_flow",
            "recommendation_id": REC_ID,
            "expert_name": "CapitalFlowAgent",
            "stance": "support",
            "confidence": 0.6,
            "evidence": ["signal:sig_20260706_US_TEST_volume_expansion"],
            "risks": [],
            "missing_data": [],
            "summary": "Volume expansion.",
            "created_at": CREATED_AT,
        },
    ]

    signals = [
        {
            "signal_id": "sig_20260706_US_TEST_risk_volatility_drawdown",
            "signal_name": "risk_volatility_drawdown",
            "signal_type": "risk",
            "symbol": "TEST",
            "market": "US",
            "date": "2026-07-06",
            "value": {
                "volatility": 0.0618692952369419,
                "max_drawdown": -0.3157720329521754,
                "flags": ["high_volatility", "severe_drawdown", "liquidity_risk"],
            },
            "interpretation": "Risk flags.",
            "evidence_strength": "strong",
            "data_source": "test",
            "lookback_window": "20d",
            "valid_until": None,
        },
        {
            "signal_id": "sig_20260706_US_TEST_volume_expansion",
            "signal_name": "volume_expansion",
            "signal_type": "volume",
            "symbol": "TEST",
            "market": "US",
            "date": "2026-07-06",
            "value": {
                "latest_vol": 17683500.0,
                "avg_vol": 14283960.0,
                "state": "expansion",
            },
            "interpretation": "Volume expansion.",
            "evidence_strength": "strong",
            "data_source": "test",
            "lookback_window": "20d",
            "valid_until": None,
        },
        {
            "signal_id": "sig_20260706_US_TEST_trend_ma_alignment",
            "signal_name": "trend_ma_alignment",
            "signal_type": "trend",
            "symbol": "TEST",
            "market": "US",
            "date": "2026-07-06",
            "value": {
                "ma20": 76.59549980163574,
                "ma60": 96.5538330078125,
                "recent_return": -0.060892238928562874,
                "direction": "downtrend",
            },
            "interpretation": "Downtrend.",
            "evidence_strength": "strong",
            "data_source": "test",
            "lookback_window": "60d",
            "valid_until": None,
        },
        {
            "signal_id": "sig_20260706_US_TEST_relative_strength_vs_index",
            "signal_name": "relative_strength_vs_index",
            "signal_type": "relative_strength",
            "symbol": "TEST",
            "market": "US",
            "date": "2026-07-06",
            "value": {
                "symbol_return": -0.060892238928562874,
                "index_return": 0.017091426015420616,
                "relative_strength": -0.07798366494398348,
                "state": "underperforming",
            },
            "interpretation": "Underperforming.",
            "evidence_strength": "moderate",
            "data_source": "test",
            "lookback_window": "5d",
            "valid_until": None,
        },
    ]

    stale_gap = {
        "gap_id": "gap_20260706_US_TEST_daily_bars",
        "date": "20260706",
        "market": "US",
        "symbol": "TEST",
        "provider": "yahoo_finance",
        "data_type": "daily_bars",
        "severity": "warning",
        "message": "No daily bars returned for TEST via provider_route='yahoo_finance'.",
        "created_at": CREATED_AT,
    }

    _write_jsonl(records / "recommendations.jsonl", [rec])
    _write_jsonl(records / "decisions.jsonl", [dec])
    _write_jsonl(records / "expert_opinions.jsonl", ops)
    _write_jsonl(records / "signals.jsonl", signals)
    _write_jsonl(records / "data_gaps.jsonl", [stale_gap])


def test_p1d9_latest_recommendations_not_empty(tmp_path: Path) -> None:
    records = tmp_path / "records"
    _seed_records(records)

    out = build_recommendation_details(records, tmp_path / "recommendation_details.json")

    assert len(out["latest_recommendations"]) == 1
    assert out["latest_recommendations"][0]["symbol"] == "TEST"


def test_p1d9_risk_metrics_are_built_from_signals_jsonl(tmp_path: Path) -> None:
    records = tmp_path / "records"
    _seed_records(records)

    out = build_recommendation_details(records, tmp_path / "recommendation_details.json")
    rec = out["latest_recommendations"][0]
    metrics = rec["risk_veto_details"]["metrics"]

    assert metrics["volatility"] == 0.0618692952369419
    assert metrics["max_drawdown"] == -0.3157720329521754
    assert metrics["latest_volume"] == 17683500.0
    assert metrics["avg_volume"] == 14283960.0
    assert metrics["relative_strength_5d"] == -0.07798366494398348
    assert rec["data_availability"]["signals_with_numeric_values"] == [
        "trend_ma_alignment",
        "relative_strength_vs_index",
        "volume_expansion",
        "risk_volatility_drawdown",
    ]


def test_p1d9_refresh_preserves_metrics_in_stock_agent_workspace(tmp_path: Path) -> None:
    records = tmp_path / "records"
    _seed_records(records)

    workspace = tmp_path / "stock-agent-workspace"
    rec_details_path = tmp_path / "desktop" / "recommendation_details.json"

    refresh(
        holdings_path=tmp_path / "missing_holdings.yaml",
        records_dir=records,
        output_html=tmp_path / "desktop" / "aegis_status.html",
        output_json=tmp_path / "desktop" / "aegis_status.json",
        rec_details_path=rec_details_path,
        provider_coverage_report=tmp_path / "missing_provider_coverage.json",
        provider_router_live_report=tmp_path / "missing_provider_router.json",
        market_snapshot_smoke_report=tmp_path / "missing_smoke.json",
        stock_agent_workspace=workspace,
    )

    mirrored = json.loads((workspace / "recommendation_details.json").read_text())
    rec = mirrored["latest_recommendations"][0]
    metrics = rec["risk_veto_details"]["metrics"]

    assert len(mirrored["latest_recommendations"]) == 1
    assert rec["symbol"] == "TEST"
    assert metrics["volatility"] == 0.0618692952369419
    assert metrics["max_drawdown"] == -0.3157720329521754
    assert metrics["relative_strength_5d"] == -0.07798366494398348
