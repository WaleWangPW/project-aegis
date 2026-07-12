from __future__ import annotations

import json
from pathlib import Path

import scripts.validate_v2_5_a_candidate_binding as validator
from aegis.strategy.candidate_binding import build_candidate_binding_report, build_candidate_bindings


def _write_sources(tmp_path: Path) -> tuple[Path, Path, Path]:
    suggestions = [
        {
            "suggestion_id": "sug_research_hyp_a_low_vol_dividend_defensive",
            "strategy_id": "strategy_a_low_vol_dividend_defensive",
            "symbol": "A_LOW_VOL_DIVIDEND_PAPER_BASKET",
            "market": "A",
            "action": "paper_entry_candidate",
            "simulation_only": True,
            "user_must_execute_externally": True,
            "reasons": ["sandbox PASS"],
            "risk_warnings": ["simulation only"],
            "evidence_refs": ["v2_4_d_report.json"],
            "blocked_by": [],
            "created_at": "2026-07-11T00:00:00+08:00",
        },
        {
            "suggestion_id": "sug_research_hyp_h_low_vol_dividend",
            "strategy_id": "strategy_h_low_vol_dividend",
            "symbol": "H_LOW_VOL_DIVIDEND_PAPER_BASKET",
            "market": "H",
            "action": "paper_entry_candidate",
            "simulation_only": True,
            "user_must_execute_externally": True,
            "reasons": ["sandbox PASS"],
            "risk_warnings": ["simulation only"],
            "evidence_refs": ["v2_4_d_report.json"],
            "blocked_by": [],
            "created_at": "2026-07-11T00:00:00+08:00",
        },
        {
            "suggestion_id": "sug_research_hyp_us_value_quality_momentum",
            "strategy_id": "strategy_us_value_quality_momentum",
            "symbol": "US_VALUE_QUALITY_MOMENTUM_PAPER_BASKET",
            "market": "US",
            "action": "paper_entry_candidate",
            "simulation_only": True,
            "user_must_execute_externally": True,
            "reasons": ["sandbox PASS"],
            "risk_warnings": ["simulation only"],
            "evidence_refs": ["v2_4_d_report.json"],
            "blocked_by": [],
            "created_at": "2026-07-11T00:00:00+08:00",
        },
        {
            "suggestion_id": "sug_research_hyp_us_low_vol_risk_overlay",
            "strategy_id": "strategy_us_low_vol_risk_overlay",
            "symbol": "US_LOW_VOL_RISK_OVERLAY_PAPER_BASKET",
            "market": "US",
            "action": "blocked",
            "simulation_only": True,
            "user_must_execute_externally": True,
            "reasons": ["sandbox FAIL"],
            "risk_warnings": ["simulation only"],
            "evidence_refs": ["v2_4_d_report.json"],
            "blocked_by": ["strategy_sandbox_not_passed"],
            "created_at": "2026-07-11T00:00:00+08:00",
        },
    ]
    watchlist = {
        "top5": [
            {"symbol": "600036.SH", "name": "招商银行", "market": "A", "score": 0.85, "status": "Watch"},
            {"symbol": "601398.SH", "name": "工商银行", "market": "A", "score": 0.72, "status": "Watch"},
        ]
    }
    desktop_status = {
        "holdings": {
            "holdings": [
                {
                    "symbol": "CRCL",
                    "name": "Circle Internet Group",
                    "market": "US",
                    "status": "open",
                    "shares": 254,
                }
            ]
        }
    }

    suggestions_json = tmp_path / "suggestions.json"
    watchlist_json = tmp_path / "watchlist.json"
    desktop_json = tmp_path / "desktop.json"
    suggestions_json.write_text(json.dumps(suggestions, ensure_ascii=False), encoding="utf-8")
    watchlist_json.write_text(json.dumps(watchlist, ensure_ascii=False), encoding="utf-8")
    desktop_json.write_text(json.dumps(desktop_status, ensure_ascii=False), encoding="utf-8")
    return suggestions_json, watchlist_json, desktop_json


