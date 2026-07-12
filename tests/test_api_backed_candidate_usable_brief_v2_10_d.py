from __future__ import annotations

import json
from pathlib import Path

from aegis.external_sources.api_backed_brief import build_api_backed_candidate_brief
import scripts.validate_v2_10_d_api_backed_candidate_usable_brief as validator


def _suggestions(path: Path) -> Path:
    target = path / "suggestions.json"
    target.write_text(
        json.dumps(
            [
                {
                    "suggestion_id": "sug_a",
                    "strategy_id": "strategy_a_low_vol_dividend_defensive",
                    "market": "A",
                    "action": "paper_entry_candidate",
                    "reasons": ["sandbox_status=PASS"],
                    "risk_warnings": ["No live price."],
                    "evidence_refs": ["sandbox.json"],
                    "blocked_by": [],
                },
                {
                    "suggestion_id": "sug_h",
                    "strategy_id": "strategy_h_low_vol_dividend",
                    "market": "H",
                    "action": "paper_entry_candidate",
                    "reasons": ["sandbox_status=PASS"],
                    "risk_warnings": ["No live price."],
                    "evidence_refs": ["sandbox.json"],
                    "blocked_by": [],
                },
                {
                    "suggestion_id": "sug_us",
                    "strategy_id": "strategy_us_value_quality_momentum",
                    "market": "US",
                    "action": "paper_entry_candidate",
                    "reasons": ["sandbox_status=PASS"],
                    "risk_warnings": ["No live price."],
                    "evidence_refs": ["sandbox.json"],
                    "blocked_by": [],
                },
                {
                    "suggestion_id": "sug_blocked",
                    "strategy_id": "strategy_blocked_failed_hypothesis",
                    "market": "A",
                    "action": "blocked",
                    "reasons": ["sandbox_status=FAIL"],
                    "risk_warnings": ["Blocked by historical sandbox."],
                    "evidence_refs": ["sandbox.json"],
                    "blocked_by": ["historical_sandbox_failed"],
                },
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return target


def _bindings(path: Path) -> Path:
    target = path / "bindings.json"
    target.write_text(
        json.dumps(
            [
                {
                    "binding_id": "bind_a",
                    "suggestion_id": "sug_a",
                    "strategy_id": "strategy_a_low_vol_dividend_defensive",
                    "market": "A",
                    "binding_status": "bound",
                    "bound_candidates": [
                        {
                            "symbol": "600036.SH",
                            "market": "A",
                            "name": "招商银行",
                            "source": "api_user_candidate_refresh_approved_env",
                            "score": 0.86,
                            "status": "Watch",
                            "evidence_refs": ["registry.json"],
                        }
                    ],
                    "blocked_by": [],
                    "evidence_refs": ["registry.json"],
                    "warnings": ["Simulation-only."],
                    "created_at": "2026-07-11T00:00:00+08:00",
                },
                {
                    "binding_id": "bind_h",
                    "suggestion_id": "sug_h",
                    "strategy_id": "strategy_h_low_vol_dividend",
                    "market": "H",
                    "binding_status": "bound",
                    "bound_candidates": [
                        {
                            "symbol": "00700.HK",
                            "market": "H",
                            "name": "Tencent",
                            "source": "api_user_candidate_refresh_approved_env",
                            "score": 0.83,
                            "status": "Watch",
                            "evidence_refs": ["registry.json"],
                        }
                    ],
                    "blocked_by": [],
                    "evidence_refs": ["registry.json"],
                    "warnings": ["Simulation-only."],
                    "created_at": "2026-07-11T00:00:00+08:00",
                },
                {
                    "binding_id": "bind_us",
                    "suggestion_id": "sug_us",
                    "strategy_id": "strategy_us_value_quality_momentum",
                    "market": "US",
                    "binding_status": "bound",
                    "bound_candidates": [
                        {
                            "symbol": "MSFT",
                            "market": "US",
                            "name": "Microsoft",
                            "source": "api_user_candidate_refresh_approved_env",
                            "score": 0.78,
                            "status": "Watch",
                            "evidence_refs": ["registry.json"],
                        }
                    ],
                    "blocked_by": [],
                    "evidence_refs": ["registry.json"],
                    "warnings": ["Simulation-only."],
                    "created_at": "2026-07-11T00:00:00+08:00",
                },
                {
                    "binding_id": "bind_blocked",
                    "suggestion_id": "sug_blocked",
                    "strategy_id": "strategy_blocked_failed_hypothesis",
                    "market": "A",
                    "binding_status": "blocked",
                    "bound_candidates": [],
                    "blocked_by": ["historical_sandbox_failed"],
                    "evidence_refs": ["registry.json"],
                    "warnings": ["Simulation-only blocked path."],
                    "created_at": "2026-07-11T00:00:00+08:00",
                },
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return target


def test_v2_10_d_blocks_when_real_api_artifacts_missing(tmp_path: Path):
    report = build_api_backed_candidate_brief(
        live_dry_run_report={
            "run_id": "v2_10_c_missing",
            "dry_run_status": "blocked_missing_metadata",
            "api_fetch_item_json": None,
            "api_candidate_source_registry_json": None,
            "api_candidate_bindings_json": None,
        },
        suggestion_drafts_json=_suggestions(tmp_path),
        run_id="v2_10_d_blocked",
    )

    assert report["overall_status"] == "PASS"
    assert report["brief_status"] == "blocked_missing_real_api_artifacts"
    assert report["checks"]["no_api_backed_claim_when_missing_artifacts"] is True
    assert report["summary"]["candidate_count"] == 0


def test_v2_10_d_builds_api_backed_brief_when_artifacts_exist(tmp_path: Path):
    bindings = _bindings(tmp_path)
    fetch_item = tmp_path / "api_fetch_item.json"
    registry = tmp_path / "api_candidate_source_registry.json"
    fetch_item.write_text("{}", encoding="utf-8")
    registry.write_text("{}", encoding="utf-8")

    report = build_api_backed_candidate_brief(
        live_dry_run_report={
            "run_id": "v2_10_c_ready",
            "dry_run_status": "completed",
            "api_fetch_item_json": str(fetch_item),
            "api_candidate_source_registry_json": str(registry),
            "api_candidate_bindings_json": str(bindings),
        },
        suggestion_drafts_json=_suggestions(tmp_path),
        run_id="v2_10_d_ready",
    )

    assert report["overall_status"] == "PASS"
    assert report["brief_status"] == "completed"
    assert report["source_mode"] == "real_api_backed_candidate_refresh"
    assert report["checks"]["has_a_h_us_candidates"] is True
    assert report["summary"]["candidate_count"] == 3
    assert report["safety"]["api_backed_candidate_summaries_only"] is True
    assert report["safety"]["no_broker_api"] is True


def test_v2_10_d_validator_writes_blocked_report_and_marker(tmp_path: Path):
    live_report = tmp_path / "v2_10_c.json"
    live_report.write_text(
        json.dumps(
            {
                "run_id": "v2_10_c_missing",
                "dry_run_status": "blocked_missing_metadata",
                "api_fetch_item_json": None,
                "api_candidate_source_registry_json": None,
                "api_candidate_bindings_json": None,
            }
        ),
        encoding="utf-8",
    )

    report = validator.run_acceptance(
        output_root=tmp_path / "processed",
        reports_dir=tmp_path / "reports",
        run_id="v2_10_d_test",
        command="test command",
        live_dry_run_report_json=live_report,
        suggestion_drafts_json=_suggestions(tmp_path),
    )

    assert report["overall_status"] == "PASS"
    assert report["brief_status"] == "blocked_missing_real_api_artifacts"
    assert report["production_records_written"] is False
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()
