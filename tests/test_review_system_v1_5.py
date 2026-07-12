from __future__ import annotations

import json
from pathlib import Path

import scripts.validate_v1_5_review_system as validator
from aegis.review.system import build_review_system_report, render_review_system_markdown


def test_review_system_report_contains_weekly_errors_and_memory(tmp_path: Path):
    records_dir = tmp_path / "records"
    validator._seed(records_dir)

    report = build_review_system_report(
        records_dir=records_dir,
        start="2026-07-01",
        end="2026-07-12",
        period="weekly",
    )

    assert report["period"] == "weekly"
    assert report["review_count"] == 2
    assert report["best_cases"]
    assert report["failed_cases"]
    assert report["error_attribution"]
    assert report["memory_reuse"]["reference_count"] >= 2
    assert report["safety"]["no_strategy_mutation"] is True

    md = render_review_system_markdown(report)
    assert "Error Attribution" in md
    assert "Investment Memory References" in md


def test_v1_5_acceptance_writes_weekly_monthly_reports_and_marker(tmp_path: Path):
    report = validator.run_acceptance(
        output_root=tmp_path / "processed",
        reports_dir=tmp_path / "reports",
        run_id="v1_5_test",
        command="test command",
    )

    assert report["overall_status"] == "PASS"
    assert report["checks"]["weekly_report"] is True
    assert report["checks"]["monthly_report"] is True
    assert report["checks"]["error_attribution"] is True
    assert report["checks"]["memory_reuse"] is True
    assert report["production_records_written"] is False

    reports_dir = tmp_path / "reports"
    assert (reports_dir / validator.PASS_MARKER).exists()
    payload = json.loads((reports_dir / validator.REPORT_JSON).read_text(encoding="utf-8"))
    assert payload["summary"]["memory_reference_count"] >= 2


def test_v1_5_cli_exits_zero_and_prints_no_secrets(tmp_path: Path, capsys):
    exit_code = validator.main(
        [
            "--output-root",
            str(tmp_path / "processed"),
            "--reports-dir",
            str(tmp_path / "reports"),
            "--run-id",
            "v1_5_cli",
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "PASS" in captured.out
    assert "token" not in captured.out.lower()
    assert "secret" not in captured.out.lower()
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()
