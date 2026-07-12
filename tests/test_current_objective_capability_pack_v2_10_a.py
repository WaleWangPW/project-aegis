from __future__ import annotations

import json
from pathlib import Path

from aegis.operations.current_objective_pack import build_current_objective_pack
import scripts.validate_v2_10_a_current_objective_capability_pack as validator


def _current_brief() -> dict:
    return {
        "overall_status": "PASS",
        "summary": {
            "candidate_count": 3,
            "blocked_count": 1,
            "candidate_markets": ["A", "H", "US"],
            "top_candidate_symbols": ["600519.SH", "00700.HK", "MSFT"],
            "real_user_api_status": "blocked_missing_metadata",
        },
        "top_candidates": [
            {
                "symbol": "600519.SH",
                "name": "贵州茅台",
                "market": "A",
                "strategy_id": "strategy_a_low_vol_dividend_defensive",
                "candidate_score": 0.95,
                "source_mode": "approved_fixture_not_live_market_data",
                "user_action": "manual verification only",
            }
        ],
        "checks": {
            "has_a_h_us_candidates": True,
            "blocked_paths_visible": True,
            "manual_external_execution_only": True,
            "no_live_price": True,
            "no_position_size": True,
        },
    }


def _live_public_source_audit() -> dict:
    return {
        "overall_status": "PASS",
        "network_used": True,
        "attempted_count": 12,
        "reachable_count": 8,
        "status_counts": {"reachable": 8, "fetch_error": 4},
        "checks": {"covers_a_h_us": True},
        "safety": {"no_secret_values_stored": True},
    }


def _api_candidate_dry_run() -> dict:
    return {
        "fixture_dry_run_status": "completed",
        "summary": {"real_user_status": "blocked_missing_metadata"},
        "checks": {"real_user_not_claimed_completed_when_blocked": True},
    }


def _sandbox_report() -> dict:
    return {
        "overall_status": "PASS",
        "summary": {
            "historical_case_count": 24,
            "pass_count": 3,
            "fail_count": 3,
            "passing_strategies": ["strategy_a_low_vol_dividend_defensive"],
            "failing_strategies": ["strategy_a_value_quality_multifactor"],
        },
        "checks": {"production_records_not_written": True},
    }


def _source_catalog() -> dict:
    return {
        "overall_status": "PASS",
        "summary": {
            "record_count": 12,
            "market_coverage": {"A": 4, "H": 2, "US": 6},
            "strategy_family_coverage": {"value": 10, "quality": 9, "momentum": 7},
            "publisher_coverage": {"MSCI": 3},
        },
        "checks": {
            "covers_a_h_us": True,
            "covers_core_strategy_families": True,
            "summary_only": True,
            "requires_sandbox_before_suggestion": True,
        },
    }


def test_v2_10_a_pack_marks_goal_parts_without_overclaiming_api():
    pack = build_current_objective_pack(
        current_brief=_current_brief(),
        live_public_source_audit=_live_public_source_audit(),
        api_candidate_dry_run=_api_candidate_dry_run(),
        historical_sandbox=_sandbox_report(),
        refresh_sandbox=_sandbox_report(),
        strategy_source_catalog=_source_catalog(),
        run_id="test",
        command="test command",
    )

    assert pack["overall_status"] == "PASS"
    assert pack["objective_status"]["online_reading"]["status"] == "partial_ready_waiting_user_api"
    assert pack["objective_status"]["historical_sandbox"]["status"] == "ready_simulation_only"
    assert pack["objective_status"]["strategy_research"]["status"] == "ready_summary_only_requires_sandbox_before_suggestion"
    assert pack["objective_status"]["usable_suggestions"]["status"] == "ready_simulation_only_manual_execution"
    assert pack["checks"]["blockers_visible"] is True
    assert pack["safety"]["no_real_trade"] is True
    assert pack["top_candidates"][0]["symbol"] == "600519.SH"


def test_v2_10_a_pack_fails_if_suggestions_lack_a_h_us_coverage():
    brief = _current_brief()
    brief["summary"]["candidate_markets"] = ["A", "US"]
    brief["checks"]["has_a_h_us_candidates"] = False

    pack = build_current_objective_pack(
        current_brief=brief,
        live_public_source_audit=_live_public_source_audit(),
        api_candidate_dry_run=_api_candidate_dry_run(),
        historical_sandbox=_sandbox_report(),
        refresh_sandbox=_sandbox_report(),
        strategy_source_catalog=_source_catalog(),
        run_id="test",
        command="test command",
    )

    assert pack["overall_status"] == "FAIL"
    assert pack["checks"]["usable_suggestions_ready"] is False


def test_v2_10_a_validator_writes_report_and_marker(tmp_path: Path):
    inputs = {
        "current_brief_json": _current_brief(),
        "live_public_source_audit_json": _live_public_source_audit(),
        "api_candidate_dry_run_json": _api_candidate_dry_run(),
        "historical_sandbox_json": _sandbox_report(),
        "refresh_sandbox_json": _sandbox_report(),
        "strategy_source_catalog_json": _source_catalog(),
    }
    paths: dict[str, Path] = {}
    for name, payload in inputs.items():
        path = tmp_path / f"{name}.json"
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        paths[name] = path

    report = validator.run_acceptance(
        output_root=tmp_path / "processed",
        reports_dir=tmp_path / "reports",
        run_id="v2_10_a_test",
        command="test command",
        **paths,
    )

    assert report["overall_status"] == "PASS"
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()
    assert (tmp_path / "reports" / validator.REPORT_JSON).exists()
    assert (tmp_path / "processed" / "v2_10_a_test" / "current_objective_capability_pack.md").exists()
