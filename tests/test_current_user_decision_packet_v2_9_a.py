from __future__ import annotations

import json
from pathlib import Path

import scripts.validate_v2_9_a_current_user_decision_packet as validator


def _concrete_brief() -> dict:
    items = []
    for market, symbol in [("A", "600036.SH"), ("H", "00700.HK"), ("US", "MSFT")]:
        items.append(
            {
                "brief_status": "candidate",
                "symbol": symbol,
                "market": market,
                "strategy_id": f"strategy_{market}",
                "candidate_score": 0.8,
                "candidate_status": "Watch",
                "reasons": ["sandbox_status=PASS"],
                "risk_warnings": ["simulation-only"],
                "evidence_refs": ["evidence.json"],
            }
        )
        items.append(
            {
                "brief_status": "blocked",
                "symbol": f"{market}_BLOCKED",
                "market": market,
                "strategy_id": f"strategy_{market}_blocked",
                "candidate_score": None,
                "candidate_status": None,
                "reasons": ["sandbox_status=FAIL"],
                "risk_warnings": ["blocked"],
                "blocked_by": ["strategy_sandbox_not_passed"],
                "evidence_refs": ["evidence.json"],
            }
        )
    return {
        "source_mode": "approved_fixture_not_live_market_data",
        "production_records_written": False,
        "dashboard_contract_changed": False,
        "items": items,
        "safety": {
            "no_live_price": True,
            "no_position_size": True,
            "manual_external_execution_only": True,
            "no_real_trade": True,
            "no_broker_api": True,
        },
    }


def _sandbox_report() -> dict:
    return {
        "summary": {
            "pass_count": 3,
            "fail_count": 3,
            "passing_hypotheses": ["hyp_a", "hyp_h", "hyp_us"],
            "failing_hypotheses": ["fail_a", "fail_h", "fail_us"],
        }
    }


def _api_report() -> dict:
    return {
        "real_user_dry_run_status": "blocked_missing_metadata",
        "production_records_written": False,
        "dashboard_contract_changed": False,
        "summary": {"fixture_bound_markets": ["A", "H", "US"]},
        "safety": {
            "no_real_trade": True,
            "no_broker_api": True,
            "no_trading_webhook": True,
        },
    }


def test_v2_9_a_packet_builds_user_actions_and_boundaries():
    packet = validator._build_packet(
        concrete_brief=_concrete_brief(),
        sandbox_report=_sandbox_report(),
        api_dry_run_report=_api_report(),
        run_id="unit",
        generated_at="2026-07-11T00:00:00+08:00",
    )

    assert packet["overall_status"] == "PASS"
    assert packet["summary"]["candidate_count"] == 3
    assert packet["summary"]["blocked_count"] == 3
    assert packet["summary"]["real_user_api_status"] == "blocked_missing_metadata"
    assert packet["checks"]["has_a_h_us_candidates"] is True
    assert packet["checks"]["sandbox_pass_fail_visible"] is True
    assert packet["safety"]["no_real_trade"] is True
    assert all(item["user_action"] for item in packet["items"])


def test_v2_9_a_acceptance_writes_packet_and_reports(tmp_path: Path):
    concrete = tmp_path / "concrete.json"
    sandbox = tmp_path / "sandbox.json"
    api = tmp_path / "api.json"
    concrete.write_text(json.dumps(_concrete_brief(), ensure_ascii=False), encoding="utf-8")
    sandbox.write_text(json.dumps(_sandbox_report(), ensure_ascii=False), encoding="utf-8")
    api.write_text(json.dumps(_api_report(), ensure_ascii=False), encoding="utf-8")

    report = validator.run_acceptance(
        output_root=tmp_path / "processed",
        reports_dir=tmp_path / "reports",
        run_id="v2_9_a_test",
        command="test command",
        concrete_brief_json=concrete,
        sandbox_report_json=sandbox,
        api_dry_run_json=api,
    )

    assert report["overall_status"] == "PASS"
    assert report["checks"]["packet_json_written"] is True
    assert report["checks"]["packet_md_written"] is True
    assert report["summary"]["candidate_markets"] == ["A", "H", "US"]
    assert report["production_records_written"] is False
    assert report["dashboard_contract_changed"] is False
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()


def test_v2_9_a_cli_exits_zero(tmp_path: Path, capsys):
    concrete = tmp_path / "concrete.json"
    sandbox = tmp_path / "sandbox.json"
    api = tmp_path / "api.json"
    concrete.write_text(json.dumps(_concrete_brief(), ensure_ascii=False), encoding="utf-8")
    sandbox.write_text(json.dumps(_sandbox_report(), ensure_ascii=False), encoding="utf-8")
    api.write_text(json.dumps(_api_report(), ensure_ascii=False), encoding="utf-8")

    exit_code = validator.main(
        [
            "--output-root",
            str(tmp_path / "processed"),
            "--reports-dir",
            str(tmp_path / "reports"),
            "--run-id",
            "v2_9_a_cli",
            "--concrete-brief-json",
            str(concrete),
            "--sandbox-report-json",
            str(sandbox),
            "--api-dry-run-json",
            str(api),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "PASS" in captured.out
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()
