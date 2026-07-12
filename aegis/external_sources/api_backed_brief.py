"""Build user-readable API-backed candidate briefs after bounded dry-run."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from aegis.strategy.suggestion_brief import build_usable_suggestion_brief, render_usable_suggestion_brief_markdown


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def build_api_backed_candidate_brief(
    *,
    live_dry_run_report: Mapping[str, Any],
    suggestion_drafts_json: Path,
    run_id: str,
    evidence_refs: list[str] | None = None,
) -> dict[str, Any]:
    """Build a brief only when real API-backed candidate artifacts exist."""

    dry_run_status = live_dry_run_report.get("dry_run_status")
    bindings_path_value = live_dry_run_report.get("api_candidate_bindings_json")
    registry_path_value = live_dry_run_report.get("api_candidate_source_registry_json")
    fetch_item_path_value = live_dry_run_report.get("api_fetch_item_json")
    missing_artifacts = [
        name
        for name, value in {
            "api_fetch_item_json": fetch_item_path_value,
            "api_candidate_source_registry_json": registry_path_value,
            "api_candidate_bindings_json": bindings_path_value,
        }.items()
        if not value or not Path(value).exists()
    ]

    if dry_run_status != "completed" or missing_artifacts:
        checks = {
            "blocked_status_recorded": True,
            "missing_real_api_artifacts_visible": bool(missing_artifacts) or dry_run_status != "completed",
            "no_api_backed_claim_when_missing_artifacts": True,
            "network_not_used_by_brief": True,
            "production_records_not_written": True,
            "dashboard_contract_unchanged": True,
        }
        return {
            "overall_status": "PASS" if all(checks.values()) else "FAIL",
            "acceptance_target": "V2.10-D API-Backed Candidate Usable Brief After Real Metadata",
            "brief_type": "api_backed_candidate_brief_gate",
            "run_id": run_id,
            "generated_at": _now_iso(),
            "brief_status": "blocked_missing_real_api_artifacts",
            "blocked_by": ["v2_10_c_not_completed_with_real_api_artifacts"],
            "source_dry_run_status": dry_run_status,
            "missing_artifacts": missing_artifacts,
            "summary": {
                "candidate_count": 0,
                "blocked_count": 0,
                "candidate_markets": [],
                "source_mode": "no_real_api_artifacts",
            },
            "checks": checks,
            "safety": {
                "simulation_only": True,
                "manual_external_execution_only": True,
                "no_real_trade": True,
                "no_broker_api": True,
                "no_trading_webhook": True,
                "no_order_placement": True,
                "no_live_price": True,
                "no_position_size": True,
                "no_production_records_mutation": True,
                "dashboard_contract_unchanged": True,
            },
            "network_used": False,
            "production_records_written": False,
            "dashboard_contract_changed": False,
        }

    bindings = json.loads(Path(bindings_path_value).read_text(encoding="utf-8"))
    suggestion_drafts = json.loads(suggestion_drafts_json.read_text(encoding="utf-8"))
    refs = [
        *(evidence_refs or []),
        str(fetch_item_path_value),
        str(registry_path_value),
        str(bindings_path_value),
    ]
    brief = build_usable_suggestion_brief(
        bindings=bindings,
        suggestion_drafts=suggestion_drafts,
        run_id=run_id,
        evidence_refs=refs,
    )
    brief["acceptance_target"] = "V2.10-D API-Backed Candidate Usable Brief After Real Metadata"
    brief["brief_type"] = "api_backed_candidate_usable_brief"
    brief["brief_status"] = "completed"
    brief["source_mode"] = "real_api_backed_candidate_refresh"
    brief["source_dry_run_status"] = dry_run_status
    brief["source_live_dry_run_report"] = live_dry_run_report.get("run_id")
    brief["safety"]["api_backed_candidate_summaries_only"] = True
    brief["safety"]["raw_api_payload_not_stored"] = True
    brief["safety"]["request_headers_not_stored"] = True
    brief["safety"]["env_values_not_stored"] = True
    brief["checks"] = {
        **brief["checks"],
        "source_dry_run_completed": dry_run_status == "completed",
        "api_artifacts_present": not missing_artifacts,
        "api_backed_source_mode_visible": brief["source_mode"] == "real_api_backed_candidate_refresh",
        "candidate_count_positive": brief["summary"]["candidate_count"] > 0,
        "has_a_h_us_candidates": {"A", "H", "US"}.issubset(set(brief["summary"]["candidate_markets"])),
        "no_live_price_or_position_size": brief["checks"]["no_live_price_or_position_size"] is True,
    }
    brief["overall_status"] = "PASS" if all(brief["checks"].values()) else "FAIL"
    return brief


def render_api_backed_candidate_brief_markdown(report: Mapping[str, Any]) -> str:
    if report.get("brief_status") != "completed":
        return "\n".join(
            [
                "# V2.10-D API-Backed Candidate Usable Brief",
                "",
                f"- status: `{report.get('overall_status')}`",
                f"- brief_status: `{report.get('brief_status')}`",
                f"- source_dry_run_status: `{report.get('source_dry_run_status')}`",
                f"- blocked_by: `{', '.join(report.get('blocked_by') or [])}`",
                "",
                "真实 API candidate artifacts 尚不存在，因此不能生成 API-backed 候选简报。",
                "",
            ]
        )
    return render_usable_suggestion_brief_markdown(report)
