from __future__ import annotations

import json
from pathlib import Path

from aegis.strategy.refreshed_candidate_suggestion_gate import (
    build_refreshed_candidate_suggestion_gate_report,
    render_refreshed_candidate_suggestion_gate_markdown,
)
import scripts.validate_v2_14_d_refreshed_candidate_suggestion_gate as validator


def _covered(symbol: str, market: str, strategy_id: str) -> dict:
    return {
        "candidate_id": f"candidate_{symbol}",
        "symbol": symbol,
        "market": market,
        "strategy_id": strategy_id,
        "evidence_refs": [f"candidate_ref:{symbol}"],
        "coverage_status": "historical_case_available",
    }


def _missing(symbol: str, market: str, strategy_id: str) -> dict:
    return {
        "candidate_id": f"candidate_{symbol}",
        "symbol": symbol,
        "market": market,
        "strategy_id": strategy_id,
        "evidence_refs": [f"candidate_ref:{symbol}"],
        "coverage_status": "missing_historical_case",
        "missing_reason": "no_source_case_for_symbol",
    }


def _result(strategy_id: str, status: str, failed_reasons: list[str] | None = None) -> dict:
    return {
        "strategy_id": strategy_id,
        "status": status,
        "metrics": {
            "strategy_id": strategy_id,
            "sample_count": 1,
            "eligible_case_count": 1,
            "win_rate": 1.0 if status == "PASS" else 0.0,
            "average_return": 0.1 if status == "PASS" else -0.03,
            "max_drawdown": -0.01,
            "turnover_proxy": 1.0,
            "exposure_count": 1,
            "risk_flag_counts": {},
            "failed_reasons": failed_reasons or [],
        },
        "safety": {"simulation_only": True},
        "notes": [],
    }


def _source_report() -> dict:
    return {
        "overall_status": "PASS",
        "acceptance_target": "V2.14-C Refreshed Candidate Historical Sandbox",
        "run_id": "unit_v2_14_c",
        "summary": {
            "covered_candidate_count": 3,
            "missing_coverage_count": 3,
            "strategy_pass_count": 1,
            "strategy_fail_count": 1,
            "sandbox_passed_strategies": ["strategy_h_low_vol_dividend"],
            "sandbox_failed_strategies": ["strategy_a_low_vol_dividend_defensive"],
        },
        "covered_candidates": [
            _covered("600519.SH", "A", "strategy_a_low_vol_dividend_defensive"),
            _covered("600036.SH", "A", "strategy_a_low_vol_dividend_defensive"),
            _covered("00700.HK", "H", "strategy_h_low_vol_dividend"),
        ],
        "missing_coverage_candidates": [
            _missing("601398.SH", "A", "strategy_a_low_vol_dividend_defensive"),
            _missing("00005.HK", "H", "strategy_h_low_vol_dividend"),
            _missing("00941.HK", "H", "strategy_h_low_vol_dividend"),
        ],
        "historical_cases": [
            {
                "case_id": "case_600519",
                "strategy_id": "strategy_a_low_vol_dividend_defensive",
                "date": "2026-01-01",
                "symbol": "600519.SH",
                "market": "A",
                "entry_price": 100.0,
                "exit_price": 98.0,
                "max_drawdown": -0.04,
                "risk_flags": [],
                "factor_values": {"actual_return": -0.02},
                "evidence_ref": "tushare_cache:600519.SH",
            },
            {
                "case_id": "case_600036",
                "strategy_id": "strategy_a_low_vol_dividend_defensive",
                "date": "2026-01-01",
                "symbol": "600036.SH",
                "market": "A",
                "entry_price": 100.0,
                "exit_price": 97.0,
                "max_drawdown": -0.05,
                "risk_flags": [],
                "factor_values": {"actual_return": -0.03},
                "evidence_ref": "tushare_cache:600036.SH",
            },
            {
                "case_id": "case_00700",
                "strategy_id": "strategy_h_low_vol_dividend",
                "date": "2026-07-01",
                "symbol": "00700.HK",
                "market": "H",
                "entry_price": 100.0,
                "exit_price": 110.0,
                "max_drawdown": -0.01,
                "risk_flags": [],
                "factor_values": {"actual_return": 0.1},
                "evidence_ref": "v2_12_c_normalized_cache:h_00700",
            },
        ],
        "results": [
            _result("strategy_a_low_vol_dividend_defensive", "FAIL", ["average_return_below_threshold"]),
            _result("strategy_h_low_vol_dividend", "PASS"),
        ],
    }


