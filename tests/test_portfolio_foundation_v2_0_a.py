from __future__ import annotations

import json
from pathlib import Path

import yaml

import scripts.validate_v2_0_a_portfolio_foundation as validator
from aegis.portfolio.holdings_loader import HoldingLoader
from aegis.portfolio.snapshot import RiskBudget, build_portfolio_snapshot, render_portfolio_snapshot_markdown


def _write_holdings(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(
            {
                "holdings": [
                    {
                        "holding_id": "hold_US_TEST",
                        "symbol": "TEST",
                        "market": "US",
                        "shares": 10,
                        "avg_cost": 100.0,
                        "current_price": 110.0,
                        "currency": "USD",
                        "status": "open",
                    }
                ]
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )


def test_portfolio_snapshot_contains_cash_exposure_and_safety_boundary(tmp_path: Path):
    holdings_path = tmp_path / "holdings.yaml"
    _write_holdings(holdings_path)
    holdings = HoldingLoader(holdings_path).load_holdings()

    report = build_portfolio_snapshot(
        holdings=holdings,
        date="2026-07-11",
        cash=900.0,
        risk_budget=RiskBudget(max_exposure_pct=0.8, max_single_position_pct=0.7),
    )

    snapshot = report["portfolio_snapshot"]
    assert snapshot["total_market_value"] == 1100.0
    assert snapshot["cash"] == 900.0
    assert snapshot["exposure_pct"] == 0.55
    assert report["holdings"][0]["position_pct"] == 0.55
    assert report["safety"]["simulation_only"] is True
    assert report["safety"]["no_broker_api"] is True
    assert report["safety"]["manual_external_execution_only"] is True

    md = render_portfolio_snapshot_markdown(report)
    assert "Portfolio Snapshot" in md
    assert "User-submitted external execution facts" in md


def test_v2_0_a_acceptance_writes_marker_and_hashes(tmp_path: Path):
    report = validator.run_acceptance(
        output_root=tmp_path / "processed",
        reports_dir=tmp_path / "reports",
        run_id="v2_0_a_test",
        command="test command",
    )

    assert report["overall_status"] == "PASS"
    assert report["checks"]["holdings_record"] is True
    assert report["checks"]["cash_record"] is True
    assert report["checks"]["manual_execution_boundary"] is True
    assert report["production_records_written"] is False
    assert report["hashes"]["snapshot_json"]
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()
    payload = json.loads((tmp_path / "reports" / validator.REPORT_JSON).read_text(encoding="utf-8"))
    assert payload["summary"]["holding_count"] == 2


def test_v2_0_a_cli_exits_zero_and_prints_no_secrets(tmp_path: Path, capsys):
    exit_code = validator.main(
        [
            "--output-root",
            str(tmp_path / "processed"),
            "--reports-dir",
            str(tmp_path / "reports"),
            "--run-id",
            "v2_0_a_cli",
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "PASS" in captured.out
    assert "token" not in captured.out.lower()
    assert "secret" not in captured.out.lower()
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()
