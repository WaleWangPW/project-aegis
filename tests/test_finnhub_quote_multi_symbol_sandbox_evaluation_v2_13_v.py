from __future__ import annotations

import json
from pathlib import Path

from aegis.external_sources.finnhub_quote_multi_symbol_sandbox_evaluation import (
    build_finnhub_quote_multi_symbol_sandbox_evaluation_report,
    render_finnhub_quote_multi_symbol_sandbox_evaluation_markdown,
)
import scripts.validate_v2_13_v_finnhub_quote_multi_symbol_sandbox_evaluation as validator


def _candidate(symbol: str) -> dict:
    symbol_id = symbol.lower().replace(".", "_")
    return {
        "strategy_id": f"strategy_{symbol_id}_finnhub_multi_quote_context_probe",
        "name": f"{symbol} Finnhub multi-symbol quote context sandbox probe",
        "market": "US",
        "universe": f"{symbol} Finnhub verified quote context universe",
        "factor_family": "multi_factor",
        "entry_rule": "Use Finnhub quote context as research evidence only.",
        "exit_rule": "Exit after rolling window.",
        "exit_horizon_days": 5,
        "risk_controls": ["manual_execution_only", "suggestion_gate_required"],
        "pass_criteria": {
            "min_sample_count": 3,
            "min_win_rate": 0.5,
            "min_average_return": 0.0,
            "max_drawdown_floor": -0.12,
        },
        "source_research_refs": ["ctx", "hash"],
        "created_at": "2026-07-12T00:00:00+08:00",
    }


def _source_report(*, all_fail: bool = False) -> dict:
    symbols = ["CRCL.US", "MSFT.US", "NVDA.US"]
    candidates = [_candidate(symbol) for symbol in symbols]
    cases = []
    for candidate in candidates:
        returns = [-0.03, -0.02, 0.01, -0.01] if all_fail else [0.04, 0.02, -0.01, 0.03]
        for idx, ret in enumerate(returns, start=1):
            entry = 100.0
            cases.append(
                {
                    "case_id": f"{candidate['strategy_id']}_case_{idx}",
                    "strategy_id": candidate["strategy_id"],
                    "date": f"2026-07-0{idx}",
                    "symbol": candidate["strategy_id"].split("_")[1].upper() + ".US",
                    "market": "US",
                    "eligible": True,
                    "entry_price": entry,
                    "exit_price": entry * (1 + ret),
                    "max_drawdown": -0.03,
                    "risk_flags": [],
                    "factor_values": {"actual_return": ret},
                    "evidence_ref": "v2_13_u_multi_symbol_case:binding:context:symbol:hash",
                }
            )
    return {
        "overall_status": "PASS",
        "acceptance_target": "V2.13-U Finnhub Quote Multi-Symbol Historical Case Assembly",
        "run_id": "unit_v2_13_u",
        "summary": {
            "candidate_packet_count": len(candidates),
            "historical_case_count": len(cases),
            "sandbox_evaluation_run": False,
            "social_sentiment_status": "blocked_plan_or_rate_limit",
        },
        "candidate_packets": [{"strategy_candidate": candidate} for candidate in candidates],
        "historical_cases": cases,
    }


def test_v2_13_v_evaluates_multi_symbol_cases_with_passes():
    report = build_finnhub_quote_multi_symbol_sandbox_evaluation_report(
        source_report=_source_report(),
        run_id="unit",
        generated_at="2026-07-12T00:00:00+08:00",
    )
    text = json.dumps(report, ensure_ascii=False)

    assert report["overall_status"] == "PASS"
    assert report["network_used"] is False
    assert report["summary"]["candidate_count"] == 3
    assert report["summary"]["historical_case_count"] == 12
    assert report["summary"]["strategy_pass_count"] == 3
    assert report["summary"]["suggestion_gate_ready"] is True
    assert report["summary"]["user_facing_suggestion_allowed"] is False
    assert report["checks"]["suggestion_gate_not_run"] is True
    assert "token=" not in text
    assert "https://" not in text


def test_v2_13_v_passes_stage_but_blocks_all_failed_results():
    report = build_finnhub_quote_multi_symbol_sandbox_evaluation_report(
        source_report=_source_report(all_fail=True),
        run_id="unit",
    )

    assert report["overall_status"] == "PASS"
    assert report["summary"]["strategy_pass_count"] == 0
    assert report["summary"]["strategy_fail_count"] == 3
    assert report["summary"]["suggestion_gate_ready"] is False
    assert report["summary"]["user_facing_suggestion_allowed"] is False
    assert report["checks"]["failed_results_not_promoted_to_suggestions"] is True


def test_v2_13_v_fails_if_source_not_pass():
    source = _source_report()
    source["overall_status"] = "FAIL"

    report = build_finnhub_quote_multi_symbol_sandbox_evaluation_report(source_report=source, run_id="unit")

    assert report["overall_status"] == "FAIL"
    assert report["checks"]["source_report_pass"] is False


def test_v2_13_v_fails_if_no_historical_cases():
    source = _source_report()
    source["historical_cases"] = []
    source["summary"]["historical_case_count"] = 0

    report = build_finnhub_quote_multi_symbol_sandbox_evaluation_report(source_report=source, run_id="unit")

    assert report["overall_status"] == "FAIL"
    assert report["checks"]["historical_cases_present"] is False


def test_v2_13_v_markdown_states_no_suggestion_boundary():
    report = build_finnhub_quote_multi_symbol_sandbox_evaluation_report(source_report=_source_report(), run_id="unit")
    md = render_finnhub_quote_multi_symbol_sandbox_evaluation_markdown(report)

    assert "Sandbox evaluation only" in md
    assert "Failed sandbox results are not promoted" in md
    assert "No user-facing suggestion" in md


def test_v2_13_v_validator_writes_report_and_marker(tmp_path: Path):
    source_path = tmp_path / "source.json"
    marker_path = tmp_path / "source.marker"
    source_path.write_text(json.dumps(_source_report(), ensure_ascii=False), encoding="utf-8")
    marker_path.write_text("source pass\n", encoding="utf-8")

    report = validator.run_acceptance(
        output_root=tmp_path / "processed",
        reports_dir=tmp_path / "reports",
        run_id="v2_13_v_test",
        command="test command",
        source_v2_13_u_report_json=source_path,
        source_v2_13_u_pass_marker=marker_path,
    )

    assert report["overall_status"] == "PASS"
    assert report["checks"]["sandbox_json_written"] is True
    assert report["checks"]["results_json_written"] is True
    assert report["checks"]["production_record_files_unchanged"] is True
    assert report["safety"]["no_broker_api"] is True
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()


def test_v2_13_v_cli_like_acceptance_writes_latest_report(tmp_path: Path):
    source_path = tmp_path / "source.json"
    marker_path = tmp_path / "source.marker"
    source_path.write_text(json.dumps(_source_report(all_fail=True), ensure_ascii=False), encoding="utf-8")
    marker_path.write_text("source pass\n", encoding="utf-8")

    report = validator.run_acceptance(
        output_root=tmp_path / "processed",
        reports_dir=tmp_path / "reports",
        run_id="v2_13_v_cli_like",
        source_v2_13_u_report_json=source_path,
        source_v2_13_u_pass_marker=marker_path,
    )

    assert report["overall_status"] == "PASS"
    assert report["summary"]["strategy_pass_count"] == 0
    assert (tmp_path / "reports" / validator.REPORT_JSON).exists()
