"""Build sandbox refresh proposals from live strategy source audit evidence."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

SCHEMA_VERSION = "source_audit_sandbox_refresh_queue.v1"
SUPPORTED_MARKETS = ("A", "H", "US")


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def _stable_hash(payload: dict) -> str:
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def _source_is_reachable(source: dict) -> bool:
    return source.get("status") == "reachable" and bool(source.get("content_sample_hash"))


def _market_sources(sources: Iterable[dict], market: str) -> list[dict]:
    return [source for source in sources if market in source.get("markets", [])]


def _blocked_source(source: dict) -> dict:
    return {
        "research_id": source.get("research_id"),
        "publisher": source.get("publisher"),
        "status": source.get("status"),
        "status_code": source.get("status_code"),
        "error_type": source.get("error_type"),
        "error_message": source.get("error_message"),
        "markets": source.get("markets", []),
        "strategy_families": source.get("strategy_families", []),
        "blocked_reason": "not_reachable_in_live_public_source_audit",
        "eligible_for_refresh": False,
    }


def _refresh_proposal(market: str, sources: list[dict], *, audit_run_id: str) -> dict:
    families = sorted({family for source in sources for family in source.get("strategy_families", [])})
    source_ids = sorted(source["research_id"] for source in sources)
    source_hashes = {source["research_id"]: source["content_sample_hash"] for source in sources}
    proposal = {
        "proposal_id": f"refresh_{market.lower()}_strategy_hypotheses_from_live_source_audit",
        "market": market,
        "refresh_status": "proposed_for_sandbox",
        "source_audit_run_id": audit_run_id,
        "source_research_ids": source_ids,
        "source_hashes": source_hashes,
        "strategy_families": families,
        "refresh_intent": (
            "Use reachable live public-source metadata/hash evidence to refresh sandbox "
            "hypotheses for this market. This is not a user-facing recommendation."
        ),
        "next_gate": "historical_sandbox",
        "requires_sandbox": True,
        "auto_applied": False,
        "user_facing_suggestion_allowed": False,
        "production_records_mutation_allowed": False,
    }
    proposal["proposal_hash"] = _stable_hash(
        {
            "proposal_id": proposal["proposal_id"],
            "market": proposal["market"],
            "source_research_ids": proposal["source_research_ids"],
            "source_hashes": proposal["source_hashes"],
            "strategy_families": proposal["strategy_families"],
            "next_gate": proposal["next_gate"],
        }
    )
    return proposal


def build_source_audit_sandbox_refresh_queue(
    audit_report: dict,
    *,
    run_id: str,
    command: str | None = None,
    generated_at: str | None = None,
) -> dict:
    """Convert a live public source audit into bounded sandbox refresh proposals."""

    sources = list(audit_report.get("audited_sources", []))
    reachable = [source for source in sources if _source_is_reachable(source)]
    blocked = [source for source in sources if not _source_is_reachable(source)]
    market_counts: Counter[str] = Counter()
    family_counts: Counter[str] = Counter()
    for source in reachable:
        market_counts.update(market for market in source.get("markets", []) if market in SUPPORTED_MARKETS)
        family_counts.update(source.get("strategy_families", []))

    proposals = [
        _refresh_proposal(market, market_sources, audit_run_id=audit_report.get("run_id", "unknown"))
        for market in SUPPORTED_MARKETS
        if (market_sources := _market_sources(reachable, market))
    ]
    blocked_sources = [_blocked_source(source) for source in blocked]
    proposal_source_ids = {
        source_id for proposal in proposals for source_id in proposal.get("source_research_ids", [])
    }
    blocked_source_ids = {source.get("research_id") for source in blocked_sources}
    checks = {
        "source_audit_passed": audit_report.get("overall_status") == "PASS",
        "uses_live_public_source_audit": audit_report.get("acceptance_target")
        == "V2.8-B Live Public Strategy Source Audit",
        "network_not_used": True,
        "reachable_sources_have_hashes": all(bool(source.get("content_sample_hash")) for source in reachable),
        "all_reachable_sources_queued": all(source.get("research_id") in proposal_source_ids for source in reachable),
        "blocked_sources_preserved": len(blocked_sources) == len(blocked),
        "blocked_sources_not_queued": blocked_source_ids.isdisjoint(proposal_source_ids),
        "covers_a_h_us_with_reachable_sources": all(market_counts.get(market, 0) > 0 for market in SUPPORTED_MARKETS),
        "requires_sandbox": all(proposal["requires_sandbox"] is True for proposal in proposals),
        "not_auto_applied": all(proposal["auto_applied"] is False for proposal in proposals),
        "no_user_facing_suggestion": all(
            proposal["user_facing_suggestion_allowed"] is False for proposal in proposals
        ),
        "proposal_hashes_written": all(bool(proposal.get("proposal_hash")) for proposal in proposals),
        "raw_text_not_stored": all(source.get("raw_text_stored") is False for source in sources),
        "sample_bytes_not_stored": all(source.get("sample_bytes_stored") is False for source in sources),
        "no_real_trade": True,
        "no_broker_api": True,
        "no_trading_webhook": True,
        "no_strategy_auto_mutation": True,
        "no_production_records_mutation": True,
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "overall_status": "PASS" if proposals and all(checks.values()) else "FAIL",
        "acceptance_target": "V2.8-C Source Audit To Sandbox Refresh Queue",
        "generated_at": generated_at or _now_iso(),
        "run_id": run_id,
        "command": command,
        "source_audit_run_id": audit_report.get("run_id"),
        "source_audit_target": audit_report.get("acceptance_target"),
        "network_used": False,
        "audited_source_count": len(sources),
        "reachable_source_count": len(reachable),
        "blocked_source_count": len(blocked_sources),
        "refresh_proposal_count": len(proposals),
        "market_coverage": dict(sorted(market_counts.items())),
        "strategy_family_coverage": dict(sorted(family_counts.items())),
        "refresh_proposals": proposals,
        "blocked_sources": blocked_sources,
        "checks": checks,
        "safety": {
            "metadata_hash_only": True,
            "raw_text_not_stored": True,
            "sample_bytes_not_stored": True,
            "requires_sandbox": True,
            "auto_applied": False,
            "user_facing_suggestion_allowed": False,
            "no_real_trade": True,
            "no_broker_api": True,
            "no_trading_webhook": True,
            "no_strategy_auto_mutation": True,
            "no_production_records_mutation": True,
        },
    }


def write_source_audit_sandbox_refresh_queue(
    audit_report: dict,
    output_path: Path,
    *,
    run_id: str,
    command: str | None = None,
) -> dict:
    payload = build_source_audit_sandbox_refresh_queue(audit_report, run_id=run_id, command=command)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return payload
