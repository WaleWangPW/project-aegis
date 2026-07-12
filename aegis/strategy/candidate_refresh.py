"""Refresh approved candidate sources for suggestion binding."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping, Sequence

from aegis.models.candidate_binding import BoundCandidate, SuggestionCandidateBinding
from aegis.models.candidate_source import CandidateSourceRegistry, CandidateSourceSpec
from aegis.strategy.candidate_binding import build_candidate_bindings


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def load_candidate_source_registry(path: Path) -> CandidateSourceRegistry:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return CandidateSourceRegistry(**payload)


def default_approved_candidate_source_registry(*, generated_at: str | None = None) -> CandidateSourceRegistry:
    generated = generated_at or _now_iso()
    sources = [
        CandidateSourceSpec(
            source_id="approved_fixture_a_low_vol_dividend",
            source_type="approved_fixture",
            refresh_mode="fixture",
            markets=["A"],
            license_status="not_required",
            can_refresh=True,
            retention_policy="candidate_summary_only",
            candidates=[
                {"symbol": "600519.SH", "market": "A", "name": "贵州茅台", "score": 0.95, "status": "Watch"},
                {"symbol": "600036.SH", "market": "A", "name": "招商银行", "score": 0.85, "status": "Watch"},
                {"symbol": "601398.SH", "market": "A", "name": "工商银行", "score": 0.72, "status": "Watch"},
            ],
            notes="Approved local fixture sourced from existing A-share watchlist shape.",
        ),
        CandidateSourceSpec(
            source_id="approved_fixture_h_low_vol_dividend",
            source_type="approved_fixture",
            refresh_mode="fixture",
            markets=["H"],
            license_status="not_required",
            can_refresh=True,
            retention_policy="candidate_summary_only",
            candidates=[
                {"symbol": "00700.HK", "market": "H", "name": "Tencent Holdings", "score": 0.82, "status": "Watch"},
                {"symbol": "00005.HK", "market": "H", "name": "HSBC Holdings", "score": 0.74, "status": "Watch"},
                {"symbol": "00941.HK", "market": "H", "name": "China Mobile", "score": 0.71, "status": "Watch"},
            ],
            notes="Approved fixture to prove H-share candidate binding; not live market data.",
        ),
        CandidateSourceSpec(
            source_id="approved_fixture_us_value_quality_momentum",
            source_type="approved_fixture",
            refresh_mode="fixture",
            markets=["US"],
            license_status="not_required",
            can_refresh=True,
            retention_policy="candidate_summary_only",
            candidates=[
                {"symbol": "CRCL", "market": "US", "name": "Circle Internet Group", "score": 0.78, "status": "Watch"},
                {"symbol": "MSFT", "market": "US", "name": "Microsoft", "score": 0.76, "status": "Watch"},
                {"symbol": "NVDA", "market": "US", "name": "NVIDIA", "score": 0.73, "status": "Watch"},
            ],
            notes="Approved fixture candidate source for U.S. value-quality-momentum binding.",
        ),
    ]
    return CandidateSourceRegistry(
        schema_version="candidate_source_registry.v1",
        generated_at=generated,
        sources=sources,
        safety={
            "no_secret_values_stored": True,
            "env_var_names_only_for_user_api": True,
            "no_broker_api": True,
            "no_trading_webhook": True,
            "no_real_trade": True,
            "candidate_summary_only": True,
        },
    )


def refreshed_candidates_by_market(registry: CandidateSourceRegistry, *, evidence_ref: str) -> dict[str, list[BoundCandidate]]:
    by_market: dict[str, list[BoundCandidate]] = {"A": [], "H": [], "US": []}
    for source in registry.sources:
        if not source.can_refresh or source.license_status not in {"approved", "not_required"}:
            continue
        for candidate in source.candidates:
            by_market[candidate.market].append(
                BoundCandidate(
                    symbol=candidate.symbol,
                    market=candidate.market,
                    name=candidate.name,
                    source=source.source_id,
                    score=candidate.score,
                    status=candidate.status,
                    evidence_refs=[evidence_ref],
                )
            )
    return by_market


def candidate_items_from_api_payload(payload: bytes, *, source_id: str) -> list[BoundCandidate]:
    """Parse candidate summaries from an approved API response payload.

    The caller is responsible for not persisting the raw payload. This function
    returns only candidate summary fields suitable for report artifacts.
    """

    data = json.loads(payload.decode("utf-8"))
    items = data.get("items") if isinstance(data, dict) else data
    if not isinstance(items, list):
        raise ValueError("candidate API payload must contain a list or an items list")

    candidates: list[BoundCandidate] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        if item.get("market") not in {"A", "H", "US"}:
            continue
        if not item.get("symbol"):
            continue
        candidates.append(
            BoundCandidate(
                symbol=item["symbol"],
                market=item["market"],
                name=item.get("name"),
                source=source_id,
                score=item.get("score"),
                status=item.get("status") or "Watch",
                evidence_refs=[],
            )
        )
    return candidates


def candidate_source_registry_from_api_candidates(
    candidates: Sequence[BoundCandidate],
    *,
    source_id: str,
    auth_env_vars: Sequence[str] | None = None,
    generated_at: str | None = None,
) -> CandidateSourceRegistry:
    generated = generated_at or _now_iso()
    markets = sorted({candidate.market for candidate in candidates})
    return CandidateSourceRegistry(
        schema_version="candidate_source_registry.v1",
        generated_at=generated,
        sources=[
            CandidateSourceSpec(
                source_id=source_id,
                source_type="user_provided_api",
                refresh_mode="api_dry_run",
                markets=markets,
                license_status="approved",
                auth_env_vars=list(auth_env_vars or ["AEGIS_RESEARCH_API_KEY"]),
                can_refresh=True,
                retention_policy="candidate_summary_only",
                candidates=[
                    {
                        "symbol": candidate.symbol,
                        "market": candidate.market,
                        "name": candidate.name,
                        "score": candidate.score,
                        "status": candidate.status or "Watch",
                    }
                    for candidate in candidates
                ],
                notes="Candidate summaries parsed from approved API dry-run response; raw payload not stored.",
            )
        ],
        safety={
            "no_secret_values_stored": True,
            "env_var_names_only_for_user_api": True,
            "no_broker_api": True,
            "no_trading_webhook": True,
            "no_real_trade": True,
            "candidate_summary_only": True,
        },
    )


def bind_suggestions_with_refreshed_candidates(
    suggestion_drafts: Sequence[Mapping],
    registry: CandidateSourceRegistry,
    *,
    evidence_ref: str,
    created_at: str | None = None,
) -> list[SuggestionCandidateBinding]:
    """Bind suggestions using refreshed candidates from approved source specs."""

    created = created_at or _now_iso()
    pool = refreshed_candidates_by_market(registry, evidence_ref=evidence_ref)

    # Reuse V2.5-A binding behavior by writing through small in-memory source
    # files would be clumsy; instead, mirror its logic with an explicit pool.
    bindings: list[SuggestionCandidateBinding] = []
    for draft in suggestion_drafts:
        suggestion_id = draft["suggestion_id"]
        market = draft["market"]
        evidence_refs = list(draft.get("evidence_refs") or [])
        warnings = [
            "Simulation-only refreshed candidate binding; user decides and executes manually outside Aegis.",
            "Refreshed candidates are not production RecommendationRecords and not orders.",
        ]
        if draft.get("action") == "blocked":
            bindings.append(
                SuggestionCandidateBinding(
                    binding_id=f"refresh_bind_{suggestion_id}",
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
                    binding_id=f"refresh_bind_{suggestion_id}",
                    suggestion_id=suggestion_id,
                    strategy_id=draft["strategy_id"],
                    market=market,
                    binding_status="blocked",
                    bound_candidates=[],
                    blocked_by=["missing_refreshed_candidate_source"],
                    evidence_refs=evidence_refs,
                    warnings=warnings,
                    created_at=created,
                )
            )
            continue

        bindings.append(
            SuggestionCandidateBinding(
                binding_id=f"refresh_bind_{suggestion_id}",
                suggestion_id=suggestion_id,
                strategy_id=draft["strategy_id"],
                market=market,
                binding_status="bound",
                bound_candidates=candidates,
                blocked_by=[],
                evidence_refs=evidence_refs + [evidence_ref],
                warnings=warnings,
                created_at=created,
            )
        )
    return bindings


def build_candidate_refresh_report(
    suggestion_drafts: Sequence[Mapping],
    registry: CandidateSourceRegistry,
    *,
    run_id: str,
    evidence_ref: str,
    command: str | None = None,
) -> dict:
    bindings = bind_suggestions_with_refreshed_candidates(
        suggestion_drafts,
        registry,
        evidence_ref=evidence_ref,
    )
    bound = [item for item in bindings if item.binding_status == "bound"]
    blocked = [item for item in bindings if item.binding_status == "blocked"]
    candidate_counts_by_market = {
        market: len(candidates)
        for market, candidates in refreshed_candidates_by_market(registry, evidence_ref=evidence_ref).items()
    }
    return {
        "overall_status": "PASS" if {"A", "H", "US"}.issubset({item.market for item in bound}) else "FAIL",
        "generated_at": _now_iso(),
        "run_id": run_id,
        "command": command,
        "acceptance_target": "V2.5-B Approved Live Candidate Refresh",
        "isolated": True,
        "network_used": False,
        "user_api_live_status": "blocked_missing_metadata",
        "production_records_written": False,
        "dashboard_contract_changed": False,
        "summary": {
            "source_count": len(registry.sources),
            "suggestion_draft_count": len(suggestion_drafts),
            "binding_count": len(bindings),
            "bound_count": len(bound),
            "blocked_count": len(blocked),
            "bound_markets": sorted({item.market for item in bound}),
            "blocked_markets": sorted({item.market for item in blocked}),
            "candidate_counts_by_market": candidate_counts_by_market,
        },
        "bindings": [item.model_dump() for item in bindings],
        "source_registry": registry.model_dump(),
        "safety": {
            "simulation_only": True,
            "manual_external_execution_only": True,
            "approved_sources_only": True,
            "fixture_not_live_market_data": True,
            "user_api_requires_metadata_and_env_var": True,
            "no_secret_values_stored": True,
            "no_real_trade": True,
            "no_broker_api": True,
            "no_webhook": True,
            "candidate_binding_not_recommendation_record": True,
            "dashboard_contract_unchanged": True,
            "no_production_records_mutation": True,
        },
    }
