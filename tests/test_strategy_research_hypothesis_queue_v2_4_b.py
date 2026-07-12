from __future__ import annotations

import json
from pathlib import Path

import pytest

import scripts.validate_v2_4_b_strategy_research_hypothesis_queue as validator
from aegis.models.strategy_hypothesis import StrategySandboxHypothesis
from aegis.strategy.hypothesis_queue import (
    build_strategy_sandbox_hypotheses,
    build_strategy_sandbox_hypothesis_queue,
    write_strategy_sandbox_hypothesis_queue,
)
from aegis.strategy.research_source_catalog import canonical_strategy_research_records


def test_research_sources_build_a_h_us_sandbox_hypotheses():
    records = canonical_strategy_research_records()
    hypotheses = build_strategy_sandbox_hypotheses(records, created_at="2026-07-11T00:00:00+08:00")
    markets = [item.market for item in hypotheses]

    assert len(hypotheses) >= 6
    assert markets.count("A") >= 2
    assert markets.count("H") >= 2
    assert markets.count("US") >= 2
    assert all(item.source_research_ids for item in hypotheses)
    assert all(item.proposed_metrics for item in hypotheses)


def test_hypothesis_queue_keeps_sandbox_and_suggestion_gate_required(tmp_path: Path):
    queue = write_strategy_sandbox_hypothesis_queue(
        canonical_strategy_research_records(),
        tmp_path / "strategy_sandbox_hypothesis_queue.json",
    )

    assert queue["hypothesis_count"] >= 6
    assert queue["market_coverage"]["A"] >= 2
    assert queue["market_coverage"]["H"] >= 2
    assert queue["market_coverage"]["US"] >= 2
    assert queue["safety"]["hypothesis_only"] is True
    assert queue["safety"]["requires_sandbox"] is True
    assert queue["safety"]["auto_applied"] is False
    assert queue["safety"]["user_facing_suggestion_allowed"] is False
    assert queue["safety"]["no_real_trade"] is True
    assert len(queue["hypothesis_hashes"]) == queue["hypothesis_count"]


def test_strategy_sandbox_hypothesis_rejects_direct_suggestion():
    with pytest.raises(ValueError):
        StrategySandboxHypothesis(
            hypothesis_id="bad_direct_suggestion",
            title="Bad direct suggestion",
            market="US",
            strategy_families=["value"],
            thesis="Should be rejected.",
            source_research_ids=["catalog_fama_french_five_factor"],
            proposed_universe="US large cap",
            proposed_metrics=["win_rate"],
            requires_sandbox=True,
            auto_applied=False,
            user_facing_suggestion_allowed=True,
            created_at="2026-07-11T00:00:00+08:00",
        )


def test_hypothesis_queue_report_has_required_family_coverage():
    queue = build_strategy_sandbox_hypothesis_queue(
        canonical_strategy_research_records(),
        created_at="2026-07-11T00:00:00+08:00",
    )

    for family in ["value", "quality", "momentum", "low_volatility", "dividend", "multi_factor", "risk_overlay"]:
        assert queue["strategy_family_coverage"].get(family, 0) > 0


def test_v2_4_b_acceptance_writes_marker_hashes_and_reports(tmp_path: Path):
    report = validator.run_acceptance(
        output_root=tmp_path / "processed",
        reports_dir=tmp_path / "reports",
        run_id="v2_4_b_test",
        command="test command",
    )

    assert report["overall_status"] == "PASS"
    assert report["checks"]["covers_a_h_us"] is True
    assert report["checks"]["requires_sandbox"] is True
    assert report["checks"]["not_auto_applied"] is True
    assert report["checks"]["no_user_facing_suggestion"] is True
    assert report["production_records_written"] is False
    assert report["hashes"]["strategy_sandbox_hypothesis_queue"]
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()
    payload = json.loads((tmp_path / "reports" / validator.REPORT_JSON).read_text(encoding="utf-8"))
    assert payload["summary"]["next_target"] == "V2.4-C Historical Sandbox Run For Research Hypotheses"


def test_v2_4_b_cli_exits_zero_and_prints_no_secrets(tmp_path: Path, capsys):
    exit_code = validator.main(
        [
            "--output-root",
            str(tmp_path / "processed"),
            "--reports-dir",
            str(tmp_path / "reports"),
            "--run-id",
            "v2_4_b_cli",
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "PASS" in captured.out
    assert "secret" not in captured.out.lower()
    assert "token" not in captured.out.lower()
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()
