from __future__ import annotations

import json
from pathlib import Path

from aegis.external_sources.h_us_provider_metadata_activation import (
    build_h_us_provider_metadata_activation,
    contains_secret_like_material,
    render_h_us_provider_metadata_activation_markdown,
)
import scripts.validate_v2_12_b_h_us_provider_metadata_activation as validator


def _probe_report() -> dict:
    return {
        "overall_status": "PASS",
        "acceptance_target": "V2.12-A EODHD Twelve Data H-US Provider Probe",
        "run_id": "unit_v2_12_a",
        "summary": {
            "case_count": 4,
            "pass_count": 3,
            "fail_count": 1,
            "h_us_provider_status": {"H": ["eodhd"], "US": ["eodhd", "twelve_data"]},
        },
        "results": [
            {
                "provider": "eodhd",
                "market": "US",
                "symbol": "AAPL.US",
                "data_type": "daily_bars",
                "required_env_var": "AEGIS_EODHD_API_TOKEN",
                "status": "pass",
                "ok": True,
                "summary_sha256": "us-eodhd-summary",
                "blocked_by": [],
            },
            {
                "provider": "eodhd",
                "market": "H",
                "symbol": "0700.HK",
                "data_type": "daily_bars",
                "required_env_var": "AEGIS_EODHD_API_TOKEN",
                "status": "pass",
                "ok": True,
                "summary_sha256": "h-eodhd-summary",
                "blocked_by": [],
            },
            {
                "provider": "twelve_data",
                "market": "US",
                "symbol": "AAPL",
                "data_type": "daily_bars",
                "required_env_var": "AEGIS_TWELVE_DATA_API_KEY",
                "status": "pass",
                "ok": True,
                "summary_sha256": "us-twelve-summary",
                "blocked_by": [],
            },
            {
                "provider": "twelve_data",
                "market": "H",
                "symbol": "0700",
                "data_type": "daily_bars",
                "required_env_var": "AEGIS_TWELVE_DATA_API_KEY",
                "status": "fail",
                "ok": False,
                "error_type": "HTTPError",
                "blocked_by": ["fetch_error"],
            },
        ],
        "checks": {
            "no_secret_values_stored": True,
            "request_urls_not_stored": True,
            "raw_payloads_not_stored": True,
        },
    }


def test_v2_12_b_builds_secret_safe_h_us_route_packet():
    packet = build_h_us_provider_metadata_activation(
        probe_report=_probe_report(),
        run_id="unit",
        generated_at="2026-07-12T00:00:00+08:00",
    )
    text = json.dumps(packet, ensure_ascii=False)

    assert packet["overall_status"] == "PASS"
    assert packet["summary"]["h_route"] == "eodhd_primary_ready"
    assert packet["summary"]["us_route"] == "eodhd_primary_twelve_backup_ready"
    assert packet["summary"]["twelve_data_h_status"] == "blocked_fetch_error"
    assert packet["checks"]["production_provider_config_not_mutated"] is True
    assert packet["checks"]["suggestion_path_not_enabled"] is True
    assert "api_token=" not in text
    assert "apikey=" not in text
    assert "https://" not in text


def test_v2_12_b_hk_symbol_rule_is_explicit():
    packet = build_h_us_provider_metadata_activation(probe_report=_probe_report(), run_id="unit")
    h_route = next(route for route in packet["route_proposals"] if route["route_id"] == "h_daily_bars_eodhd_primary")

    assert h_route["primary_provider"] == "eodhd"
    assert h_route["symbol_rules"]["examples"] == [
        {"canonical": "00700.HK", "eodhd": "0700.HK"},
        {"canonical": "00005.HK", "eodhd": "0005.HK"},
    ]
    assert "real_trade" in h_route["forbidden_uses"]


def test_v2_12_b_secret_like_source_report_fails():
    report = _probe_report()
    report["debug"] = "apikey=SHOULD_NOT_BE_STORED"
    packet = build_h_us_provider_metadata_activation(probe_report=report, run_id="unit")

    assert contains_secret_like_material(report) is True
    assert packet["overall_status"] == "FAIL"
    assert packet["checks"]["source_secret_like_material_absent"] is False


def test_v2_12_b_markdown_states_boundaries():
    packet = build_h_us_provider_metadata_activation(probe_report=_probe_report(), run_id="unit")
    md = render_h_us_provider_metadata_activation_markdown(packet)

    assert "Route Proposals" in md
    assert "Production provider config is not mutated" in md
    assert "Suggestion path is not enabled" in md
    assert "No real trade" in md


def test_v2_12_b_validator_writes_packet_and_marker(tmp_path: Path):
    source = tmp_path / "v2_12_a.json"
    source.write_text(json.dumps(_probe_report(), ensure_ascii=False), encoding="utf-8")

    report = validator.run_acceptance(
        output_root=tmp_path / "processed",
        reports_dir=tmp_path / "reports",
        run_id="v2_12_b_test",
        command="test command",
        source_probe_report_json=source,
    )

    assert report["overall_status"] == "PASS"
    assert report["checks"]["packet_json_written"] is True
    assert report["checks"]["source_probe_hash_only"] is True
    assert report["safety"]["no_broker_api"] is True
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()


def test_v2_12_b_cli_exits_zero(tmp_path: Path, capsys):
    source = tmp_path / "v2_12_a.json"
    source.write_text(json.dumps(_probe_report(), ensure_ascii=False), encoding="utf-8")

    exit_code = validator.main(
        [
            "--output-root",
            str(tmp_path / "processed"),
            "--reports-dir",
            str(tmp_path / "reports"),
            "--run-id",
            "v2_12_b_cli",
            "--source-probe-report-json",
            str(source),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "PASS" in captured.out
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()
