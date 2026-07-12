from __future__ import annotations

import json
from pathlib import Path

from aegis.strategy.candidate_pool_live_refresh import (
    build_candidate_pool_live_refresh_report,
    render_candidate_pool_live_refresh_markdown,
)
import scripts.validate_v2_14_b_candidate_pool_live_refresh as validator


def _candidate(symbol: str, market: str, strategy_id: str) -> dict:
    return {
        "symbol": symbol,
        "market": market,
        "strategy_id": strategy_id,
        "decision_packet_status": "simulation_candidate",
    }


def _source_plan() -> dict:
    return {
        "overall_status": "PASS",
        "acceptance_target": "V2.14-A Post-Blocked Candidate Pool Refresh Plan",
        "run_id": "unit_v2_14_a",
        "summary": {
            "source_blocked_symbols": ["CRCL", "MSFT", "NVDA"],
            "retained_candidate_count": 6,
            "removed_candidate_count": 3,
            "retained_markets": ["A", "H"],
            "replacement_required_markets": ["US"],
        },
        "retained_candidates": [
            _candidate("600519.SH", "A", "strategy_a_low_vol_dividend_defensive"),
            _candidate("600036.SH", "A", "strategy_a_low_vol_dividend_defensive"),
            _candidate("601398.SH", "A", "strategy_a_low_vol_dividend_defensive"),
            _candidate("00700.HK", "H", "strategy_h_low_vol_dividend"),
            _candidate("00005.HK", "H", "strategy_h_low_vol_dividend"),
            _candidate("00941.HK", "H", "strategy_h_low_vol_dividend"),
        ],
        "route_plan": [
            {
                "market": "A",
                "route_id": "tushare_a_share_candidate_refresh",
                "provider": "tushare",
                "refresh_status": "ready_for_live_refresh",
                "requires_sandbox": True,
                "requires_suggestion_gate": True,
            },
            {
                "market": "H",
                "route_id": "h_share_h_us_provider_candidate_refresh",
                "provider": "h_us_provider",
                "refresh_status": "ready_for_h_us_refresh",
                "requires_sandbox": True,
                "requires_suggestion_gate": True,
            },
            {
                "market": "US",
                "route_id": "us_candidate_replacement_required",
                "provider": "finnhub_or_h_us_provider",
                "refresh_status": "blocked_until_replacement_candidates_found",
                "requires_sandbox": True,
                "requires_suggestion_gate": True,
            },
        ],
        "replacement_requests": [
            {
                "market": "US",
                "request_id": "replace_blocked_us_multi_symbol_candidates",
                "blocked_symbols": ["CRCL", "MSFT", "NVDA"],
                "needed_count": 3,
                "requires_historical_sandbox": True,
                "requires_suggestion_gate": True,
            }
        ],
    }


def test_v2_14_b_refreshes_a_h_only_and_keeps_us_replacement_open():
    report = build_candidate_pool_live_refresh_report(
        source_plan=_source_plan(),
        run_id="unit",
        generated_at="2026-07-12T00:00:00+08:00",
    )
    symbols = [item["symbol"] for item in report["refreshed_candidates"]]

    assert report["overall_status"] == "PASS"
    assert report["summary"]["refreshed_candidate_count"] == 6
    assert report["summary"]["refreshed_markets"] == ["A", "H"]
    assert report["summary"]["replacement_required_markets"] == ["US"]
    assert {"CRCL", "MSFT", "NVDA"}.isdisjoint(set(symbols))
    assert "600519.SH" in symbols
    assert "00700.HK" in symbols
    assert report["replacement_requests"][0]["refresh_status"] == "open_pending_replacement_candidates"
    assert report["checks"]["blocked_symbols_not_revived"] is True


