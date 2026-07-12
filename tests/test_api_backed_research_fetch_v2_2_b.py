from __future__ import annotations

import json
from pathlib import Path

import pytest

import scripts.validate_v2_2_b_api_backed_research_fetch as validator
from aegis.external_sources.api_fetcher import APIFetchError, fetch_external_api_summary


def test_api_fetch_uses_env_value_but_serializes_only_env_name():
    item = fetch_external_api_summary(
        spec=validator._approved_research_api(),
        endpoint_path="/strategy-notes",
        query={"market": "A"},
        env={"AEGIS_RESEARCH_API_KEY": validator._FIXTURE_SECRET},
        fetch_fn=validator._fixture_fetch,
    )
    payload = json.dumps(item.model_dump(), ensure_ascii=False)

    assert item.status_code == 200
    assert item.auth_env_vars_used == ["AEGIS_RESEARCH_API_KEY"]
    assert item.raw_bytes_stored is False
    assert item.request_headers_stored is False
    assert validator._FIXTURE_SECRET not in payload
    assert "secret_values_not_stored" in item.safety_notes


def test_api_fetch_requires_env_var_for_env_auth():
    with pytest.raises(APIFetchError):
        fetch_external_api_summary(
            spec=validator._approved_research_api(),
            endpoint_path="/strategy-notes",
            env={},
            fetch_fn=validator._fixture_fetch,
        )


def test_api_fetch_denies_broker_connector():
    with pytest.raises(APIFetchError):
        fetch_external_api_summary(
            spec=validator._forbidden_broker_api(),
            endpoint_path="/orders",
            env={"BROKER_API_KEY": validator._FIXTURE_SECRET},
            fetch_fn=validator._fixture_fetch,
        )


def test_v2_2_b_acceptance_writes_marker_hashes_and_reports(tmp_path: Path):
    report = validator.run_acceptance(
        output_root=tmp_path / "processed",
        reports_dir=tmp_path / "reports",
        run_id="v2_2_b_test",
        command="test command",
    )

    assert report["overall_status"] == "PASS"
    assert report["checks"]["approved_api_fetch_succeeded"] is True
    assert report["checks"]["secret_value_not_serialized"] is True
    assert report["checks"]["broker_api_denied"] is True
    assert report["production_records_written"] is False
    assert report["hashes"]["api_fetch_item_json"]
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()
    payload = json.loads((tmp_path / "reports" / validator.REPORT_JSON).read_text(encoding="utf-8"))
    assert payload["summary"]["next_target"] == "V2.2-C API Research To Sandbox Candidate Bridge"


def test_v2_2_b_cli_exits_zero_and_prints_no_secret_value(tmp_path: Path, capsys):
    exit_code = validator.main(
        [
            "--output-root",
            str(tmp_path / "processed"),
            "--reports-dir",
            str(tmp_path / "reports"),
            "--run-id",
            "v2_2_b_cli",
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "PASS" in captured.out
    assert validator._FIXTURE_SECRET not in captured.out
    assert "secret" not in captured.out.lower()
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()
