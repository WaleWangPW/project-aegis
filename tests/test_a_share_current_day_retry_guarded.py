from __future__ import annotations

from scripts.run_a_share_current_day_retry_guarded import build_report, render_markdown


def _readiness(status: str, ready_to_run: bool) -> dict:
    return {
        "status": status,
        "ready_to_run": ready_to_run,
        "recommended_command": "make a-share-current-day-retry" if ready_to_run else None,
        "blockers": [] if ready_to_run else ["before_retry_window"],
    }


def test_guard_report_waiting_does_not_run_retry():
    report = build_report(
        status="WAITING",
        readiness=_readiness("WAITING", False),
        preflight_exit_code=0,
        retry_exit_code=None,
        audit_exit_code=None,
        started_at="2026-07-13T14:00:00+08:00",
        finished_at="2026-07-13T14:00:01+08:00",
        wait_mode=False,
    )

    assert report["status"] == "WAITING"
    assert report["preflight_status"] == "WAITING"
    assert report["preflight_ready_to_run"] is False
    assert report["retry_exit_code"] is None
    assert report["audit_exit_code"] is None
    assert report["safety"]["preflight_required"] is True
    assert report["safety"]["no_broker_api"] is True
    assert report["safety"]["no_order_placement"] is True
    assert report["safety"]["no_trading_webhook"] is True


def test_guard_report_ready_pass_records_retry_and_audit_exit_codes():
    report = build_report(
        status="PASS",
        readiness=_readiness("READY", True),
        preflight_exit_code=0,
        retry_exit_code=0,
        audit_exit_code=0,
        started_at="2026-07-13T15:31:00+08:00",
        finished_at="2026-07-13T15:40:00+08:00",
        wait_mode=False,
    )

    assert report["status"] == "PASS"
    assert report["preflight_status"] == "READY"
    assert report["preflight_ready_to_run"] is True
    assert report["recommended_command"] == "make a-share-current-day-retry"
    assert report["retry_exit_code"] == 0
    assert report["audit_exit_code"] == 0


def test_guard_markdown_keeps_simulation_only_boundary_visible():
    report = build_report(
        status="BLOCKED",
        readiness={"status": "BLOCKED", "ready_to_run": False, "blockers": ["coverage_status_not_waiting"]},
        preflight_exit_code=0,
        retry_exit_code=None,
        audit_exit_code=None,
        started_at="2026-07-13T15:31:00+08:00",
        finished_at="2026-07-13T15:31:01+08:00",
        wait_mode=False,
    )

    markdown = render_markdown(report)

    assert "Runs the retry chain only after the preflight is READY" in markdown
    assert "Does not print secret values" in markdown
    assert "place orders" in markdown
    assert "trading webhooks" in markdown
