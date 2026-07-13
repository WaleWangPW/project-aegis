from __future__ import annotations

from datetime import datetime

from scripts.build_dashboard_real_click_acceptance import build_acceptance


def _event() -> dict:
    return {
        "event_id": "aegis_stock_feedback_20260713T050152191406Z",
        "received_at": "2026-07-13T13:01:52+08:00",
        "source": "dashboard_local_intent_export",
        "action": "aegis_more_news",
        "feedback_type": "user_requests_more_news",
        "symbol": "VRTX",
        "raw_value_sha256": "abc",
        "record_mode": "feedback_evidence_only",
        "effects": {
            "recommendation_mutated": False,
            "paper_trade_created": False,
            "holding_mutated": False,
            "broker_called": False,
            "order_placed": False,
            "trading_webhook_called": False,
        },
    }


def _intent_report(event: dict | None = None) -> dict:
    return {"status": "RECORDED", "latest_event": event or _event()}


def _feedback_report(event: dict | None = None) -> dict:
    event = event or _event()
    return {"status": "RECORDED", "event": event, "safety": event["effects"]}


def test_dashboard_real_click_acceptance_accepts_recent_dashboard_feedback():
    report = build_acceptance(
        intent_report=_intent_report(),
        feedback_report=_feedback_report(),
        now=datetime.fromisoformat("2026-07-13T14:00:00+08:00"),
    )

    assert report["status"] == "ACCEPTED"
    assert report["blockers"] == []
    assert report["latest_click"]["symbol"] == "VRTX"
    assert report["checks"]["no_trading_side_effects"] is True


def test_dashboard_real_click_acceptance_rejects_non_dashboard_source():
    event = _event()
    event["source"] = "openclaw_stock_assistant_feishu_card"
    report = build_acceptance(
        intent_report=_intent_report(event),
        feedback_report=_feedback_report(event),
        now=datetime.fromisoformat("2026-07-13T14:00:00+08:00"),
    )

    assert report["status"] == "WAITING_FOR_USER_CLICK"
    assert "source_is_dashboard_local" in report["blockers"]


def test_dashboard_real_click_acceptance_rejects_trading_side_effects():
    event = _event()
    event["effects"]["order_placed"] = True
    report = build_acceptance(
        intent_report=_intent_report(event),
        feedback_report=_feedback_report(event),
        now=datetime.fromisoformat("2026-07-13T14:00:00+08:00"),
    )

    assert report["status"] == "WAITING_FOR_USER_CLICK"
    assert "no_trading_side_effects" in report["blockers"]
