from __future__ import annotations

import json
from pathlib import Path

import scripts.validate_v2_8_g_concrete_candidate_binding_refresh as v2_8_g
import scripts.validate_v2_8_h_concrete_candidate_usable_brief as validator


def _drafts() -> list[dict]:
    return [
        {
            "suggestion_id": "sug_research_hyp_a_low_vol_dividend_defensive",
            "strategy_id": "strategy_a_low_vol_dividend_defensive",
            "symbol": "A_LOW_VOL_DIVIDEND_PAPER_BASKET",
            "market": "A",
            "action": "paper_entry_candidate",
            "reasons": ["sandbox_status=PASS"],
            "risk_warnings": ["No live price, order size, or broker execution is produced."],
            "evidence_refs": ["v2_8_e_report.json"],
            "blocked_by": [],
        },
        {
            "suggestion_id": "sug_research_hyp_h_low_vol_dividend",
            "strategy_id": "strategy_h_low_vol_dividend",
            "symbol": "H_LOW_VOL_DIVIDEND_PAPER_BASKET",
            "market": "H",
            "action": "paper_entry_candidate",
            "reasons": ["sandbox_status=PASS"],
            "risk_warnings": ["No live price, order size, or broker execution is produced."],
            "evidence_refs": ["v2_8_e_report.json"],
            "blocked_by": [],
        },
        {
            "suggestion_id": "sug_research_hyp_us_value_quality_momentum",
            "strategy_id": "strategy_us_value_quality_momentum",
            "symbol": "US_VALUE_QUALITY_MOMENTUM_PAPER_BASKET",
            "market": "US",
            "action": "paper_entry_candidate",
            "reasons": ["sandbox_status=PASS"],
            "risk_warnings": ["No live price, order size, or broker execution is produced."],
            "evidence_refs": ["v2_8_e_report.json"],
            "blocked_by": [],
        },
        {
            "suggestion_id": "sug_research_hyp_a_value_quality_multifactor",
            "strategy_id": "strategy_a_value_quality_multifactor",
            "symbol": "A_VALUE_QUALITY_PAPER_BASKET",
            "market": "A",
            "action": "blocked",
            "reasons": ["sandbox_status=FAIL"],
            "risk_warnings": ["drawdown"],
            "evidence_refs": ["v2_8_e_report.json"],
            "blocked_by": ["strategy_sandbox_not_passed"],
        },
        {
            "suggestion_id": "sug_research_hyp_h_smart_beta_multifactor",
            "strategy_id": "strategy_h_smart_beta_multifactor",
            "symbol": "H_SMART_BETA_PAPER_BASKET",
            "market": "H",
            "action": "blocked",
            "reasons": ["sandbox_status=FAIL"],
            "risk_warnings": ["drawdown"],
            "evidence_refs": ["v2_8_e_report.json"],
            "blocked_by": ["strategy_sandbox_not_passed"],
        },
        {
            "suggestion_id": "sug_research_hyp_us_low_vol_risk_overlay",
            "strategy_id": "strategy_us_low_vol_risk_overlay",
            "symbol": "US_LOW_VOL_RISK_OVERLAY_PAPER_BASKET",
            "market": "US",
            "action": "blocked",
            "reasons": ["sandbox_status=FAIL"],
            "risk_warnings": ["drawdown"],
            "evidence_refs": ["v2_8_e_report.json"],
            "blocked_by": ["strategy_sandbox_not_passed"],
        },
    ]


def _v2_8_g_fixture(tmp_path: Path) -> tuple[Path, Path]:
    drafts_json = tmp_path / "drafts.json"
    drafts_json.write_text(json.dumps(_drafts(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report = v2_8_g.run_acceptance(
        output_root=tmp_path / "v2_8_g_processed",
        reports_dir=tmp_path / "v2_8_g_reports",
        suggestion_drafts_json=drafts_json,
        run_id="v2_8_g_for_v2_8_h",
        command="unit test v2.8-g",
    )
    return Path(report["concrete_candidate_bindings_json"]), drafts_json


def test_v2_8_h_acceptance_builds_concrete_candidate_brief(tmp_path: Path):
    bindings_json, drafts_json = _v2_8_g_fixture(tmp_path)

    report = validator.run_acceptance(
        output_root=tmp_path / "processed",
        reports_dir=tmp_path / "reports",
        bindings_json=bindings_json,
        suggestion_drafts_json=drafts_json,
        run_id="v2_8_h_test",
        command="test command",
    )

    assert report["overall_status"] == "PASS"
    assert report["acceptance_target"] == "V2.8-H Concrete Candidate Usable Brief"
    assert report["checks"]["candidate_count_at_least_9"] is True
    assert report["checks"]["has_a_h_us_concrete_candidates"] is True
    assert report["checks"]["blocked_paths_visible"] is True
    assert report["checks"]["fixture_status_honest"] is True
    assert report["checks"]["no_live_price_or_position_size"] is True
    assert report["production_records_written"] is False
    assert report["hashes"]["brief_json"]
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()


def test_v2_8_h_cli_exits_zero_and_prints_no_secrets(tmp_path: Path, capsys):
    bindings_json, drafts_json = _v2_8_g_fixture(tmp_path)

    exit_code = validator.main(
        [
            "--output-root",
            str(tmp_path / "processed"),
            "--reports-dir",
            str(tmp_path / "reports"),
            "--bindings-json",
            str(bindings_json),
            "--suggestion-drafts-json",
            str(drafts_json),
            "--run-id",
            "v2_8_h_cli",
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "PASS" in captured.out
    assert "secret" not in captured.out.lower()
    assert "token" not in captured.out.lower()
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()
