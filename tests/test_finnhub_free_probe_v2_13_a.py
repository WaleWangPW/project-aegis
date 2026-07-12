from __future__ import annotations

import json
from pathlib import Path

from aegis.external_sources.finnhub_free_probe import build_finnhub_free_probe_report, probe_finnhub_case
import scripts.validate_v2_13_a_finnhub_free_probe as validator


def _fetch_json(url: str):
    if "quote" in url:
        return 200, {"c": 199.12, "d": 1.0, "dp": 0.5, "h": 200.0, "l": 198.0, "o": 198.5, "pc": 198.12, "t": 1}
    if "social-sentiment" in url:
        return 403, {"error": "Premium access required"}
    raise AssertionError(f"unexpected url: {url}")


def _fetch_json_social_ok(url: str):
    if "quote" in url:
        return 200, {"c": 199.12, "pc": 198.12, "t": 1}
    if "social-sentiment" in url:
        return 200, {"reddit": [{"atTime": "2026-07-12", "score": 0.1}], "twitter": []}
    raise AssertionError(f"unexpected url: {url}")


def test_v2_13_a_blocks_missing_env_without_fetch():
    called = False

    def fetch_json(_url: str):
        nonlocal called
        called = True
        return 200, {}

    result = probe_finnhub_case(
        {"endpoint": "quote", "market": "US", "symbol": "AAPL", "data_type": "quote"},
        env={},
        fetch_json=fetch_json,
    )

    assert result["status"] == "blocked_missing_env"
    assert result["env_present"] is False
    assert result["token_value_stored"] is False
    assert result["request_url_stored"] is False
    assert called is False


def test_v2_13_a_passes_with_quote_and_plan_blocked_social_sentiment():
    report = build_finnhub_free_probe_report(
        run_id="unit",
        env={"AEGIS_FINNHUB_API_KEY": "unit-finnhub-key"},
        fetch_json=_fetch_json,
    )
    text = json.dumps(report, ensure_ascii=False)

    assert report["overall_status"] == "PASS"
    assert report["summary"]["quote_status"] == "pass"
    assert report["summary"]["social_sentiment_status"] == "blocked_plan_or_rate_limit"
    assert report["checks"]["quote_endpoint_passed"] is True
    assert "unit-finnhub-key" not in text
    assert "token=" not in text


def test_v2_13_a_passes_with_social_sentiment_series():
    report = build_finnhub_free_probe_report(
        run_id="unit",
        env={"AEGIS_FINNHUB_API_TOKEN": "unit-fallback-key"},
        fetch_json=_fetch_json_social_ok,
    )
    text = json.dumps(report, ensure_ascii=False)

    assert report["overall_status"] == "PASS"
    assert report["summary"]["social_sentiment_status"] == "pass"
    assert "unit-fallback-key" not in text


def test_v2_13_a_validator_writes_pass_report_and_marker(tmp_path: Path):
    report = validator.run_acceptance(
        output_root=tmp_path / "processed",
        reports_dir=tmp_path / "reports",
        run_id="v2_13_a_test",
        command="test command",
        env={"AEGIS_FINNHUB_API_KEY": "unit-finnhub-key"},
        fetch_json=_fetch_json,
    )

    assert report["overall_status"] == "PASS"
    assert report["hashes"]["run_report_json"]
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()
    assert not (tmp_path / "reports" / validator.FAIL_MARKER).exists()


def test_v2_13_a_validator_writes_blocked_marker_when_env_missing(tmp_path: Path):
    report = validator.run_acceptance(
        output_root=tmp_path / "processed",
        reports_dir=tmp_path / "reports",
        run_id="v2_13_a_blocked",
        command="test command",
        env={},
        fetch_json=_fetch_json,
    )

    assert report["overall_status"] == "BLOCKED"
    assert report["network_used"] is False
    assert (tmp_path / "reports" / validator.BLOCKED_MARKER).exists()


def test_v2_13_a_cli_prints_no_secret_values(tmp_path: Path, capsys, monkeypatch):
    monkeypatch.setenv("AEGIS_FINNHUB_API_KEY", "unit-finnhub-key")

    def fake_run_acceptance(**_kwargs):
        return {
            "overall_status": "PASS",
            "summary": {"quote_status": "pass", "social_sentiment_status": "blocked_plan_or_rate_limit"},
        }

    monkeypatch.setattr(validator, "run_acceptance", fake_run_acceptance)
    exit_code = validator.main(
        [
            "--output-root",
            str(tmp_path / "processed"),
            "--reports-dir",
            str(tmp_path / "reports"),
            "--run-id",
            "v2_13_a_cli",
        ]
    )
    captured = capsys.readouterr()

    assert exit_code in {0, 1, 2}
    assert "unit-finnhub-key" not in captured.out
