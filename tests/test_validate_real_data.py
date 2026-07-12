"""P1A tests for scripts/validate_real_data.py — CLI-level.

Fake provider only, isolated tmp_path output, no real Tushare/network.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

import scripts.validate_real_data as vrd


class _FakeProvider:
    def get_daily_bars(self, symbol, market, start, end):
        return pd.DataFrame({"trade_date": ["20260601"], "close": [10.0], "vol": [1000.0]})

    def get_index_bars(self, index_code, market, start, end):
        return pd.DataFrame({"trade_date": ["20260601"], "close": [10.0], "vol": [1000.0]})

    def get_stock_basic(self, market):
        # Per-market-distinct row counts — a genuinely healthy provider,
        # not the "H/US silently reuse A股 data" bug P1A.1 hardens
        # against (see tests/test_provider_diagnostics.py).
        sizes = {"A": 40, "H": 25, "US": 60}
        n = sizes.get(market, 10)
        return pd.DataFrame([{"symbol": f"{market}-{i}"} for i in range(n)])

    def get_sector_classification(self, market):
        return pd.DataFrame([{"index_code": "801010.SI"}])

    def get_fundamentals(self, symbol, market, as_of):
        return pd.DataFrame([{"pe_ratio": 18.4}])

    def get_trading_calendar(self, market, start, end):
        return pd.DataFrame({"cal_date": ["20260601"], "is_open": [1]})


def test_validate_real_data_cli_missing_token_exits_cleanly(monkeypatch, capsys, tmp_path: Path):
    monkeypatch.delenv("TUSHARE_TOKEN", raising=False)
    # Prevent load_dotenv() from picking up a real .env: python-dotenv's
    # bare load_dotenv() walks up from the *calling module's* file
    # location, not from process cwd, so monkeypatch.chdir(tmp_path) alone
    # does not isolate this test from a real .env that may exist in the
    # repo root (P1A.1 discovered this repo now has one, written by the
    # user's own local real-token run — never read/printed here). Patch
    # load_dotenv itself so this test's missing-token assertion is
    # deterministic regardless of what's actually on disk.
    monkeypatch.setattr("aegis.data.live_validation.load_dotenv", lambda *a, **k: None)
    monkeypatch.chdir(tmp_path)

    output_path = tmp_path / "report.json"
    exit_code = vrd.main(["--markets", "A", "--output", str(output_path)])
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "TUSHARE_TOKEN" in captured.err
    assert "missing" in captured.err.lower()
    assert "Traceback" not in captured.err
    # Even on the missing-token path, a report is still written (an
    # honest, all-skipped/empty one) — never silently nothing.
    assert output_path.exists()
    written = json.loads(output_path.read_text(encoding="utf-8"))
    assert written["token_present"] is False


def test_validate_real_data_cli_writes_report_with_fake_provider(tmp_path: Path):
    output_path = tmp_path / "provider_coverage_report.json"

    report = vrd.run_validate_real_data(
        markets=["A", "H", "US"],
        date="2026-07-04",
        output_path=output_path,
        env={"TUSHARE_TOKEN": "fake-token"},
        provider=_FakeProvider(),
    )

    assert output_path.exists()
    written = json.loads(output_path.read_text(encoding="utf-8"))
    assert written["run_id"] == report.run_id
    assert written["token_present"] is True
    assert written["network_available"] is True
    assert len(written["checks"]) == len(report.checks)
    assert written["summary"]["pass_count"] == len(report.checks)


def test_validate_real_data_cli_rejects_unknown_market():
    import pytest

    with pytest.raises(vrd.ValidateRealDataArgumentError):
        vrd.run_validate_real_data(markets=["ZZ"], output_path="unused.json", provider=_FakeProvider())
