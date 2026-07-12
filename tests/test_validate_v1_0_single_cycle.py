from __future__ import annotations

import json
from pathlib import Path

import scripts.validate_v1_0_single_cycle as validator


def test_v1_0_single_cycle_acceptance_writes_report_and_marker(tmp_path: Path):
    report = validator.run_acceptance(
        output_root=tmp_path / "processed",
        reports_dir=tmp_path / "reports",
        run_id="v1_0_test",
        command="test command",
    )

    assert report["overall_status"] == "PASS"
    assert report["production_records_written"] is False
    assert report["chain"]["status"] == "Recommendation -> PaperTrade -> Review -> InvestmentMemory"
    assert report["counts"]["updated_trades"] == 1
    assert report["counts"]["generated_reviews"] == 1
    assert report["counts"]["created_memories"] >= 1
    assert report["review"]["decision_quality"] in {
        "good_decision",
        "reasonable_decision",
        "poor_decision",
        "unclear",
    }

    reports_dir = tmp_path / "reports"
    report_path = reports_dir / validator.REPORT_JSON
    marker_path = reports_dir / validator.PASS_MARKER
    assert report_path.exists()
    assert marker_path.exists()
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    assert payload["chain"]["memory_id"] == report["chain"]["memory_id"]
    assert "exit_code=0" in marker_path.read_text(encoding="utf-8")


def test_v1_0_single_cycle_cli_exits_zero_and_prints_no_secrets(tmp_path: Path, capsys):
    exit_code = validator.main(
        [
            "--output-root",
            str(tmp_path / "processed"),
            "--reports-dir",
            str(tmp_path / "reports"),
            "--run-id",
            "v1_0_cli",
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "PASS" in captured.out
    assert "token" not in captured.out.lower()
    assert "secret" not in captured.out.lower()
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()

