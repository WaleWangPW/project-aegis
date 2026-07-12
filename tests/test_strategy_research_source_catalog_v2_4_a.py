from __future__ import annotations

import json
from pathlib import Path

import scripts.validate_v2_4_a_strategy_research_source_catalog as validator
from aegis.strategy.research_ingestion import write_strategy_research_corpus
from aegis.strategy.research_source_catalog import canonical_strategy_research_records, summarize_catalog


def test_catalog_covers_a_h_us_and_core_strategy_families():
    records = canonical_strategy_research_records()
    summary = summarize_catalog(records)

    assert summary["record_count"] >= 10
    assert all(summary["market_coverage"].get(market, 0) >= 2 for market in ["A", "H", "US"])
    assert all(
        summary["strategy_family_coverage"].get(family, 0) > 0
        for family in [
            "value",
            "quality",
            "momentum",
            "low_volatility",
            "dividend",
            "size",
            "multi_factor",
            "risk_overlay",
        ]
    )


def test_catalog_records_are_summary_only_and_unique():
    records = canonical_strategy_research_records()
    ids = [record.research_id for record in records]
    urls = [record.url for record in records]

    assert len(ids) == len(set(ids))
    assert len(urls) == len(set(urls))
    assert all(record.retention_policy == "summary_only" for record in records)
    assert all(not record.raw_text_stored for record in records)
    assert all(record.implications for record in records)


def test_catalog_can_write_strategy_research_corpus(tmp_path: Path):
    output = tmp_path / "strategy_research_source_catalog_corpus.json"
    corpus = write_strategy_research_corpus(canonical_strategy_research_records(), output)

    assert output.exists()
    assert corpus["record_count"] >= 10
    assert corpus["safety"]["raw_text_not_stored"] is True
    assert corpus["safety"]["no_real_trade"] is True
    assert "record_hashes" in corpus


def test_v2_4_a_acceptance_writes_marker_hashes_and_reports(tmp_path: Path):
    report = validator.run_acceptance(
        output_root=tmp_path / "processed",
        reports_dir=tmp_path / "reports",
        run_id="v2_4_a_test",
        command="test command",
    )

    assert report["overall_status"] == "PASS"
    assert report["checks"]["covers_a_h_us"] is True
    assert report["checks"]["covers_core_strategy_families"] is True
    assert report["checks"]["requires_sandbox_before_suggestion"] is True
    assert report["production_records_written"] is False
    assert report["hashes"]["strategy_research_source_catalog_corpus"]
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()
    payload = json.loads((tmp_path / "reports" / validator.REPORT_JSON).read_text(encoding="utf-8"))
    assert payload["summary"]["next_target"] == "V2.4-B Strategy Research To Sandbox Hypothesis Queue"


def test_v2_4_a_cli_exits_zero_and_prints_no_secrets(tmp_path: Path, capsys):
    exit_code = validator.main(
        [
            "--output-root",
            str(tmp_path / "processed"),
            "--reports-dir",
            str(tmp_path / "reports"),
            "--run-id",
            "v2_4_a_cli",
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "PASS" in captured.out
    assert "secret" not in captured.out.lower()
    assert "token" not in captured.out.lower()
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()
