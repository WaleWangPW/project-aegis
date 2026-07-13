import json
from pathlib import Path

import scripts.handle_aegis_stock_card_action as feedback_handler
import scripts.ingest_dashboard_local_intents as ingest


def _patch_paths(monkeypatch, tmp_path: Path) -> None:
    records = tmp_path / "records"
    reports = tmp_path / "reports"
    monkeypatch.setattr(feedback_handler, "RECORDS", records)
    monkeypatch.setattr(feedback_handler, "REPORTS", reports)
    monkeypatch.setattr(feedback_handler, "EVENT_LOG", records / "aegis_stock_feedback_events.jsonl")
    monkeypatch.setattr(feedback_handler, "LATEST", reports / "aegis_stock_feedback_latest.json")
    monkeypatch.setattr(ingest, "REPORTS", reports)
    monkeypatch.setattr(ingest, "OUT", reports / "aegis_dashboard_local_intent_ingest_latest.json")


def test_dashboard_local_intent_ingest_records_evidence_only(monkeypatch, tmp_path):
    _patch_paths(monkeypatch, tmp_path)
    rows = ingest.extract_intents(
        {
            "type": "aegis_dashboard_local_intents",
            "intents": [
                {
                    "symbol": "603893",
                    "name": "瑞芯微",
                    "market": "A",
                    "status": "research_candidate",
                    "score": 60,
                    "action": "aegis_watch",
                    "time": "2026/7/13 09:10:00",
                    "source": "dashboard-local",
                }
            ],
        }
    )
    report = ingest.ingest(rows)

    assert report["status"] == "RECORDED"
    assert report["intent_count"] == 1
    assert report["latest_symbol"] == "603893"
    assert report["latest_action"] == "aegis_watch"
    assert report["latest_feedback_type"] == "user_wants_simulation_watch"
    assert report["safety"]["broker_called"] is False
    latest = json.loads(feedback_handler.LATEST.read_text(encoding="utf-8"))
    event = latest["event"]
    assert event["source"] == "dashboard_local_intent_export"
    assert event["symbol"] == "603893"
    assert event["action"] == "aegis_watch"
    assert event["dashboard_recorded_at"] == "2026/7/13 09:10:00"
    assert event["effects"]["order_placed"] is False
    assert ingest.OUT.exists()


def test_dashboard_local_intent_ingest_rejects_secret_like_text():
    payload = {"intents": [{"symbol": "603893", "action": "aegis_watch", "note": "api_key=abc"}]}

    try:
        ingest.extract_intents(payload)
    except ValueError as exc:
        assert "secret-like" in str(exc)
    else:
        raise AssertionError("secret-like payload should be rejected")
