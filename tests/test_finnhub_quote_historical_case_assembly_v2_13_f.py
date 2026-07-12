from __future__ import annotations

import hashlib
import json
from pathlib import Path

from aegis.external_sources.finnhub_quote_historical_case_assembly import (
    build_finnhub_quote_historical_case_assembly_report,
    render_finnhub_quote_historical_case_assembly_markdown,
)
import scripts.validate_v2_13_f_finnhub_quote_historical_case_assembly as validator


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_csv(path: Path) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "date,open,high,low,close,volume\n"
        "2026-07-01,100,103,99,100,1000\n"
        "2026-07-02,101,104,100,103,1200\n"
        "2026-07-03,103,106,102,105,1300\n"
        "2026-07-04,105,107,101,102,1400\n"
        "2026-07-05,102,108,101,107,1500\n",
        encoding="utf-8",
    )
    return str(path)


def _binding_report() -> dict:
    return {
        "overall_status": "PASS",
        "acceptance_target": "V2.13-E Finnhub Quote Context To Sandbox Candidate Binding",
        "run_id": "unit_v2_13_e",
        "summary": {
            "binding_count": 1,
            "social_sentiment_status": "blocked_plan_or_rate_limit",
        },
        "bindings": [
            {
                "binding_id": "bind_finnhub_quote_context_us_aapl_finnhub_quote_sandbox_candidate",
                "binding_status": "bound_pending_historical_cases",
                "market": "US",
                "canonical_symbol": "AAPL.US",
                "context_id": "finnhub_quote_context_us_aapl_finnhub_quote",
                "strategy_candidate": {
                    "strategy_id": "strategy_aapl_us_finnhub_quote_context_probe",
                    "name": "AAPL.US Finnhub quote context sandbox probe",
                    "market": "US",
                    "universe": "AAPL.US Finnhub verified quote context universe",
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
        ],
    }


def _cache_report(tmp_path: Path) -> dict:
    csv_path = Path(_write_csv(tmp_path / "aapl.csv"))
    return {
        "overall_status": "PASS",
        "acceptance_target": "V2.12-C H-US Historical Cache Readiness Dry Run",
        "run_id": "unit_v2_12_c",
        "summary": {"us_cache_ready": True},
        "results": [
            {
                "case_id": "us_aapl_eodhd_daily_bars",
                "provider": "eodhd",
                "market": "US",
                "canonical_symbol": "AAPL.US",
                "data_type": "daily_bars",
                "normalized_csv": str(csv_path),
                "normalized_csv_sha256": _sha256(csv_path),
                "status": "pass",
            }
        ],
    }


def test_v2_13_f_assembles_rolling_historical_cases(tmp_path: Path):
    report = build_finnhub_quote_historical_case_assembly_report(
        binding_report=_binding_report(),
        cache_readiness_report=_cache_report(tmp_path),
        run_id="unit",
        generated_at="2026-07-12T00:00:00+08:00",
    )
    text = json.dumps(report, ensure_ascii=False)

    assert report["overall_status"] == "PASS"
    assert report["network_used"] is False
    assert report["summary"]["historical_case_count"] == 4
    assert report["summary"]["sandbox_evaluation_run"] is False
    assert report["summary"]["user_facing_suggestion_allowed"] is False
    assert report["checks"]["historical_cases_meet_candidate_minimum"] is True
    assert report["checks"]["sandbox_evaluation_not_run"] is True
    assert report["checks"]["all_cases_have_quote_context_evidence"] is True
    case = report["historical_cases"][0]
    assert case["strategy_id"] == "strategy_aapl_us_finnhub_quote_context_probe"
    assert case["symbol"] == "AAPL.US"
    assert case["evidence_ref"].startswith("v2_13_f_quote_context_case:")
    assert "token=" not in text
    assert "https://" not in text


def test_v2_13_f_fails_if_cache_hash_mismatch(tmp_path: Path):
    cache = _cache_report(tmp_path)
    cache["results"][0]["normalized_csv_sha256"] = "bad"

    report = build_finnhub_quote_historical_case_assembly_report(
        binding_report=_binding_report(),
        cache_readiness_report=cache,
        run_id="unit",
    )

    assert report["overall_status"] == "FAIL"
    assert report["checks"]["all_artifacts_verified"] is False
    assert report["summary"]["historical_case_count"] == 0


def test_v2_13_f_fails_if_binding_source_not_pass(tmp_path: Path):
    binding = _binding_report()
    binding["overall_status"] = "FAIL"

    report = build_finnhub_quote_historical_case_assembly_report(
        binding_report=binding,
        cache_readiness_report=_cache_report(tmp_path),
        run_id="unit",
    )

    assert report["overall_status"] == "FAIL"
    assert report["checks"]["source_binding_report_pass"] is False


def test_v2_13_f_markdown_states_assembly_only(tmp_path: Path):
    report = build_finnhub_quote_historical_case_assembly_report(
        binding_report=_binding_report(),
        cache_readiness_report=_cache_report(tmp_path),
        run_id="unit",
    )
    md = render_finnhub_quote_historical_case_assembly_markdown(report)

    assert "Historical case assembly only" in md
    assert "Sandbox evaluation is not run" in md
    assert "No user-facing suggestion" in md


def test_v2_13_f_validator_writes_report_and_marker(tmp_path: Path):
    binding_path = tmp_path / "binding.json"
    cache_path = tmp_path / "cache.json"
    binding_path.write_text(json.dumps(_binding_report(), ensure_ascii=False), encoding="utf-8")
    cache_path.write_text(json.dumps(_cache_report(tmp_path), ensure_ascii=False), encoding="utf-8")

    report = validator.run_acceptance(
        output_root=tmp_path / "processed",
        reports_dir=tmp_path / "reports",
        run_id="v2_13_f_test",
        command="test command",
        source_binding_report_json=binding_path,
        source_cache_report_json=cache_path,
    )

    assert report["overall_status"] == "PASS"
    assert report["checks"]["cases_jsonl_written"] is True
    assert report["checks"]["candidates_json_written"] is True
    assert report["safety"]["no_broker_api"] is True
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()


def test_v2_13_f_cli_like_acceptance_writes_latest_report(tmp_path: Path):
    binding_path = tmp_path / "binding.json"
    cache_path = tmp_path / "cache.json"
    binding_path.write_text(json.dumps(_binding_report(), ensure_ascii=False), encoding="utf-8")
    cache_path.write_text(json.dumps(_cache_report(tmp_path), ensure_ascii=False), encoding="utf-8")

    report = validator.run_acceptance(
        output_root=tmp_path / "processed",
        reports_dir=tmp_path / "reports",
        run_id="v2_13_f_cli_like",
        source_binding_report_json=binding_path,
        source_cache_report_json=cache_path,
    )

    assert report["overall_status"] == "PASS"
    assert (tmp_path / "reports" / validator.REPORT_JSON).exists()
