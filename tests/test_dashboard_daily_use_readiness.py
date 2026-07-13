from __future__ import annotations

from datetime import datetime

from scripts.build_dashboard_daily_use_readiness import build_readiness


def _stock_selection() -> dict:
    return {
        "summary": {
            "total_candidates": 30,
            "research_candidate_count": 13,
            "news_enriched_count": 9,
            "markets_passed": ["A", "HK", "US"],
        }
    }


def _intent() -> dict:
    return {
        "status": "RECORDED",
        "latest_symbol": "VRTX",
        "latest_action": "aegis_more_news",
        "safety": {
            "recommendation_mutated": False,
            "paper_trade_created": False,
            "holding_mutated": False,
            "broker_called": False,
            "order_placed": False,
            "trading_webhook_called": False,
        },
    }


def _real_click() -> dict:
    return {
        "status": "ACCEPTED",
        "latest_click": {
            "symbol": "VRTX",
            "action": "aegis_more_news",
        },
        "safety": {
            "feedback_evidence_only": True,
            "no_broker_api": True,
            "no_order_placement": True,
            "no_trading_webhook": True,
        },
    }


def _gate() -> dict:
    return {
        "summary": {
            "ranking_gate_approved_count": 0,
            "user_facing_suggestion_allowed": False,
        },
        "safety": {
            "no_broker_api": True,
            "no_order_placement": True,
            "no_trading_webhook": True,
        },
    }


def _retry() -> dict:
    return {
        "status": "WAITING",
        "ready_to_run": False,
        "safety": {
            "secret_values_read": False,
            "executes_retry": False,
            "no_broker_api": True,
            "no_order_placement": True,
            "no_trading_webhook": True,
        },
    }


def test_daily_use_readiness_allows_simulation_use_with_gate_closed():
    report = build_readiness(
        stock_selection=_stock_selection(),
        intent_ingest=_intent(),
        real_click_acceptance=_real_click(),
        ranking_gate=_gate(),
        retry_readiness=_retry(),
        health={"health_status": "NORMAL"},
        now=datetime.fromisoformat("2026-07-13T13:35:00+08:00"),
    )

    assert report["status"] == "READY_FOR_SIMULATION_USE"
    assert report["blockers"] == []
    assert report["summary"]["user_facing_suggestion_allowed"] is False
    assert report["summary"]["real_click_acceptance_status"] == "ACCEPTED"
    assert report["safety"]["no_order_placement"] is True


def test_daily_use_readiness_blocks_when_button_feedback_has_trading_effect():
    intent = _intent()
    intent["safety"]["order_placed"] = True

    report = build_readiness(
        stock_selection=_stock_selection(),
        intent_ingest=intent,
        real_click_acceptance=_real_click(),
        ranking_gate=_gate(),
        retry_readiness=_retry(),
        health={"health_status": "NORMAL"},
        now=datetime.fromisoformat("2026-07-13T13:35:00+08:00"),
    )

    assert report["status"] == "NOT_READY"
    assert "button_feedback_has_no_trading_side_effects" in report["blockers"]


def test_daily_use_readiness_blocks_missing_news():
    stock_selection = _stock_selection()
    stock_selection["summary"]["news_enriched_count"] = 0

    report = build_readiness(
        stock_selection=stock_selection,
        intent_ingest=_intent(),
        real_click_acceptance=_real_click(),
        ranking_gate=_gate(),
        retry_readiness=_retry(),
        health={"health_status": "NORMAL"},
        now=datetime.fromisoformat("2026-07-13T13:35:00+08:00"),
    )

    assert report["status"] == "NOT_READY"
    assert "news_summary_available" in report["blockers"]


def test_daily_use_readiness_blocks_without_real_click_acceptance():
    report = build_readiness(
        stock_selection=_stock_selection(),
        intent_ingest=_intent(),
        real_click_acceptance={"status": "WAITING_FOR_USER_CLICK", "safety": {}},
        ranking_gate=_gate(),
        retry_readiness=_retry(),
        health={"health_status": "NORMAL"},
        now=datetime.fromisoformat("2026-07-13T13:35:00+08:00"),
    )

    assert report["status"] == "NOT_READY"
    assert "real_dashboard_click_accepted" in report["blockers"]
