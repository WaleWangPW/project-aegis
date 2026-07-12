from __future__ import annotations

import json
from pathlib import Path

import scripts.validate_v2_8_d_refresh_queue_historical_sandbox as validator
from aegis.strategy.hypothesis_queue import build_strategy_sandbox_hypotheses
from aegis.strategy.research_source_catalog import canonical_strategy_research_records
from aegis.strategy.source_audit_refresh_sandbox import (
    build_refresh_queue_historical_sandbox_report,
    refreshed_hypotheses_from_queue,
)


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


def _hypotheses():
    return build_strategy_sandbox_hypotheses(
        canonical_strategy_research_records(),
        created_at="2026-07-11T00:00:00+08:00",
    )


def test_refresh_queue_selects_hypotheses_and_trims_blocked_refs():
    refreshed, proposal_to_hypotheses = refreshed_hypotheses_from_queue(
        _refresh_queue(),
        _hypotheses(),
        created_at="2026-07-11T00:00:00+08:00",
    )
    blocked_refs = {source["research_id"] for source in _refresh_queue()["blocked_sources"]}

    assert len(refreshed) == 6
    assert all(ids for ids in proposal_to_hypotheses.values())
    assert all(set(hypothesis.source_research_ids).isdisjoint(blocked_refs) for hypothesis in refreshed)
    assert all(hypothesis.requires_sandbox for hypothesis in refreshed)


def test_refresh_queue_sandbox_report_has_pass_fail_and_keeps_gate():
    report = build_refresh_queue_historical_sandbox_report(
        _refresh_queue(),
        _hypotheses(),
        run_id="v2_8_d_unit",
        command="unit test",
        historical_cache_file_count=10,
    )

    assert report["overall_status"] == "PASS"
    assert report["summary"]["hypothesis_count"] == 6
    assert report["summary"]["historical_case_count"] == 24
    assert report["summary"]["pass_count"] >= 2
    assert report["summary"]["fail_count"] >= 2
    assert report["checks"]["blocked_refs_excluded"] is True
    assert report["checks"]["suggestion_gate_still_required"] is True
    assert report["safety"]["source_audit_refresh_only"] is True


def test_v2_8_d_acceptance_writes_reports_and_marker(tmp_path: Path):
    queue_json = tmp_path / "refresh_queue.json"
    queue_json.write_text(json.dumps(_refresh_queue(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    report = validator.run_acceptance(
        output_root=tmp_path / "processed",
        reports_dir=tmp_path / "reports",
        refresh_queue_json=queue_json,
        run_id="v2_8_d_test",
        command="test command",
    )

    assert report["overall_status"] == "PASS"
    assert report["checks"]["all_proposals_evaluated"] is True
    assert report["checks"]["blocked_refs_excluded"] is True
    assert report["checks"]["suggestion_gate_still_required"] is True
    assert report["production_records_written"] is False
    assert report["dashboard_contract_changed"] is False
    assert report["hashes"]["refresh_queue_sandbox_report_json"]
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()


def test_v2_8_d_cli_exits_zero_and_prints_no_secrets(tmp_path: Path, capsys):
    queue_json = tmp_path / "refresh_queue.json"
    queue_json.write_text(json.dumps(_refresh_queue(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    exit_code = validator.main(
        [
            "--output-root",
            str(tmp_path / "processed"),
            "--reports-dir",
            str(tmp_path / "reports"),
            "--refresh-queue-json",
            str(queue_json),
            "--run-id",
            "v2_8_d_cli",
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "PASS" in captured.out
    assert "secret" not in captured.out.lower()
    assert "token" not in captured.out.lower()
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()
