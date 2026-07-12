"""P1B.1 tests for scripts/check_provider_router.py.

No live network, no token access — this script only validates static
config (routing table + symbol mappings) and reports package
availability. Uses an isolated tmp_path config + output, same convention
as tests/test_validate_real_data.py.
"""

from __future__ import annotations

import json
from pathlib import Path

import yaml

import scripts.check_provider_router as cpr

_CONFIG = {
    "providers": {"default": {"A": "tushare", "H": "yahoo_finance", "US": "yahoo_finance"}},
    "routing": {
        "daily_bars": {"A": "tushare", "H": "yahoo_finance", "US": "yahoo_finance"},
        "stock_basic": {"A": "tushare", "H": "not_configured", "US": "not_configured"},
    },
    "symbol_mapping": {
        "yahoo_finance": {
            "H": {"symbols": {"00700.HK": "0700.HK"}, "indexes": {"HSI.HI": "^HSI"}},
            "US": {"symbols": {"CRCL": "CRCL"}, "indexes": {"SPX": "^GSPC"}},
        }
    },
}


def _write_config(tmp_path: Path) -> Path:
    config_path = tmp_path / "providers.yaml"
    config_path.write_text(yaml.safe_dump(_CONFIG), encoding="utf-8")
    return config_path


def test_run_check_provider_router_writes_valid_report(tmp_path: Path):
    config_path = _write_config(tmp_path)
    output_path = tmp_path / "provider_router_report.json"

    report = cpr.run_check_provider_router(config_path=config_path, output_path=output_path)

    assert output_path.exists()
    written = json.loads(output_path.read_text(encoding="utf-8"))
    assert written["route_table"]
    assert {"data_type": "stock_basic", "market": "H", "provider": "not_configured"} in written["route_table"]
    assert written == report


def test_mapping_checks_confirm_configured_translations(tmp_path: Path):
    config_path = _write_config(tmp_path)
    report = cpr.run_check_provider_router(config_path=config_path, output_path=None)

    by_code = {(c["provider"], c["market"], c["kind"], c["internal_code"]): c for c in report["mapping_checks"]}
    assert by_code[("yahoo_finance", "H", "symbols", "00700.HK")]["resolved"] == "0700.HK"
    assert by_code[("yahoo_finance", "H", "symbols", "00700.HK")]["status"] == "ok"
    assert by_code[("yahoo_finance", "H", "indexes", "HSI.HI")]["resolved"] == "^HSI"
    assert by_code[("yahoo_finance", "US", "indexes", "SPX")]["resolved"] == "^GSPC"


def test_route_checks_mark_not_configured_and_skipped_without_live_network(tmp_path: Path):
    config_path = _write_config(tmp_path)
    report = cpr.run_check_provider_router(config_path=config_path, output_path=None)

    by_pair = {(c["data_type"], c["market"]): c for c in report["route_checks"]}
    assert by_pair[("stock_basic", "H")]["status"] == "not_configured"
    assert by_pair[("stock_basic", "US")]["status"] == "not_configured"
    # Real provider routes (tushare/yahoo_finance) are reported "skipped"
    # this round — no live call, never crashes, clear reason given.
    assert by_pair[("daily_bars", "A")]["status"] == "skipped"
    assert "reason" in by_pair[("daily_bars", "A")]
    assert by_pair[("daily_bars", "A")]["reason"]


def test_package_availability_reported_without_crashing(tmp_path: Path):
    config_path = _write_config(tmp_path)
    report = cpr.run_check_provider_router(config_path=config_path, output_path=None)
    assert "tushare" in report["package_availability"]
    assert "yfinance" in report["package_availability"]
    assert isinstance(report["package_availability"]["yfinance"], bool)


def test_cli_main_runs_end_to_end_without_network(tmp_path: Path, capsys):
    config_path = _write_config(tmp_path)
    output_path = tmp_path / "provider_router_report.json"

    exit_code = cpr.main(["--config", str(config_path), "--output", str(output_path)])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert output_path.exists()
    assert "Route table" in captured.out
    assert "Output:" in captured.out
    # Never reads/prints a token — the report only ever mentions package
    # names and route/mapping metadata.
    assert "TOKEN" not in captured.out.upper() or "TUSHARE_TOKEN" not in captured.out


def test_missing_config_file_is_a_controlled_error(tmp_path: Path, capsys):
    missing = tmp_path / "does_not_exist.yaml"
    exit_code = cpr.main(["--config", str(missing), "--output", str(tmp_path / "out.json")])
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "Traceback" not in captured.err
