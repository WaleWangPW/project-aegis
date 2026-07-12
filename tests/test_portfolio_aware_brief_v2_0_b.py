from __future__ import annotations

import json
from pathlib import Path

import scripts.validate_v2_0_b_portfolio_aware_brief as validator
from aegis.portfolio.aware_brief import build_portfolio_aware_brief, render_portfolio_aware_brief_markdown


def test_portfolio_aware_brief_explains_action_hold_and_wait():
    report = build_portfolio_aware_brief(
        recommendations=validator._recommendations(),
        portfolio_report=validator._portfolio_report(),
        planned_position_value=1000.0,
    )

    actions = {item["symbol"]: item["portfolio_action"] for item in report["items"]}
    assert actions["NEW"] == "wait_due_to_portfolio_risk"
    assert actions["HOLD"] == "hold"
    assert actions["WAIT"] == "wait"
    assert report["safety"]["dashboard_contract_unchanged"] is True
    assert report["safety"]["no_real_trade"] is True

    text = json.dumps(report, ensure_ascii=False)
    assert "cash=" in text
    assert "current_exposure_pct=" in text
    assert "max_exposure_pct=" in text
    assert "max_single_position_pct=" in text

    md = render_portfolio_aware_brief_markdown(report)
    assert "Portfolio-Aware Daily Brief" in md
    assert "Dashboard Contract unchanged" in md


def test_v2_0_b_acceptance_writes_marker_and_reports(tmp_path: Path):
    report = validator.run_acceptance(
        output_root=tmp_path / "processed",
        reports_dir=tmp_path / "reports",
        run_id="v2_0_b_test",
        command="test command",
    )

    assert report["overall_status"] == "PASS"
    assert report["checks"]["action_explained"] is True
    assert report["checks"]["hold_explained"] is True
    assert report["checks"]["wait_explained"] is True
    assert report["checks"]["dashboard_contract_unchanged"] is True
    assert report["production_records_written"] is False
    assert report["hashes"]["brief_json"]
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()


def test_v2_0_b_cli_exits_zero_and_prints_no_secrets(tmp_path: Path, capsys):
    exit_code = validator.main(
        [
            "--output-root",
            str(tmp_path / "processed"),
            "--reports-dir",
            str(tmp_path / "reports"),
            "--run-id",
            "v2_0_b_cli",
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "PASS" in captured.out
    assert "token" not in captured.out.lower()
    assert "secret" not in captured.out.lower()
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()
