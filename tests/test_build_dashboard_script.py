"""Phase 5 tests for scripts/build_dashboard.py — PHASE5 doc §10.3."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import scripts.build_dashboard as bds
from aegis.dashboard.schema import validate_dashboard_payload

HOLDINGS_YAML = """
holdings:
  - holding_id: hold_US_CRCL_20260701
    symbol: CRCL
    name: Circle Internet Group
    market: US
    shares: 254
    avg_cost: 109.157
    currency: USD
    entry_date: "2026-07-01"
    status: open
    notes: "test fixture"
"""


def test_script_writes_dashboard_json_from_temp_records_dir(tmp_path: Path):
    records_dir = tmp_path / "records"
    holdings_config = tmp_path / "holdings.yaml"
    holdings_config.write_text(HOLDINGS_YAML, encoding="utf-8")
    output_path = tmp_path / "dashboard" / "dashboard_data.json"

    result_path = bds.build_dashboard(
        date="2026-07-04",
        session="pre_market",
        records_dir=records_dir,
        holdings_config=holdings_config,
        output_path=output_path,
    )

    assert result_path == output_path
    assert output_path.exists()
    written = json.loads(output_path.read_text(encoding="utf-8"))
    assert written["date"] == "2026-07-04"


def test_invalid_output_path_is_handled_as_controlled_failure_via_cli(tmp_path: Path, capsys):
    # A missing holdings config or empty records dir are both handled
    # gracefully (no holdings configured / DATA_GAP snapshots) — not real
    # failures. A genuine failure case is an output path whose parent
    # cannot be created as a directory (it already exists as a file).
    records_dir = tmp_path / "records"
    holdings_config = tmp_path / "does_not_exist.yaml"
    blocked_output_dir = tmp_path / "dashboard_is_actually_a_file"
    blocked_output_dir.write_text("not a directory", encoding="utf-8")
    output_path = blocked_output_dir / "dashboard_data.json"

    exit_code = bds.main(
        [
            "--date",
            "2026-07-04",
            "--records-dir",
            str(records_dir),
            "--holdings-config",
            str(holdings_config),
            "--output",
            str(output_path),
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "Dashboard build failed" in captured.err


def test_output_json_validates_against_schema(tmp_path: Path):
    records_dir = tmp_path / "records"
    holdings_config = tmp_path / "holdings.yaml"
    holdings_config.write_text(HOLDINGS_YAML, encoding="utf-8")
    output_path = tmp_path / "dashboard" / "dashboard_data.json"

    bds.build_dashboard(
        date="2026-07-04",
        session="pre_market",
        records_dir=records_dir,
        holdings_config=holdings_config,
        output_path=output_path,
    )

    written = json.loads(output_path.read_text(encoding="utf-8"))
    validated = validate_dashboard_payload(written)
    assert validated["date"] == "2026-07-04"


def test_cli_prints_output_path_on_success(tmp_path: Path, capsys):
    records_dir = tmp_path / "records"
    holdings_config = tmp_path / "holdings.yaml"
    holdings_config.write_text(HOLDINGS_YAML, encoding="utf-8")
    output_path = tmp_path / "dashboard" / "dashboard_data.json"

    exit_code = bds.main(
        [
            "--date",
            "2026-07-04",
            "--records-dir",
            str(records_dir),
            "--holdings-config",
            str(holdings_config),
            "--output",
            str(output_path),
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert str(output_path) in captured.out
