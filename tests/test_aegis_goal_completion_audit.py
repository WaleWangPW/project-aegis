from __future__ import annotations

from datetime import datetime

from scripts.build_aegis_goal_completion_audit import build_audit


def _readiness() -> dict:
    return {
        "status": "READY_FOR_SIMULATION_USE",
        "safety": {
            "no_broker_api": True,
            "no_order_placement": True,
            "no_trading_webhook": True,
            "no_secret_values_read": True,
        },
    }


def _smoke() -> dict:
    return {
        "status": "PASS",
        "safety": {
            "secret_values_read": False,
            "no_broker_api": True,
            "no_order_placement": True,
            "no_trading_webhook": True,
        },
    }


def _real_click() -> dict:
    return {
        "status": "ACCEPTED",
        "latest_click": {"symbol": "VRTX", "action": "aegis_more_news"},
        "safety": {
            "feedback_evidence_only": True,
            "no_broker_api": True,
            "no_order_placement": True,
            "no_trading_webhook": True,
        },
    }


def _dry_run() -> dict:
    return {"status": "PASS"}


def _selection() -> dict:
    return {
        "summary": {
            "total_candidates": 30,
            "research_candidate_count": 13,
            "news_enriched_count": 9,
            "markets_passed": ["A", "HK", "US"],
        }
    }


def _stock_agent() -> dict:
    return {
        "status": "PASS",
        "summary": {
            "command_count": 15,
            "failed_command_count": 0,
            "rankable_strategy_count": 0,
        },
    }


def _gate() -> dict:
    return {
        "status": "PASS",
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


def _retry_waiting() -> dict:
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


def _retry_ready() -> dict:
    return {
        "status": "READY",
        "ready_to_run": True,
        "recommended_command": "make a-share-current-day-retry",
        "safety": {
            "secret_values_read": False,
            "executes_retry": False,
            "no_broker_api": True,
            "no_order_placement": True,
            "no_trading_webhook": True,
        },
    }


def _retry_guard(status: str, retry_exit_code: int | None, audit_exit_code: int | None) -> dict:
    return {
        "status": status,
        "retry_exit_code": retry_exit_code,
        "audit_exit_code": audit_exit_code,
        "retry_failure": {
            "failed_dates": [
                {
                    "trade_date": "20260713",
                    "error": "daily 20260713 insufficient rows: 0",
                }
            ]
        }
        if status == "FAIL"
        else None,
    }


def test_goal_audit_marks_daily_use_ready_with_pending_a_share_retry():
    report = build_audit(
        dashboard_readiness=_readiness(),
        dashboard_smoke=_smoke(),
        real_click=_real_click(),
        intent_dry_run=_dry_run(),
        stock_selection=_selection(),
        stock_agent_cycle=_stock_agent(),
        ranking_gate=_gate(),
        retry_readiness=_retry_waiting(),
        now=datetime.fromisoformat("2026-07-13T14:15:00+08:00"),
    )

    assert report["status"] == "READY_FOR_DAILY_USE_WITH_PENDING_A_SHARE_RETRY"
    assert report["missing_count"] == 0
    assert report["pending_count"] == 1


def test_goal_audit_keeps_retry_pending_when_guarded_retry_fails():
    report = build_audit(
        dashboard_readiness=_readiness(),
        dashboard_smoke=_smoke(),
        real_click=_real_click(),
        intent_dry_run=_dry_run(),
        stock_selection=_selection(),
        stock_agent_cycle=_stock_agent(),
        ranking_gate=_gate(),
        retry_readiness=_retry_ready(),
        retry_guard=_retry_guard("FAIL", 2, 0),
        now=datetime.fromisoformat("2026-07-13T15:50:00+08:00"),
    )

    retry_row = report["requirements"][-1]
    assert report["status"] == "READY_FOR_DAILY_USE_WITH_PENDING_A_SHARE_RETRY"
    assert report["missing_count"] == 0
    assert report["pending_count"] == 1
    assert retry_row["status"] == "PENDING"
    assert retry_row["detail"]["guard_status"] == "FAIL"
    assert retry_row["detail"]["guard_failed_dates"][0]["trade_date"] == "20260713"


def test_goal_audit_marks_retry_achieved_only_after_guarded_retry_passes():
    report = build_audit(
        dashboard_readiness=_readiness(),
        dashboard_smoke=_smoke(),
        real_click=_real_click(),
        intent_dry_run=_dry_run(),
        stock_selection=_selection(),
        stock_agent_cycle=_stock_agent(),
        ranking_gate=_gate(),
        retry_readiness=_retry_ready(),
        retry_guard=_retry_guard("PASS", 0, 0),
        now=datetime.fromisoformat("2026-07-13T15:50:00+08:00"),
    )

    assert report["status"] == "READY_FOR_DAILY_SIMULATION_USE"
    assert report["missing_count"] == 0
    assert report["pending_count"] == 0


def test_goal_audit_fails_if_gate_allows_user_facing_suggestions():
    gate = _gate()
    gate["summary"]["ranking_gate_approved_count"] = 1
    gate["summary"]["user_facing_suggestion_allowed"] = True
    report = build_audit(
        dashboard_readiness=_readiness(),
        dashboard_smoke=_smoke(),
        real_click=_real_click(),
        intent_dry_run=_dry_run(),
        stock_selection=_selection(),
        stock_agent_cycle=_stock_agent(),
        ranking_gate=gate,
        retry_readiness=_retry_waiting(),
        now=datetime.fromisoformat("2026-07-13T14:15:00+08:00"),
    )

    assert report["status"] == "NOT_READY"
    assert report["missing_count"] == 1
