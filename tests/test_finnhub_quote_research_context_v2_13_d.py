from __future__ import annotations

import hashlib
import json
from pathlib import Path

from aegis.external_sources.finnhub_quote_research_context import (
    build_finnhub_quote_research_context_report,
    render_finnhub_quote_research_context_markdown,
)
import scripts.validate_v2_13_d_finnhub_quote_research_context as validator


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _source_report(tmp_path: Path) -> dict:
    quote_path = tmp_path / "us_aapl_finnhub_quote.json"
    quote_path.write_text(
        json.dumps(
            {
                "provider": "finnhub",
                "market": "US",
                "canonical_symbol": "AAPL.US",
                "provider_symbol": "AAPL",
                "current_price": 199.12,
                "previous_close": 198.12,
                "open": 198.5,
                "high": 200.0,
                "low": 198.0,
                "change": 1.0,
                "percent_change": 0.5,
                "provider_timestamp": 1783800000,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return {
        "overall_status": "PASS",
        "acceptance_target": "V2.13-C Finnhub Quote Cache Readiness Dry Run",
        "run_id": "unit_v2_13_c",
        "network_used": True,
        "summary": {
            "quote_cache_ready": True,
            "social_sentiment_status": "blocked_plan_or_rate_limit",
        },
        "results": [
            {
                "case_id": "us_aapl_finnhub_quote",
                "route_id": "us_quote_finnhub_verified_free",
                "provider": "finnhub",
                "market": "US",
                "canonical_symbol": "AAPL.US",
                "provider_symbol": "AAPL",
                "data_type": "quote",
                "status": "pass",
                "normalized_quote_json": str(quote_path),
                "normalized_quote_json_sha256": _sha256(quote_path),
            }
        ],
    }


def test_v2_13_d_builds_research_context_from_verified_quote_artifact(tmp_path: Path):
    report = build_finnhub_quote_research_context_report(
        source_report=_source_report(tmp_path),
        run_id="unit",
        generated_at="2026-07-12T00:00:00+08:00",
    )
    text = json.dumps(report, ensure_ascii=False)

    assert report["overall_status"] == "PASS"
    assert report["network_used"] is False
    assert report["summary"]["context_item_count"] == 1
    assert report["summary"]["symbols"] == ["AAPL.US"]
    assert report["checks"]["all_source_quote_artifacts_verified"] is True
    assert report["checks"]["source_social_sentiment_still_blocked"] is True
    item = report["context_items"][0]
    assert item["evidence_role"] == "research_context_only"
    assert item["requires_sandbox_before_suggestion"] is True
    assert item["requires_suggestion_gate_before_user_facing"] is True
    assert item["user_facing_suggestion_allowed"] is False
    assert item["no_position_size"] is True
    assert item["no_live_order_signal"] is True
    assert "token=" not in text
    assert "https://" not in text
    assert report["checks"]["raw_payloads_not_stored"] is True
    assert report["safety"]["no_raw_payload_storage"] is True


def test_v2_13_d_fails_if_source_report_not_pass(tmp_path: Path):
    source = _source_report(tmp_path)
    source["overall_status"] = "FAIL"

    report = build_finnhub_quote_research_context_report(source_report=source, run_id="unit")

    assert report["overall_status"] == "FAIL"
    assert report["checks"]["source_report_pass"] is False


def test_v2_13_d_fails_if_quote_artifact_hash_mismatch(tmp_path: Path):
    source = _source_report(tmp_path)
    source["results"][0]["normalized_quote_json_sha256"] = "bad"

    report = build_finnhub_quote_research_context_report(source_report=source, run_id="unit")

    assert report["overall_status"] == "FAIL"
    assert report["checks"]["all_source_quote_artifacts_verified"] is False
    assert report["summary"]["context_item_count"] == 0


def test_v2_13_d_fails_if_social_sentiment_unblocked(tmp_path: Path):
    source = _source_report(tmp_path)
    source["summary"]["social_sentiment_status"] = "ready"

    report = build_finnhub_quote_research_context_report(source_report=source, run_id="unit")

    assert report["overall_status"] == "FAIL"
    assert report["checks"]["source_social_sentiment_still_blocked"] is False


def test_v2_13_d_markdown_states_boundaries(tmp_path: Path):
    report = build_finnhub_quote_research_context_report(source_report=_source_report(tmp_path), run_id="unit")
    md = render_finnhub_quote_research_context_markdown(report)

    assert "Research context only" in md
    assert "Network is not used" in md
    assert "social sentiment remains blocked" in md
    assert "No real trade" in md


def test_v2_13_d_validator_writes_report_and_marker(tmp_path: Path):
    source_path = tmp_path / "source.json"
    source_path.write_text(json.dumps(_source_report(tmp_path), ensure_ascii=False), encoding="utf-8")

    report = validator.run_acceptance(
        output_root=tmp_path / "processed",
        reports_dir=tmp_path / "reports",
        run_id="v2_13_d_test",
        command="test command",
        source_report_json=source_path,
    )

    assert report["overall_status"] == "PASS"
    assert report["checks"]["context_json_written"] is True
    assert report["checks"]["source_report_hash_only"] is True
    assert report["safety"]["no_broker_api"] is True
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()


def test_v2_13_d_cli_like_acceptance_writes_latest_report(tmp_path: Path):
    source_path = tmp_path / "source.json"
    source_path.write_text(json.dumps(_source_report(tmp_path), ensure_ascii=False), encoding="utf-8")

    report = validator.run_acceptance(
        output_root=tmp_path / "processed",
        reports_dir=tmp_path / "reports",
        run_id="v2_13_d_cli_like",
        source_report_json=source_path,
    )

    assert report["overall_status"] == "PASS"
    assert (tmp_path / "reports" / validator.REPORT_JSON).exists()
