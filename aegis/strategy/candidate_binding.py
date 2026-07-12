"""Bind gated suggestion drafts to concrete approved candidate sources."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping, Sequence

from aegis.models.candidate_binding import BoundCandidate, SuggestionCandidateBinding


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def _read_json(path: Path) -> Mapping:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_a_share_watchlist(path: Path) -> list[BoundCandidate]:
    if not path.exists():
        return []
    payload = _read_json(path)
    stocks = payload.get("top5") or payload.get("stocks") or []
    candidates: list[BoundCandidate] = []
    for item in stocks[:5]:
        candidates.append(
            BoundCandidate(
                symbol=item["symbol"],
                market="A",
                name=item.get("name"),
                source="a_share_watchlist_latest",
                score=item.get("score"),
                status=item.get("status"),
                evidence_refs=[str(path)],
            )
        )
    return candidates


def _load_us_holding_candidates(path: Path) -> list[BoundCandidate]:
    if not path.exists():
        return []
    payload = _read_json(path)
    holdings = (payload.get("holdings") or {}).get("holdings") or []
    candidates: list[BoundCandidate] = []
    for item in holdings:
        if item.get("market") != "US" or item.get("status") != "open":
            continue
        candidates.append(
            BoundCandidate(
                symbol=item["symbol"],
                market="US",
                name=item.get("name"),
                source="current_manual_holding",
                score=None,
                status="open_holding",
                evidence_refs=[str(path)],
            )
        )
    return candidates


def _candidate_pool_by_market(
    *,
    a_share_watchlist_json: Path,
    desktop_status_json: Path,
) -> dict[str, list[BoundCandidate]]:
    return {
        "A": _load_a_share_watchlist(a_share_watchlist_json),
        "H": [],
        "US": _load_us_holding_candidates(desktop_status_json),
    }


def build_candidate_bindings(
    suggestion_drafts: Sequence[Mapping],
    *,
    a_share_watchlist_json: Path,
    desktop_status_json: Path,
    created_at: str | None = None,
) -> list[SuggestionCandidateBinding]:
    """Bind non-blocked suggestion drafts to concrete candidates when evidence exists."""

    created = created_at or _now_iso()
    pool = _candidate_pool_by_market(
        a_share_watchlist_json=a_share_watchlist_json,
        desktop_status_json=desktop_status_json,
    )
    bindings: list[SuggestionCandidateBinding] = []

    for draft in suggestion_drafts:
        suggestion_id = draft["suggestion_id"]
        market = draft["market"]
        evidence_refs = list(draft.get("evidence_refs") or [])
        warnings = [
            "Simulation-only candidate binding; user decides and executes manually outside Aegis.",
            "This binding is not a production RecommendationRecord and not an order.",
        ]

        if draft.get("action") == "blocked":
            bindings.append(
                SuggestionCandidateBinding(
                    binding_id=f"bind_{suggestion_id}",
                    suggestion_id=suggestion_id,
                    strategy_id=draft["strategy_id"],
                    market=market,
                    binding_status="blocked",
                    bound_candidates=[],
                    blocked_by=list(draft.get("blocked_by") or ["suggestion_draft_blocked"]),
                    evidence_refs=evidence_refs,
                    warnings=warnings,
                    created_at=created,
                )
            )
            continue

        candidates = pool.get(market, [])
        if not candidates:
            bindings.append(
                SuggestionCandidateBinding(
                    binding_id=f"bind_{suggestion_id}",
                    suggestion_id=suggestion_id,
                    strategy_id=draft["strategy_id"],
                    market=market,
                    binding_status="blocked",
                    bound_candidates=[],
                    blocked_by=["missing_candidate_source"],
                    evidence_refs=evidence_refs,
                    warnings=warnings + ["No approved concrete candidate source is available for this market yet."],
                    created_at=created,
                )
            )
            continue

        bindings.append(
            SuggestionCandidateBinding(
                binding_id=f"bind_{suggestion_id}",
                suggestion_id=suggestion_id,
                strategy_id=draft["strategy_id"],
                market=market,
                binding_status="bound",
                bound_candidates=candidates,
                blocked_by=[],
                evidence_refs=evidence_refs + sorted({ref for candidate in candidates for ref in candidate.evidence_refs}),
                warnings=warnings,
                created_at=created,
            )
        )
    return bindings


def build_candidate_binding_report(
    suggestion_drafts: Sequence[Mapping],
    *,
    a_share_watchlist_json: Path,
    desktop_status_json: Path,
    run_id: str,
    command: str | None = None,
) -> dict:
    bindings = build_candidate_bindings(
        suggestion_drafts,
        a_share_watchlist_json=a_share_watchlist_json,
        desktop_status_json=desktop_status_json,
    )
    bound = [item for item in bindings if item.binding_status == "bound"]
    blocked = [item for item in bindings if item.binding_status == "blocked"]
    return {
        "overall_status": "PASS" if len(bound) >= 2 and any(item.market == "A" for item in bound) else "FAIL",
        "generated_at": _now_iso(),
        "run_id": run_id,
        "command": command,
        "acceptance_target": "V2.5-A Approved Candidate Binding For Suggestion Drafts",
        "isolated": True,
        "network_used": False,
        "production_records_written": False,
        "dashboard_contract_changed": False,
        "summary": {
            "suggestion_draft_count": len(suggestion_drafts),
            "binding_count": len(bindings),
            "bound_count": len(bound),
            "blocked_count": len(blocked),
            "bound_markets": sorted({item.market for item in bound}),
            "blocked_markets": sorted({item.market for item in blocked}),
            "bound_bindings": [item.binding_id for item in bound],
            "blocked_bindings": [item.binding_id for item in blocked],
        },
        "bindings": [item.model_dump() for item in bindings],
        "candidate_sources": {
            "A": str(a_share_watchlist_json),
            "US": str(desktop_status_json),
            "H": None,
        },
        "safety": {
            "simulation_only": True,
            "manual_external_execution_only": True,
            "no_real_trade": True,
            "no_broker_api": True,
            "no_webhook": True,
            "no_secret_storage": True,
            "suggestion_drafts_not_orders": True,
            "candidate_binding_not_recommendation_record": True,
            "missing_market_source_blocks_binding": True,
            "dashboard_contract_unchanged": True,
            "no_production_records_mutation": True,
        },
    }

