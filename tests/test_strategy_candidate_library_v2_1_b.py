from __future__ import annotations

import json
from pathlib import Path

import pytest

import scripts.validate_v2_1_b_strategy_candidate_library as validator
from aegis.strategy.library import StrategyCandidateLibrary, StrategyLibraryError, default_strategy_candidates


def test_strategy_candidate_library_persists_and_filters(tmp_path: Path):
    path = tmp_path / "strategy_candidate_library.json"
    library = StrategyCandidateLibrary(path)
    candidates = default_strategy_candidates(created_at="2026-07-11T00:00:00+08:00")

    payload = library.save(candidates)
    loaded = library.load()

    assert payload["schema_version"] == "strategy_candidate_library.v1"
    assert len(loaded) == 4
    assert [candidate.strategy_id for candidate in library.list_by_market("A")] == ["value_quality_defensive_a"]
    assert [candidate.strategy_id for candidate in library.list_by_market("H")] == ["low_volatility_dividend_h"]
    assert len(library.list_by_market("US")) == 2
    assert len(library.list_by_factor_family("multi_factor")) == 3
    assert library.get("portfolio_risk_veto_overlay").factor_family == "risk_overlay"
    assert payload["safety"]["no_real_trade"] is True
    assert payload["safety"]["no_strategy_auto_mutation"] is True


def test_strategy_candidate_library_rejects_duplicates(tmp_path: Path):
    path = tmp_path / "strategy_candidate_library.json"
    library = StrategyCandidateLibrary(path)
    candidates = default_strategy_candidates(created_at="2026-07-11T00:00:00+08:00")

    with pytest.raises(StrategyLibraryError):
        library.save([*candidates, candidates[0]])


def test_v2_1_b_acceptance_writes_marker_hashes_and_reports(tmp_path: Path):
    report = validator.run_acceptance(
        output_root=tmp_path / "processed",
        reports_dir=tmp_path / "reports",
        run_id="v2_1_b_test",
        command="test command",
    )

    assert report["overall_status"] == "PASS"
    assert report["checks"]["candidate_count"] is True
    assert report["checks"]["a_h_us_coverage"] is True
    assert report["checks"]["duplicate_rejected"] is True
    assert report["checks"]["no_real_trade_or_broker"] is True
    assert report["production_records_written"] is False
    assert report["hashes"]["library_json"]
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()
    payload = json.loads((tmp_path / "reports" / validator.REPORT_JSON).read_text(encoding="utf-8"))
    assert payload["summary"]["next_gate_required"] == "V2.1-C Suggestion Gate"


def test_v2_1_b_cli_exits_zero_and_prints_no_secrets(tmp_path: Path, capsys):
    exit_code = validator.main(
        [
            "--output-root",
            str(tmp_path / "processed"),
            "--reports-dir",
            str(tmp_path / "reports"),
            "--run-id",
            "v2_1_b_cli",
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "PASS" in captured.out
    assert "token" not in captured.out.lower()
    assert "secret" not in captured.out.lower()
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()
