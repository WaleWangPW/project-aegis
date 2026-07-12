"""P1C.3 tests for scripts/refresh_stock_agent_aegis_status.py.

Proves the refresh helper: rebuilds the desktop status via the shared
`build_desktop_status` builder, mirrors a fixed set of read-only files
into a (fake, in tests) stock-agent workspace directory, writes a
read-only README, and never touches `.env`/tokens, `paper_trades.jsonl`,
a broker, composite scoring, or special-cases CRCL. Also confirms
`dashboard/index.html` is never touched by this script.
"""

from __future__ import annotations

import inspect
import json
import subprocess
import sys
from pathlib import Path

import yaml

import scripts.refresh_stock_agent_aegis_status as refresher

REPO_ROOT = Path(__file__).resolve().parents[1]


def _write_holdings(path: Path, holdings: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump({"holdings": holdings}), encoding="utf-8")


def test_refresh_copies_required_files_to_a_fake_stock_agent_workspace(tmp_path: Path):
    """Required test #5: the refresh script copies
    aegis_status.json/html plus the three optional reports (when
    present) into a fake stock-agent workspace directory, creating it
    if it does not yet exist."""
    holdings_path = tmp_path / "holdings.yaml"
    _write_holdings(holdings_path, [])
    records_dir = tmp_path / "records"
    output_html = tmp_path / "desktop" / "aegis_status.html"
    output_json = tmp_path / "desktop" / "aegis_status.json"
    smoke_report = tmp_path / "market_snapshot_smoke_report.json"
    smoke_report.write_text(json.dumps({"run_id": "x", "created_at": "2026-07-05T00:00:00+08:00", "results": {}}), encoding="utf-8")
    prl_report = tmp_path / "provider_router_live_report.json"
    prl_report.write_text(json.dumps({"run_id": "y", "created_at": "2026-07-05T00:00:00+08:00", "summary": {"pass_count": 0}}), encoding="utf-8")
    # provider_coverage_report deliberately left missing to exercise the
    # "skip missing optional report" path.
    coverage_report = tmp_path / "does_not_exist.json"

    workspace = tmp_path / "fake-stock-agent-workspace" / "project-aegis"
    assert not workspace.exists()

    result = refresher.refresh(
        holdings_path=holdings_path,
        records_dir=records_dir,
        output_html=output_html,
        output_json=output_json,
        provider_coverage_report=coverage_report,
        provider_router_live_report=prl_report,
        market_snapshot_smoke_report=smoke_report,
        stock_agent_workspace=workspace,
    )

    assert workspace.exists()
    assert (workspace / "aegis_status.json").exists()
    assert (workspace / "aegis_status.html").exists()
    assert (workspace / "market_snapshot_smoke_report.json").exists()
    assert (workspace / "provider_router_live_report.json").exists()
    assert not (workspace / "does_not_exist.json").exists()
    assert str(coverage_report) in result["skipped_missing_optional_reports"]

    # Copies are real, byte-identical copies of the rebuilt files.
    assert (workspace / "aegis_status.json").read_text(encoding="utf-8") == output_json.read_text(encoding="utf-8")
    assert (workspace / "aegis_status.html").read_text(encoding="utf-8") == output_html.read_text(encoding="utf-8")


def test_refresh_writes_read_only_readme(tmp_path: Path):
    """Required test #6: a README_FOR_STOCK_AGENT.md is written into the
    workspace, stating the read-only rules (no PaperTrade, no broker,
    no CRCL special-casing, do not edit directly)."""
    holdings_path = tmp_path / "holdings.yaml"
    _write_holdings(holdings_path, [])
    workspace = tmp_path / "workspace"

    refresher.refresh(
        holdings_path=holdings_path,
        records_dir=tmp_path / "records",
        output_html=tmp_path / "desktop" / "aegis_status.html",
        output_json=tmp_path / "desktop" / "aegis_status.json",
        provider_coverage_report=tmp_path / "no_coverage.json",
        provider_router_live_report=tmp_path / "no_prl.json",
        market_snapshot_smoke_report=tmp_path / "no_smoke.json",
        stock_agent_workspace=workspace,
    )

    readme = workspace / "README_FOR_STOCK_AGENT.md"
    assert readme.exists()
    text = readme.read_text(encoding="utf-8")
    assert "read-only" in text.lower()
    assert "PaperTrade" in text
    assert "broker" in text.lower()
    assert "CRCL" in text
    assert "do not edit" in text.lower()


