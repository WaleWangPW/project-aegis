from __future__ import annotations

import json
from pathlib import Path

from aegis.external_sources.finnhub_quote_multi_symbol_result_brief import (
    build_finnhub_quote_multi_symbol_result_brief,
    render_finnhub_quote_multi_symbol_result_brief_markdown,
)
import scripts.validate_v2_13_w_finnhub_quote_multi_symbol_result_brief as validator


def _result(strategy_id: str, *, reasons: list[str]) -> dict:
    return {
        "strategy_id": strategy_id,
        "status": "FAIL",
        "metrics": {
            "strategy_id": strategy_id,
            "sample_count": 27,
            "eligible_case_count": 27,
            "win_rate": 0.37,
            "average_return": -0.01,
            "max_drawdown": -0.17,
            "turnover_proxy": 1.0,
            "exposure_count": 1,
            "risk_flag_counts": {},
            "failed_reasons": reasons,
        },
        "safety": {"simulation_only": True},
        "notes": [],
    }


def _source_report() -> dict:
    results = [
        _result(
            "strategy_crcl_us_finnhub_multi_quote_context_probe",
            reasons=["win_rate_below_threshold", "average_return_below_threshold", "max_drawdown_breached"],
        ),
        _result(
            "strategy_msft_us_finnhub_multi_quote_context_probe",
            reasons=["win_rate_below_threshold", "average_return_below_threshold"],
        ),
        _result(
            "strategy_nvda_us_finnhub_multi_quote_context_probe",
            reasons=["win_rate_below_threshold", "average_return_below_threshold"],
        ),
    ]
    cases = []
    for symbol, strategy_id in [
        ("CRCL.US", "strategy_crcl_us_finnhub_multi_quote_context_probe"),
        ("MSFT.US", "strategy_msft_us_finnhub_multi_quote_context_probe"),
        ("NVDA.US", "strategy_nvda_us_finnhub_multi_quote_context_probe"),
    ]:
        cases.append(
            {
                "case_id": f"{symbol}_case",
                "strategy_id": strategy_id,
                "date": "2026-07-01",
                "symbol": symbol,
                "market": "US",
                "entry_price": 100.0,
                "exit_price": 99.0,
                "max_drawdown": -0.05,
                "risk_flags": [],
                "factor_values": {"actual_return": -0.01},
                "evidence_ref": "v2_13_u_multi_symbol_case:binding:context:symbol:hash",
            }
        )
    return {
        "overall_status": "PASS",
        "acceptance_target": "V2.13-V Finnhub Quote Multi-Symbol Sandbox Evaluation",
        "run_id": "unit_v2_13_v",
        "network_used": False,
        "production_records_written": False,
        "production_cache_mutated": False,
        "production_provider_config_mutated": False,
        "dashboard_contract_changed": False,
        "summary": {
            "strategy_pass_count": 0,
            "strategy_fail_count": 3,
            "sandbox_evaluation_run": True,
            "suggestion_gate_ready": False,
            "user_facing_suggestion_allowed": False,
            "blocked_symbols": ["CRCL.US", "MSFT.US", "NVDA.US"],
        },
        "results": results,
        "historical_cases": cases,
    }


def test_v2_13_w_builds_blocked_result_brief():
    brief = build_finnhub_quote_multi_symbol_result_brief(
        _source_report(),
        run_id="unit",
        generated_at="2026-07-12T00:00:00+08:00",
    )
    text = json.dumps(brief, ensure_ascii=False)

    assert brief["overall_status"] == "PASS"
    assert brief["summary"]["blocked_item_count"] == 3
    assert brief["summary"]["passed_item_count"] == 0
    assert brief["summary"]["blocked_symbols"] == ["CRCL.US", "MSFT.US", "NVDA.US"]
    assert brief["summary"]["suggestion_gate_ready"] is False
    assert brief["summary"]["user_facing_suggestion_allowed"] is False
    assert brief["checks"]["all_items_forbid_suggestion_gate"] is True
    assert brief["checks"]["no_passed_results_promoted"] is True
    assert "不得进入 Suggestion Gate" in text
    assert "token=" not in text
    assert "https://" not in text


def test_v2_13_w_markdown_is_user_readable_and_not_a_suggestion():
    brief = build_finnhub_quote_multi_symbol_result_brief(_source_report(), run_id="unit")
    md = render_finnhub_quote_multi_symbol_result_brief_markdown(brief)

    assert "Project Aegis 多股票沙盘阻断简报" in md
    assert "CRCL.US" in md
    assert "MSFT.US" in md
    assert "NVDA.US" in md
    assert "这是阻断简报，不是建议" in md
    assert "不进入 Suggestion Gate" in md
    assert "不含仓位数量" in md
    assert "不下单" in md


def test_v2_13_w_fails_if_source_has_passed_strategy():
    source = _source_report()
    source["summary"]["strategy_pass_count"] = 1
    source["summary"]["suggestion_gate_ready"] = True

    brief = build_finnhub_quote_multi_symbol_result_brief(source, run_id="unit")

    assert brief["overall_status"] == "FAIL"
    assert brief["checks"]["source_has_no_passed_strategies"] is False
    assert brief["checks"]["source_suggestion_gate_not_ready"] is False


def test_v2_13_w_fails_if_source_not_sandbox_evaluation():
    source = _source_report()
    source["acceptance_target"] = "wrong"

    brief = build_finnhub_quote_multi_symbol_result_brief(source, run_id="unit")

    assert brief["overall_status"] == "FAIL"
    assert brief["checks"]["source_acceptance_target_correct"] is False


def test_v2_13_w_validator_writes_brief_and_marker(tmp_path: Path):
    source_path = tmp_path / "source.json"
    marker_path = tmp_path / "source.marker"
    source_path.write_text(json.dumps(_source_report(), ensure_ascii=False), encoding="utf-8")
    marker_path.write_text("source pass\n", encoding="utf-8")
    record = tmp_path / "records" / "recommendations.jsonl"
    record.parent.mkdir()
    record.write_text("existing\n", encoding="utf-8")

    report = validator.run_acceptance(
        output_root=tmp_path / "processed",
        reports_dir=tmp_path / "reports",
        run_id="v2_13_w_test",
        command="test command",
        source_v2_13_v_report_json=source_path,
        source_v2_13_v_pass_marker=marker_path,
        record_paths={"recommendations_jsonl": record},
    )

    assert report["overall_status"] == "PASS"
    assert report["checks"]["brief_json_written"] is True
    assert report["checks"]["brief_md_written"] is True
    assert report["checks"]["production_record_files_unchanged"] is True
    assert report["safety"]["not_a_suggestion"] is True
    assert record.read_text(encoding="utf-8") == "existing\n"
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()


def test_v2_13_w_cli_like_acceptance_prints_no_secret_values(tmp_path: Path, capsys):
    source_path = tmp_path / "source.json"
    marker_path = tmp_path / "source.marker"
    source_path.write_text(json.dumps(_source_report(), ensure_ascii=False), encoding="utf-8")
    marker_path.write_text("source pass\n", encoding="utf-8")

    exit_code = validator.main(
        [
            "--output-root",
            str(tmp_path / "processed"),
            "--reports-dir",
            str(tmp_path / "reports"),
            "--run-id",
            "v2_13_w_cli",
            "--source-v2-13-v-report-json",
            str(source_path),
            "--source-v2-13-v-pass-marker",
            str(marker_path),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "PASS" in captured.out
    assert "CRCL.US,MSFT.US,NVDA.US" in captured.out
    assert "token" not in captured.out.lower()
    assert "secret" not in captured.out.lower()
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()
