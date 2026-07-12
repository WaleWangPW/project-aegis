from __future__ import annotations

import json
from pathlib import Path

import scripts.validate_v2_8_g_concrete_candidate_binding_refresh as validator


def _drafts() -> list[dict]:
    return [
        {
            "suggestion_id": "sug_research_hyp_a_low_vol_dividend_defensive",
            "strategy_id": "strategy_a_low_vol_dividend_defensive",
            "symbol": "A_LOW_VOL_DIVIDEND_PAPER_BASKET",
            "market": "A",
            "action": "paper_entry_candidate",
            "evidence_refs": ["v2_8_e_report.json"],
            "blocked_by": [],
        },
        {
            "suggestion_id": "sug_research_hyp_h_low_vol_dividend",
            "strategy_id": "strategy_h_low_vol_dividend",
            "symbol": "H_LOW_VOL_DIVIDEND_PAPER_BASKET",
            "market": "H",
            "action": "paper_entry_candidate",
            "evidence_refs": ["v2_8_e_report.json"],
            "blocked_by": [],
        },
        {
            "suggestion_id": "sug_research_hyp_us_value_quality_momentum",
            "strategy_id": "strategy_us_value_quality_momentum",
            "symbol": "US_VALUE_QUALITY_MOMENTUM_PAPER_BASKET",
            "market": "US",
            "action": "paper_entry_candidate",
            "evidence_refs": ["v2_8_e_report.json"],
            "blocked_by": [],
        },
        {
            "suggestion_id": "sug_research_hyp_us_low_vol_risk_overlay",
            "strategy_id": "strategy_us_low_vol_risk_overlay",
            "symbol": "US_LOW_VOL_RISK_OVERLAY_PAPER_BASKET",
            "market": "US",
            "action": "blocked",
            "evidence_refs": ["v2_8_e_report.json"],
            "blocked_by": ["strategy_sandbox_not_passed"],
        },
    ]


def test_v2_8_g_acceptance_binds_a_h_us_concrete_candidates(tmp_path: Path):
    drafts_json = tmp_path / "drafts.json"
    drafts_json.write_text(json.dumps(_drafts(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    report = validator.run_acceptance(
        output_root=tmp_path / "processed",
        reports_dir=tmp_path / "reports",
        suggestion_drafts_json=drafts_json,
        run_id="v2_8_g_test",
        command="test command",
    )

    assert report["overall_status"] == "PASS"
    assert report["acceptance_target"] == "V2.8-G Concrete Candidate Binding Refresh"
    assert report["checks"]["a_h_us_bound"] is True
    assert report["checks"]["every_bound_has_concrete_candidates"] is True
    assert report["checks"]["blocked_paths_preserved"] is True
    assert report["checks"]["fixture_status_honest"] is True
    assert report["checks"]["user_api_live_blocked_until_metadata"] is True
    assert report["checks"]["no_real_trade"] is True
    assert report["checks"]["no_broker_api"] is True
    assert report["production_records_written"] is False
    assert report["hashes"]["concrete_candidate_bindings_json"]
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()


def test_v2_8_g_cli_exits_zero_and_prints_no_secrets(tmp_path: Path, capsys):
    drafts_json = tmp_path / "drafts.json"
    drafts_json.write_text(json.dumps(_drafts(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    exit_code = validator.main(
        [
            "--output-root",
            str(tmp_path / "processed"),
            "--reports-dir",
            str(tmp_path / "reports"),
            "--suggestion-drafts-json",
            str(drafts_json),
            "--run-id",
            "v2_8_g_cli",
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "PASS" in captured.out
    assert "secret" not in captured.out.lower()
    assert "token" not in captured.out.lower()
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()
