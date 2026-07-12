from __future__ import annotations

import json
from pathlib import Path

from aegis.external_sources.finnhub_quote_cache_readiness import (
    build_finnhub_quote_cache_readiness_report,
    render_finnhub_quote_cache_readiness_markdown,
    run_finnhub_quote_cache_readiness_case,
)
import scripts.validate_v2_13_c_finnhub_quote_cache_readiness as validator


def _metadata_report() -> dict:
    return {
        "overall_status": "PASS",
        "acceptance_target": "V2.13-B Finnhub Metadata Activation",
        "run_id": "unit_v2_13_b",
        "summary": {
            "quote_route": "finnhub_quote_ready",
            "social_sentiment_route": "blocked_plan_or_rate_limit",
        },
        "route_proposals": [
            {"route_id": "us_quote_finnhub_verified_free", "status": "ready_for_metadata"},
            {"route_id": "us_social_sentiment_finnhub_plan_blocked", "status": "blocked_plan_or_rate_limit"},
        ],
    }


def _fetch_json(url: str):
    return 200, {"c": 199.12, "pc": 198.12, "o": 198.5, "h": 200.0, "l": 198.0, "d": 1.0, "dp": 0.5, "t": 1783800000}


def test_v2_13_c_writes_run_specific_normalized_quote_samples(tmp_path: Path):
    report = build_finnhub_quote_cache_readiness_report(
        metadata_report=_metadata_report(),
        output_dir=tmp_path / "cache",
        run_id="unit",
        env={"AEGIS_FINNHUB_API_KEY": "secret"},
        fetch_json=_fetch_json,
        generated_at="2026-07-12T00:00:00+08:00",
    )
    text = json.dumps(report, ensure_ascii=False)

    assert report["overall_status"] == "PASS"
    assert report["network_used"] is False
    assert report["summary"]["quote_cache_ready"] is True
    assert report["summary"]["social_sentiment_status"] == "blocked_plan_or_rate_limit"
    assert report["checks"]["production_cache_not_mutated"] is True
    assert report["checks"]["suggestion_path_not_enabled"] is True
    assert report["checks"]["social_sentiment_not_enabled"] is True
    assert "token=" not in text
    assert "https://" not in text
    result = report["results"][0]
    assert Path(result["normalized_quote_json"]).exists()
    assert Path(result["normalized_quote_csv"]).exists()
    assert result["normalized_quote_json_sha256"]
    assert result["normalized_quote_csv_sha256"]


def test_v2_13_c_missing_env_blocks_before_fetch(tmp_path: Path):
    called = False

    def fetch_json(_url: str):
        nonlocal called
        called = True
        return 200, {}

    result = run_finnhub_quote_cache_readiness_case(
        {
            "case_id": "unit",
            "route_id": "us_quote_finnhub_verified_free",
            "provider": "finnhub",
            "market": "US",
            "canonical_symbol": "AAPL.US",
            "provider_symbol": "AAPL",
            "data_type": "quote",
        },
        output_dir=tmp_path,
        env={},
        fetch_json=fetch_json,
    )

    assert called is False
    assert result["status"] == "blocked_missing_env"
    assert result["request_url_stored"] is False
    assert result["raw_payload_stored"] is False


def test_v2_13_c_fails_if_metadata_not_b_ready(tmp_path: Path):
    metadata = _metadata_report()
    metadata["overall_status"] = "FAIL"
    report = build_finnhub_quote_cache_readiness_report(
        metadata_report=metadata,
        output_dir=tmp_path / "cache",
        run_id="unit",
        env={"AEGIS_FINNHUB_API_KEY": "secret"},
        fetch_json=_fetch_json,
    )

    assert report["overall_status"] == "FAIL"
    assert report["checks"]["source_metadata_report_pass"] is False


def test_v2_13_c_fails_if_social_sentiment_route_not_blocked(tmp_path: Path):
    metadata = _metadata_report()
    metadata["route_proposals"][1]["status"] = "ready_for_metadata"
    report = build_finnhub_quote_cache_readiness_report(
        metadata_report=metadata,
        output_dir=tmp_path / "cache",
        run_id="unit",
        env={"AEGIS_FINNHUB_API_KEY": "secret"},
        fetch_json=_fetch_json,
    )

    assert report["overall_status"] == "FAIL"
    assert report["checks"]["social_sentiment_still_blocked"] is False


def test_v2_13_c_markdown_states_boundaries(tmp_path: Path):
    report = build_finnhub_quote_cache_readiness_report(
        metadata_report=_metadata_report(),
        output_dir=tmp_path / "cache",
        run_id="unit",
        env={"AEGIS_FINNHUB_API_KEY": "secret"},
        fetch_json=_fetch_json,
    )
    md = render_finnhub_quote_cache_readiness_markdown(report)

    assert "Quote cache readiness only" in md
    assert "production cache is not mutated" in md
    assert "social sentiment remains plan/rate-limit blocked" in md
    assert "No candidate/suggestion path activation" in md


def test_v2_13_c_validator_writes_report_and_marker(tmp_path: Path):
    source = tmp_path / "metadata.json"
    source.write_text(json.dumps(_metadata_report(), ensure_ascii=False), encoding="utf-8")
    report = validator.run_acceptance(
        output_root=tmp_path / "processed",
        reports_dir=tmp_path / "reports",
        run_id="v2_13_c_test",
        command="test command",
        source_metadata_report_json=source,
        env={"AEGIS_FINNHUB_API_KEY": "secret"},
        fetch_json=_fetch_json,
    )

    assert report["overall_status"] == "PASS"
    assert report["checks"]["readiness_report_json_written"] is True
    assert report["checks"]["source_metadata_hash_only"] is True
    assert report["safety"]["no_broker_api"] is True
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()


def test_v2_13_c_cli_like_acceptance_writes_report(tmp_path: Path):
    source = tmp_path / "metadata.json"
    source.write_text(json.dumps(_metadata_report(), ensure_ascii=False), encoding="utf-8")
    report = validator.run_acceptance(
        output_root=tmp_path / "processed",
        reports_dir=tmp_path / "reports",
        run_id="v2_13_c_cli_like",
        source_metadata_report_json=source,
        env={"AEGIS_FINNHUB_API_KEY": "secret"},
        fetch_json=_fetch_json,
    )

    assert report["overall_status"] == "PASS"
    assert (tmp_path / "reports" / validator.REPORT_JSON).exists()
