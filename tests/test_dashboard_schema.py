"""Phase 5 tests for the Dashboard JSON schema — PHASE5 doc §10.1."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from aegis.dashboard.schema import validate_dashboard_payload


def _minimal_payload() -> dict:
    return {
        "date": "2026-07-04",
        "stage_note": "Phase 5 test",
        "market_snapshot": {"A": "DATA_GAP: 未找到 A 股 MarketSnapshot", "H": "DATA_GAP: 未找到 H 股 MarketSnapshot", "US": "DATA_GAP: 未找到 美股 MarketSnapshot"},
        "today_focus": [],
        "holdings": [],
        "recommendations": {"action": [], "ready": [], "watch": []},
        "paper_trading": {"new_today": [], "open_positions_perf": []},
        "review_note": "Phase 5: Review backend not implemented yet.",
    }


def test_valid_minimal_payload_passes():
    result = validate_dashboard_payload(_minimal_payload())
    assert result["date"] == "2026-07-04"
    assert result["recommendations"]["action"] == []


def test_missing_top_level_key_fails():
    payload = _minimal_payload()
    del payload["review_note"]
    with pytest.raises(ValidationError):
        validate_dashboard_payload(payload)


def test_missing_recommendation_bucket_fails():
    payload = _minimal_payload()
    del payload["recommendations"]["watch"]
    with pytest.raises(ValidationError):
        validate_dashboard_payload(payload)


def test_missing_paper_trading_bucket_fails():
    payload = _minimal_payload()
    del payload["paper_trading"]["open_positions_perf"]
    with pytest.raises(ValidationError):
        validate_dashboard_payload(payload)


def test_crcl_holding_shape_passes():
    payload = _minimal_payload()
    payload["holdings"] = [
        {
            "ticker": "CRCL",
            "market": "US",
            "shares": 254,
            "cost_price": 109.157,
            "action": "wait",
            "action_label": "持有观察",
            "reason": "test reason",
            "risk": "test risk",
            "invalidation_condition": "test invalidation",
        }
    ]
    result = validate_dashboard_payload(payload)
    assert result["holdings"][0]["ticker"] == "CRCL"
