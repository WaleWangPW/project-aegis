from __future__ import annotations

import json
from pathlib import Path

from aegis.external_sources.finnhub_quote_sandbox_binding import (
    build_finnhub_quote_sandbox_binding_report,
    render_finnhub_quote_sandbox_binding_markdown,
)
import scripts.validate_v2_13_e_finnhub_quote_sandbox_binding as validator


def _source_report() -> dict:
    return {
        "overall_status": "PASS",
        "acceptance_target": "V2.13-D Finnhub Quote Research Context Bridge",
        "run_id": "unit_v2_13_d",
        "summary": {
            "context_item_count": 1,
            "social_sentiment_status": "blocked_plan_or_rate_limit",
        },
        "context_items": [
            {
                "context_id": "finnhub_quote_context_us_aapl_finnhub_quote",
                "provider": "finnhub",
                "market": "US",
                "canonical_symbol": "AAPL.US",
                "provider_symbol": "AAPL",
                "source_case_id": "us_aapl_finnhub_quote",
                "source_quote_json": "/tmp/aapl.json",
                "source_quote_json_sha256": "quotehash",
                "evidence_role": "research_context_only",
                "evidence_type": "price_data",
                "evidence_status": "verified",
                "requires_sandbox_before_suggestion": True,
                "requires_suggestion_gate_before_user_facing": True,
                "user_facing_suggestion_allowed": False,
                "auto_applied": False,
                "no_position_size": True,
                "no_live_order_signal": True,
            }
        ],
    }


def test_v2_13_e_builds_pending_sandbox_candidate_binding():
    report = build_finnhub_quote_sandbox_binding_report(
        source_report=_source_report(),
        run_id="unit",
        generated_at="2026-07-12T00:00:00+08:00",
    )
    text = json.dumps(report, ensure_ascii=False)

    assert report["overall_status"] == "PASS"
    assert report["network_used"] is False
    assert report["summary"]["binding_count"] == 1
    assert report["summary"]["symbols"] == ["AAPL.US"]
    assert report["summary"]["historical_cases_required"] is True
    assert report["summary"]["user_facing_suggestion_allowed"] is False
    binding = report["bindings"][0]
    assert binding["binding_status"] == "bound_pending_historical_cases"
    assert "historical_cases" in binding["required_next_inputs"]
    assert "sandbox_evaluation" in binding["required_next_inputs"]
    assert "suggestion_gate" in binding["required_next_inputs"]
    assert binding["strategy_candidate"]["market"] == "US"
    assert binding["strategy_candidate"]["pass_criteria"]["min_sample_count"] == 3
    assert binding["user_facing_suggestion_allowed"] is False
    assert report["checks"]["no_historical_sandbox_result_claimed"] is True
    assert "token=" not in text
    assert "https://" not in text


def test_v2_13_e_fails_if_source_not_pass():
    source = _source_report()
    source["overall_status"] = "FAIL"

    report = build_finnhub_quote_sandbox_binding_report(source_report=source, run_id="unit")

    assert report["overall_status"] == "FAIL"
    assert report["checks"]["source_report_pass"] is False


def test_v2_13_e_fails_if_context_allows_user_facing_suggestion():
    source = _source_report()
    source["context_items"][0]["user_facing_suggestion_allowed"] = True

    report = build_finnhub_quote_sandbox_binding_report(source_report=source, run_id="unit")

    assert report["overall_status"] == "FAIL"
    assert report["checks"]["all_contexts_forbid_direct_suggestions"] is False


def test_v2_13_e_fails_if_social_sentiment_unblocked():
    source = _source_report()
    source["summary"]["social_sentiment_status"] = "ready"

    report = build_finnhub_quote_sandbox_binding_report(source_report=source, run_id="unit")

    assert report["overall_status"] == "FAIL"
    assert report["checks"]["source_social_sentiment_still_blocked"] is False


def test_v2_13_e_markdown_states_pending_historical_cases():
    report = build_finnhub_quote_sandbox_binding_report(source_report=_source_report(), run_id="unit")
    md = render_finnhub_quote_sandbox_binding_markdown(report)

    assert "Sandbox candidate binding only" in md
    assert "single quote snapshot is not a historical sandbox result" in md
    assert "Historical cases" in md
    assert "No user-facing suggestion" in md


def test_v2_13_e_validator_writes_report_and_marker(tmp_path: Path):
    source_path = tmp_path / "source.json"
    source_path.write_text(json.dumps(_source_report(), ensure_ascii=False), encoding="utf-8")

    report = validator.run_acceptance(
        output_root=tmp_path / "processed",
        reports_dir=tmp_path / "reports",
        run_id="v2_13_e_test",
        command="test command",
        source_report_json=source_path,
    )

    assert report["overall_status"] == "PASS"
    assert report["checks"]["binding_json_written"] is True
    assert report["checks"]["candidates_json_written"] is True
    assert report["safety"]["no_broker_api"] is True
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()


def test_v2_13_e_cli_like_acceptance_writes_latest_report(tmp_path: Path):
    source_path = tmp_path / "source.json"
    source_path.write_text(json.dumps(_source_report(), ensure_ascii=False), encoding="utf-8")

    report = validator.run_acceptance(
        output_root=tmp_path / "processed",
        reports_dir=tmp_path / "reports",
        run_id="v2_13_e_cli_like",
        source_report_json=source_path,
    )

    assert report["overall_status"] == "PASS"
    assert (tmp_path / "reports" / validator.REPORT_JSON).exists()
