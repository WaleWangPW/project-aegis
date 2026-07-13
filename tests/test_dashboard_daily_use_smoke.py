from __future__ import annotations

from datetime import datetime

from scripts.smoke_dashboard_daily_use import build_smoke


def _health() -> dict:
    return {
        "status": "READY",
        "safety": {
            "simulation_only": True,
            "no_broker_api": True,
            "no_order_placement": True,
            "no_trading_webhook": True,
        },
    }


def _readiness() -> dict:
    return {
        "status": "READY_FOR_SIMULATION_USE",
        "safety": {
            "simulation_only": True,
            "no_broker_api": True,
            "no_order_placement": True,
            "no_trading_webhook": True,
        },
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
        }
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


def test_dashboard_daily_use_smoke_passes_for_simulation_ready_dashboard():
    report = build_smoke(
        health_response=_health(),
        dashboard_html="<title>Project Aegis</title>",
        daily_use_readiness=_readiness(),
        intent_ingest=_intent(),
        real_click_acceptance=_real_click(),
        ranking_gate=_gate(),
        retry_readiness=_retry(),
        now=datetime.fromisoformat("2026-07-13T13:45:00+08:00"),
    )

    assert report["status"] == "PASS"
    assert report["blockers"] == []
    assert report["safety"]["no_order_placement"] is True


def test_dashboard_daily_use_smoke_fails_without_bridge_health():
    report = build_smoke(
        health_response=None,
        dashboard_html="<title>Project Aegis</title>",
        daily_use_readiness=_readiness(),
        intent_ingest=_intent(),
        real_click_acceptance=_real_click(),
        ranking_gate=_gate(),
        retry_readiness=_retry(),
        now=datetime.fromisoformat("2026-07-13T13:45:00+08:00"),
    )

    assert report["status"] == "FAIL"
    assert "bridge_health_ready" in report["blockers"]


def test_dashboard_daily_use_smoke_fails_if_gate_allows_unapproved_suggestions():
    gate = _gate()
    gate["summary"]["ranking_gate_approved_count"] = 1
    gate["summary"]["user_facing_suggestion_allowed"] = True

    report = build_smoke(
        health_response=_health(),
        dashboard_html="<title>Project Aegis</title>",
        daily_use_readiness=_readiness(),
        intent_ingest=_intent(),
        real_click_acceptance=_real_click(),
        ranking_gate=gate,
        retry_readiness=_retry(),
        now=datetime.fromisoformat("2026-07-13T13:45:00+08:00"),
    )

    assert report["status"] == "FAIL"
    assert "ranking_gate_blocks_suggestions" in report["blockers"]


def test_dashboard_daily_use_smoke_fails_without_real_click_acceptance():
    report = build_smoke(
        health_response=_health(),
        dashboard_html="<title>Project Aegis</title>",
        daily_use_readiness=_readiness(),
        intent_ingest=_intent(),
        real_click_acceptance={"status": "WAITING_FOR_USER_CLICK", "safety": {}},
        ranking_gate=_gate(),
        retry_readiness=_retry(),
        now=datetime.fromisoformat("2026-07-13T13:45:00+08:00"),
    )

    assert report["status"] == "FAIL"
    assert "real_dashboard_click_accepted" in report["blockers"]
