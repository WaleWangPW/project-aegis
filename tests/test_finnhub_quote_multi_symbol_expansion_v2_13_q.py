from __future__ import annotations

import json
from pathlib import Path

from aegis.external_sources.finnhub_quote_multi_symbol_expansion import (
    ACCEPTANCE_TARGET,
    build_finnhub_quote_multi_symbol_expansion_plan,
    render_finnhub_quote_multi_symbol_expansion_markdown,
)
import scripts.validate_v2_13_q_finnhub_quote_multi_symbol_expansion_plan as validator


def _refresh_report() -> dict:
    return {
        "overall_status": "PASS",
        "acceptance_target": "V2.13-P Finnhub Quote Current Usable Simulation Brief Refresh With Review/Memory Context",
        "network_used": False,
        "production_records_written": False,
        "dashboard_contract_changed": False,
        "summary": {
            "candidate_count": 1,
            "candidate_symbols": ["AAPL.US"],
            "review_memory_context_count": 1,
            "social_sentiment_status": "blocked_plan_or_rate_limit",
        },
        "items": [
            {
                "symbol": "AAPL.US",
                "market": "US",
                "brief_status": "simulation_candidate",
                "review_memory_status": "formal_pending",
            }
        ],
    }


def _decision_packet() -> dict:
    return {
        "overall_status": "PASS",
        "acceptance_target": "V2.9-A Current User Decision Packet",
        "items": [
            {
                "symbol": "600519.SH",
                "name": "贵州茅台",
                "market": "A",
                "strategy_id": "strategy_a_low_vol_dividend_defensive",
                "candidate_score": 0.95,
                "candidate_status": "Watch",
                "decision_packet_status": "simulation_candidate",
            },
            {
                "symbol": "00700.HK",
                "name": "Tencent Holdings",
                "market": "H",
                "strategy_id": "strategy_h_low_vol_dividend",
                "candidate_score": 0.82,
                "candidate_status": "Watch",
                "decision_packet_status": "simulation_candidate",
            },
            {
                "symbol": "AAPL.US",
                "name": "Apple",
                "market": "US",
                "strategy_id": "strategy_aapl_us_finnhub_quote_context_probe",
                "candidate_score": 0.80,
                "candidate_status": "Watch",
                "decision_packet_status": "simulation_candidate",
            },
            {
                "symbol": "MSFT",
                "name": "Microsoft",
                "market": "US",
                "strategy_id": "strategy_us_value_quality_momentum",
                "candidate_score": 0.86,
                "candidate_status": "Watch",
                "decision_packet_status": "simulation_candidate",
            },
            {
                "symbol": "NVDA",
                "name": "NVIDIA",
                "market": "US",
                "strategy_id": "strategy_us_value_quality_momentum",
                "candidate_score": 0.83,
                "candidate_status": "Watch",
                "decision_packet_status": "simulation_candidate",
            },
        ],
    }


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def test_v2_13_q_builds_us_finnhub_queue_and_routes_non_us_away():
    report = build_finnhub_quote_multi_symbol_expansion_plan(
        _refresh_report(),
        _decision_packet(),
        run_id="unit",
    )

    assert report["overall_status"] == "PASS"
    assert report["acceptance_target"] == ACCEPTANCE_TARGET
    assert report["summary"]["candidate_count"] == 5
    assert report["summary"]["source_context_symbols"] == ["AAPL.US"]
    assert report["summary"]["already_context_symbols"] == ["AAPL.US"]
    assert report["summary"]["finnhub_probe_symbols"] == ["MSFT.US", "NVDA.US"]
    assert report["provider_routes"]["finnhub_quote"]["symbols"] == ["MSFT.US", "NVDA.US"]
    routed = {item["symbol"]: item for item in report["queue_items"]}
    assert routed["600519.SH"]["provider_route"] == "tushare_a_share_daily_bar_or_snapshot"
    assert routed["00700.HK"]["provider_route"] == "eodhd_or_twelve_data_h_quote_or_daily_bar"
    assert routed["600519.SH"]["blocked_by"] == ["not_a_finnhub_quote_scope_candidate"]
    assert routed["00700.HK"]["blocked_by"] == ["not_a_finnhub_quote_scope_candidate"]
    assert report["checks"]["all_non_us_candidates_routed_away_from_finnhub"] is True


