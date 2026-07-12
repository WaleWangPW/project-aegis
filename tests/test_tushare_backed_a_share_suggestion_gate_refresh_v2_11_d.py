from __future__ import annotations

import json
from pathlib import Path

from aegis.strategy.tushare_suggestion_gate import (
    build_tushare_a_share_suggestion_gate_report,
    build_tushare_a_share_suggestion_opportunities,
)
import scripts.validate_v2_11_d_tushare_backed_a_share_suggestion_gate_refresh as validator


def _source_report() -> dict:
    return {
        "overall_status": "PASS",
        "acceptance_target": "V2.11-C Tushare A-Share Historical Sandbox Live Data Refresh",
        "live_data_source": {"provider": "tushare", "market": "A"},
        "production_records_written": False,
        "dashboard_contract_changed": False,
        "summary": {
            "candidate_count": 2,
            "historical_case_count": 8,
            "strategy_pass_count": 0,
            "strategy_fail_count": 2,
            "passing_strategies": [],
            "failing_strategies": [
                "strategy_a_low_vol_dividend_defensive",
                "strategy_a_value_quality_multifactor",
            ],
        },
        "candidates": [
            {
                "strategy_id": "strategy_a_low_vol_dividend_defensive",
                "name": "A-share low-volatility dividend defensive sandbox candidate",
                "market": "A",
                "risk_controls": ["liquidity_filter", "max_drawdown_floor", "risk_veto"],
            },
            {
                "strategy_id": "strategy_a_value_quality_multifactor",
                "name": "A-share value quality multi-factor sandbox candidate",
                "market": "A",
                "risk_controls": ["liquidity_filter", "financial_quality_check", "risk_veto"],
            },
        ],
        "historical_cases": [
            {"strategy_id": "strategy_a_low_vol_dividend_defensive", "symbol": "600000.SH"},
            {"strategy_id": "strategy_a_low_vol_dividend_defensive", "symbol": "601318.SH"},
            {"strategy_id": "strategy_a_value_quality_multifactor", "symbol": "600036.SH"},
            {"strategy_id": "strategy_a_value_quality_multifactor", "symbol": "000858.SZ"},
        ],
        "results": [
            {
                "strategy_id": "strategy_a_low_vol_dividend_defensive",
                "status": "FAIL",
                "metrics": {
                    "sample_count": 4,
                    "win_rate": 0.25,
                    "average_return": -0.0439,
                    "max_drawdown": -0.1038,
                    "failed_reasons": [
                        "win_rate_below_threshold",
                        "average_return_below_threshold",
                        "max_drawdown_breached",
                    ],
                },
            },
            {
                "strategy_id": "strategy_a_value_quality_multifactor",
                "status": "FAIL",
                "metrics": {
                    "sample_count": 4,
                    "win_rate": 0.75,
                    "average_return": -0.0041,
                    "max_drawdown": -0.1045,
                    "failed_reasons": [
                        "average_return_below_threshold",
                        "max_drawdown_breached",
                    ],
                },
            },
        ],
    }


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def test_v2_11_d_builds_opportunities_from_tushare_failed_strategies():
    opportunities = build_tushare_a_share_suggestion_opportunities(
        _source_report(),
        evidence_refs=["source-report.json", "pass.marker"],
    )

    assert len(opportunities) == 2
    assert all(item.market == "A" for item in opportunities)
    assert all(item.evidence_refs for item in opportunities)
    assert all("failed_reasons=" in " ".join(item.reasons) for item in opportunities)


def test_v2_11_d_all_failed_tushare_strategies_are_blocked_but_report_passes():
    report = build_tushare_a_share_suggestion_gate_report(
        _source_report(),
        run_id="v2_11_d_unit",
        evidence_refs=["source-report.json", "pass.marker"],
        command="unit test",
        generated_at="2026-07-11T00:00:00+08:00",
    )

    assert report["overall_status"] == "PASS"
    assert report["summary"]["allowed_count"] == 0
    assert report["summary"]["blocked_count"] == 2
    assert report["checks"]["no_allowed_suggestions"] is True
    assert report["checks"]["all_source_failed_strategies_blocked"] is True
    assert all(item["action"] == "blocked" for item in report["suggestions"])
    assert all("strategy_sandbox_not_passed" in item["blocked_by"] for item in report["suggestions"])
    assert report["safety"]["no_order_placement"] is True


def test_v2_11_d_fails_if_source_has_passing_strategy_but_gate_blocks_all():
    source = _source_report()
    source["summary"]["strategy_pass_count"] = 1
    source["summary"]["passing_strategies"] = ["strategy_a_low_vol_dividend_defensive"]
    source["summary"]["failing_strategies"] = ["strategy_a_value_quality_multifactor"]
    source["results"][0]["status"] = "PASS"
    source["results"][0]["metrics"]["failed_reasons"] = []

    report = build_tushare_a_share_suggestion_gate_report(
        source,
        run_id="v2_11_d_unit_fail",
        evidence_refs=["source-report.json"],
    )

    assert report["overall_status"] == "FAIL"
    assert report["checks"]["source_has_zero_strategy_pass"] is False


def test_v2_11_d_validator_writes_reports_marker_and_hashes(tmp_path: Path):
    source_json = tmp_path / "v2_11_c.json"
    marker = tmp_path / "v2_11_c.marker"
    _write_json(source_json, _source_report())
    marker.write_text("exit_code=0\n", encoding="utf-8")

    report = validator.run_acceptance(
        output_root=tmp_path / "processed",
        reports_dir=tmp_path / "reports",
        run_id="v2_11_d_test",
        command="test command",
        source_v2_11_c_report_json=source_json,
        source_v2_11_c_pass_marker=marker,
    )

    assert report["overall_status"] == "PASS"
    assert report["summary"]["allowed_count"] == 0
    assert report["summary"]["blocked_count"] == 2
    assert report["checks"]["suggestions_json_written"] is True
    assert report["hashes"]["suggestions_json"]
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()


def test_v2_11_d_cli_exits_zero_and_prints_no_secret_values(tmp_path: Path, capsys):
    source_json = tmp_path / "v2_11_c.json"
    marker = tmp_path / "v2_11_c.marker"
    _write_json(source_json, _source_report())
    marker.write_text("exit_code=0\n", encoding="utf-8")

    exit_code = validator.main(
        [
            "--output-root",
            str(tmp_path / "processed"),
            "--reports-dir",
            str(tmp_path / "reports"),
            "--run-id",
            "v2_11_d_cli",
            "--source-v2-11-c-report-json",
            str(source_json),
            "--source-v2-11-c-pass-marker",
            str(marker),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "PASS" in captured.out
    assert "token" not in captured.out.lower()
    assert "secret" not in captured.out.lower()
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()
