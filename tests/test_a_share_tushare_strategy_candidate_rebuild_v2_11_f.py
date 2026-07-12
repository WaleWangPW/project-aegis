from __future__ import annotations

import json
from pathlib import Path

from aegis.strategy.a_share_tushare_candidate_rebuild import (
    build_a_share_tushare_candidate_rebuild_report,
    build_a_share_tushare_rebuild_proposals,
)
import scripts.validate_v2_11_f_a_share_tushare_strategy_candidate_rebuild as validator


def _v2_11_c() -> dict:
    return {
        "overall_status": "PASS",
        "acceptance_target": "V2.11-C Tushare A-Share Historical Sandbox Live Data Refresh",
        "live_data_source": {"provider": "tushare", "market": "A"},
        "summary": {
            "historical_case_count": 8,
            "strategy_pass_count": 0,
            "strategy_fail_count": 2,
        },
        "historical_cases": [
            {"strategy_id": "strategy_a_low_vol_dividend_defensive", "symbol": "600000.SH"},
            {"strategy_id": "strategy_a_low_vol_dividend_defensive", "symbol": "601318.SH"},
            {"strategy_id": "strategy_a_value_quality_multifactor", "symbol": "600036.SH"},
            {"strategy_id": "strategy_a_value_quality_multifactor", "symbol": "000858.SZ"},
        ],
    }


def _v2_11_d() -> dict:
    return {
        "overall_status": "PASS",
        "acceptance_target": "V2.11-D Tushare-Backed A-Share Suggestion Gate Refresh",
        "summary": {"allowed_count": 0, "blocked_count": 2},
        "blocked_strategy_evidence": [
            {
                "strategy_id": "strategy_a_low_vol_dividend_defensive",
                "status": "FAIL",
                "failed_reasons": [
                    "win_rate_below_threshold",
                    "average_return_below_threshold",
                    "max_drawdown_breached",
                ],
                "win_rate": 0.25,
                "average_return": -0.0439,
                "max_drawdown": -0.1038,
            },
            {
                "strategy_id": "strategy_a_value_quality_multifactor",
                "status": "FAIL",
                "failed_reasons": ["average_return_below_threshold", "max_drawdown_breached"],
                "win_rate": 0.75,
                "average_return": -0.0041,
                "max_drawdown": -0.1045,
            },
        ],
    }


def _v2_11_e() -> dict:
    return {
        "overall_status": "PASS",
        "acceptance_target": "V2.11-E Current Action Packet After Tushare Gate",
        "summary": {
            "removed_focus_count": 2,
            "removed_focus_symbols": ["600519.SH", "600036.SH"],
        },
    }


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def test_v2_11_f_builds_rebuild_proposals_without_user_facing_suggestions():
    proposals = build_a_share_tushare_rebuild_proposals(
        source_v2_11_c=_v2_11_c(),
        source_v2_11_d=_v2_11_d(),
        evidence_refs=["c.json", "d.json", "e.json"],
    )

    assert len(proposals) == 2
    assert all(item["market"] == "A" for item in proposals)
    assert all(item["requires_sandbox"] is True for item in proposals)
    assert all(item["requires_suggestion_gate"] is True for item in proposals)
    assert all(item["auto_applied"] is False for item in proposals)
    assert all(item["user_facing_suggestion_allowed"] is False for item in proposals)
    assert all(item["blocked_until_sandbox_pass"] is True for item in proposals)


def test_v2_11_f_derives_actions_from_failed_reasons():
    proposals = build_a_share_tushare_rebuild_proposals(
        source_v2_11_c=_v2_11_c(),
        source_v2_11_d=_v2_11_d(),
        evidence_refs=["source"],
    )
    low_vol = next(item for item in proposals if item["source_strategy_id"].endswith("defensive"))
    value_quality = next(item for item in proposals if item["source_strategy_id"].endswith("multifactor"))

    assert "tighten_drawdown_and_volatility_filter" in low_vol["rebuild_actions"]
    assert "expand_historical_sample_before_retest" in low_vol["rebuild_actions"]
    assert "add_positive_momentum_confirmation" in value_quality["rebuild_actions"]
    assert value_quality["retest_requirements"]["minimum_total_sample_count"] >= 24


