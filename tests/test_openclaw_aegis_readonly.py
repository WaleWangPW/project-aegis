"""P1C.1 tests for scripts/openclaw_aegis_readonly.py.

Proves the OpenClaw/Feishu text-command adapter correctly maps
`"aegis <command>"` strings onto scripts.aegis_agent_gateway.dispatch(),
has no allow/forbid logic of its own (forbidden commands are still
refused, by the gateway), fails closed on malformed input, and never
touches .env/tokens/broker/PaperTrade/CRCL special-casing.
"""

from __future__ import annotations

import inspect
import json
from pathlib import Path

import pytest
import yaml

import scripts.openclaw_aegis_readonly as adapter
from scripts.openclaw_aegis_readonly import OpenClawCommandError, parse_command, run_command

REPO_ROOT = Path(__file__).resolve().parents[1]


def _write_holdings(path: Path, holdings: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump({"holdings": holdings}), encoding="utf-8")


def _run_kwargs(tmp_path: Path) -> dict:
    return dict(
        holdings_path=tmp_path / "holdings.yaml",
        records_dir=tmp_path / "records",
        provider_coverage_report=tmp_path / "no_coverage.json",
        provider_router_live_report=tmp_path / "no_report.json",
        market_snapshot_smoke_report=tmp_path / "no_smoke.json",
        provider_diagnostics_report=tmp_path / "no_diag.json",
        output_html=tmp_path / "desktop" / "aegis_status.html",
        output_json=tmp_path / "desktop" / "aegis_status.json",
    )


@pytest.mark.parametrize(
    "text,expected_command",
    [
        ("aegis status", "status"),
        ("  aegis   holdings  ", "holdings"),
        ("aegis desktop-page", "desktop-page"),
        ("aegis data-gaps", "data-gaps"),
    ],
)
def test_parse_command_extracts_gateway_command(text: str, expected_command: str):
    assert parse_command(text) == expected_command


def test_parse_command_matches_aegis_prefix_case_insensitively(tmp_path: Path):
    # parse_command itself preserves the extracted command's case (it's a
    # pure text splitter) — case-insensitive matching of the *command*
    # happens one layer down, in scripts.aegis_agent_gateway.dispatch()'s
    # own `.strip().lower()` normalization. Verified end to end here via
    # run_command rather than asserting a specific parse_command return
    # value.
    assert parse_command("AEGIS STATUS").strip().lower() == "status"
    result, exit_code = run_command("AEGIS STATUS", **_run_kwargs(tmp_path))
    assert exit_code == 0
    assert result["ok"] is True


@pytest.mark.parametrize("text", ["hello world", "", "status", "aegis"])
def test_parse_command_rejects_text_without_aegis_prefix(text: str):
    with pytest.raises(OpenClawCommandError):
        parse_command(text)


def test_run_command_fails_closed_when_command_text_is_blank_after_prefix(tmp_path: Path):
    # "aegis   " (only whitespace after the prefix) extracts an empty
    # command string, which the gateway then rejects as `unknown_command`
    # — a different error code than `invalid_command_text`, but still a
    # non-zero exit, never a silently-accepted no-op.
    result, exit_code = run_command("aegis   ", **_run_kwargs(tmp_path))
    assert exit_code == 1
    assert result["ok"] is False


def test_run_command_maps_allowed_command_to_gateway_result(tmp_path: Path):
    """Required test #8: the adapter maps an allowed command
    (`"aegis status"`) onto the gateway and returns its ok result
    unmodified."""
    _write_holdings(tmp_path / "holdings.yaml", [])
    result, exit_code = run_command("aegis status", **_run_kwargs(tmp_path))
    assert exit_code == 0
    assert result["ok"] is True
    assert result["command"] == "status"


def test_run_command_maps_desktop_page_to_flat_gateway_shape(tmp_path: Path):
    _write_holdings(tmp_path / "holdings.yaml", [])
    result, exit_code = run_command("aegis desktop-page", **_run_kwargs(tmp_path))
    assert exit_code == 0
    assert result["ok"] is True
    assert set(result.keys()) == {"ok", "path", "absolute_path", "open_command"}


def test_run_command_still_refuses_forbidden_commands(tmp_path: Path):
    """The adapter has no allow/forbid logic of its own — forbidden
    commands must still be refused, by the gateway underneath it."""
    result, exit_code = run_command("aegis buy", **_run_kwargs(tmp_path))
    assert exit_code == 1
    assert result["ok"] is False
    assert result["error"] == "forbidden_command"


@pytest.mark.parametrize("command_text", ["aegis sell", "aegis trade", "aegis create-paper-trade", "aegis rebalance"])
def test_run_command_refuses_every_forbidden_command_variant(tmp_path: Path, command_text: str):
    result, exit_code = run_command(command_text, **_run_kwargs(tmp_path))
    assert exit_code == 1
    assert result["error"] == "forbidden_command"


