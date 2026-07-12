from __future__ import annotations

import json
from pathlib import Path

import pytest

import scripts.validate_v2_0_f_official_source_fetcher as validator
from aegis.external_sources.fetcher import SourceFetchError, fetch_official_source_item


def test_official_source_fetcher_creates_summary_hash_and_blocks_raw_storage():
    item = fetch_official_source_item(
        source=validator._official_source(),
        symbol="AAPL",
        market="US",
        url="https://data.sec.gov/submissions/CIK0000320193.json",
        publisher="SEC",
        user_agent="ProjectAegis/0.1 test@example.com",
        fetch_fn=validator._fixture_fetch,
    )

    assert item.source_id == "src_sec_company_filings"
    assert item.summary
    assert item.content_hash
    assert item.raw_bytes_stored is False
    assert "no_cookie_header" in item.safety_notes
    assert "no_secret_header" in item.safety_notes


def test_official_source_fetcher_blocks_denied_source():
    with pytest.raises(SourceFetchError):
        fetch_official_source_item(
            source=validator._bloomberg_denied_source(),
            symbol="AAPL",
            market="US",
            url="https://example.com/paywalled",
            publisher="Bloomberg",
            user_agent="ProjectAegis/0.1 test@example.com",
            fetch_fn=validator._fixture_fetch,
        )


def test_v2_0_f_acceptance_writes_marker_and_reports(tmp_path: Path):
    report = validator.run_acceptance(
        output_root=tmp_path / "processed",
        reports_dir=tmp_path / "reports",
        run_id="v2_0_f_test",
        command="test command",
    )

    assert report["overall_status"] == "PASS"
    assert report["checks"]["official_source_fetched"] is True
    assert report["checks"]["denied_source_blocked"] is True
    assert report["checks"]["raw_bytes_not_stored"] is True
    assert report["network_used"] is False
    assert report["production_records_written"] is False
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()
    payload = json.loads((tmp_path / "reports" / validator.REPORT_JSON).read_text(encoding="utf-8"))
    assert payload["summary"]["source_id"] == "src_sec_company_filings"


def test_v2_0_f_cli_exits_zero_and_prints_no_secrets(tmp_path: Path, capsys):
    exit_code = validator.main(
        [
            "--output-root",
            str(tmp_path / "processed"),
            "--reports-dir",
            str(tmp_path / "reports"),
            "--run-id",
            "v2_0_f_cli",
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "PASS" in captured.out
    assert "token" not in captured.out.lower()
    assert "secret" not in captured.out.lower()
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()
