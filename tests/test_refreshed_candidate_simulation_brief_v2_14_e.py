from __future__ import annotations

import json
from pathlib import Path

from aegis.strategy.refreshed_candidate_simulation_brief import (
    ACCEPTANCE_TARGET,
    build_refreshed_candidate_current_simulation_brief,
    render_refreshed_candidate_current_simulation_brief_markdown,
)
import scripts.validate_v2_14_e_refreshed_candidate_simulation_brief as validator


def _suggestion(symbol: str, market: str, action: str, strategy_id: str, blocked_by: list[str] | None = None) -> dict:
    blocked_by = blocked_by or []
    return {
        "suggestion_id": f"sug_{symbol}",
        "opportunity_id": f"opp_{symbol}",
        "strategy_id": strategy_id,
        "symbol": symbol,
        "market": market,
        "action": action,
        "simulation_only": True,
        "user_must_execute_externally": True,
        "reasons": [
            f"symbol={symbol}",
            "coverage_status=historical_case_available" if not blocked_by else "coverage_status=missing_historical_case",
            "sandbox_status=PASS" if action != "blocked" else "sandbox_status=FAIL",
            "sample_count=1",
            "win_rate=1.0" if action != "blocked" else "win_rate=0.0",
            "average_return=0.1" if action != "blocked" else "average_return=-0.03",
            "max_drawdown=-0.01",
            "failed_reasons=average_return_below_threshold" if blocked_by else "failed_reasons=",
            "source_stage=V2.14-C",
        ],
        "risk_warnings": [
            "Simulation-only draft; user decides and executes manually outside Aegis.",
            "Historical sandbox evidence only; not a future prediction.",
            "No live price, position size, broker API, webhook, or order is produced.",
        ],
        "evidence_refs": [f"candidate_ref:{symbol}", f"case_ref:{symbol}"] if action != "blocked" else [],
        "blocked_by": blocked_by,
        "created_at": "2026-07-12T04:00:00+08:00",
    }


def _gate_report() -> dict:
    return {
        "overall_status": "PASS",
        "acceptance_target": "V2.14-D Refreshed Candidate Suggestion Gate",
        "run_id": "unit_v2_14_d",
        "network_used": False,
        "production_records_written": False,
        "production_cache_mutated": False,
        "production_provider_config_mutated": False,
        "dashboard_contract_changed": False,
        "summary": {
            "allowed_count": 1,
            "blocked_count": 5,
            "allowed_symbols": ["00700.HK"],
            "blocked_symbols": ["00005.HK", "00941.HK", "600036.SH", "600519.SH", "601398.SH"],
            "simulation_suggestion_available": True,
            "real_trade_allowed": False,
        },
        "suggestions": [
            _suggestion("00700.HK", "H", "paper_entry_candidate", "strategy_h_low_vol_dividend"),
            _suggestion("600519.SH", "A", "blocked", "strategy_a_low_vol_dividend_defensive", ["strategy_sandbox_not_passed"]),
            _suggestion("600036.SH", "A", "blocked", "strategy_a_low_vol_dividend_defensive", ["strategy_sandbox_not_passed"]),
            _suggestion("601398.SH", "A", "blocked", "strategy_a_low_vol_dividend_defensive", ["strategy_sandbox_not_passed", "missing_evidence_refs"]),
            _suggestion("00005.HK", "H", "blocked", "strategy_h_low_vol_dividend", ["missing_evidence_refs"]),
            _suggestion("00941.HK", "H", "blocked", "strategy_h_low_vol_dividend", ["missing_evidence_refs"]),
        ],
    }


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def test_v2_14_e_builds_user_readable_current_simulation_brief():
    brief = build_refreshed_candidate_current_simulation_brief(
        _gate_report(),
        run_id="v2_14_e_unit",
        generated_at="2026-07-12T04:30:00+08:00",
    )

    assert brief["overall_status"] == "PASS"
    assert brief["acceptance_target"] == ACCEPTANCE_TARGET
    assert brief["summary"]["candidate_count"] == 1
    assert brief["summary"]["blocked_count"] == 5
    assert brief["summary"]["candidate_symbols"] == ["00700.HK"]
    assert "600519.SH" in brief["summary"]["blocked_symbols"]
    assert brief["checks"]["has_00700_candidate"] is True
    assert brief["checks"]["blocked_symbols_visible"] is True
    assert brief["checks"]["manual_external_execution_only"] is True
    assert brief["items"][0]["brief_status"] == "simulation_candidate"
    assert brief["items"][0]["no_order_placement"] is True
    assert brief["items"][0]["no_position_size"] is True
    assert "00700.HK" in brief["current_answer"]["usable_suggestion_status"]


