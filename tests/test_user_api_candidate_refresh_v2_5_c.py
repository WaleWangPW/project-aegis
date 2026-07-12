from __future__ import annotations

import json
from pathlib import Path

import scripts.validate_v2_5_c_user_api_candidate_refresh as validator
from aegis.strategy.candidate_refresh import (
    build_candidate_refresh_report,
    candidate_items_from_api_payload,
    candidate_source_registry_from_api_candidates,
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
    ]


def test_candidate_items_parse_summary_only_payload():
    payload = json.dumps(
        {
            "items": [
                {"symbol": "600036.SH", "market": "A", "name": "招商银行", "score": 0.86},
                {"symbol": "00700.HK", "market": "H", "name": "Tencent Holdings", "score": 0.83},
                {"symbol": "MSFT", "market": "US", "name": "Microsoft", "score": 0.78},
                {"symbol": "", "market": "US", "name": "Bad"},
            ]
        }
    ).encode("utf-8")

    candidates = candidate_items_from_api_payload(payload, source_id="api_fixture_candidate_refresh")

    assert len(candidates) == 3
    assert {candidate.market for candidate in candidates} == {"A", "H", "US"}
    assert all(candidate.source == "api_fixture_candidate_refresh" for candidate in candidates)


def test_api_candidate_registry_can_refresh_a_h_us_bindings():
    payload = json.dumps(
        {
            "items": [
                {"symbol": "600036.SH", "market": "A", "name": "招商银行", "score": 0.86},
                {"symbol": "00700.HK", "market": "H", "name": "Tencent Holdings", "score": 0.83},
                {"symbol": "MSFT", "market": "US", "name": "Microsoft", "score": 0.78},
            ]
        }
    ).encode("utf-8")
    candidates = candidate_items_from_api_payload(payload, source_id="api_fixture_candidate_refresh")
    registry = candidate_source_registry_from_api_candidates(
        candidates,
        source_id="api_fixture_candidate_refresh",
        generated_at="2026-07-11T00:00:00+08:00",
    )

    report = build_candidate_refresh_report(
        _suggestions(),
        registry,
        run_id="v2_5_c_unit",
        evidence_ref="api_registry.json",
        command="unit test",
    )

    assert report["overall_status"] == "PASS"
    assert set(report["summary"]["bound_markets"]) == {"A", "H", "US"}
    assert report["safety"]["no_secret_values_stored"] is True
    assert report["production_records_written"] is False


def test_v2_5_c_acceptance_writes_reports_and_does_not_store_secret(tmp_path: Path):
    suggestions_json = tmp_path / "suggestions.json"
    suggestions_json.write_text(json.dumps(_suggestions(), ensure_ascii=False), encoding="utf-8")

    report = validator.run_acceptance(
        output_root=tmp_path / "processed",
        reports_dir=tmp_path / "reports",
        run_id="v2_5_c_test",
        command="test command",
        suggestion_drafts_json=suggestions_json,
    )

    report_text = (tmp_path / "reports" / validator.REPORT_JSON).read_text(encoding="utf-8")
    assert report["overall_status"] == "PASS"
    assert report["checks"]["fixture_api_dry_run_passed"] is True
    assert report["checks"]["secret_value_not_serialized"] is True
    assert report["checks"]["a_h_us_bound_from_api_candidates"] is True
    assert report["real_user_config_status"] in {"blocked_missing_metadata", "available"}
    assert validator._FIXTURE_SECRET not in report_text
    assert report["hashes"]["api_refreshed_candidate_bindings_json"]
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()


def test_v2_5_c_cli_exits_zero_and_prints_no_secret_values(tmp_path: Path, capsys):
    suggestions_json = tmp_path / "suggestions.json"
    suggestions_json.write_text(json.dumps(_suggestions(), ensure_ascii=False), encoding="utf-8")

    exit_code = validator.main(
        [
            "--output-root",
            str(tmp_path / "processed"),
            "--reports-dir",
            str(tmp_path / "reports"),
            "--run-id",
            "v2_5_c_cli",
            "--suggestion-drafts-json",
            str(suggestions_json),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "PASS" in captured.out
    assert validator._FIXTURE_SECRET not in captured.out
    assert "secret" not in captured.out.lower()
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()

