from __future__ import annotations

import json
from pathlib import Path

from aegis.external_sources.finnhub_quote_multi_symbol_sandbox_binding import (
    ACCEPTANCE_TARGET,
    build_finnhub_quote_multi_symbol_sandbox_binding_report,
    render_finnhub_quote_multi_symbol_sandbox_binding_markdown,
)
import scripts.validate_v2_13_t_finnhub_quote_multi_symbol_sandbox_binding as validator


def _source_report() -> dict:
    context_items = []
    for symbol, provider_symbol in [("CRCL.US", "CRCL"), ("MSFT.US", "MSFT"), ("NVDA.US", "NVDA")]:
        case_id = f"us_{provider_symbol.lower()}_finnhub_quote"
        context_items.append(
            {
                "context_id": f"finnhub_quote_context_{case_id}",
                "provider": "finnhub",
                "market": "US",
                "canonical_symbol": symbol,
                "provider_symbol": provider_symbol,
                "source_case_id": case_id,
                "source_route_id": "us_quote_finnhub_verified_free",
                "source_quote_json": f"/tmp/{case_id}.json",
                "source_quote_json_sha256": f"hash-{case_id}",
                "source_artifact_ref_sha256": f"ref-{case_id}",
                "evidence_role": "research_context_only",
                "evidence_type": "multi_symbol_price_data",
                "evidence_status": "verified",
                "requires_sandbox_before_suggestion": True,
                "requires_suggestion_gate_before_user_facing": True,
                "user_facing_suggestion_allowed": False,
                "auto_applied": False,
            }
        )
    return {
        "overall_status": "PASS",
        "acceptance_target": "V2.13-S Finnhub Quote Multi-Symbol Research Context Bridge",
        "summary": {
            "context_item_count": 3,
            "symbols": ["CRCL.US", "MSFT.US", "NVDA.US"],
            "social_sentiment_status": "blocked_plan_or_rate_limit",
        },
        "context_items": context_items,
    }


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def test_v2_13_t_binds_three_contexts_to_pending_sandbox_candidates():
    report = build_finnhub_quote_multi_symbol_sandbox_binding_report(_source_report(), run_id="unit")

    assert report["overall_status"] == "PASS"
    assert report["acceptance_target"] == ACCEPTANCE_TARGET
    assert report["summary"]["binding_count"] == 3
    assert report["summary"]["symbols"] == ["CRCL.US", "MSFT.US", "NVDA.US"]
    assert report["summary"]["binding_statuses"] == ["bound_pending_historical_cases"]
    assert report["checks"]["binding_symbols_match_source_symbols"] is True
    assert report["checks"]["no_historical_sandbox_result_claimed"] is True
    assert all(item["binding_status"] == "bound_pending_historical_cases" for item in report["bindings"])
    assert all("historical_cases" in item["required_next_inputs"] for item in report["bindings"])
    assert all("sandbox_evaluation" in item["required_next_inputs"] for item in report["bindings"])
    assert all("suggestion_gate" in item["required_next_inputs"] for item in report["bindings"])
    assert all(item["user_facing_suggestion_allowed"] is False for item in report["bindings"])


def test_v2_13_t_markdown_shows_pending_boundary():
    report = build_finnhub_quote_multi_symbol_sandbox_binding_report(_source_report(), run_id="unit")

    md = render_finnhub_quote_multi_symbol_sandbox_binding_markdown(report)

    assert "V2.13-T Finnhub Quote Multi-Symbol Sandbox Candidate Binding" in md
    assert "CRCL.US" in md
    assert "MSFT.US" in md
    assert "NVDA.US" in md
    assert "bound_pending_historical_cases" in md
    assert "Historical cases" in md
    assert "Suggestion Gate" in md


def test_v2_13_t_validator_writes_outputs_without_touching_records(tmp_path: Path):
    source_json = tmp_path / "v2_13_s.json"
    source_marker = tmp_path / "v2_13_s.marker"
    _write_json(source_json, _source_report())
    source_marker.write_text("exit_code=0\n", encoding="utf-8")
    record = tmp_path / "records" / "recommendations.jsonl"
    record.parent.mkdir()
    record.write_text("existing\n", encoding="utf-8")

    report = validator.run_acceptance(
        output_root=tmp_path / "processed",
        reports_dir=tmp_path / "reports",
        run_id="v2_13_t_test",
        command="test command",
        source_v2_13_s_report_json=source_json,
        source_v2_13_s_pass_marker=source_marker,
        record_paths={"recommendations_jsonl": record},
    )

    assert report["overall_status"] == "PASS"
    assert report["checks"]["production_record_files_unchanged"] is True
    assert report["hashes"]["binding_json"]
    assert report["hashes"]["candidates_json"]
    assert record.read_text(encoding="utf-8") == "existing\n"
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()


def test_v2_13_t_cli_exits_zero_and_prints_no_secret_values(tmp_path: Path, capsys):
    source_json = tmp_path / "v2_13_s.json"
    source_marker = tmp_path / "v2_13_s.marker"
    _write_json(source_json, _source_report())
    source_marker.write_text("exit_code=0\n", encoding="utf-8")

    exit_code = validator.main(
        [
            "--output-root",
            str(tmp_path / "processed"),
            "--reports-dir",
            str(tmp_path / "reports"),
            "--run-id",
            "v2_13_t_cli",
            "--source-v2-13-s-report-json",
            str(source_json),
            "--source-v2-13-s-pass-marker",
            str(source_marker),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "PASS" in captured.out
    assert "CRCL.US,MSFT.US,NVDA.US" in captured.out
    assert "token" not in captured.out.lower()
    assert "secret" not in captured.out.lower()
