from __future__ import annotations

import json
from pathlib import Path

from aegis.external_sources.eodhd_twelve_provider_probe import (
    build_eodhd_twelve_provider_probe_report,
    probe_provider_case,
)
import scripts.validate_v2_12_a_eodhd_twelve_h_us_provider_probe as validator


def _fetch_json(url: str):
    if "eodhd.com" in url:
        return 200, [{"date": "2026-07-01", "close": 100.0}]
    if "twelvedata.com" in url and "exchange=HKEX" in url:
        raise RuntimeError("upstream plan does not allow HKEX")
    return 200, {"status": "ok", "values": [{"datetime": "2026-07-01", "close": "100.0"}]}


def test_v2_12_a_blocks_missing_env_without_fetch():
    result = probe_provider_case(
        {"provider": "eodhd", "market": "US", "symbol": "AAPL.US", "data_type": "daily_bars"},
        env={},
        fetch_json=_fetch_json,
    )

    assert result["status"] == "blocked_missing_env"
    assert result["token_value_stored"] is False
    assert result["request_url_stored"] is False


def test_v2_12_a_builds_secret_safe_provider_report():
    report = build_eodhd_twelve_provider_probe_report(
        run_id="unit",
        env={"AEGIS_EODHD_API_TOKEN": "unit-eod", "AEGIS_TWELVE_DATA_API_KEY": "unit-td"},
        fetch_json=_fetch_json,
    )
    text = json.dumps(report, ensure_ascii=False)

    assert report["overall_status"] == "PASS"
    assert report["summary"]["pass_count"] == 3
    assert report["summary"]["fail_count"] == 1
    assert report["checks"]["eodhd_h_passed"] is True
    assert report["checks"]["twelve_data_us_passed"] is True
    assert "unit-eod" not in text
    assert "unit-td" not in text
    assert "api_token" not in text
    assert "apikey" not in text


def test_v2_12_a_validator_writes_report_and_marker(tmp_path: Path):
    report = validator.run_acceptance(
        output_root=tmp_path / "processed",
        reports_dir=tmp_path / "reports",
        run_id="v2_12_a_test",
        command="test command",
        env={"AEGIS_EODHD_API_TOKEN": "unit-eod", "AEGIS_TWELVE_DATA_API_KEY": "unit-td"},
        fetch_json=_fetch_json,
    )

    assert report["overall_status"] == "PASS"
    assert report["summary"]["pass_count"] == 3
    assert report["hashes"]["run_report_json"]
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()


def test_v2_12_a_cli_exits_zero_and_prints_no_secret_values(tmp_path: Path, capsys, monkeypatch):
    monkeypatch.setenv("AEGIS_EODHD_API_TOKEN", "unit-eod")
    monkeypatch.setenv("AEGIS_TWELVE_DATA_API_KEY", "unit-td")
    exit_code = validator.main(
        [
            "--output-root",
            str(tmp_path / "processed"),
            "--reports-dir",
            str(tmp_path / "reports"),
            "--run-id",
            "v2_12_a_cli",
        ]
    )
    captured = capsys.readouterr()

    assert exit_code in {0, 1}
    assert "unit-eod" not in captured.out
    assert "unit-td" not in captured.out
