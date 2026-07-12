"""P1C tests for scripts/aegis_agent_gateway.py.

Proves the gateway's allowed commands work and return valid JSON,
forbidden commands are refused with a structured JSON error and
non-zero exit code, unknown commands fail closed, and the gateway
never touches .env/tokens, never creates a PaperTrade, and never
special-cases CRCL.
"""

from __future__ import annotations

import inspect
import json
from pathlib import Path

import pytest
import yaml

import scripts.aegis_agent_gateway as gateway_module
from scripts.aegis_agent_gateway import ALLOWED_COMMANDS, FORBIDDEN_COMMANDS, dispatch

REPO_ROOT = Path(__file__).resolve().parents[1]


def _write_holdings(path: Path, holdings: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump({"holdings": holdings}), encoding="utf-8")


def _dispatch_kwargs(tmp_path: Path) -> dict:
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


@pytest.mark.parametrize("command", sorted(ALLOWED_COMMANDS))
def test_every_allowed_command_returns_ok_json_and_exit_zero(tmp_path: Path, command: str):
    _write_holdings(tmp_path / "holdings.yaml", [])
    result, exit_code = dispatch(command, **_dispatch_kwargs(tmp_path))
    assert exit_code == 0
    assert result["ok"] is True
    # P1C.1: `desktop-page` deliberately returns a flat
    # {"ok", "path", "absolute_path", "open_command"} shape instead of the
    # {"ok", "command", "data"} wrapper every other command uses.
    if command == "desktop-page":
        assert set(result.keys()) == {"ok", "path", "absolute_path", "open_command"}
    else:
        assert result["command"] == command
        assert "data" in result
    # Must be JSON-serializable end to end (this is what actually goes to stdout).
    json.dumps(result, default=str)


@pytest.mark.parametrize("command", sorted(FORBIDDEN_COMMANDS))
def test_every_forbidden_command_is_refused_with_nonzero_exit(tmp_path: Path, command: str):
    result, exit_code = dispatch(command, **_dispatch_kwargs(tmp_path))
    assert exit_code == 1
    assert result["ok"] is False
    assert result["error"] == "forbidden_command"
    assert result["command"] == command


@pytest.mark.parametrize("command", ["Buy", "SELL", "Create-Paper-Trade"])
def test_forbidden_commands_are_matched_case_insensitively(tmp_path: Path, command: str):
    result, exit_code = dispatch(command, **_dispatch_kwargs(tmp_path))
    assert exit_code == 1
    assert result["error"] == "forbidden_command"


def test_unknown_command_fails_closed_not_silently_accepted(tmp_path: Path):
    result, exit_code = dispatch("frobnicate", **_dispatch_kwargs(tmp_path))
    assert exit_code == 1
    assert result["ok"] is False
    assert result["error"] == "unknown_command"


def test_holdings_command_returns_real_holdings(tmp_path: Path):
    _write_holdings(
        tmp_path / "holdings.yaml",
        [{
            "holding_id": "hold_US_CRCL_20260701", "symbol": "CRCL", "market": "US",
            "shares": 254, "avg_cost": 109.157, "currency": "USD", "status": "open",
        }],
    )
    result, exit_code = dispatch("holdings", **_dispatch_kwargs(tmp_path))
    assert exit_code == 0
    assert result["data"]["count"] == 1
    assert result["data"]["holdings"][0]["symbol"] == "CRCL"


def test_market_snapshot_smoke_command_is_read_only_and_notes_it(tmp_path: Path):
    smoke_path = tmp_path / "no_smoke.json"
    smoke_path.write_text(json.dumps({"run_id": "x", "results": {}}), encoding="utf-8")
    result, exit_code = dispatch("market-snapshot-smoke", **_dispatch_kwargs(tmp_path))
    assert exit_code == 0
    assert "note" in result
    assert "does not trigger a new run" in result["note"]


def test_desktop_page_command_writes_files(tmp_path: Path):
    _write_holdings(tmp_path / "holdings.yaml", [])
    kwargs = _dispatch_kwargs(tmp_path)
    result, exit_code = dispatch("desktop-page", **kwargs)
    assert exit_code == 0
    assert kwargs["output_html"].exists()
    assert kwargs["output_json"].exists()
    # P1C.1: flat shape with path/absolute_path/open_command, per
    # docs/P1C1_OPENCLAW_FEISHU_READONLY_SETUP.md's required schema.
    assert result["ok"] is True
    assert result["absolute_path"] == str(kwargs["output_html"].resolve())
    assert result["open_command"].startswith("open ")
    assert "path" in result


def test_summary_command_is_condensed(tmp_path: Path):
    _write_holdings(tmp_path / "holdings.yaml", [])
    result, exit_code = dispatch("summary", **_dispatch_kwargs(tmp_path))
    assert exit_code == 0
    data = result["data"]
    assert set(data.keys()) == {
        "generated_at", "coverage", "holdings_count", "recommendations_count",
        "paper_trading", "review_count", "data_gaps_count", "next_operational_action",
    }


