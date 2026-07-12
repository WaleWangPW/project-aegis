from __future__ import annotations

import json
from pathlib import Path

from aegis.external_sources.finnhub_quote_suggestion_gate import (
    ACCEPTANCE_TARGET,
    build_finnhub_quote_suggestion_gate_report,
    build_finnhub_quote_suggestion_opportunities,
)
import scripts.validate_v2_13_h_finnhub_quote_suggestion_gate as validator


def _source_report() -> dict:
    return {
        "overall_status": "PASS",
        "acceptance_target": "V2.13-G Finnhub Quote Context Sandbox Evaluation",
        "network_used": False,
        "production_records_written": False,
        "dashboard_contract_changed": False,
        "summary": {
            "candidate_count": 1,
            "historical_case_count": 2,
            "strategy_pass_count": 1,
            "strategy_fail_count": 0,
            "passing_strategies": ["strategy_aapl_us_finnhub_quote_context_probe"],
            "failing_strategies": [],
            "symbols": ["AAPL.US"],
            "markets": ["US"],
            "sandbox_evaluation_run": True,
            "suggestion_gate_required": True,
            "user_facing_suggestion_allowed": False,
            "social_sentiment_status": "blocked_plan_or_rate_limit",
            "next_stage": "V2.13-H Finnhub Quote Sandbox Evidence To Suggestion Gate Draft",
        },
        "safety": {
            "sandbox_evaluation_only": True,
            "suggestion_gate_required": True,
            "user_facing_suggestion_allowed": False,
            "social_sentiment_not_enabled": True,
            "no_real_trade": True,
            "no_broker_api": True,
            "no_trading_webhook": True,
            "no_order_placement": True,
            "no_position_size": True,
        },
        "candidates": [
            {
                "strategy_id": "strategy_aapl_us_finnhub_quote_context_probe",
                "name": "AAPL.US Finnhub quote context sandbox probe",
                "market": "US",
                "risk_controls": [
                    "manual_execution_only",
                    "historical_cases_required",
                    "suggestion_gate_required",
                    "single_quote_snapshot_not_strategy_evidence",
                ],
            }
        ],
        "historical_cases": [
            {
                "strategy_id": "strategy_aapl_us_finnhub_quote_context_probe",
                "symbol": "AAPL.US",
                "evidence_ref": "v2_13_f_quote_context_case:binding:context:eodhd:hash",
            },
            {
                "strategy_id": "strategy_aapl_us_finnhub_quote_context_probe",
                "symbol": "AAPL.US",
                "evidence_ref": "v2_13_f_quote_context_case:binding:context:twelve:hash",
            },
        ],
        "results": [
            {
                "strategy_id": "strategy_aapl_us_finnhub_quote_context_probe",
                "status": "PASS",
                "metrics": {
                    "sample_count": 8,
                    "win_rate": 0.625,
                    "average_return": 0.009053844504582794,
                    "max_drawdown": -0.04843987946732331,
                    "failed_reasons": [],
                },
            }
        ],
    }


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def test_v2_13_h_builds_finnhub_quote_opportunity_from_sandbox_pass():
    opportunities = build_finnhub_quote_suggestion_opportunities(
        _source_report(),
        evidence_refs=["source-report.json", "pass.marker"],
    )

    assert len(opportunities) == 1
    opportunity = opportunities[0]
    assert opportunity.symbol == "AAPL.US"
    assert opportunity.market == "US"
    assert opportunity.evidence_refs
    assert any(ref.startswith("v2_13_f_quote_context_case:") for ref in opportunity.evidence_refs)
    assert "blocked_plan_or_rate_limit" in " ".join(opportunity.reasons)
    assert "social sentiment" in " ".join(opportunity.risk_warnings).lower()


def test_v2_13_h_routes_passing_quote_context_to_simulation_only_draft():
    report = build_finnhub_quote_suggestion_gate_report(
        _source_report(),
        run_id="v2_13_h_unit",
        evidence_refs=["source-report.json", "pass.marker"],
        command="unit test",
        generated_at="2026-07-12T02:20:00+08:00",
    )

    assert report["overall_status"] == "PASS"
    assert report["acceptance_target"] == ACCEPTANCE_TARGET
    assert report["summary"]["allowed_count"] == 1
    assert report["summary"]["blocked_count"] == 0
    assert report["summary"]["social_sentiment_status"] == "blocked_plan_or_rate_limit"
    assert report["checks"]["quote_context_case_evidence_refs_present"] is True
    assert report["checks"]["social_sentiment_blocked_visible"] is True
    assert report["checks"]["all_allowed_are_paper_entry_candidates"] is True
    assert report["suggestions"][0]["action"] == "paper_entry_candidate"
    assert report["suggestions"][0]["simulation_only"] is True
    assert report["suggestions"][0]["user_must_execute_externally"] is True
    assert report["safety"]["no_order_placement"] is True
    assert report["safety"]["social_sentiment_not_enabled"] is True


def test_v2_13_h_fails_if_source_already_allowed_user_facing_suggestions():
    source = _source_report()
    source["summary"]["user_facing_suggestion_allowed"] = True

    report = build_finnhub_quote_suggestion_gate_report(
        source,
        run_id="v2_13_h_unit_fail",
        evidence_refs=["source-report.json"],
    )

    assert report["overall_status"] == "FAIL"
    assert report["checks"]["source_user_facing_suggestion_was_blocked"] is False


def test_v2_13_h_fails_if_social_sentiment_is_not_blocked():
    source = _source_report()
    source["summary"]["social_sentiment_status"] = "pass"

    report = build_finnhub_quote_suggestion_gate_report(
        source,
        run_id="v2_13_h_social_fail",
        evidence_refs=["source-report.json"],
    )

    assert report["overall_status"] == "FAIL"
    assert report["checks"]["source_social_sentiment_still_blocked"] is False


def test_v2_13_h_validator_writes_reports_marker_and_hashes(tmp_path: Path):
    source_json = tmp_path / "v2_13_g.json"
    marker = tmp_path / "v2_13_g.marker"
    _write_json(source_json, _source_report())
    marker.write_text("exit_code=0\n", encoding="utf-8")

    report = validator.run_acceptance(
        output_root=tmp_path / "processed",
        reports_dir=tmp_path / "reports",
        run_id="v2_13_h_test",
        command="test command",
        source_v2_13_g_report_json=source_json,
        source_v2_13_g_pass_marker=marker,
    )

    assert report["overall_status"] == "PASS"
    assert report["summary"]["allowed_count"] == 1
    assert report["checks"]["suggestions_json_written"] is True
    assert report["hashes"]["suggestions_json"]
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()


def test_v2_13_h_cli_exits_zero_and_prints_no_secret_values(tmp_path: Path, capsys):
    source_json = tmp_path / "v2_13_g.json"
    marker = tmp_path / "v2_13_g.marker"
    _write_json(source_json, _source_report())
    marker.write_text("exit_code=0\n", encoding="utf-8")

    exit_code = validator.main(
        [
            "--output-root",
            str(tmp_path / "processed"),
            "--reports-dir",
            str(tmp_path / "reports"),
            "--run-id",
            "v2_13_h_cli",
            "--source-v2-13-g-report-json",
            str(source_json),
            "--source-v2-13-g-pass-marker",
            str(marker),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "PASS" in captured.out
    assert "token" not in captured.out.lower()
    assert "secret" not in captured.out.lower()
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()