def test_v2_14_e_markdown_is_chinese_and_boundary_explicit():
    brief = build_refreshed_candidate_current_simulation_brief(_gate_report(), run_id="v2_14_e_unit")

    md = render_refreshed_candidate_current_simulation_brief_markdown(brief)

    assert "Project Aegis 当前模拟建议简报" in md
    assert "00700.HK" in md
    assert "600519.SH" in md
    assert "不含实时价格" in md
    assert "不含仓位数量" in md
    assert "不接券商" in md
    assert "不下单" in md
    assert "真实交易允许：`False`" in md


def test_v2_14_e_fails_if_source_is_not_v2_14_d():
    source = _gate_report()
    source["acceptance_target"] = "wrong"

    brief = build_refreshed_candidate_current_simulation_brief(source, run_id="v2_14_e_fail")

    assert brief["overall_status"] == "FAIL"
    assert brief["checks"]["source_is_v2_14_d"] is False


def test_v2_14_e_fails_without_allowed_draft():
    source = _gate_report()
    source["summary"]["allowed_count"] = 0
    source["suggestions"][0]["action"] = "blocked"
    source["suggestions"][0]["blocked_by"] = ["strategy_sandbox_not_passed"]

    brief = build_refreshed_candidate_current_simulation_brief(source, run_id="v2_14_e_no_candidate")

    assert brief["overall_status"] == "FAIL"
    assert brief["checks"]["source_has_allowed_draft"] is False
    assert brief["checks"]["has_00700_candidate"] is False


def test_v2_14_e_validator_writes_brief_marker_and_preserves_records(tmp_path: Path):
    source_json = tmp_path / "v2_14_d.json"
    marker = tmp_path / "v2_14_d.marker"
    _write_json(source_json, _gate_report())
    marker.write_text("exit_code=0\n", encoding="utf-8")
    record = tmp_path / "records" / "recommendations.jsonl"
    record.parent.mkdir()
    record.write_text("existing\n", encoding="utf-8")

    report = validator.run_acceptance(
        output_root=tmp_path / "processed",
        reports_dir=tmp_path / "reports",
        run_id="v2_14_e_test",
        command="test command",
        source_v2_14_d_report_json=source_json,
        source_v2_14_d_pass_marker=marker,
        record_paths={"recommendations_jsonl": record},
    )

    assert report["overall_status"] == "PASS"
    assert report["checks"]["brief_json_written"] is True
    assert report["checks"]["brief_md_written"] is True
    assert report["checks"]["production_record_files_unchanged"] is True
    assert report["hashes"]["brief_json"]
    assert record.read_text(encoding="utf-8") == "existing\n"
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()


def test_v2_14_e_cli_exits_zero_and_prints_no_secret_values(tmp_path: Path, capsys):
    source_json = tmp_path / "v2_14_d.json"
    marker = tmp_path / "v2_14_d.marker"
    _write_json(source_json, _gate_report())
    marker.write_text("exit_code=0\n", encoding="utf-8")

    exit_code = validator.main(
        [
            "--output-root",
            str(tmp_path / "processed"),
            "--reports-dir",
            str(tmp_path / "reports"),
            "--run-id",
            "v2_14_e_cli",
            "--source-v2-14-d-report-json",
            str(source_json),
            "--source-v2-14-d-pass-marker",
            str(marker),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "PASS" in captured.out
    assert "00700.HK" in captured.out
    assert "token" not in captured.out.lower()
    assert "secret" not in captured.out.lower()
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()