def test_cli_main_buy_returns_exit_one(tmp_path: Path, capsys):
    exit_code = gateway_module.main([
        "buy",
        "--holdings-path", str(tmp_path / "holdings.yaml"),
        "--records-dir", str(tmp_path / "records"),
        "--provider-coverage-report", str(tmp_path / "no_coverage.json"),
        "--provider-router-live-report", str(tmp_path / "no_report.json"),
        "--market-snapshot-smoke-report", str(tmp_path / "no_smoke.json"),
        "--provider-diagnostics-report", str(tmp_path / "no_diag.json"),
        "--output-html", str(tmp_path / "desktop" / "aegis_status.html"),
        "--output-json", str(tmp_path / "desktop" / "aegis_status.json"),
    ])
    assert exit_code == 1
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert payload["error"] == "forbidden_command"


def test_cli_main_status_returns_exit_zero(tmp_path: Path, capsys):
    _write_holdings(tmp_path / "holdings.yaml", [])
    exit_code = gateway_module.main([
        "status",
        "--holdings-path", str(tmp_path / "holdings.yaml"),
        "--records-dir", str(tmp_path / "records"),
        "--provider-coverage-report", str(tmp_path / "no_coverage.json"),
        "--provider-router-live-report", str(tmp_path / "no_report.json"),
        "--market-snapshot-smoke-report", str(tmp_path / "no_smoke.json"),
        "--provider-diagnostics-report", str(tmp_path / "no_diag.json"),
        "--output-html", str(tmp_path / "desktop" / "aegis_status.html"),
        "--output-json", str(tmp_path / "desktop" / "aegis_status.json"),
    ])
    assert exit_code == 0
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert payload["ok"] is True


def test_cli_main_desktop_page_returns_open_command(tmp_path: Path, capsys):
    _write_holdings(tmp_path / "holdings.yaml", [])
    exit_code = gateway_module.main([
        "desktop-page",
        "--holdings-path", str(tmp_path / "holdings.yaml"),
        "--records-dir", str(tmp_path / "records"),
        "--provider-coverage-report", str(tmp_path / "no_coverage.json"),
        "--provider-router-live-report", str(tmp_path / "no_report.json"),
        "--market-snapshot-smoke-report", str(tmp_path / "no_smoke.json"),
        "--provider-diagnostics-report", str(tmp_path / "no_diag.json"),
        "--output-html", str(tmp_path / "desktop" / "aegis_status.html"),
        "--output-json", str(tmp_path / "desktop" / "aegis_status.json"),
    ])
    assert exit_code == 0
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert payload["ok"] is True
    assert "open_command" in payload
    assert "path" in payload
    assert "absolute_path" in payload


def test_forbidden_commands_set_matches_task_spec():
    assert FORBIDDEN_COMMANDS == {
        "buy", "sell", "trade", "order", "broker", "auto-trade", "rebalance",
        "paper-buy", "paper-sell", "create-paper-trade",
        "modify-decision", "modify-recommendation",
    }


def test_allowed_commands_set_matches_task_spec():
    assert ALLOWED_COMMANDS == {
        "status", "holdings", "recommendations", "paper-summary", "review-summary",
        "provider-report", "provider-router-report", "market-snapshot-smoke",
        "data-gaps", "desktop-page", "summary",
    }


def test_dashboard_index_html_unchanged():
    repo_dashboard = REPO_ROOT / "dashboard" / "index.html"
    vault_dashboard = REPO_ROOT.parent / "dashboard" / "index.html"
    assert repo_dashboard.read_text(encoding="utf-8") == vault_dashboard.read_text(encoding="utf-8")


def test_gateway_never_touches_dotenv_or_token_or_broker():
    source = inspect.getsource(gateway_module)
    assert "import dotenv" not in source
    assert "load_dotenv(" not in source
    assert "os.environ[" not in source
    assert "os.environ.get(" not in source
    assert "os.getenv(" not in source
    assert "TushareAdapter" not in source
    assert "yfinance" not in source


def test_gateway_never_constructs_a_paper_trade_object():
    source = inspect.getsource(gateway_module)
    assert "PaperTrade(" not in source
    assert "PaperTradeRepository(" not in source or ".append(" not in source


def test_gateway_does_not_special_case_crcl():
    # CRCL is legitimately *mentioned* in this module's docstring/comments
    # to explain that it deliberately does NOT special-case it — check for
    # actual conditional/special-case logic instead of a bare substring
    # (same convention as the P1B.4 CRCL non-special-casing tests).
    source = inspect.getsource(gateway_module)
    assert '"CRCL"' not in source
    assert "'CRCL'" not in source
    assert "== CRCL" not in source
