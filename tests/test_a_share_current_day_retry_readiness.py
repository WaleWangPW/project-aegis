from __future__ import annotations

from datetime import datetime

from scripts.build_a_share_current_day_retry_readiness import build_readiness


def _coverage() -> dict:
    return {
        "generated_at": "2026-07-13T12:19:06+08:00",
        "coverage_status": "WAITING_CURRENT_TRADING_DAY_DAILY",
        "answer_label": "NO",
        "current_day_retry": {
            "needed": True,
            "retry_not_before_local_time": "15:30 Asia/Shanghai",
            "command": "make build-p23-2-historical-market-cache START_DATE=20250713 END_DATE=20260713",
        },
    }


def test_retry_readiness_waits_before_retry_window():
    report = build_readiness(coverage_report=_coverage(), now=datetime.fromisoformat("2026-07-13T13:05:00+08:00"))

    assert report["status"] == "WAITING"
    assert report["ready_to_run"] is False
    assert report["recommended_command"] is None
    assert report["safety"]["network_used"] is False
    assert report["safety"]["executes_retry"] is False


def test_retry_readiness_ready_after_retry_window():
    report = build_readiness(coverage_report=_coverage(), now=datetime.fromisoformat("2026-07-13T15:31:00+08:00"))

    assert report["status"] == "READY"
    assert report["ready_to_run"] is True
    assert report["recommended_command"] == "make a-share-current-day-retry"
    assert "make stock-agent-a-share-strategy-cycle-managed-expanded" in report["command_chain"]


def test_retry_readiness_not_needed_when_coverage_yes():
    coverage = _coverage()
    coverage["answer_label"] = "YES"
    coverage["coverage_status"] = "MATERIALIZED_CURRENT_FULL_YEAR_CANDIDATE"

    report = build_readiness(coverage_report=coverage, now=datetime.fromisoformat("2026-07-13T15:31:00+08:00"))

    assert report["status"] == "NOT_NEEDED"
    assert report["ready_to_run"] is False


def test_retry_readiness_blocks_unexpected_coverage_status():
    coverage = _coverage()
    coverage["coverage_status"] = "NOT_MATERIALIZED"

    report = build_readiness(coverage_report=coverage, now=datetime.fromisoformat("2026-07-13T15:31:00+08:00"))

    assert report["status"] == "BLOCKED"
    assert "coverage_status_not_waiting:NOT_MATERIALIZED" in report["blockers"]
