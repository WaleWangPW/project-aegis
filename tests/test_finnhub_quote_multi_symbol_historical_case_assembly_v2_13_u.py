from __future__ import annotations

import json
from pathlib import Path

from aegis.external_sources.finnhub_quote_multi_symbol_historical_case_assembly import (
    build_finnhub_quote_multi_symbol_historical_case_assembly_report,
    render_finnhub_quote_multi_symbol_historical_case_assembly_markdown,
)
import scripts.validate_v2_13_u_finnhub_quote_multi_symbol_historical_case_assembly as validator


def _source_report() -> dict:
    symbols = ["CRCL.US", "MSFT.US", "NVDA.US"]
    return {
        "overall_status": "PASS",
        "acceptance_target": "V2.13-T Finnhub Quote Multi-Symbol Sandbox Candidate Binding",
        "run_id": "unit_v2_13_t",
        "summary": {
            "binding_count": 3,
            "symbols": symbols,
            "social_sentiment_status": "blocked_plan_or_rate_limit",
        },
        "bindings": [_binding(symbol) for symbol in symbols],
    }


def _binding(symbol: str) -> dict:
    symbol_id = symbol.lower().replace(".", "_")
    return {
        "binding_id": f"bind_finnhub_quote_context_{symbol_id}_multi_symbol_sandbox_candidate",
        "binding_status": "bound_pending_historical_cases",
        "market": "US",
        "canonical_symbol": symbol,
        "provider": "finnhub",
        "context_id": f"finnhub_quote_context_{symbol_id}",
        "strategy_candidate": {
            "strategy_id": f"strategy_{symbol_id}_finnhub_multi_quote_context_probe",
            "name": f"{symbol} Finnhub multi-symbol quote context sandbox probe",
            "market": "US",
            "universe": f"{symbol} Finnhub verified quote context universe",
            "factor_family": "multi_factor",
            "entry_rule": "Use Finnhub quote context as research evidence only.",
            "exit_rule": "Exit after rolling window.",
            "exit_horizon_days": 5,
            "risk_controls": [
                "manual_execution_only",
                "historical_cases_required",
                "suggestion_gate_required",
            ],
            "pass_criteria": {
                "min_sample_count": 3,
                "min_win_rate": 0.5,
                "min_average_return": 0.0,
                "max_drawdown_floor": -0.12,
            },
            "source_research_refs": ["ctx", "hash"],
            "created_at": "2026-07-12T00:00:00+08:00",
        },
    }


def _payload_for_symbol(symbol: str) -> list[dict]:
    base = {"CRCL.US": 100.0, "MSFT.US": 200.0, "NVDA.US": 300.0}[symbol]
    return [
        {
            "date": f"2026-07-0{idx + 1}",
            "open": base + idx,
            "high": base + idx + 3,
            "low": base + idx - 1,
            "close": base + idx + (1 if idx % 2 == 0 else 2),
            "volume": 1000 + idx,
        }
        for idx in range(5)
    ]


def _fetch_json(url: str):
    if "CRCL.US" in url:
        return 200, _payload_for_symbol("CRCL.US")
    if "MSFT.US" in url:
        return 200, _payload_for_symbol("MSFT.US")
    if "NVDA.US" in url:
        return 200, _payload_for_symbol("NVDA.US")
    return 404, []


def test_v2_13_u_assembles_multi_symbol_historical_cases(tmp_path: Path):
    report = build_finnhub_quote_multi_symbol_historical_case_assembly_report(
        _source_report(),
        output_dir=tmp_path / "cache",
        run_id="unit",
        env={"AEGIS_EODHD_API_TOKEN": "unit-token"},
        fetch_json=_fetch_json,
        generated_at="2026-07-12T00:00:00+08:00",
    )
    text = json.dumps(report, ensure_ascii=False)

    assert report["overall_status"] == "PASS"
    assert report["summary"]["daily_bars_case_count"] == 3
    assert report["summary"]["historical_case_count"] == 12
    assert report["summary"]["symbols"] == ["CRCL.US", "MSFT.US", "NVDA.US"]
    assert report["summary"]["sandbox_evaluation_run"] is False
    assert report["summary"]["user_facing_suggestion_allowed"] is False
    assert report["checks"]["historical_cases_meet_candidate_minimum"] is True
    assert report["checks"]["all_artifacts_verified"] is True
    assert report["checks"]["all_cases_have_multi_symbol_quote_context_evidence"] is True
    assert "unit-token" not in text
    assert "api_token=" not in text
    assert "https://" not in text


