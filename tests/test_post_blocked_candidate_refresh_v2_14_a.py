from __future__ import annotations

import json
from pathlib import Path

from aegis.strategy.post_blocked_candidate_refresh import (
    build_post_blocked_candidate_refresh_plan,
    render_post_blocked_candidate_refresh_markdown,
)
import scripts.validate_v2_14_a_post_blocked_candidate_refresh_plan as validator


def _blocked_brief() -> dict:
    return {
        "overall_status": "PASS",
        "acceptance_target": "V2.13-W Finnhub Quote Multi-Symbol Sandbox Result Brief",
        "run_id": "unit_v2_13_w",
        "summary": {
            "blocked_item_count": 3,
            "passed_item_count": 0,
            "blocked_symbols": ["CRCL.US", "MSFT.US", "NVDA.US"],
            "suggestion_gate_ready": False,
            "user_facing_suggestion_allowed": False,
            "real_trade_allowed": False,
        },
    }


def _candidate(symbol: str, market: str, strategy_id: str) -> dict:
    return {
        "symbol": symbol,
        "market": market,
        "strategy_id": strategy_id,
        "decision_packet_status": "simulation_candidate",
        "source_mode": "approved_fixture_not_live_market_data",
        "user_action": "simulation_only",
    }


def _decision_packet() -> dict:
    return {
        "overall_status": "PASS",
        "acceptance_target": "V2.9-A Current User Decision Packet",
        "run_id": "unit_v2_9_a",
        "summary": {
            "candidate_count": 9,
            "candidate_markets": ["A", "H", "US"],
            "candidate_symbols": [
                "600519.SH",
                "600036.SH",
                "601398.SH",
                "00700.HK",
                "00005.HK",
                "00941.HK",
                "CRCL",
                "MSFT",
                "NVDA",
            ],
        },
        "items": [
            _candidate("600519.SH", "A", "strategy_a_low_vol_dividend_defensive"),
            _candidate("600036.SH", "A", "strategy_a_low_vol_dividend_defensive"),
            _candidate("601398.SH", "A", "strategy_a_low_vol_dividend_defensive"),
            _candidate("00700.HK", "H", "strategy_h_low_vol_dividend"),
            _candidate("00005.HK", "H", "strategy_h_low_vol_dividend"),
            _candidate("00941.HK", "H", "strategy_h_low_vol_dividend"),
            _candidate("CRCL", "US", "strategy_us_value_quality_momentum"),
            _candidate("MSFT", "US", "strategy_us_value_quality_momentum"),
            _candidate("NVDA", "US", "strategy_us_value_quality_momentum"),
        ],
    }


def test_v2_14_a_removes_blocked_us_candidates_and_retains_a_h_candidates():
    report = build_post_blocked_candidate_refresh_plan(
        blocked_brief=_blocked_brief(),
        decision_packet=_decision_packet(),
        run_id="unit",
        generated_at="2026-07-12T00:00:00+08:00",
    )
    retained_symbols = [item["symbol"] for item in report["retained_candidates"]]
    removed_symbols = [item["symbol"] for item in report["removed_candidates"]]

    assert report["overall_status"] == "PASS"
    assert report["summary"]["removed_candidate_count"] == 3
    assert report["summary"]["retained_candidate_count"] == 6
    assert report["summary"]["retained_markets"] == ["A", "H"]
    assert report["summary"]["replacement_required_markets"] == ["US"]
    assert removed_symbols == ["CRCL", "MSFT", "NVDA"]
    assert "CRCL" not in retained_symbols
    assert "MSFT" not in retained_symbols
    assert "NVDA" not in retained_symbols
    assert "600519.SH" in retained_symbols
    assert "00700.HK" in retained_symbols
    assert report["checks"]["us_candidates_require_replacement"] is True
    assert report["checks"]["not_user_facing_suggestion"] is True


def test_v2_14_a_routes_require_sandbox_and_suggestion_gate():
    report = build_post_blocked_candidate_refresh_plan(
        blocked_brief=_blocked_brief(),
        decision_packet=_decision_packet(),
        run_id="unit",
    )
    routes = {item["market"]: item for item in report["route_plan"]}

    assert routes["A"]["provider"] == "tushare"
    assert routes["A"]["refresh_status"] == "ready_for_live_refresh"
    assert routes["H"]["provider"] == "h_us_provider"
    assert routes["US"]["refresh_status"] == "blocked_until_replacement_candidates_found"
    assert all(item["requires_sandbox"] is True for item in report["route_plan"])
    assert all(item["requires_suggestion_gate"] is True for item in report["route_plan"])
    assert report["replacement_requests"][0]["market"] == "US"
    assert report["replacement_requests"][0]["requires_historical_sandbox"] is True