def test_v2_14_b_every_refreshed_candidate_still_requires_sandbox_and_gate():
    report = build_candidate_pool_live_refresh_report(source_plan=_source_plan(), run_id="unit")

    assert all(item["requires_historical_sandbox"] is True for item in report["refreshed_candidates"])
    assert all(item["requires_suggestion_gate"] is True for item in report["refreshed_candidates"])
    assert all(item["user_facing_suggestion_allowed"] is False for item in report["refreshed_candidates"])
    assert report["safety"]["not_user_facing_suggestion"] is True
    assert report["safety"]["no_real_trade"] is True
    assert report["network_used"] is False


def test_v2_14_b_fails_if_blocked_us_symbol_is_revived():
    source = _source_plan()
    source["retained_candidates"].append(_candidate("MSFT", "H", "strategy_bad_revive"))

    report = build_candidate_pool_live_refresh_report(source_plan=source, run_id="unit")

    assert report["overall_status"] == "FAIL"
    assert report["revived_blocked_symbols"] == ["MSFT"]
    assert report["checks"]["blocked_symbols_not_revived"] is False


def test_v2_14_b_fails_if_source_is_not_v2_14_a():
    source = _source_plan()
    source["acceptance_target"] = "wrong"

    report = build_candidate_pool_live_refresh_report(source_plan=source, run_id="unit")

    assert report["overall_status"] == "FAIL"
    assert report["checks"]["source_plan_target_correct"] is False


def test_v2_14_b_markdown_is_refresh_not_suggestion():
    report = build_candidate_pool_live_refresh_report(source_plan=_source_plan(), run_id="unit")
    md = render_candidate_pool_live_refresh_markdown(report)

    assert "Candidate Pool Live Refresh" in md
    assert "600519.SH" in md
    assert "00700.HK" in md
    assert "replace_blocked_us_multi_symbol_candidates" in md
    assert "Not a user-facing suggestion" in md
    assert "No real trade" in md
    assert "token=" not in md
    assert "https://" not in md


def test_v2_14_b_validator_writes_refresh_and_marker(tmp_path: Path):
    source_path = tmp_path / "source.json"
    marker_path = tmp_path / "source.marker"
    source_path.write_text(json.dumps(_source_plan(), ensure_ascii=False), encoding="utf-8")
    marker_path.write_text("source pass\n", encoding="utf-8")
    record = tmp_path / "records" / "recommendations.jsonl"
    record.parent.mkdir()
    record.write_text("existing\n", encoding="utf-8")

    report = validator.run_acceptance(
        output_root=tmp_path / "processed",
        reports_dir=tmp_path / "reports",
        run_id="v2_14_b_test",
        command="test command",
        source_v2_14_a_report_json=source_path,
        source_v2_14_a_pass_marker=marker_path,
        record_paths={"recommendations_jsonl": record},
    )

    assert report["overall_status"] == "PASS"
    assert report["checks"]["refresh_json_written"] is True
    assert report["checks"]["refresh_md_written"] is True
    assert report["checks"]["production_record_files_unchanged"] is True
    assert record.read_text(encoding="utf-8") == "existing\n"
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()


def test_v2_14_b_cli_like_acceptance_prints_no_secret_values(tmp_path: Path, capsys):
    source_path = tmp_path / "source.json"
    marker_path = tmp_path / "source.marker"
    source_path.write_text(json.dumps(_source_plan(), ensure_ascii=False), encoding="utf-8")
    marker_path.write_text("source pass\n", encoding="utf-8")

    exit_code = validator.main(
        [
            "--output-root",
            str(tmp_path / "processed"),
            "--reports-dir",
            str(tmp_path / "reports"),
            "--run-id",
            "v2_14_b_cli",
            "--source-v2-14-a-report-json",
            str(source_path),
            "--source-v2-14-a-pass-marker",
            str(marker_path),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "PASS" in captured.out
    assert "refreshed_candidate_count=6" in captured.out
    assert "replacement_required_markets=US" in captured.out
    assert "token" not in captured.out.lower()
    assert "secret" not in captured.out.lower()
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()
