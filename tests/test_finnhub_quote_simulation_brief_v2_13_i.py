from __future__ import annotations

import json
from pathlib import Path

from aegis.external_sources.finnhub_quote_simulation_brief import (
    ACCEPTANCE_TARGET,
    build_finnhub_quote_current_simulation_brief,
    render_finnhub_quote_current_simulation_brief_markdown,
)
import scripts.validate_v2_13_i_finnhub_quote_simulation_brief as validator


def _gate_report() -> dict:
    return {
        "overall_status": "PASS",
        "acceptance_target": "V2.13-H Finnhub Quote Sandbox Evidence To Suggestion Gate Draft",
        "network_used": False,
        "production_records_written": False,
        "production_cache_mutated": False,
        "production_provider_config_mutated": False,
        "dashboard_contract_changed": False,
        "summary": {
            "allowed_count": 1,
            "blocked_count": 0,
            "symbols": ["AAPL.US"],
            "markets": ["US"],
            "social_sentiment_status": "blocked_plan_or_rate_limit",
            "user_facing_simulation_brief_allowed": True,
            "real_trade_allowed": False,
        },
        "suggestions": [
            {
                "suggestion_id": "sug_finnhub_quote_us_strategy_aapl_us_finnhub_quote_context_probe",
                "strategy_id": "strategy_aapl_us_finnhub_quote_context_probe",
                "symbol": "AAPL.US",
                "market": "US",
                "action": "paper_entry_candidate",
                "simulation_only": True,
                "user_must_execute_externally": True,
                "reasons": [
                    "finnhub_quote_sandbox_status=PASS",
                    "sample_count=8",
                    "win_rate=0.6250",
                    "average_return=0.0091",
                    "max_drawdown=-0.0484",
                    "historical_symbols=AAPL.US",
                    "source_stage=V2.13-G",
                    "social_sentiment_status=blocked_plan_or_rate_limit",
                ],
                "risk_warnings": [
                    "Finnhub quote context is research evidence only; one quote snapshot is not standalone strategy proof.",
                    "Finnhub social sentiment remains blocked by plan or rate limit and is not used in this suggestion draft.",
                    "Simulation-only draft; user decides and executes manually outside Aegis.",
                    "Manual external execution only.",
                    "No live price, position size, trading webhook, broker execution, or order is produced.",
                ],
                "evidence_refs": [
                    "source-report.json",
                    "pass.marker",
                    "v2_13_f_quote_context_case:binding:context:eodhd:hash",
                    "v2_13_f_quote_context_case:binding:context:twelve:hash",
                ],
                "blocked_by": [],
            }
        ],
    }


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def test_v2_13_i_builds_user_readable_finnhub_quote_brief():
    brief = build_finnhub_quote_current_simulation_brief(
        _gate_report(),
        run_id="v2_13_i_unit",
        generated_at="2026-07-12T02:30:00+08:00",
    )

    assert brief["overall_status"] == "PASS"
    assert brief["acceptance_target"] == ACCEPTANCE_TARGET
    assert brief["summary"]["candidate_count"] == 1
    assert brief["summary"]["candidate_symbols"] == ["AAPL.US"]
    assert brief["summary"]["social_sentiment_status"] == "blocked_plan_or_rate_limit"
    assert brief["checks"]["has_aapl_candidate"] is True
    assert brief["checks"]["social_sentiment_blocked_visible"] is True
    assert brief["checks"]["manual_external_execution_only"] is True
    assert brief["items"][0]["brief_status"] == "simulation_candidate"
    assert brief["items"][0]["no_order_placement"] is True
    assert brief["items"][0]["no_position_size"] is True
    assert "simulation-only" in brief["current_answer"]["usable_suggestions_status"]


def test_v2_13_i_markdown_is_chinese_and_boundary_explicit():
    brief = build_finnhub_quote_current_simulation_brief(_gate_report(), run_id="v2_13_i_unit")

    md = render_finnhub_quote_current_simulation_brief_markdown(brief)

    assert "Project Aegis Finnhub Quote 当前模拟建议简报" in md
    assert "AAPL.US" in md
    assert "blocked_plan_or_rate_limit" in md
    assert "不含实时价格" in md
    assert "不含仓位数量" in md
    assert "不接券商" in md
    assert "不下单" in md
    assert "不使用 Finnhub social sentiment" in md


def test_v2_13_i_fails_if_source_does_not_allow_user_facing_brief():
    source = _gate_report()
    source["summary"]["user_facing_simulation_brief_allowed"] = False

    brief = build_finnhub_quote_current_simulation_brief(source, run_id="v2_13_i_fail")

    assert brief["overall_status"] == "FAIL"
    assert brief["checks"]["source_allows_user_facing_simulation_brief"] is False


def test_v2_13_i_fails_if_social_sentiment_not_blocked():
    source = _gate_report()
    source["summary"]["social_sentiment_status"] = "pass"

    brief = build_finnhub_quote_current_simulation_brief(source, run_id="v2_13_i_social_fail")

    assert brief["overall_status"] == "FAIL"
    assert brief["checks"]["source_social_sentiment_still_blocked"] is False


def test_v2_13_i_validator_writes_brief_marker_and_preserves_records(tmp_path: Path):
    source_json = tmp_path / "v2_13_h.json"
    marker = tmp_path / "v2_13_h.marker"
    _write_json(source_json, _gate_report())
    marker.write_text("exit_code=0\n", encoding="utf-8")
    record = tmp_path / "records" / "paper_trades.jsonl"
    record.parent.mkdir()
    record.write_text("existing\n", encoding="utf-8")

    report = validator.run_acceptance(
        output_root=tmp_path / "processed",
        reports_dir=tmp_path / "reports",
        run_id="v2_13_i_test",
        command="test command",
        source_v2_13_h_report_json=source_json,
        source_v2_13_h_pass_marker=marker,
        record_paths={"paper_trades_jsonl": record},
    )

    assert report["overall_status"] == "PASS"
    assert report["checks"]["brief_json_written"] is True
    assert report["checks"]["brief_md_written"] is True
    assert report["checks"]["production_record_files_unchanged"] is True
    assert report["hashes"]["brief_json"]
    assert record.read_text(encoding="utf-8") == "existing\n"
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()


def test_v2_13_i_cli_exits_zero_and_prints_no_secret_values(tmp_path: Path, capsys):
    source_json = tmp_path / "v2_13_h.json"
    marker = tmp_path / "v2_13_h.marker"
    _write_json(source_json, _gate_report())
    marker.write_text("exit_code=0\n", encoding="utf-8")

    exit_code = validator.main(
        [
            "--output-root",
            str(tmp_path / "processed"),
            "--reports-dir",
            str(tmp_path / "reports"),
            "--run-id",
            "v2_13_i_cli",
            "--source-v2-13-h-report-json",
            str(source_json),
            "--source-v2-13-h-pass-marker",
            str(marker),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "PASS" in captured.out
    assert "token" not in captured.out.lower()
    assert "secret" not in captured.out.lower()
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()