def test_v2_14_a_markdown_is_a_refresh_plan_not_a_suggestion():
    report = build_post_blocked_candidate_refresh_plan(
        blocked_brief=_blocked_brief(),
        decision_packet=_decision_packet(),
        run_id="unit",
    )
    md = render_post_blocked_candidate_refresh_markdown(report)

    assert "Post-Blocked Candidate Pool Refresh Plan" in md
    assert "CRCL" in md
    assert "MSFT" in md
    assert "NVDA" in md
    assert "Not a user-facing suggestion" in md
    assert "No real trade" in md
    assert "broker API" in md
    assert "token=" not in md
    assert "https://" not in md


def test_v2_14_a_fails_if_blocked_source_is_not_v2_13_w():
    source = _blocked_brief()
    source["acceptance_target"] = "wrong"

    report = build_post_blocked_candidate_refresh_plan(
        blocked_brief=source,
        decision_packet=_decision_packet(),
        run_id="unit",
    )

    assert report["overall_status"] == "FAIL"
    assert report["checks"]["blocked_source_target_correct"] is False


def test_v2_14_a_fails_if_blocked_us_candidates_are_not_removed():
    decision_packet = _decision_packet()
    decision_packet["items"] = [
        item for item in decision_packet["items"] if item["symbol"] not in {"CRCL", "MSFT"}
    ]

    report = build_post_blocked_candidate_refresh_plan(
        blocked_brief=_blocked_brief(),
        decision_packet=decision_packet,
        run_id="unit",
    )

    assert report["overall_status"] == "FAIL"
    assert report["checks"]["removed_candidates_match_blocked_symbols"] is False


def test_v2_14_a_validator_writes_plan_and_marker(tmp_path: Path):
    blocked_path = tmp_path / "blocked.json"
    blocked_marker = tmp_path / "blocked.marker"
    packet_path = tmp_path / "packet.json"
    packet_marker = tmp_path / "packet.marker"
    blocked_path.write_text(json.dumps(_blocked_brief(), ensure_ascii=False), encoding="utf-8")
    blocked_marker.write_text("source pass\n", encoding="utf-8")
    packet_path.write_text(json.dumps(_decision_packet(), ensure_ascii=False), encoding="utf-8")
    packet_marker.write_text("source pass\n", encoding="utf-8")
    record = tmp_path / "records" / "recommendations.jsonl"
    record.parent.mkdir()
    record.write_text("existing\n", encoding="utf-8")

    report = validator.run_acceptance(
        output_root=tmp_path / "processed",
        reports_dir=tmp_path / "reports",
        run_id="v2_14_a_test",
        command="test command",
        source_v2_13_w_report_json=blocked_path,
        source_v2_13_w_pass_marker=blocked_marker,
        source_v2_9_a_report_json=packet_path,
        source_v2_9_a_pass_marker=packet_marker,
        record_paths={"recommendations_jsonl": record},
    )

    assert report["overall_status"] == "PASS"
    assert report["checks"]["plan_json_written"] is True
    assert report["checks"]["plan_md_written"] is True
    assert report["checks"]["production_record_files_unchanged"] is True
    assert report["safety"]["not_user_facing_suggestion"] is True
    assert record.read_text(encoding="utf-8") == "existing\n"
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()


def test_v2_14_a_cli_like_acceptance_prints_no_secret_values(tmp_path: Path, capsys):
    blocked_path = tmp_path / "blocked.json"
    blocked_marker = tmp_path / "blocked.marker"
    packet_path = tmp_path / "packet.json"
    packet_marker = tmp_path / "packet.marker"
    blocked_path.write_text(json.dumps(_blocked_brief(), ensure_ascii=False), encoding="utf-8")
    blocked_marker.write_text("source pass\n", encoding="utf-8")
    packet_path.write_text(json.dumps(_decision_packet(), ensure_ascii=False), encoding="utf-8")
    packet_marker.write_text("source pass\n", encoding="utf-8")

    exit_code = validator.main(
        [
            "--output-root",
            str(tmp_path / "processed"),
            "--reports-dir",
            str(tmp_path / "reports"),
            "--run-id",
            "v2_14_a_cli",
            "--source-v2-13-w-report-json",
            str(blocked_path),
            "--source-v2-13-w-pass-marker",
            str(blocked_marker),
            "--source-v2-9-a-report-json",
            str(packet_path),
            "--source-v2-9-a-pass-marker",
            str(packet_marker),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "PASS" in captured.out
    assert "removed_candidate_count=3" in captured.out
    assert "replacement_required_markets=US" in captured.out
    assert "token" not in captured.out.lower()
    assert "secret" not in captured.out.lower()
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()
