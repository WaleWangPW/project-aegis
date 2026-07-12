from __future__ import annotations

import json
from pathlib import Path

import scripts.validate_v2_8_d_refresh_queue_historical_sandbox as v2_8_d
import scripts.validate_v2_8_e_refresh_queue_suggestion_gate as validator
from aegis.strategy.hypothesis_suggestion import build_hypothesis_suggestion_gate_report


def _refresh_queue() -> dict:
    return {
        "overall_status": "PASS",
        "run_id": "v2_8_c_unit",
        "refresh_proposal_count": 3,
        "refresh_proposals": [
            {
                "proposal_id": "refresh_a_strategy_hypotheses_from_live_source_audit",
                "market": "A",
                "source_research_ids": ["catalog_msci_china_a_factor_2025", "catalog_panagora_china_a_factor"],
            },
            {
                "proposal_id": "refresh_h_strategy_hypotheses_from_live_source_audit",
                "market": "H",
                "source_research_ids": ["catalog_hsi_smart_beta_index_series"],
            },
            {
                "proposal_id": "refresh_us_strategy_hypotheses_from_live_source_audit",
                "market": "US",
                "source_research_ids": [
                    "catalog_aqr_low_vol_cycles",
                    "catalog_ken_french_factor_library",
                    "catalog_msci_factor_indexes",
                    "catalog_msci_low_volatility_construction",
                    "catalog_research_affiliates_vqm",
                ],
            },
        ],
        "blocked_sources": [
            {"research_id": "catalog_spdji_a_share_factor"},
            {"research_id": "catalog_spdji_a_low_vol_high_dividend"},
            {"research_id": "catalog_spdji_hk_smart_beta"},
            {"research_id": "catalog_fama_french_five_factor"},
        ],
    }


def _v2_8_d_fixture(tmp_path: Path) -> tuple[Path, Path, dict]:
    queue_json = tmp_path / "refresh_queue.json"
    queue_json.write_text(json.dumps(_refresh_queue(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report = v2_8_d.run_acceptance(
        output_root=tmp_path / "v2_8_d_processed",
        reports_dir=tmp_path / "v2_8_d_reports",
        refresh_queue_json=queue_json,
        run_id="v2_8_d_for_v2_8_e",
        command="unit test v2.8-d",
    )
    return Path(report["refreshed_hypotheses_json"]), Path(report["refresh_queue_sandbox_report_json"]), report


def test_refresh_queue_suggestion_gate_allows_only_sandbox_passes(tmp_path: Path):
    hypotheses_json, sandbox_report_json, sandbox_acceptance = _v2_8_d_fixture(tmp_path)
    hypotheses = validator._load_hypotheses(hypotheses_json)
    sandbox_report = validator._load_json(sandbox_report_json)

    report = build_hypothesis_suggestion_gate_report(
        hypotheses,
        sandbox_report,
        run_id="v2_8_e_unit",
        evidence_refs=[str(sandbox_report_json)],
        command="unit test",
    )

    assert report["overall_status"] == "PASS"
    assert report["summary"]["allowed_count"] == sandbox_acceptance["summary"]["pass_count"]
    assert report["summary"]["blocked_count"] == sandbox_acceptance["summary"]["fail_count"]
    assert all(item["simulation_only"] for item in report["suggestions"])
    assert all(item["user_must_execute_externally"] for item in report["suggestions"])
    assert all(
        "strategy_sandbox_not_passed" in item["blocked_by"]
        for item in report["suggestions"]
        if item["action"] == "blocked"
    )


def test_v2_8_e_acceptance_writes_reports_hashes_and_keeps_boundaries(tmp_path: Path):
    hypotheses_json, sandbox_report_json, _ = _v2_8_d_fixture(tmp_path)

    report = validator.run_acceptance(
        output_root=tmp_path / "processed",
        reports_dir=tmp_path / "reports",
        refreshed_hypotheses_json=hypotheses_json,
        sandbox_report_json=sandbox_report_json,
        run_id="v2_8_e_test",
        command="test command",
    )

    assert report["overall_status"] == "PASS"
    assert report["acceptance_target"] == "V2.8-E Refresh Queue Suggestion Gate Drafts"
    assert report["checks"]["allowed_count_matches_sandbox_pass"] is True
    assert report["checks"]["blocked_count_matches_sandbox_fail"] is True
    assert report["checks"]["manual_external_execution_only"] is True
    assert report["checks"]["no_real_trade"] is True
    assert report["checks"]["no_broker_api"] is True
    assert report["checks"]["no_trading_webhook"] is True
    assert report["production_records_written"] is False
    assert report["dashboard_contract_changed"] is False
    assert report["hashes"]["suggestions_json"]
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()


def test_v2_8_e_cli_exits_zero_and_prints_no_secret_values(tmp_path: Path, capsys):
    hypotheses_json, sandbox_report_json, _ = _v2_8_d_fixture(tmp_path)

    exit_code = validator.main(
        [
            "--output-root",
            str(tmp_path / "processed"),
            "--reports-dir",
            str(tmp_path / "reports"),
            "--run-id",
            "v2_8_e_cli",
            "--refreshed-hypotheses-json",
            str(hypotheses_json),
            "--sandbox-report-json",
            str(sandbox_report_json),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "PASS" in captured.out
    assert "token" not in captured.out.lower()
    assert "secret" not in captured.out.lower()
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()