def test_v2_14_d_allows_only_passed_covered_candidate():
    report = build_refreshed_candidate_suggestion_gate_report(
        _source_report(),
        run_id="unit",
        generated_at="2026-07-12T00:00:00+08:00",
    )

    assert report["overall_status"] == "PASS"
    assert report["summary"]["allowed_count"] == 1
    assert report["summary"]["blocked_count"] == 5
    assert report["summary"]["allowed_symbols"] == ["00700.HK"]
    assert {"600519.SH", "600036.SH", "601398.SH", "00005.HK", "00941.HK"}.issubset(
        set(report["summary"]["blocked_symbols"])
    )
    assert report["summary"]["simulation_suggestion_available"] is True
    assert report["checks"]["missing_coverage_symbols_blocked"] is True
    assert report["checks"]["no_missing_coverage_allowed"] is True


def test_v2_14_d_allowed_draft_is_simulation_only_not_order():
    report = build_refreshed_candidate_suggestion_gate_report(_source_report(), run_id="unit")
    allowed = [item for item in report["suggestions"] if item["action"] != "blocked"]

    assert len(allowed) == 1
    assert allowed[0]["symbol"] == "00700.HK"
    assert allowed[0]["simulation_only"] is True
    assert allowed[0]["user_must_execute_externally"] is True
    assert allowed[0]["evidence_refs"]
    assert report["safety"]["not_real_trade_advice"] is True
    assert report["safety"]["not_an_order"] is True
    assert report["safety"]["no_broker_api"] is True
    assert report["network_used"] is False


def test_v2_14_d_fails_if_no_passed_strategy():
    source = _source_report()
    source["summary"]["strategy_pass_count"] = 0
    source["results"][1]["status"] = "FAIL"
    source["results"][1]["metrics"]["failed_reasons"] = ["average_return_below_threshold"]

    report = build_refreshed_candidate_suggestion_gate_report(source, run_id="unit")

    assert report["overall_status"] == "FAIL"
    assert report["checks"]["source_has_passed_strategy"] is False


def test_v2_14_d_markdown_is_readable_and_keeps_boundaries():
    report = build_refreshed_candidate_suggestion_gate_report(_source_report(), run_id="unit")
    md = render_refreshed_candidate_suggestion_gate_markdown(report)

    assert "Refreshed Candidate Suggestion Gate" in md
    assert "00700.HK" in md
    assert "Simulation-only suggestion draft" in md
    assert "Not real trade advice" in md
    assert "position size" in md
    assert "token=" not in md
    assert "https://" not in md


def test_v2_14_d_validator_writes_gate_marker_and_suggestions(tmp_path: Path):
    source_path = tmp_path / "source.json"
    source_marker = tmp_path / "source.marker"
    source_path.write_text(json.dumps(_source_report(), ensure_ascii=False), encoding="utf-8")
    source_marker.write_text("source pass\n", encoding="utf-8")
    record = tmp_path / "records" / "recommendations.jsonl"
    record.parent.mkdir()
    record.write_text("existing\n", encoding="utf-8")

    report = validator.run_acceptance(
        output_root=tmp_path / "processed",
        reports_dir=tmp_path / "reports",
        run_id="v2_14_d_test",
        command="test command",
        source_v2_14_c_report_json=source_path,
        source_v2_14_c_pass_marker=source_marker,
        record_paths={"recommendations_jsonl": record},
    )

    assert report["overall_status"] == "PASS"
    assert report["checks"]["gate_json_written"] is True
    assert report["checks"]["suggestions_json_written"] is True
    assert report["checks"]["production_record_files_unchanged"] is True
    assert record.read_text(encoding="utf-8") == "existing\n"
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()


def test_v2_14_d_cli_like_acceptance_prints_no_secret_values(tmp_path: Path, capsys):
    source_path = tmp_path / "source.json"
    source_marker = tmp_path / "source.marker"
    source_path.write_text(json.dumps(_source_report(), ensure_ascii=False), encoding="utf-8")
    source_marker.write_text("source pass\n", encoding="utf-8")

    exit_code = validator.main(
        [
            "--output-root",
            str(tmp_path / "processed"),
            "--reports-dir",
            str(tmp_path / "reports"),
            "--run-id",
            "v2_14_d_cli",
            "--source-v2-14-c-report-json",
            str(source_path),
            "--source-v2-14-c-pass-marker",
            str(source_marker),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "PASS" in captured.out
    assert "allowed_count=1" in captured.out
    assert "allowed_symbols=00700.HK" in captured.out
    assert "token" not in captured.out.lower()
    assert "secret" not in captured.out.lower()
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()
