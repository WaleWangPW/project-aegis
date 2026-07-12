"""Event timeline and scenario report builder for V2.0-D."""

from __future__ import annotations

from typing import Any

from aegis.models.event_timeline import EventRecord, ScenarioRecord


def build_event_timeline_report(
    *,
    symbol: str,
    market: str,
    events: list[EventRecord],
    scenarios: list[ScenarioRecord],
) -> dict[str, Any]:
    scoped_events = [event for event in events if event.symbol == symbol and event.market == market]
    scoped_scenarios = [scenario for scenario in scenarios if scenario.symbol == symbol and scenario.market == market]
    event_ids = {event.event_id for event in scoped_events}

    missing_scenario_evidence: list[str] = []
    scenario_summaries: list[dict[str, Any]] = []
    for scenario in scoped_scenarios:
        missing = [event_id for event_id in scenario.evidence_event_ids if event_id not in event_ids]
        missing_scenario_evidence.extend(missing)
        scenario_summaries.append(
            {
                "scenario_id": scenario.scenario_id,
                "title": scenario.title,
                "impact": scenario.impact,
                "confidence": scenario.confidence,
                "evidence_event_ids": scenario.evidence_event_ids,
                "missing_evidence_event_ids": missing,
                "rationale": scenario.rationale,
            }
        )

    verified_events = [event for event in scoped_events if event.verified]
    unverified_events = [event for event in scoped_events if not event.verified]
    sorted_events = sorted(scoped_events, key=lambda item: (item.event_date, item.event_id))

    return {
        "timeline_type": "event_timeline_and_scenarios",
        "symbol": symbol,
        "market": market,
        "event_count": len(scoped_events),
        "verified_event_count": len(verified_events),
        "unverified_event_count": len(unverified_events),
        "scenario_count": len(scoped_scenarios),
        "events": [event.model_dump() for event in sorted_events],
        "scenarios": scenario_summaries,
        "quality": {
            "missing_scenario_evidence": sorted(set(missing_scenario_evidence)),
            "accepted_for_decision_support": not missing_scenario_evidence and bool(verified_events),
            "unverified_events_are_context_only": True,
        },
        "safety": {
            "read_only": True,
            "no_real_trade": True,
            "no_broker_api": True,
            "no_webhook": True,
            "no_strategy_mutation": True,
            "dashboard_contract_unchanged": True,
            "does_not_bypass_evidence_gate": True,
            "social_sentiment_not_fact": True,
        },
    }


def render_event_timeline_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# V2.0-D Event Timeline and Scenarios",
        "",
        f"- symbol: `{report['symbol']}`",
        f"- market: `{report['market']}`",
        f"- event_count: `{report['event_count']}`",
        f"- verified_event_count: `{report['verified_event_count']}`",
        f"- scenario_count: `{report['scenario_count']}`",
        f"- accepted_for_decision_support: `{report['quality']['accepted_for_decision_support']}`",
        "",
        "## Events",
        "",
    ]
    for event in report["events"]:
        lines.append(
            "- "
            f"{event['event_date']} "
            f"{event['event_type']} "
            f"verified=`{event['verified']}` "
            f"level=`{event['evidence_level']}` "
            f"title={event['title']}"
        )
    lines.extend(["", "## Scenarios", ""])
    for scenario in report["scenarios"]:
        lines.append(
            "- "
            f"{scenario['title']} "
            f"impact=`{scenario['impact']}` "
            f"confidence=`{scenario['confidence']}` "
            f"missing_evidence=`{scenario['missing_evidence_event_ids']}`"
        )
    lines.extend(
        [
            "",
            "## Safety",
            "",
            "- Event timeline is read-only decision support.",
            "- Social/community discussion is context only, not verified fact.",
            "- No real trade, broker API, webhook, strategy mutation, or Dashboard Contract change.",
            "",
        ]
    )
    return "\n".join(lines)
