from __future__ import annotations

import json
from pathlib import Path

from aegis.external_sources.finnhub_quote_multi_symbol_research_context import (
    ACCEPTANCE_TARGET,
    build_finnhub_quote_multi_symbol_research_context_report,
    render_finnhub_quote_multi_symbol_research_context_markdown,
)
import scripts.validate_v2_13_s_finnhub_quote_multi_symbol_research_context as validator


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _source_report(tmp_path: Path) -> dict:
    results = []
    for symbol, provider_symbol in [("CRCL.US", "CRCL"), ("MSFT.US", "MSFT"), ("NVDA.US", "NVDA")]:
        case_id = f"us_{provider_symbol.lower()}_finnhub_quote"
        quote_path = tmp_path / "quotes" / f"{case_id}.json"
        _write_json(
            quote_path,
            {
                "provider": "finnhub",
                "market": "US",
                "canonical_symbol": symbol,
                "provider_symbol": provider_symbol,
                "current_price": 101.0,
                "previous_close": 100.0,
                "open": 99.0,
                "high": 102.0,
                "low": 98.0,
                "change": 1.0,
                "percent_change": 1.0,
                "provider_timestamp": 123456,
            },
        )
        import hashlib

        quote_hash = hashlib.sha256(quote_path.read_bytes()).hexdigest()
        results.append(
            {
                "case_id": case_id,
                "route_id": "us_quote_finnhub_verified_free",
                "provider": "finnhub",
                "market": "US",
                "canonical_symbol": symbol,
                "provider_symbol": provider_symbol,
                "data_type": "quote",
                "status": "pass",
                "normalized_quote_json": str(quote_path),
                "normalized_quote_json_sha256": quote_hash,
                "request_url_stored": False,
                "raw_payload_stored": False,
                "token_value_stored": False,
            }
        )
    return {
        "overall_status": "PASS",
        "acceptance_target": "V2.13-R Finnhub Quote Multi-Symbol Live Probe Dry Run",
        "network_used": True,
        "summary": {
            "quote_probe_ready": True,
            "passed_symbols": ["CRCL.US", "MSFT.US", "NVDA.US"],
            "social_sentiment_status": "blocked_plan_or_rate_limit",
        },
        "results": results,
    }


def test_v2_13_s_builds_three_research_context_items(tmp_path: Path):
    report = build_finnhub_quote_multi_symbol_research_context_report(
        _source_report(tmp_path),
        run_id="unit",
    )

    assert report["overall_status"] == "PASS"
    assert report["acceptance_target"] == ACCEPTANCE_TARGET
    assert report["summary"]["context_item_count"] == 3
    assert report["summary"]["symbols"] == ["CRCL.US", "MSFT.US", "NVDA.US"]
    assert report["checks"]["context_symbols_match_source_passed_symbols"] is True
    assert report["checks"]["all_source_quote_artifacts_verified"] is True
    assert all(item["evidence_role"] == "research_context_only" for item in report["context_items"])
    assert all(item["requires_sandbox_before_suggestion"] is True for item in report["context_items"])
    assert all(item["requires_suggestion_gate_before_user_facing"] is True for item in report["context_items"])
    assert all(item["user_facing_suggestion_allowed"] is False for item in report["context_items"])


def test_v2_13_s_markdown_shows_not_a_recommendation_boundary(tmp_path: Path):
    report = build_finnhub_quote_multi_symbol_research_context_report(_source_report(tmp_path), run_id="unit")

    md = render_finnhub_quote_multi_symbol_research_context_markdown(report)

    assert "V2.13-S Finnhub Quote Multi-Symbol Research Context Bridge" in md
    assert "CRCL.US" in md
    assert "MSFT.US" in md
    assert "NVDA.US" in md
    assert "not a recommendation" in md
    assert "Suggestion Gate" in md


def test_v2_13_s_validator_writes_outputs_without_touching_records(tmp_path: Path):
    source_json = tmp_path / "v2_13_r.json"
    source_marker = tmp_path / "v2_13_r.marker"
    _write_json(source_json, _source_report(tmp_path))
    source_marker.write_text("exit_code=0\n", encoding="utf-8")
    record = tmp_path / "records" / "recommendations.jsonl"
    record.parent.mkdir()
    record.write_text("existing\n", encoding="utf-8")

    report = validator.run_acceptance(
        output_root=tmp_path / "processed",
        reports_dir=tmp_path / "reports",
        run_id="v2_13_s_test",
        command="test command",
        source_v2_13_r_report_json=source_json,
        source_v2_13_r_pass_marker=source_marker,
        record_paths={"recommendations_jsonl": record},
    )

    assert report["overall_status"] == "PASS"
    assert report["checks"]["production_record_files_unchanged"] is True
    assert report["hashes"]["context_json"]
    assert record.read_text(encoding="utf-8") == "existing\n"
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()


def test_v2_13_s_cli_exits_zero_and_prints_no_secret_values(tmp_path: Path, capsys):
    source_json = tmp_path / "v2_13_r.json"
    source_marker = tmp_path / "v2_13_r.marker"
    _write_json(source_json, _source_report(tmp_path))
    source_marker.write_text("exit_code=0\n", encoding="utf-8")

    exit_code = validator.main(
        [
            "--output-root",
            str(tmp_path / "processed"),
            "--reports-dir",
            str(tmp_path / "reports"),
            "--run-id",
            "v2_13_s_cli",
            "--source-v2-13-r-report-json",
            str(source_json),
            "--source-v2-13-r-pass-marker",
            str(source_marker),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "PASS" in captured.out
    assert "CRCL.US,MSFT.US,NVDA.US" in captured.out
    assert "token" not in captured.out.lower()
    assert "secret" not in captured.out.lower()
