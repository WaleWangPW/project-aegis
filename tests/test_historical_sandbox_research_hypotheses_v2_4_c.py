from __future__ import annotations

import json
from pathlib import Path

import scripts.validate_v2_4_c_historical_sandbox_research_hypotheses as validator
from aegis.models.strategy_hypothesis import StrategySandboxHypothesis
from aegis.strategy.hypothesis_sandbox import (
    build_hypothesis_sandbox_report,
    fixture_historical_cases_for_hypotheses,
    strategy_candidates_from_hypotheses,
)
from aegis.strategy.hypothesis_queue import build_strategy_sandbox_hypotheses
from aegis.strategy.research_source_catalog import canonical_strategy_research_records


def _hypotheses() -> list[StrategySandboxHypothesis]:
    return build_strategy_sandbox_hypotheses(
        canonical_strategy_research_records(),
        created_at="2026-07-11T00:00:00+08:00",
    )


def test_hypotheses_convert_to_sandbox_candidates_and_cases():
    hypotheses = _hypotheses()
    candidates = strategy_candidates_from_hypotheses(hypotheses, created_at="2026-07-11T00:00:00+08:00")
    cases = fixture_historical_cases_for_hypotheses(hypotheses)

    assert len(candidates) == len(hypotheses)
    assert len(cases) == len(hypotheses) * 4
    assert {candidate.market for candidate in candidates} == {"A", "H", "US"}
    assert all(candidate.source_research_refs for candidate in candidates)
    assert all(case.evidence_ref and case.evidence_ref.startswith("v2_4_b_hypothesis:") for case in cases)


def test_hypothesis_sandbox_report_has_pass_fail_and_keeps_suggestion_gate():
    report = build_hypothesis_sandbox_report(
        _hypotheses(),
        run_id="v2_4_c_unit",
        command="unit test",
        historical_cache_file_count=10,
    )

    assert report["overall_status"] == "PASS"
    assert report["summary"]["hypothesis_count"] == 6
    assert report["summary"]["pass_count"] >= 2
    assert report["summary"]["fail_count"] >= 2
    assert report["summary"]["passing_hypotheses"]
    assert report["summary"]["failing_hypotheses"]
    assert report["safety"]["suggestion_gate_still_required"] is True
    assert report["safety"]["hypothesis_only_until_suggestion_gate"] is True
    assert report["production_records_written"] is False


def test_failed_hypotheses_include_explicit_reasons():
    report = build_hypothesis_sandbox_report(
        _hypotheses(),
        run_id="v2_4_c_unit",
        command="unit test",
        historical_cache_file_count=10,
    )
    failed = [item for item in report["results"] if item["status"] == "FAIL"]

    assert failed
    assert all(item["metrics"]["failed_reasons"] for item in failed)


def test_v2_4_c_acceptance_writes_marker_hashes_and_reports(tmp_path: Path):
    queue_json = tmp_path / "queue.json"
    queue_json.write_text(
        json.dumps(
            {
                "hypotheses": [hypothesis.model_dump() for hypothesis in _hypotheses()],
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    report = validator.run_acceptance(
        output_root=tmp_path / "processed",
        reports_dir=tmp_path / "reports",
        run_id="v2_4_c_test",
        command="test command",
        hypothesis_queue_json=queue_json,
    )

    assert report["overall_status"] == "PASS"
    assert report["checks"]["all_hypotheses_evaluated"] is True
    assert report["checks"]["at_least_two_hypotheses_passed"] is True
    assert report["checks"]["at_least_two_hypotheses_failed"] is True
    assert report["checks"]["suggestion_gate_still_required"] is True
    assert report["production_records_written"] is False
    assert report["hashes"]["hypothesis_sandbox_report_json"]
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()


def test_v2_4_c_cli_exits_zero_and_prints_no_secrets(tmp_path: Path, capsys):
    queue_json = tmp_path / "queue.json"
    queue_json.write_text(
        json.dumps(
            {
                "hypotheses": [hypothesis.model_dump() for hypothesis in _hypotheses()],
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    exit_code = validator.main(
        [
            "--output-root",
            str(tmp_path / "processed"),
            "--reports-dir",
            str(tmp_path / "reports"),
            "--run-id",
            "v2_4_c_cli",
            "--hypothesis-queue-json",
            str(queue_json),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "PASS" in captured.out
    assert "secret" not in captured.out.lower()
    assert "token" not in captured.out.lower()
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()
