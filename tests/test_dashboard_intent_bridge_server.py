import json
from pathlib import Path

import scripts.handle_aegis_stock_card_action as feedback_handler
import scripts.ingest_dashboard_local_intents as ingest
import scripts.run_aegis_dashboard_intent_bridge_server as server


def _patch_paths(monkeypatch, tmp_path: Path) -> None:
    records = tmp_path / "records"
    reports = tmp_path / "reports"
    monkeypatch.setattr(feedback_handler, "RECORDS", records)
    monkeypatch.setattr(feedback_handler, "REPORTS", reports)
    monkeypatch.setattr(feedback_handler, "EVENT_LOG", records / "aegis_stock_feedback_events.jsonl")
    monkeypatch.setattr(feedback_handler, "LATEST", reports / "aegis_stock_feedback_latest.json")
    monkeypatch.setattr(ingest, "REPORTS", reports)
    monkeypatch.setattr(ingest, "OUT", reports / "aegis_dashboard_local_intent_ingest_latest.json")


def test_process_payload_records_feedback_evidence(monkeypatch, tmp_path):
    _patch_paths(monkeypatch, tmp_path)
    report = server.process_payload(
        {
            "type": "aegis_dashboard_local_intents",
            "intents": [
                {
                    "symbol": "PANW",
                    "name": "Palo Alto Networks",
                    "market": "US",
                    "status": "research_candidate",
                    "score": "10",
                    "action": "aegis_more_news",
                    "time": "2026/7/13 09:30:00",
                    "source": "dashboard-local",
                }
            ],
        }
    )

    assert report["status"] == "RECORDED"
    assert report["event_count"] == 1
    assert report["safety"]["trading_webhook_called"] is False
    latest = json.loads(feedback_handler.LATEST.read_text(encoding="utf-8"))
    assert latest["event"]["symbol"] == "PANW"
    assert latest["event"]["source"] == "dashboard_local_intent_export"


def test_process_payload_rejects_unknown_action(monkeypatch, tmp_path):
    _patch_paths(monkeypatch, tmp_path)
    try:
        server.process_payload({"intents": [{"symbol": "PANW", "action": "buy"}]})
    except ValueError as exc:
        assert "unsupported action" in str(exc)
    else:
        raise AssertionError("unsupported action should be rejected")