def test_v2_13_q_preserves_simulation_and_no_trading_boundaries():
    report = build_finnhub_quote_multi_symbol_expansion_plan(_refresh_report(), _decision_packet(), run_id="unit")

    assert report["network_used"] is False
    assert report["production_records_written"] is False
    assert report["safety"]["simulation_only"] is True
    assert report["safety"]["manual_external_execution_only"] is True
    assert report["safety"]["no_real_trade"] is True
    assert report["safety"]["no_broker_api"] is True
    assert report["safety"]["no_webhook"] is True
    assert report["safety"]["no_order_placement"] is True
    assert all(item["no_live_price"] is True for item in report["queue_items"])
    assert all(item["no_position_size"] is True for item in report["queue_items"])


def test_v2_13_q_markdown_exposes_provider_routing():
    report = build_finnhub_quote_multi_symbol_expansion_plan(_refresh_report(), _decision_packet(), run_id="unit")

    md = render_finnhub_quote_multi_symbol_expansion_markdown(report)

    assert "V2.13-Q Finnhub Quote Multi-Symbol Candidate Expansion Plan" in md
    assert "MSFT.US" in md
    assert "NVDA.US" in md
    assert "h_us_provider_branch" in md
    assert "tushare_branch" in md
    assert "no broker API" in md
    assert "place orders" in md


def test_v2_13_q_validator_writes_plan_and_queues_without_touching_records(tmp_path: Path):
    refresh_json = tmp_path / "v2_13_p.json"
    refresh_marker = tmp_path / "v2_13_p.marker"
    decision_json = tmp_path / "v2_9_a.json"
    decision_marker = tmp_path / "v2_9_a.marker"
    _write_json(refresh_json, _refresh_report())
    _write_json(decision_json, _decision_packet())
    refresh_marker.write_text("exit_code=0\n", encoding="utf-8")
    decision_marker.write_text("exit_code=0\n", encoding="utf-8")
    record = tmp_path / "records" / "recommendations.jsonl"
    record.parent.mkdir()
    record.write_text("existing\n", encoding="utf-8")

    report = validator.run_acceptance(
        output_root=tmp_path / "processed",
        reports_dir=tmp_path / "reports",
        run_id="v2_13_q_test",
        command="test command",
        source_v2_13_p_report_json=refresh_json,
        source_v2_13_p_pass_marker=refresh_marker,
        source_v2_9_a_decision_packet_json=decision_json,
        source_v2_9_a_pass_marker=decision_marker,
        record_paths={"recommendations_jsonl": record},
    )

    assert report["overall_status"] == "PASS"
    assert report["checks"]["production_record_files_unchanged"] is True
    assert report["hashes"]["plan_json"]
    assert report["hashes"]["probe_queue_json"]
    assert record.read_text(encoding="utf-8") == "existing\n"
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()


def test_v2_13_q_cli_exits_zero_and_prints_no_secret_values(tmp_path: Path, capsys):
    refresh_json = tmp_path / "v2_13_p.json"
    refresh_marker = tmp_path / "v2_13_p.marker"
    decision_json = tmp_path / "v2_9_a.json"
    decision_marker = tmp_path / "v2_9_a.marker"
    _write_json(refresh_json, _refresh_report())
    _write_json(decision_json, _decision_packet())
    refresh_marker.write_text("exit_code=0\n", encoding="utf-8")
    decision_marker.write_text("exit_code=0\n", encoding="utf-8")

    exit_code = validator.main(
        [
            "--output-root",
            str(tmp_path / "processed"),
            "--reports-dir",
            str(tmp_path / "reports"),
            "--run-id",
            "v2_13_q_cli",
            "--source-v2-13-p-report-json",
            str(refresh_json),
            "--source-v2-13-p-pass-marker",
            str(refresh_marker),
            "--source-v2-9-a-decision-packet-json",
            str(decision_json),
            "--source-v2-9-a-pass-marker",
            str(decision_marker),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "PASS" in captured.out
    assert "MSFT.US,NVDA.US" in captured.out
    assert "token" not in captured.out.lower()
    assert "secret" not in captured.out.lower()
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()