def test_main_cli_status_returns_exit_zero(tmp_path: Path, monkeypatch, capsys):
    _write_holdings(tmp_path / "holdings.yaml", [])
    monkeypatch.setattr(adapter.build_desktop_status, "DEFAULT_HOLDINGS_PATH", tmp_path / "holdings.yaml")
    monkeypatch.setattr(adapter.build_desktop_status, "DEFAULT_RECORDS_DIR", tmp_path / "records")
    monkeypatch.setattr(adapter.build_desktop_status, "DEFAULT_PROVIDER_COVERAGE_REPORT", tmp_path / "no_coverage.json")
    monkeypatch.setattr(adapter.build_desktop_status, "DEFAULT_PROVIDER_ROUTER_LIVE_REPORT", tmp_path / "no_report.json")
    monkeypatch.setattr(adapter.build_desktop_status, "DEFAULT_MARKET_SNAPSHOT_SMOKE_REPORT", tmp_path / "no_smoke.json")
    monkeypatch.setattr(adapter.gateway, "DEFAULT_PROVIDER_DIAGNOSTICS_REPORT", tmp_path / "no_diag.json")
    monkeypatch.setattr(adapter.build_desktop_status, "DEFAULT_OUTPUT_HTML", tmp_path / "desktop" / "aegis_status.html")
    monkeypatch.setattr(adapter.build_desktop_status, "DEFAULT_OUTPUT_JSON", tmp_path / "desktop" / "aegis_status.json")

    exit_code = adapter.main(["aegis", "status"])
    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True


def test_main_cli_buy_returns_exit_one(tmp_path: Path, monkeypatch, capsys):
    monkeypatch.setattr(adapter.build_desktop_status, "DEFAULT_HOLDINGS_PATH", tmp_path / "holdings.yaml")
    monkeypatch.setattr(adapter.build_desktop_status, "DEFAULT_RECORDS_DIR", tmp_path / "records")
    monkeypatch.setattr(adapter.build_desktop_status, "DEFAULT_PROVIDER_COVERAGE_REPORT", tmp_path / "no_coverage.json")
    monkeypatch.setattr(adapter.build_desktop_status, "DEFAULT_PROVIDER_ROUTER_LIVE_REPORT", tmp_path / "no_report.json")
    monkeypatch.setattr(adapter.build_desktop_status, "DEFAULT_MARKET_SNAPSHOT_SMOKE_REPORT", tmp_path / "no_smoke.json")
    monkeypatch.setattr(adapter.gateway, "DEFAULT_PROVIDER_DIAGNOSTICS_REPORT", tmp_path / "no_diag.json")
    monkeypatch.setattr(adapter.build_desktop_status, "DEFAULT_OUTPUT_HTML", tmp_path / "desktop" / "aegis_status.html")
    monkeypatch.setattr(adapter.build_desktop_status, "DEFAULT_OUTPUT_JSON", tmp_path / "desktop" / "aegis_status.json")

    exit_code = adapter.main(["aegis", "buy"])
    assert exit_code == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is False
    assert payload["error"] == "forbidden_command"


def test_main_cli_invalid_command_text_fails_closed(capsys):
    exit_code = adapter.main(["hello", "world"])
    assert exit_code == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is False
    assert payload["error"] == "invalid_command_text"


def test_main_cli_missing_command_text_fails_closed(capsys):
    exit_code = adapter.main([])
    assert exit_code == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is False
    assert payload["error"] == "missing_command_text"


def test_dashboard_index_html_unchanged():
    repo_dashboard = REPO_ROOT / "dashboard" / "index.html"
    vault_dashboard = REPO_ROOT.parent / "dashboard" / "index.html"
    assert repo_dashboard.read_text(encoding="utf-8") == vault_dashboard.read_text(encoding="utf-8")


def test_adapter_never_touches_dotenv_or_token():
    # Check actual usage patterns, not a bare substring — the module's own
    # docstring legitimately *mentions* .env/tokens to explain what it
    # deliberately does NOT do (same convention as every other P1B/P1C
    # token-check test in this repo).
    source = inspect.getsource(adapter)
    assert "import dotenv" not in source
    assert "load_dotenv(" not in source
    assert "os.environ[" not in source
    assert "os.environ.get(" not in source
    assert "os.getenv(" not in source
    assert "TushareAdapter(" not in source
    assert "import yfinance" not in source
    assert "ProviderRouter(" not in source


def test_adapter_never_constructs_a_paper_trade_or_broker_call():
    source = inspect.getsource(adapter)
    assert "PaperTrade(" not in source
    for forbidden in ("place_order(", "submit_order(", ".buy(", ".sell(", "broker_api", "import broker"):
        assert forbidden not in source.lower()


def test_adapter_has_no_allow_or_forbid_logic_of_its_own():
    # The adapter must not hardcode its own allowed/forbidden command sets
    # — that logic belongs solely to scripts.aegis_agent_gateway.
    source = inspect.getsource(adapter)
    assert "ALLOWED_COMMANDS" not in source
    assert "FORBIDDEN_COMMANDS" not in source


def test_adapter_does_not_special_case_crcl():
    source = inspect.getsource(adapter)
    assert '"CRCL"' not in source
    assert "'CRCL'" not in source
    assert "== CRCL" not in source


def test_adapter_never_uses_composite_scoring():
    source = inspect.getsource(adapter)
    assert "composite_score" not in source.lower()
