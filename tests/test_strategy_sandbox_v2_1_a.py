from __future__ import annotations

import json
from pathlib import Path

import scripts.validate_v2_1_a_historical_strategy_sandbox as validator
from aegis.strategy.sandbox import build_strategy_sandbox_report, evaluate_strategy_candidate


def test_strategy_sandbox_produces_pass_and_fail_with_metrics():
    candidates = validator._fixture_candidates()
    cases = validator._fixture_cases()

    results = [evaluate_strategy_candidate(candidate, cases) for candidate in candidates]
    by_id = {result.strategy_id: result for result in results}

    passed = by_id["low_volatility_dividend_a"]
    failed = by_id["raw_momentum_us"]

    assert passed.status == "PASS"
    assert passed.metrics.eligible_case_count == 4
    assert passed.metrics.win_rate == 0.75
    assert passed.safety["simulation_only"] is True
    assert passed.safety["no_broker_api"] is True

    assert failed.status == "FAIL"
    assert "max_drawdown_breached" in failed.metrics.failed_reasons
    assert failed.metrics.risk_flag_counts["drawdown_breach"] == 3


def test_strategy_sandbox_report_keeps_suggestions_gated():
    report = build_strategy_sandbox_report(
        validator._fixture_candidates(),
        validator._fixture_cases(),
        run_id="v2_1_a_unit",
        command="unit test",
        historical_cache_file_count=3,
    )

    assert report["overall_status"] == "PASS"
    assert report["summary"]["pass_count"] == 1
    assert report["summary"]["fail_count"] == 1
    assert report["safety"]["suggestion_gate_still_required"] is True
    assert report["production_records_written"] is False
    assert report["dashboard_contract_changed"] is False


def test_v2_1_a_acceptance_writes_marker_hashes_and_reports(tmp_path: Path):
    report = validator.run_acceptance(
        output_root=tmp_path / "processed",
        reports_dir=tmp_path / "reports",
        run_id="v2_1_a_test",
        command="test command",
    )

    assert report["overall_status"] == "PASS"
    assert report["checks"]["at_least_one_strategy_passed"] is True
    assert report["checks"]["at_least_one_strategy_failed"] is True
    assert report["checks"]["metrics_present"] is True
    assert report["checks"]["no_real_trade_or_broker"] is True
    assert report["checks"]["no_strategy_auto_mutation"] is True
    assert report["production_records_written"] is False
    assert report["hashes"]["candidates_json"]
    assert report["hashes"]["historical_cases_jsonl"]
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()
    payload = json.loads((tmp_path / "reports" / validator.REPORT_JSON).read_text(encoding="utf-8"))
    assert payload["summary"]["passing_strategies"] == ["low_volatility_dividend_a"]


def test_v2_1_a_cli_exits_zero_and_prints_no_secrets(tmp_path: Path, capsys):
    exit_code = validator.main(
        [
            "--output-root",
            str(tmp_path / "processed"),
            "--reports-dir",
            str(tmp_path / "reports"),
            "--run-id",
            "v2_1_a_cli",
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "PASS" in captured.out
    assert "token" not in captured.out.lower()
    assert "secret" not in captured.out.lower()
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()
