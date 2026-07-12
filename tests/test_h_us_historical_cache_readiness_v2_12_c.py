from __future__ import annotations

import json
from pathlib import Path

from aegis.external_sources.h_us_historical_cache_readiness import (
    build_h_us_historical_cache_readiness_report,
    render_h_us_historical_cache_readiness_markdown,
    run_h_us_cache_readiness_case,
)
import scripts.validate_v2_12_c_h_us_historical_cache_readiness as validator


def _metadata_report() -> dict:
    return {
        "overall_status": "PASS",
        "acceptance_target": "V2.12-B H-US Provider Metadata Activation",
        "run_id": "unit_v2_12_b",
        "summary": {
            "h_route": "eodhd_primary_ready",
            "us_route": "eodhd_primary_twelve_backup_ready",
            "twelve_data_h_status": "blocked_fetch_error",
        },
        "route_proposals": [
            {"route_id": "h_daily_bars_eodhd_primary", "status": "ready_for_metadata"},
            {"route_id": "us_daily_bars_eodhd_primary_twelve_backup", "status": "ready_for_metadata"},
            {"route_id": "h_daily_bars_twelve_data_review", "status": "blocked_fetch_error"},
        ],
    }


def _fetch_json(url: str):
    if "eodhd.com" in url:
        return 200, [
            {"date": "2026-07-01", "open": 10, "high": 11, "low": 9, "close": 10.5, "volume": 1000},
            {"date": "2026-07-02", "open": 10.5, "high": 12, "low": 10, "close": 11.5, "volume": 1200},
        ]
    return 200, {
        "status": "ok",
        "values": [
            {"datetime": "2026-07-02", "open": "20", "high": "21", "low": "19", "close": "20.5", "volume": "2000"},
            {"datetime": "2026-07-01", "open": "19", "high": "20", "low": "18", "close": "19.5", "volume": "1900"},
        ],
    }


def test_v2_12_c_writes_h_us_normalized_cache_samples(tmp_path: Path):
    report = build_h_us_historical_cache_readiness_report(
        metadata_report=_metadata_report(),
        output_dir=tmp_path / "cache",
        run_id="unit",
        env={"AEGIS_EODHD_API_TOKEN": "secret", "AEGIS_TWELVE_DATA_API_KEY": "secret"},
        fetch_json=_fetch_json,
        generated_at="2026-07-12T00:00:00+08:00",
    )
    text = json.dumps(report, ensure_ascii=False)

    assert report["overall_status"] == "PASS"
    assert report["network_used"] is False
    assert report["summary"]["h_cache_ready"] is True
    assert report["summary"]["us_cache_ready"] is True
    assert report["checks"]["production_cache_not_mutated"] is True
    assert report["checks"]["suggestion_path_not_enabled"] is True
    assert "api_token=" not in text
    assert "apikey=" not in text
    assert "https://" not in text
    for result in report["results"]:
        if result["status"] == "pass":
            assert Path(result["normalized_csv"]).exists()
            assert result["normalized_csv_sha256"]


def test_v2_12_c_missing_env_blocks_before_fetch(tmp_path: Path):
    called = False

    def fetch_json(_url: str):
        nonlocal called
        called = True
        return 200, []

    result = run_h_us_cache_readiness_case(
        {
            "case_id": "unit",
            "route_id": "h_daily_bars_eodhd_primary",
            "provider": "eodhd",
            "market": "H",
            "canonical_symbol": "00700.HK",
            "provider_symbol": "0700.HK",
            "data_type": "daily_bars",
            "from_date": "2026-07-01",
            "to_date": "2026-07-08",
        },
        output_dir=tmp_path,
        env={},
        fetch_json=fetch_json,
    )

    assert called is False
    assert result["status"] == "blocked_missing_env"
    assert result["request_url_stored"] is False
    assert result["raw_payload_stored"] is False


def test_v2_12_c_fails_if_metadata_not_b_ready(tmp_path: Path):
    metadata = _metadata_report()
    metadata["overall_status"] = "FAIL"
    report = build_h_us_historical_cache_readiness_report(
        metadata_report=metadata,
        output_dir=tmp_path / "cache",
        run_id="unit",
        env={"AEGIS_EODHD_API_TOKEN": "secret", "AEGIS_TWELVE_DATA_API_KEY": "secret"},
        fetch_json=_fetch_json,
    )

    assert report["overall_status"] == "FAIL"
    assert report["checks"]["source_metadata_report_pass"] is False


def test_v2_12_c_markdown_states_boundaries(tmp_path: Path):
    report = build_h_us_historical_cache_readiness_report(
        metadata_report=_metadata_report(),
        output_dir=tmp_path / "cache",
        run_id="unit",
        env={"AEGIS_EODHD_API_TOKEN": "secret", "AEGIS_TWELVE_DATA_API_KEY": "secret"},
        fetch_json=_fetch_json,
    )
    md = render_h_us_historical_cache_readiness_markdown(report)

    assert "Historical cache readiness only" in md
    assert "production cache is not mutated" in md
    assert "No candidate/suggestion path activation" in md
    assert "No real trade" in md


def test_v2_12_c_validator_writes_report_and_marker(tmp_path: Path):
    source = tmp_path / "metadata.json"
    source.write_text(json.dumps(_metadata_report(), ensure_ascii=False), encoding="utf-8")
    report = validator.run_acceptance(
        output_root=tmp_path / "processed",
        reports_dir=tmp_path / "reports",
        run_id="v2_12_c_test",
        command="test command",
        source_metadata_report_json=source,
        env={"AEGIS_EODHD_API_TOKEN": "secret", "AEGIS_TWELVE_DATA_API_KEY": "secret"},
        fetch_json=_fetch_json,
    )

    assert report["overall_status"] == "PASS"
    assert report["checks"]["readiness_report_json_written"] is True
    assert report["checks"]["source_metadata_hash_only"] is True
    assert report["safety"]["no_broker_api"] is True
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()


def test_v2_12_c_cli_exits_zero_with_mocked_validator(tmp_path: Path):
    source = tmp_path / "metadata.json"
    source.write_text(json.dumps(_metadata_report(), ensure_ascii=False), encoding="utf-8")
    report = validator.run_acceptance(
        output_root=tmp_path / "processed",
        reports_dir=tmp_path / "reports",
        run_id="v2_12_c_cli_like",
        source_metadata_report_json=source,
        env={"AEGIS_EODHD_API_TOKEN": "secret", "AEGIS_TWELVE_DATA_API_KEY": "secret"},
        fetch_json=_fetch_json,
    )

    assert report["overall_status"] == "PASS"
    assert (tmp_path / "reports" / validator.REPORT_JSON).exists()