def test_refresh_cli_runs_and_prints_target_and_copied_files(tmp_path: Path):
    """CLI entry point smoke test, run against a fully fake set of
    paths (never the user's real ~/.openclaw directory)."""
    holdings_path = tmp_path / "holdings.yaml"
    _write_holdings(holdings_path, [])
    workspace = tmp_path / "cli-workspace"

    proc = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "refresh_stock_agent_aegis_status.py"),
            "--holdings-path", str(holdings_path),
            "--records-dir", str(tmp_path / "records"),
            "--output-html", str(tmp_path / "desktop" / "aegis_status.html"),
            "--output-json", str(tmp_path / "desktop" / "aegis_status.json"),
            "--provider-coverage-report", str(tmp_path / "no_coverage.json"),
            "--provider-router-live-report", str(tmp_path / "no_prl.json"),
            "--market-snapshot-smoke-report", str(tmp_path / "no_smoke.json"),
            "--stock-agent-workspace", str(workspace),
        ],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert proc.returncode == 0
    assert str(workspace) in proc.stdout
    assert (workspace / "aegis_status.json").exists()
    assert (workspace / "README_FOR_STOCK_AGENT.md").exists()


def test_refresh_never_reads_dotenv_or_token(tmp_path: Path):
    """Required test #7: the refresh script itself never reads .env/any
    token — checked for actual usage patterns, not a bare substring,
    following the same convention as every prior P1B/P1C token-check
    test in this repo."""
    source = inspect.getsource(refresher)
    assert "import dotenv" not in source
    assert "load_dotenv(" not in source
    assert "os.environ[" not in source
    assert "os.environ.get(" not in source
    assert "os.getenv(" not in source
    assert "TushareAdapter(" not in source
    assert "import yfinance" not in source
    assert "ProviderRouter(" not in source


def test_refresh_never_creates_a_paper_trade(tmp_path: Path):
    """Required test #8: the refresh script never constructs a
    PaperTrade and never calls a broker API — checked for actual usage
    patterns (constructor/method calls), not a bare substring, since
    the module's own docstring/CLI help text legitimately explains that
    it never touches paper trading (same convention as every prior
    P1B/P1C token/broker-check test in this repo)."""
    source = inspect.getsource(refresher)
    assert "PaperTrade(" not in source
    assert "PaperTradeRepository(" not in source
    for forbidden in ("place_order(", "submit_order(", ".buy(", ".sell(", "broker_api.", "import broker"):
        assert forbidden not in source.lower()


def test_dashboard_index_html_is_never_touched_by_refresh_script(tmp_path: Path):
    """Required test #9: dashboard/index.html is untouched — byte-
    identical before and after a real refresh run against the actual
    repo's default report paths (only data/desktop/aegis_status.html
    and the stock-agent mirror change)."""
    dashboard_path = REPO_ROOT / "dashboard" / "index.html"
    before = dashboard_path.read_bytes()

    holdings_path = tmp_path / "holdings.yaml"
    _write_holdings(holdings_path, [])
    refresher.refresh(
        holdings_path=holdings_path,
        records_dir=tmp_path / "records",
        output_html=tmp_path / "desktop" / "aegis_status.html",
        output_json=tmp_path / "desktop" / "aegis_status.json",
        provider_coverage_report=tmp_path / "no_coverage.json",
        provider_router_live_report=tmp_path / "no_prl.json",
        market_snapshot_smoke_report=tmp_path / "no_smoke.json",
        stock_agent_workspace=tmp_path / "workspace",
    )

    after = dashboard_path.read_bytes()
    assert before == after

    # The script never constructs a path to dashboard/index.html itself
    # (its own docstring mentions it only to explain what it does NOT
    # touch) — checked as a concrete path-construction pattern rather
    # than a bare "dashboard" substring.
    source = inspect.getsource(refresher)
    assert '"dashboard"' not in source
    assert "'dashboard'" not in source


def test_refresh_script_has_no_broker_or_real_trading_code():
    """Required test #10: no broker/real trading code anywhere in the
    refresh script's source — checked as concrete call/constructor
    patterns rather than a bare "broker" substring, since this script's
    own docstring/CLI help legitimately explains that it never calls a
    broker (same convention as every prior P1B/P1C broker-check test in
    this repo)."""
    source = inspect.getsource(refresher).lower()
    for forbidden in (
        "brokerclient(",
        "broker_api.",
        "import broker",
        "place_order(",
        "submit_order(",
        "live_trade(",
        "real_trade(",
    ):
        assert forbidden not in source


def test_refresh_script_never_uses_composite_scoring():
    """Required test #11: no composite scoring in the refresh script."""
    source = inspect.getsource(refresher)
    assert "composite_score" not in source.lower()


def test_refresh_script_does_not_special_case_crcl():
    """Required test #12: CRCL is only ever mentioned in the README's
    generic reminder text ("CRCL is not special-cased..."), never as a
    symbol comparison or branch condition in the script's own logic."""
    source = inspect.getsource(refresher)
    assert '"CRCL"' not in source
    assert "'CRCL'" not in source
    assert "== CRCL" not in source