def test_v2_11_f_report_passes_when_a_share_remains_blocked_for_rebuild_only():
    report = build_a_share_tushare_candidate_rebuild_report(
        source_v2_11_c=_v2_11_c(),
        source_v2_11_d=_v2_11_d(),
        source_v2_11_e=_v2_11_e(),
        run_id="v2_11_f_unit",
        evidence_refs=["c.json", "d.json", "e.json"],
        generated_at="2026-07-11T00:00:00+08:00",
    )

    assert report["overall_status"] == "PASS"
    assert report["summary"]["rebuild_proposal_count"] == 2
    assert report["summary"]["user_facing_suggestion_count"] == 0
    assert report["checks"]["no_proposal_user_facing_allowed"] is True
    assert report["checks"]["no_strategy_auto_mutation"] is True
    assert report["safety"]["a_share_remains_blocked_until_rebuilt_sandbox_pass"] is True


def test_v2_11_f_fails_if_e_packet_did_not_pass():
    source_e = _v2_11_e()
    source_e["overall_status"] = "FAIL"

    report = build_a_share_tushare_candidate_rebuild_report(
        source_v2_11_c=_v2_11_c(),
        source_v2_11_d=_v2_11_d(),
        source_v2_11_e=source_e,
        run_id="v2_11_f_unit_fail",
        evidence_refs=["source"],
    )

    assert report["overall_status"] == "FAIL"
    assert report["checks"]["source_v2_11_e_pass"] is False


def test_v2_11_f_validator_writes_reports_marker_and_hashes(tmp_path: Path):
    source_c = tmp_path / "v2_11_c.json"
    source_d = tmp_path / "v2_11_d.json"
    source_e = tmp_path / "v2_11_e.json"
    marker_e = tmp_path / "v2_11_e.marker"
    _write_json(source_c, _v2_11_c())
    _write_json(source_d, _v2_11_d())
    _write_json(source_e, _v2_11_e())
    marker_e.write_text("exit_code=0\n", encoding="utf-8")

    report = validator.run_acceptance(
        output_root=tmp_path / "processed",
        reports_dir=tmp_path / "reports",
        run_id="v2_11_f_test",
        command="test command",
        source_v2_11_c_report_json=source_c,
        source_v2_11_d_report_json=source_d,
        source_v2_11_e_report_json=source_e,
        source_v2_11_e_pass_marker=marker_e,
    )

    assert report["overall_status"] == "PASS"
    assert report["checks"]["proposals_json_written"] is True
    assert report["hashes"]["proposals_json"]
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()


def test_v2_11_f_cli_exits_zero_and_prints_no_secret_values(tmp_path: Path, capsys):
    source_c = tmp_path / "v2_11_c.json"
    source_d = tmp_path / "v2_11_d.json"
    source_e = tmp_path / "v2_11_e.json"
    marker_e = tmp_path / "v2_11_e.marker"
    _write_json(source_c, _v2_11_c())
    _write_json(source_d, _v2_11_d())
    _write_json(source_e, _v2_11_e())
    marker_e.write_text("exit_code=0\n", encoding="utf-8")

    exit_code = validator.main(
        [
            "--output-root",
            str(tmp_path / "processed"),
            "--reports-dir",
            str(tmp_path / "reports"),
            "--run-id",
            "v2_11_f_cli",
            "--source-v2-11-c-report-json",
            str(source_c),
            "--source-v2-11-d-report-json",
            str(source_d),
            "--source-v2-11-e-report-json",
            str(source_e),
            "--source-v2-11-e-pass-marker",
            str(marker_e),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "PASS" in captured.out
    assert "token" not in captured.out.lower()
    assert "secret" not in captured.out.lower()
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()