def test_v2_13_u_fails_without_eodhd_env(tmp_path: Path):
    report = build_finnhub_quote_multi_symbol_historical_case_assembly_report(
        _source_report(),
        output_dir=tmp_path / "cache",
        run_id="unit",
        env={},
        fetch_json=_fetch_json,
    )

    assert report["overall_status"] == "FAIL"
    assert report["summary"]["historical_case_count"] == 0
    assert report["checks"]["all_fetch_results_pass"] is False
    assert {item["status"] for item in report["daily_bar_fetch_results"]} == {"blocked_missing_env"}


def test_v2_13_u_fails_if_source_not_pass(tmp_path: Path):
    source = _source_report()
    source["overall_status"] = "FAIL"

    report = build_finnhub_quote_multi_symbol_historical_case_assembly_report(
        source,
        output_dir=tmp_path / "cache",
        run_id="unit",
        env={"AEGIS_EODHD_API_TOKEN": "unit-token"},
        fetch_json=_fetch_json,
    )

    assert report["overall_status"] == "FAIL"
    assert report["checks"]["source_report_pass"] is False


def test_v2_13_u_markdown_states_boundaries(tmp_path: Path):
    report = build_finnhub_quote_multi_symbol_historical_case_assembly_report(
        _source_report(),
        output_dir=tmp_path / "cache",
        run_id="unit",
        env={"AEGIS_EODHD_API_TOKEN": "unit-token"},
        fetch_json=_fetch_json,
    )
    md = render_finnhub_quote_multi_symbol_historical_case_assembly_markdown(report)

    assert "Historical case assembly only" in md
    assert "Sandbox evaluation is not run" in md
    assert "No user-facing suggestion" in md


def test_v2_13_u_validator_writes_report_and_marker(tmp_path: Path):
    source_path = tmp_path / "source.json"
    marker_path = tmp_path / "source.marker"
    source_path.write_text(json.dumps(_source_report(), ensure_ascii=False), encoding="utf-8")
    marker_path.write_text("source pass\n", encoding="utf-8")

    report = validator.run_acceptance(
        output_root=tmp_path / "processed",
        reports_dir=tmp_path / "reports",
        run_id="v2_13_u_test",
        command="test command",
        source_v2_13_t_report_json=source_path,
        source_v2_13_t_pass_marker=marker_path,
        env={"AEGIS_EODHD_API_TOKEN": "unit-token"},
        fetch_json=_fetch_json,
    )

    assert report["overall_status"] == "PASS"
    assert report["checks"]["cases_jsonl_written"] is True
    assert report["checks"]["daily_bars_json_written"] is True
    assert report["checks"]["production_record_files_unchanged"] is True
    assert report["safety"]["no_broker_api"] is True
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()


def test_v2_13_u_cli_like_acceptance_writes_latest_report(tmp_path: Path):
    source_path = tmp_path / "source.json"
    marker_path = tmp_path / "source.marker"
    source_path.write_text(json.dumps(_source_report(), ensure_ascii=False), encoding="utf-8")
    marker_path.write_text("source pass\n", encoding="utf-8")

    report = validator.run_acceptance(
        output_root=tmp_path / "processed",
        reports_dir=tmp_path / "reports",
        run_id="v2_13_u_cli_like",
        source_v2_13_t_report_json=source_path,
        source_v2_13_t_pass_marker=marker_path,
        env={"AEGIS_EODHD_API_TOKEN": "unit-token"},
        fetch_json=_fetch_json,
    )

    assert report["overall_status"] == "PASS"
    assert (tmp_path / "reports" / validator.REPORT_JSON).exists()
