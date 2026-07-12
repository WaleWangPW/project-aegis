from __future__ import annotations

import json
from pathlib import Path

import scripts.validate_v2_5_b_candidate_refresh as validator
from aegis.strategy.candidate_refresh import (
    bind_suggestions_with_refreshed_candidates,
    build_candidate_refresh_report,
    default_approved_candidate_source_registry,
    refreshed_candidates_by_market,
)


def _suggestions() -> list[dict]:
    return [
        {
            "suggestion_id": "sug_research_hyp_a_low_vol_dividend_defensive",
            "strategy_id": "strategy_a_low_vol_dividend_defensive",
            "symbol": "A_LOW_VOL_DIVIDEND_PAPER_BASKET",
            "market": "A",
            "action": "paper_entry_candidate",
            "evidence_refs": ["v2_4_d_report.json"],
            "blocked_by": [],
        },
        {
            "suggestion_id": "sug_research_hyp_h_low_vol_dividend",
            "strategy_id": "strategy_h_low_vol_dividend",
            "symbol": "H_LOW_VOL_DIVIDEND_PAPER_BASKET",
            "market": "H",
            "action": "paper_entry_candidate",
            "evidence_refs": ["v2_4_d_report.json"],
            "blocked_by": [],
        },
        {
            "suggestion_id": "sug_research_hyp_us_value_quality_momentum",
            "strategy_id": "strategy_us_value_quality_momentum",
            "symbol": "US_VALUE_QUALITY_MOMENTUM_PAPER_BASKET",
            "market": "US",
            "action": "paper_entry_candidate",
            "evidence_refs": ["v2_4_d_report.json"],
            "blocked_by": [],
        },
        {
            "suggestion_id": "sug_research_hyp_us_low_vol_risk_overlay",
            "strategy_id": "strategy_us_low_vol_risk_overlay",
            "symbol": "US_LOW_VOL_RISK_OVERLAY_PAPER_BASKET",
            "market": "US",
            "action": "blocked",
            "evidence_refs": ["v2_4_d_report.json"],
            "blocked_by": ["strategy_sandbox_not_passed"],
        },
    ]


def test_default_registry_refreshes_a_h_us_candidates_without_secrets():
    registry = default_approved_candidate_source_registry(generated_at="2026-07-11T00:00:00+08:00")
    by_market = refreshed_candidates_by_market(registry, evidence_ref="registry.json")

    assert {market for market, candidates in by_market.items() if candidates} == {"A", "H", "US"}
    assert any(candidate.symbol == "00700.HK" for candidate in by_market["H"])
    assert registry.safety["no_secret_values_stored"] is True
    assert registry.safety["no_broker_api"] is True


def test_refreshed_candidate_binding_binds_h_share_after_source_added():
    registry = default_approved_candidate_source_registry(generated_at="2026-07-11T00:00:00+08:00")

    bindings = bind_suggestions_with_refreshed_candidates(
        _suggestions(),
        registry,
        evidence_ref="registry.json",
        created_at="2026-07-11T00:00:00+08:00",
    )
    by_id = {item.suggestion_id: item for item in bindings}

    assert by_id["sug_research_hyp_h_low_vol_dividend"].binding_status == "bound"
    assert by_id["sug_research_hyp_h_low_vol_dividend"].bound_candidates[0].market == "H"
    assert by_id["sug_research_hyp_h_low_vol_dividend"].bound_candidates[0].symbol == "00700.HK"
    assert by_id["sug_research_hyp_us_low_vol_risk_overlay"].binding_status == "blocked"
    assert "strategy_sandbox_not_passed" in by_id["sug_research_hyp_us_low_vol_risk_overlay"].blocked_by


def test_candidate_refresh_report_is_honest_about_fixture_and_user_api_blocker():
    registry = default_approved_candidate_source_registry(generated_at="2026-07-11T00:00:00+08:00")

    report = build_candidate_refresh_report(
        _suggestions(),
        registry,
        run_id="v2_5_b_unit",
        evidence_ref="registry.json",
        command="unit test",
    )

    assert report["overall_status"] == "PASS"
    assert set(report["summary"]["bound_markets"]) == {"A", "H", "US"}
    assert report["user_api_live_status"] == "blocked_missing_metadata"
    assert report["safety"]["fixture_not_live_market_data"] is True
    assert report["safety"]["no_secret_values_stored"] is True
    assert report["production_records_written"] is False


def test_v2_5_b_acceptance_writes_reports_and_hashes(tmp_path: Path):
    suggestions_json = tmp_path / "suggestions.json"
    suggestions_json.write_text(json.dumps(_suggestions(), ensure_ascii=False), encoding="utf-8")

    report = validator.run_acceptance(
        output_root=tmp_path / "processed",
        reports_dir=tmp_path / "reports",
        run_id="v2_5_b_test",
        command="test command",
        suggestion_drafts_json=suggestions_json,
    )

    assert report["overall_status"] == "PASS"
    assert report["checks"]["a_h_us_bound"] is True
    assert report["checks"]["user_api_live_blocked_until_metadata"] is True
    assert report["checks"]["no_secret_values_stored"] is True
    assert report["hashes"]["refreshed_candidate_bindings_json"]
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()


def test_v2_5_b_cli_exits_zero_and_prints_no_secrets(tmp_path: Path, capsys):
    suggestions_json = tmp_path / "suggestions.json"
    suggestions_json.write_text(json.dumps(_suggestions(), ensure_ascii=False), encoding="utf-8")

    exit_code = validator.main(
        [
            "--output-root",
            str(tmp_path / "processed"),
            "--reports-dir",
            str(tmp_path / "reports"),
            "--run-id",
            "v2_5_b_cli",
            "--suggestion-drafts-json",
            str(suggestions_json),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "PASS" in captured.out
    assert "token" not in captured.out.lower()
    assert "secret" not in captured.out.lower()
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()

