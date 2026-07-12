from __future__ import annotations

import json
from pathlib import Path

from aegis.external_sources.finnhub_metadata_activation import (
    build_finnhub_metadata_activation,
    render_finnhub_metadata_activation_markdown,
)
import scripts.validate_v2_13_b_finnhub_metadata_activation as validator


def _probe_report() -> dict:
    return {
        "overall_status": "PASS",
        "acceptance_target": "V2.13-A Finnhub Free Probe",
        "run_id": "unit_v2_13_a",
        "summary": {
            "quote_status": "pass",
            "social_sentiment_status": "blocked_plan_or_rate_limit",
        },
        "results": [
            {
                "provider": "finnhub",
                "endpoint": "quote",
                "market": "US",
                "symbol": "AAPL",
                "data_type": "quote",
                "required_env_vars": ["AEGIS_FINNHUB_API_KEY", "AEGIS_FINNHUB_API_TOKEN"],
                "env_var_used": "AEGIS_FINNHUB_API_KEY",
                "status": "pass",
                "ok": True,
                "summary_sha256": "quote-summary",
                "blocked_by": [],
                "request_url_stored": False,
                "raw_payload_stored": False,
                "token_value_stored": False,
            },
            {
                "provider": "finnhub",
                "endpoint": "social_sentiment",
                "market": "US",
                "symbol": "AAPL",
                "data_type": "social_sentiment",
                "required_env_vars": ["AEGIS_FINNHUB_API_KEY", "AEGIS_FINNHUB_API_TOKEN"],
                "env_var_used": "AEGIS_FINNHUB_API_KEY",
                "status": "blocked_plan_or_rate_limit",
                "ok": False,
                "summary_sha256": "social-summary",
                "blocked_by": ["social_sentiment_not_available_on_current_plan_or_rate_limit"],
                "request_url_stored": False,
                "raw_payload_stored": False,
                "token_value_stored": False,
            },
        ],
    }


def test_v2_13_b_builds_secret_safe_finnhub_metadata_packet():
    packet = build_finnhub_metadata_activation(
        probe_report=_probe_report(),
        run_id="unit",
        generated_at="2026-07-12T00:00:00+08:00",
    )
    text = json.dumps(packet, ensure_ascii=False)

    assert packet["overall_status"] == "PASS"
    assert packet["summary"]["quote_route"] == "finnhub_quote_ready"
    assert packet["summary"]["social_sentiment_route"] == "blocked_plan_or_rate_limit"
    assert packet["checks"]["production_provider_config_not_mutated"] is True
    assert packet["checks"]["suggestion_path_not_enabled"] is True
    assert packet["safety"]["social_sentiment_not_enabled"] is True
    assert "token=" not in text
    assert "api_key=" not in text
    assert "https://" not in text


def test_v2_13_b_social_sentiment_route_is_blocked():
    packet = build_finnhub_metadata_activation(probe_report=_probe_report(), run_id="unit")
    route = next(
        item for item in packet["route_proposals"] if item["route_id"] == "us_social_sentiment_finnhub_plan_blocked"
    )

    assert route["status"] == "blocked_plan_or_rate_limit"
    assert route["allowed_uses"] == []
    assert "suggestion_inputs" in route["forbidden_uses"]
    assert route["bypass_allowed"] is False
    assert route["suggestion_path_enabled"] is False


def test_v2_13_b_quote_route_is_metadata_only():
    packet = build_finnhub_metadata_activation(probe_report=_probe_report(), run_id="unit")
    route = next(item for item in packet["route_proposals"] if item["route_id"] == "us_quote_finnhub_verified_free")

    assert route["status"] == "ready_for_metadata"
    assert route["allowed_uses"] == ["provider_health_check", "quote_freshness_probe", "research_context_inputs"]
    assert "real_trade" in route["forbidden_uses"]
    assert route["suggestion_path_enabled"] is False


def test_v2_13_b_secret_like_source_report_fails():
    report = _probe_report()
    report["debug"] = "token=SHOULD_NOT_BE_STORED"
    packet = build_finnhub_metadata_activation(probe_report=report, run_id="unit")

    assert packet["overall_status"] == "FAIL"
    assert packet["checks"]["source_secret_like_material_absent"] is False


def test_v2_13_b_markdown_states_boundaries():
    packet = build_finnhub_metadata_activation(probe_report=_probe_report(), run_id="unit")
    md = render_finnhub_metadata_activation_markdown(packet)

    assert "Route Proposals" in md
    assert "social sentiment remains plan/rate-limit blocked" in md
    assert "Production provider config is not mutated" in md
    assert "Suggestion path is not enabled" in md


def test_v2_13_b_validator_writes_packet_and_marker(tmp_path: Path):
    source = tmp_path / "v2_13_a.json"
    source.write_text(json.dumps(_probe_report(), ensure_ascii=False), encoding="utf-8")

    report = validator.run_acceptance(
        output_root=tmp_path / "processed",
        reports_dir=tmp_path / "reports",
        run_id="v2_13_b_test",
        command="test command",
        source_probe_report_json=source,
    )

    assert report["overall_status"] == "PASS"
    assert report["checks"]["packet_json_written"] is True
    assert report["checks"]["source_probe_hash_only"] is True
    assert report["safety"]["no_broker_api"] is True
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()


def test_v2_13_b_cli_exits_zero(tmp_path: Path, capsys):
    source = tmp_path / "v2_13_a.json"
    source.write_text(json.dumps(_probe_report(), ensure_ascii=False), encoding="utf-8")

    exit_code = validator.main(
        [
            "--output-root",
            str(tmp_path / "processed"),
            "--reports-dir",
            str(tmp_path / "reports"),
            "--run-id",
            "v2_13_b_cli",
            "--source-probe-report-json",
            str(source),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "PASS" in captured.out
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()