def test_candidate_bindings_use_approved_sources_and_block_missing_h_market(tmp_path: Path):
    suggestions_json, watchlist_json, desktop_json = _write_sources(tmp_path)
    suggestions = json.loads(suggestions_json.read_text(encoding="utf-8"))

    bindings = build_candidate_bindings(
        suggestions,
        a_share_watchlist_json=watchlist_json,
        desktop_status_json=desktop_json,
        created_at="2026-07-11T00:00:00+08:00",
    )
    by_id = {item.suggestion_id: item for item in bindings}

    assert by_id["sug_research_hyp_a_low_vol_dividend_defensive"].binding_status == "bound"
    assert by_id["sug_research_hyp_a_low_vol_dividend_defensive"].bound_candidates[0].symbol == "600036.SH"
    assert by_id["sug_research_hyp_a_low_vol_dividend_defensive"].bound_candidates[0].source == "a_share_watchlist_latest"

    assert by_id["sug_research_hyp_us_value_quality_momentum"].binding_status == "bound"
    assert by_id["sug_research_hyp_us_value_quality_momentum"].bound_candidates[0].symbol == "CRCL"
    assert by_id["sug_research_hyp_us_value_quality_momentum"].bound_candidates[0].source == "current_manual_holding"

    assert by_id["sug_research_hyp_h_low_vol_dividend"].binding_status == "blocked"
    assert "missing_candidate_source" in by_id["sug_research_hyp_h_low_vol_dividend"].blocked_by

    assert by_id["sug_research_hyp_us_low_vol_risk_overlay"].binding_status == "blocked"
    assert "strategy_sandbox_not_passed" in by_id["sug_research_hyp_us_low_vol_risk_overlay"].blocked_by


def test_candidate_binding_report_keeps_simulation_safety(tmp_path: Path):
    suggestions_json, watchlist_json, desktop_json = _write_sources(tmp_path)
    suggestions = json.loads(suggestions_json.read_text(encoding="utf-8"))

    report = build_candidate_binding_report(
        suggestions,
        a_share_watchlist_json=watchlist_json,
        desktop_status_json=desktop_json,
        run_id="v2_5_a_unit",
        command="unit test",
    )

    assert report["overall_status"] == "PASS"
    assert report["summary"]["bound_count"] == 2
    assert "A" in report["summary"]["bound_markets"]
    assert "US" in report["summary"]["bound_markets"]
    assert report["safety"]["candidate_binding_not_recommendation_record"] is True
    assert report["safety"]["no_real_trade"] is True
    assert report["production_records_written"] is False


def test_v2_5_a_acceptance_writes_reports_and_hashes(tmp_path: Path):
    suggestions_json, watchlist_json, desktop_json = _write_sources(tmp_path)

    report = validator.run_acceptance(
        output_root=tmp_path / "processed",
        reports_dir=tmp_path / "reports",
        run_id="v2_5_a_test",
        command="test command",
        suggestion_drafts_json=suggestions_json,
        a_share_watchlist_json=watchlist_json,
        desktop_status_json=desktop_json,
    )

    assert report["overall_status"] == "PASS"
    assert report["checks"]["a_share_bound_from_watchlist"] is True
    assert report["checks"]["us_bound_from_manual_holding"] is True
    assert report["checks"]["h_missing_source_blocked"] is True
    assert report["checks"]["no_real_trade_or_broker"] is True
    assert report["hashes"]["bindings_json"]
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()


def test_v2_5_a_cli_exits_zero_and_prints_no_secrets(tmp_path: Path, capsys):
    suggestions_json, watchlist_json, desktop_json = _write_sources(tmp_path)

    exit_code = validator.main(
        [
            "--output-root",
            str(tmp_path / "processed"),
            "--reports-dir",
            str(tmp_path / "reports"),
            "--run-id",
            "v2_5_a_cli",
            "--suggestion-drafts-json",
            str(suggestions_json),
            "--a-share-watchlist-json",
            str(watchlist_json),
            "--desktop-status-json",
            str(desktop_json),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "PASS" in captured.out
    assert "token" not in captured.out.lower()
    assert "secret" not in captured.out.lower()
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()

